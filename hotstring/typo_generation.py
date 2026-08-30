import logging
import multiprocessing as mp
import os
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from logging.handlers import QueueHandler, QueueListener
from multiprocessing.context import BaseContext
from queue import Queue

import nltk
from multypo import MultiTypoGenerator

from .constants import (
    DEFAULT_HORIZONTAL_VS_VERTICAL,
    DEFAULT_ITERATIONS_PER_DISTRIBUTION,
    DEFAULT_LANGUAGE,
    DEFAULT_TYPO_RATE,
    DEFAULT_USE_EXCLUDING_SET,
)
from .logging import configure_root_logger
from .typing import (
    LoggingContext,
    NoisyWord,
    TriggerWord,
    TypoData,
    TypoDistribution,
    TypoDistributionLabel,
)

# Global variable to hold the worker logger instance
_WORKER_LOGGER: logging.Logger | None = None


def _worker_logger_initialization(
    logging_context: LoggingContext,
    proxy_queue: Queue[logging.LogRecord] | None,
    manager_logger_name: str | None,
) -> None:
    """Initialize logging inside a spawned worker process.

    The captured main-process logging state is applied first. When a proxy
    queue is supplied, a [`QueueHandler`][logging.handlers.QueueHandler] forwards worker records to the parent
    process. The function then creates the process-specific logger object, and
    assigns it to the global [`_WORKER_LOGGER`][] variable to be used by the worker code.

    Args:
        logging_context: Captured logging state from the parent process.
        proxy_queue: Optional multiprocessing queue that receives worker log
            records.
        manager_logger_name: Optional parent logger name used to namespace the
            worker logger.

    Notes:
        - We assume the `spawn` start method is used for spawning worker processes (see [`get_context`][multiprocessing.get_context] for details).
          Other process start methods are outside the assumptions of this initialization routine.
    """
    global _WORKER_LOGGER

    # 0. Apply the captured logging context to the current process
    logging_context.apply()

    if proxy_queue is not None:
        # 1. Create the QueueHandler with the proxy queue
        queue_handler = QueueHandler(proxy_queue)

        # 2. Get the root logger for this worker and add the QueueHandler to it
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)

    # 3. Create the specific child logger of the worker
    base_worker_logger_name = f"worker_{os.getpid()}"

    if not manager_logger_name:
        worker_logger_name = base_worker_logger_name
    else:
        worker_logger_name = f"{manager_logger_name}.{base_worker_logger_name}"

    worker_logger = logging.getLogger(worker_logger_name)

    # 4. Assign the child logger of the worker to global worker logger variable
    _WORKER_LOGGER = worker_logger


def _initialize_worker(
    logging_context: LoggingContext,
    proxy_queue: Queue[logging.LogRecord] | None = None,
    manager_logger_name: str | None = None,
) -> None:
    """Initialize process-global state inside a spawned worker process.

    Worker logging is initialized from the captured parent-process logging context.

    Args:
        logging_context: Parent-process logging state to reproduce in the worker.
        proxy_queue: Optional queue used to forward worker log records to the parent.
        manager_logger_name: Optional parent logger name used to namespace the
            process-specific worker logger.
    """

    global _WORKER_LOGGER

    _worker_logger_initialization(
        logging_context,
        proxy_queue,
        manager_logger_name,
    )


def _generate_typos_for_distribution_in_worker(
    typo_distribution: TypoDistribution,
    word_list: list[str],
    iterations: int,
    typo_rate: float,
) -> list[TypoData]:
    """Worker function to generate typos for a given typo distribution and word list.

    Args:
        typo_distribution: The typo distribution to use for generating typos.
        word_list: List of words for which to generate typos.
        iterations: Number of iterations to run for each generated noise word.
        typo_rate: The rate at which typos are generated for each word.

    Returns:
        A list of tuples containing the generated typo, the target word in lowercase, and the original word.

    Notes:
        - This function is an wrapper around `generate_typos_for_distribution` to be used in a worker process, \
          since it does not accept a logger parameter, it uses the global `_WORKER_LOGGER` variable as the `logger` argument passed to `generate_typos_for_distribution`.
    """
    return generate_typos_for_distribution(
        typo_distribution,
        word_list,
        iterations,
        typo_rate,
        logger=_WORKER_LOGGER,
    )


