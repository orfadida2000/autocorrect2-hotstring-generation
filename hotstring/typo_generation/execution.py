"""Execute typo generation serially or with a spawned process pool."""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from logging.handlers import QueueHandler, QueueListener
from typing import Any

from .generation import generate_typos_for_distribution
from .models import RawTypoSample, TypoDistribution, TypoGenerationConfig


_WORKER_LOGGER: logging.Logger | None = None


def execute_typo_generation(
    word_list: list[str],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None = None,
    logger: logging.Logger | None = None,
) -> list[RawTypoSample]:
    """Execute all configured typo distributions and collect raw samples.

    Serial execution is used when one distribution is configured or the
    requested effective worker count is one. Otherwise the function uses a
    Windows-compatible spawned process pool.

    Args:
        word_list:
            Source words to corrupt.
        config:
            Typo-generation configuration.
        n_workers:
            Requested process-pool size, or `None` for the executor default.
        logger:
            Optional orchestration logger.

    Returns:
        Raw successful samples from all distributions.

    Raises:
        TypeError:
            If `n_workers` is neither a positive integer nor `None`.
        ValueError:
            If `n_workers` is not positive.
        RuntimeError:
            If a parallel generation task fails.
    """
    _validate_worker_count(n_workers)
    distributions = config.typo_distributions
    effective_n_workers = (
        min(n_workers, len(distributions)) if n_workers is not None else None
    )

    if len(distributions) == 1 or effective_n_workers == 1:
        if logger is not None:
            logger.info("Using serial typo-generation execution.")
        return _execute_serial(word_list, config, logger=logger)

    if logger is not None:
        logger.info(
            "Using parallel typo-generation execution with max workers=%s.",
            "executor default" if effective_n_workers is None else effective_n_workers,
        )
    return _execute_parallel(
        word_list,
        config,
        n_workers=effective_n_workers,
        logger=logger,
    )


def _execute_serial(
    word_list: list[str],
    config: TypoGenerationConfig,
    *,
    logger: logging.Logger | None,
) -> list[RawTypoSample]:
    """Generate every configured distribution in the current process.

    Args:
        word_list:
            Source words.
        config:
            Typo-generation configuration.
        logger:
            Optional logger forwarded to low-level generation.

    Returns:
        Concatenated raw samples.
    """
    samples: list[RawTypoSample] = []
    for distribution in config.typo_distributions:
        samples.extend(
            generate_typos_for_distribution(
                word_list,
                distribution,
                config,
                logger=logger,
            )
        )
    return samples


def _execute_parallel(
    word_list: list[str],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None,
    logger: logging.Logger | None,
) -> list[RawTypoSample]:
    """Generate configured distributions with a spawned process pool.

    Worker records are forwarded to existing root handlers through a queue
    when the parent process has non-null logging handlers.

    Args:
        word_list:
            Source words.
        config:
            Typo-generation configuration.
        n_workers:
            Effective process-pool size.
        logger:
            Optional orchestration logger.

    Returns:
        Concatenated raw samples.

    Raises:
        RuntimeError:
            If a submitted worker task fails.
    """
    mp_context = mp.get_context("spawn")
    root_logger = logging.getLogger()
    root_handlers = [
        handler
        for handler in root_logger.handlers
        if not isinstance(handler, logging.NullHandler)
    ]
    logger_name = logger.name if logger is not None else "typo_generation"

    if not root_handlers:
        return _run_process_pool(
            word_list,
            config,
            n_workers=n_workers,
            mp_context=mp_context,
            proxy_queue=None,
            root_level=root_logger.level,
            logger_name=logger_name,
        )

    with mp_context.Manager() as manager:
        proxy_queue = manager.Queue(-1)
        listener = QueueListener(
            proxy_queue,
            *root_handlers,
            respect_handler_level=True,
        )
        listener.start()
        try:
            return _run_process_pool(
                word_list,
                config,
                n_workers=n_workers,
                mp_context=mp_context,
                proxy_queue=proxy_queue,
                root_level=root_logger.level,
                logger_name=logger_name,
            )
        finally:
            listener.stop()


def _run_process_pool(
    word_list: list[str],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None,
    mp_context: Any,
    proxy_queue: Any | None,
    root_level: int,
    logger_name: str,
) -> list[RawTypoSample]:
    """Submit one process-pool task per typo distribution.

    Args:
        word_list:
            Source words.
        config:
            Typo-generation configuration.
        n_workers:
            Effective pool size.
        mp_context:
            Spawn multiprocessing context.
        proxy_queue:
            Optional multiprocessing logging queue.
        root_level:
            Parent root logger level reproduced in workers.
        logger_name:
            Base logger namespace for workers.

    Returns:
        Concatenated worker results.

    Raises:
        RuntimeError:
            If any worker task raises.
    """
    samples: list[RawTypoSample] = []
    with ProcessPoolExecutor(
        max_workers=n_workers,
        mp_context=mp_context,
        initializer=_initialize_worker,
        initargs=(proxy_queue, root_level, logger_name),
    ) as executor:
        futures: dict[Future[list[RawTypoSample]], TypoDistribution] = {
            executor.submit(
                _generate_in_worker,
                distribution,
                word_list,
                config,
            ): distribution
            for distribution in config.typo_distributions
        }

        for future in as_completed(futures):
            distribution = futures[future]
            try:
                samples.extend(future.result())
            except Exception as error:
                raise RuntimeError(
                    "Failed to generate typos for distribution "
                    f"{distribution.distribution}: {error}"
                ) from error
    return samples


def _initialize_worker(
    proxy_queue: Any | None,
    root_level: int,
    logger_name: str,
) -> None:
    """Initialize process-local logging state in a spawned worker.

    Args:
        proxy_queue:
            Optional queue forwarding records to the parent.
        root_level:
            Parent root logger level.
        logger_name:
            Base logger namespace.
    """
    global _WORKER_LOGGER

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(root_level)
    if proxy_queue is not None:
        root_logger.addHandler(QueueHandler(proxy_queue))

    _WORKER_LOGGER = logging.getLogger(f"{logger_name}.worker_{os.getpid()}")


def _generate_in_worker(
    distribution: TypoDistribution,
    word_list: list[str],
    config: TypoGenerationConfig,
) -> list[RawTypoSample]:
    """Run one distribution task inside a process-pool worker.

    Args:
        distribution:
            Distribution assigned to this task.
        word_list:
            Source words.
        config:
            Shared generation configuration.

    Returns:
        Raw successful samples for the distribution.
    """
    return generate_typos_for_distribution(
        word_list,
        distribution,
        config,
        logger=_WORKER_LOGGER,
    )


def _validate_worker_count(n_workers: int | None) -> None:
    """Validate an optional process-pool worker count.

    Args:
        n_workers:
            Requested worker count.

    Raises:
        TypeError:
            If the value is not an integer or `None`, including booleans.
        ValueError:
            If the value is not positive.
    """
    if n_workers is None:
        return
    if isinstance(n_workers, bool) or not isinstance(n_workers, int):
        raise TypeError("n_workers must be an integer or None.")
    if n_workers <= 0:
        raise ValueError("n_workers must be greater than zero.")