def generate_typos_for_distribution(
    typo_distribution: TypoDistribution,
    word_list: list[str],
    iterations: int,
    typo_rate: float,
    logger: logging.Logger | None = None,
) -> list[TypoData]:
    """Generate typos for a given typo distribution and word list.

    Args:
        typo_distribution: The typo distribution to use for generating typos.
        word_list: List of words for which to generate typos.
        iterations: Number of iterations to run for each generated noise word.
        typo_rate: The rate at which typos are generated for each word.
        logger: Optional logger for logging progress and errors.

    Returns:
        A list of tuples containing the generated typo, the target word in lowercase, and the original word.

    Notes:
        - The function uses the `iterations` and `typo_rate` parameters to control the number of typos generated for each word, \
          these 2 parameters are used instead of a single "number of typos per word" parameter for future flexibility (e.g., allowing for typo generation for sentences or phrases).
    """

    distribution = typo_distribution.distribution
    gen = MultiTypoGenerator(
        language=DEFAULT_LANGUAGE,
        use_excluding_set=DEFAULT_USE_EXCLUDING_SET,
        typo_distribution=distribution,
        horizontal_vs_vertical=DEFAULT_HORIZONTAL_VS_VERTICAL,
    )

    if logger:
        logger.info(
            "Generating typos for %d words using the typo distribution: %s",
            len(word_list),
            distribution,
        )

    effective_iterations = max(1, int(typo_rate * iterations))

    generated_data: list[TypoData] = []
    for target_word in word_list:
        target_trigger: TriggerWord = target_word.lower()
        for _ in range(effective_iterations):
            noisy: NoisyWord = gen.insert_typos_in_text(target_word, typo_rate=1).lower()
            if noisy == target_trigger:
                if logger:
                    logger.error(
                        "Generated typo is the same as the target word: %r; This should not happen with provided typo_rate=1.0 for 'insert_typos_in_text' method. Skipping this typo.",
                        target_trigger,
                    )
                continue

            # Append a tuple containing the data needed for the main thread
            generated_data.append((noisy, target_trigger))

    if logger:
        logger.info(
            "Completed generating typos for %d words using the typo distribution: %s",
            len(word_list),
            distribution,
        )

    return generated_data


def _multi_worker_typo_generation(
    word_list: list[str],
    *,
    typo_distributions: dict[TypoDistribution, None],
    iterations_per_distribution: int,
    typo_rate: float,
    n_workers: int | None,
    logging_context: LoggingContext,
    mp_context: BaseContext | None = None,
    proxy_queue: Queue[logging.LogRecord] | None = None,
    manager_logger_name: str | None = None,
) -> dict[TypoDistribution, list[TypoData]]:
    """Submit typo generation tasks to a process pool executor and collect results.

    Typo generation tasks are completed in an undefined order, and results are collected as they finish.
    The results are structured as a mapping from each submitted typo distribution to its corresponding list of generated typos.

    Args:
        word_list: List of words for which to generate typos.
        typo_distributions: Typo distributions for which to generate typos (as keys in a dictionary with `None` values for ensuring uniqueness while still preserving the order).
        iterations_per_distribution: Number of iterations to run for each generated noise word per distribution.
        typo_rate: The rate at which typos are generated for each word.
        n_workers: Requested process-pool size, or `None` for the executor default.
        logging_context: Parent-process logging state reproduced in workers.
        mp_context: Optional multiprocessing context used by the executor.
        proxy_queue: Optional queue forwarding worker log records to the parent.
        manager_logger_name: Optional logger name restored in worker processes.

    Returns:
        A dictionary mapping each submitted typo distribution to its corresponding list of generated typos.

    Raises:
        RuntimeError: If any submitted participant task raises while being fitted.
    """

    results: dict[TypoDistribution, list[TypoData]] = {}
    with ProcessPoolExecutor(
        max_workers=n_workers,
        mp_context=mp_context,
        initializer=_initialize_worker,
        initargs=(
            logging_context,
            proxy_queue,
            manager_logger_name,
        ),
    ) as executor:
        future_to_distr: dict[Future[list[TypoData]], TypoDistribution] = {
            executor.submit(
                _generate_typos_for_distribution_in_worker,
                typo_distribution,
                word_list,
                iterations_per_distribution,
                typo_rate,
            ): typo_distribution
            for typo_distribution in typo_distributions
        }

        # Collect results as the workers finish
        for future in as_completed(future_to_distr):
            typo_distribution = future_to_distr[future]

            try:
                results[typo_distribution] = future.result()
            except Exception as e:
                raise RuntimeError(
                    f"Failed to generate typos for distribution {typo_distribution}: {e}"
                ) from e

    return results


def _generate_typos_for_distributions_serial(
    word_list: list[str],
    typo_distributions: dict[TypoDistribution, None],
    iterations_per_distribution: int,
    typo_rate: float,
    manager_logger_name: str | None = None,
) -> dict[TypoDistribution, list[TypoData]]:
    """Generate typos for each distribution in a serial manner.

    Args:
        word_list: List of words for which to generate typos.
        typo_distributions: Typo distributions for which to generate typos (as keys in a dictionary with `None` values for ensuring uniqueness while still preserving the order).
        iterations_per_distribution: Number of iterations to run for each generated noise word per distribution.
        typo_rate: The rate at which typos are generated for each word.
        manager_logger_name: Optional logger name used to namespace the serial logger.

    Returns:
        A dictionary mapping each submitted typo distribution to its corresponding list of generated typos.
    """

    logger_name = "serial" if not manager_logger_name else f"{manager_logger_name}.serial"
    logger = logging.getLogger(logger_name)

    all_raw_results: dict[TypoDistribution, list[TypoData]] = {}
    for typo_distribution in typo_distributions:
        raw_results = generate_typos_for_distribution(
            typo_distribution,
            word_list,
            iterations_per_distribution,
            typo_rate,
            logger=logger,
        )

        all_raw_results[typo_distribution] = raw_results

    return all_raw_results


def _generate_typos_for_distributions_parallel(
    word_list: list[str],
    typo_distributions: dict[TypoDistribution, None],
    iterations_per_distribution: int,
    typo_rate: float,
    n_workers: int | None = None,
    manager_logger_name: str | None = None,
) -> dict[TypoDistribution, list[TypoData]]:
    """Generate typos for each distribution in parallel using a process pool.

    A multiprocessing context is created with the 'spawn' start method, and a process pool executor is used to submit typo generation tasks for each distribution.
    The results are collected as they finish, and a dictionary mapping each submitted typo distribution to its corresponding list of generated typos is returned.
    If the root logger has handlers that aren't `NullHandler`, a proxy queue and a queue listener are created to forward worker log records to the parent process.

    Args:
        word_list: List of words for which to generate typos.
        typo_distributions: Typo distributions for which to generate typos (as keys in a dictionary with `None` values for ensuring uniqueness while still preserving the order).
        iterations_per_distribution: Number of iterations to run for each generated noise word per distribution.
        typo_rate: The rate at which typos are generated for each word.
        n_workers: Requested process-pool size, or `None` for the executor default.
        manager_logger_name: Optional logger name used to namespace the worker loggers.

    Returns:
        A dictionary mapping each submitted typo distribution to its corresponding list of generated typos.
    """

    logging_context = LoggingContext()

    manager_logger = logging.getLogger(manager_logger_name)

    root_logger_handlers = logging.getLogger().handlers

    mp_context = mp.get_context("spawn")
    manager_logger.debug("Using multiprocessing context: %r", mp_context.get_start_method())

    if not root_logger_handlers or all(
        isinstance(handler, logging.NullHandler) for handler in root_logger_handlers
    ):
        manager_logger.debug(
            "No root logger handlers that aren't NullHandler were found, so multiprocessing logging will be disabled (i.e. no proxy queue and no queue listener will be created)."
        )

        all_raw_results = _multi_worker_typo_generation(
            word_list,
            typo_distributions=typo_distributions,
            iterations_per_distribution=iterations_per_distribution,
            typo_rate=typo_rate,
            n_workers=n_workers,
            logging_context=logging_context,
            mp_context=mp_context,
            proxy_queue=None,
            manager_logger_name=manager_logger_name,
        )
    else:
        manager_logger.debug(
            "Root logger handlers that aren't NullHandler were found, so multiprocessing logging will be enabled (i.e. a proxy queue and a queue listener will be created)."
        )
        with mp_context.Manager() as manager:
            # Create the proxy queue
            proxy_queue: Queue[logging.LogRecord] = manager.Queue(-1)

            # Create the QueueListener (listens to proxy queue, writes terminal and file)
            listener = QueueListener(
                proxy_queue,
                *root_logger_handlers,
                respect_handler_level=True,
            )

            # Start the listener
            listener.start()

            try:
                # Context manager for Executor, passing the proxy queue in initargs
                all_raw_results = _multi_worker_typo_generation(
                    word_list,
                    typo_distributions=typo_distributions,
                    iterations_per_distribution=iterations_per_distribution,
                    typo_rate=typo_rate,
                    n_workers=n_workers,
                    logging_context=logging_context,
                    mp_context=mp_context,
                    proxy_queue=proxy_queue,
                    manager_logger_name=manager_logger_name,
                )
            finally:
                # Stop listening
                listener.stop()

    return all_raw_results


def generate_typos_for_distributions(
    word_list: list[str],
    typo_distribution_to_label: dict[TypoDistribution, TypoDistributionLabel] | None = None,
    iterations_per_distribution: int = DEFAULT_ITERATIONS_PER_DISTRIBUTION,
    typo_rate: float = DEFAULT_TYPO_RATE,
    n_workers: int | None = None,
) -> tuple[
    dict[NoisyWord, tuple[TriggerWord, tuple[TypoDistributionLabel, ...]]],
    dict[NoisyWord, dict[TriggerWord, tuple[TypoDistributionLabel, ...]]],
    dict[NoisyWord, TriggerWord],
]:
    """Generate typos for each word using the every provided typo distribution.

    The function generates typos for each word in the provided list according to the specified typo distributions, iterations per distribution, and typo rate.
    It delegates the actual typo generation to either a serial or parallel execution path based on the number of workers and the number of distributions provided.

    Args:
        word_list: List of words for which to generate typos.
        typo_distribution_to_label: Optional mapping of typo distributions to their corresponding labels. If not provided, default distributions for "replace", "transpose", "delete", and "insert" will be used.
        iterations_per_distribution: Number of iterations to run for each generated noise word per distribution.
        typo_rate: The rate at which typos are generated for each word.
        n_workers: Requested process-pool size, or `None` for the executor default.

    Returns:
        A tuple containing
            - A dictionary mapping for the valid results, where each key is a noisy word and the value is a tuple of the target trigger word and a tuple of typo distribution labels that generated the noisy word.
            - A dictionary mapping for the clashes, where each key is a noisy word and the value is a dictionary mapping target trigger words to a tuple of typo distribution labels that generated the noisy word (the mapping value would have at least 2 entries).
            - A dictionary mapping for the hotstring map, where each key is a noisy word and the value is the corresponding target trigger word.

    Raises:
        TypeError: If `n_workers` is not an integer or `None`.
        ValueError: If `n_workers` is not a positive integer, if an empty typo distribution mapping is provided,
          if `iterations_per_distribution` is not a positive integer, or if `typo_rate` is not a float between 0.0 and 1.0 (exclusive of 0.0).
    """

    if n_workers is not None:
        if not isinstance(n_workers, int):
            raise TypeError(
                f"n_workers must be an integer or None, got {type(n_workers).__name__}."
            )

        if n_workers <= 0:
            raise ValueError("n_workers must be greater than zero.")

    if typo_distribution_to_label is None:
        error_types = ("replace", "transpose", "delete", "insert")
        typo_distribution_to_label = {
            TypoDistribution(**{err_type: 1.0}): f"{err_type.title()} typos only"
            for err_type in error_types
        }

    if len(typo_distribution_to_label) == 0:
        raise ValueError("At least one typo distribution must be provided.")

    if not isinstance(iterations_per_distribution, int) or iterations_per_distribution <= 0:
        raise ValueError(
            f"iterations_per_distribution must be a positive integer, got {iterations_per_distribution}."
        )

    if not isinstance(typo_rate, float) or not (0.0 < typo_rate <= 1.0):
        raise ValueError(
            f"typo_rate must be a float between 0.0 and 1.0 (exclusive of 0.0), got {typo_rate}."
        )

    effective_n_workers = (
        min(n_workers, len(typo_distribution_to_label)) if n_workers is not None else None
    )

    manager_logger = logging.getLogger("manager")

    if (effective_n_workers is not None and effective_n_workers == 1) or len(
        typo_distribution_to_label
    ) == 1:
        manager_logger.info(
            "Using serial execution because either n_workers=1 or only one typo distribution is provided, got n_workers=%s and len(typo_distributions)=%d.",
            n_workers,
            len(typo_distribution_to_label),
        )
        results_map = _generate_typos_for_distributions_serial(
            word_list,
            typo_distributions=dict.fromkeys(typo_distribution_to_label.keys()),
            iterations_per_distribution=iterations_per_distribution,
            typo_rate=typo_rate,
            manager_logger_name=manager_logger.name,
        )
    else:
        manager_logger.info(
            "Using parallel execution with maximum workers = %s.",
            "amount of processors" if effective_n_workers is None else effective_n_workers,
        )
        results_map = _generate_typos_for_distributions_parallel(
            word_list,
            typo_distributions=dict.fromkeys(typo_distribution_to_label.keys()),
            iterations_per_distribution=iterations_per_distribution,
            typo_rate=typo_rate,
            n_workers=effective_n_workers,
            manager_logger_name=manager_logger.name,
        )
    manager_logger.info("Typo generation completed for all distributions.")

    # 2. Main Thread Merge & Collision Check
    initial_typo_results: dict[NoisyWord, dict[TriggerWord, list[TypoDistributionLabel]]] = {}
    valid_results: dict[NoisyWord, tuple[TriggerWord, tuple[TypoDistributionLabel, ...]]] = {}
    clashes: dict[NoisyWord, dict[TriggerWord, tuple[TypoDistributionLabel, ...]]] = {}

    for distro, distro_label in typo_distribution_to_label.items():
        for noisy, target_trigger in results_map[distro]:
            if noisy not in initial_typo_results:
                initial_typo_results[noisy] = {}

            if target_trigger not in initial_typo_results[noisy]:
                initial_typo_results[noisy][target_trigger] = []

            initial_typo_results[noisy][target_trigger].append(distro_label)

    for noisy, target_map in initial_typo_results.items():
        if len(target_map) > 1:
            # Clash detected
            clashes[noisy] = {
                target_trigger: tuple(sorted(distro_labels))
                for target_trigger, distro_labels in target_map.items()
            }
        elif len(target_map) == 1:
            # No clash, valid result
            target_trigger = next(iter(target_map))
            valid_results[noisy] = (target_trigger, tuple(sorted(target_map[target_trigger])))

    hotstring_map = {noisy: target_trigger for noisy, (target_trigger, _) in valid_results.items()}

    return (
        valid_results,
        clashes,
        hotstring_map,
    )

    # 3. Print Output (Standard AHK Format)
    # print("; =====================================")
    # print("; MULTIPROCESSED AHK DICTIONARY")
    # print("; =====================================\n")

    # for word, distro_results in norm_results.items():
    #     print(f"; --- Hotstrings for: {word} ---")
    #     for label, typos in distro_results.items():
    #         if typos:
    #             print(f"; {label}:")
    #             for typo in typos:
    #                 print(f"::{typo}::{word}")
    #         else:
    #             print(f"; {label}: No typos generated.")
    #         print()
    #     print()

    # # 4. Print Clash Report
    # if clashes:
    #     print("; =====================================")
    #     print("; WARNING: CLASHES DETECTED AND STRIPPED")
    #     print("; =====================================")
    #     for typo, words in clashes.items():
    #         print(f"; Removed '{typo}' -> conflicting targets: {', '.join(words)}")
    # else:
    #     print("; =====================================")
    #     print("; SUCCESS: NO CLASHES DETECTED")
    #     print("; =====================================")


def main() -> None:
    configure_root_logger(
        root_level=logging.DEBUG,
        use_stderr=True,
        console_level=logging.INFO,
        file_path="robust_ahk_dict_generation.log",
        file_level=logging.DEBUG,
    )
    nltk.download("punkt_tab", quiet=True)

    my_words = ["screenshots", "javascript", "powershell", "screencast"]
    generate_typos_for_distributions(my_words)


if __name__ == "__main__":
    # Required guard for multiprocessing in Windows
    main()
