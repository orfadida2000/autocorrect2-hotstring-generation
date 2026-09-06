"""Execute typo-generation tasks serially or with a spawned process pool."""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import sys
from collections.abc import Sequence
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from logging.handlers import QueueHandler, QueueListener
from multiprocessing.context import BaseContext
from typing import Any, Final

from .generation import generate_typos_for_task
from .models import RawTypoSample, TypoGenerationConfig, TypoGenerationTask

_MAX_WINDOWS_PROCESS_POOL_WORKERS: Final[int] = 61

_WORKER_LOGGER: logging.Logger | None = None


def execute_typo_generation_tasks(
    word_list: Sequence[str],
    tasks: Sequence[TypoGenerationTask],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None = None,
    logger: logging.Logger | None = None,
) -> list[RawTypoSample]:
    """Execute all typo-generation tasks and collect their raw samples.

    Task count is independent of worker count. Serial execution is used when
    only one task is supplied or the requested effective worker count is one;
    otherwise all tasks are submitted to a spawned process pool and workers
    consume tasks as they become available.

    Args:
        word_list:
            Shared source words considered by every task.
        tasks:
            Ordered typo-generation tasks to execute.
        config:
            Shared generator configuration.
        n_workers:
            Requested process-pool size, or `None` for the executor default.
        logger:
            Optional orchestration logger.

    Returns:
        Concatenated raw samples in input task order.

    Raises:
        TypeError:
            If `n_workers` or a task has an invalid type.
        ValueError:
            If no tasks are supplied or `n_workers` is not positive.
        RuntimeError:
            If a parallel generation task fails.
    """
    _validate_worker_count(n_workers)
    task_tuple = _normalize_tasks(tasks)
    words = list(word_list)

    if n_workers is None:
        effective_n_workers = None
    else:
        available_cpus = (
            os.process_cpu_count() if hasattr(os, "process_cpu_count") else os.cpu_count()
        ) or 1

        max_allowed_workers = available_cpus

        if sys.platform == "win32":
            # ProcessPoolExecutor limits max_workers to 61 on Windows.
            max_allowed_workers = min(max_allowed_workers, _MAX_WINDOWS_PROCESS_POOL_WORKERS)

        effective_n_workers = min(
            n_workers,
            len(task_tuple),
            max_allowed_workers,
        )

    if len(task_tuple) == 1 or effective_n_workers == 1:
        if logger is not None:
            logger.info(
                "Using serial typo-generation execution for %d task(s).",
                len(task_tuple),
            )
        return _execute_tasks_serial(words, task_tuple, config, logger=logger)

    if logger is not None:
        logger.info(
            "Using parallel typo-generation execution for %d tasks with max workers=%s.",
            len(task_tuple),
            "executor default" if effective_n_workers is None else effective_n_workers,
        )

    return _execute_tasks_parallel(
        words,
        task_tuple,
        config,
        n_workers=effective_n_workers,
        logger=logger,
    )


def _execute_tasks_serial(
    word_list: list[str],
    tasks: tuple[TypoGenerationTask, ...],
    config: TypoGenerationConfig,
    *,
    logger: logging.Logger | None,
) -> list[RawTypoSample]:
    """Execute every task in the current process.

    Args:
        word_list:
            Shared source words.
        tasks:
            Ordered tasks to execute.
        config:
            Shared generator configuration.
        logger:
            Optional logger forwarded to low-level generation.

    Returns:
        Concatenated raw samples in task order.
    """
    samples: list[RawTypoSample] = []
    for task in tasks:
        samples.extend(
            generate_typos_for_task(
                word_list,
                task,
                config,
                logger=logger,
            )
        )

    return samples


def _execute_tasks_parallel(
    word_list: list[str],
    tasks: tuple[TypoGenerationTask, ...],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None,
    logger: logging.Logger | None,
) -> list[RawTypoSample]:
    """Execute tasks with a spawned process pool.

    Worker log records are forwarded to the parent process through a queue
    when the parent root logger has at least one non-null handler.

    Args:
        word_list:
            Shared source words.
        tasks:
            Ordered tasks to submit.
        config:
            Shared generator configuration.
        n_workers:
            Effective process-pool size.
        logger:
            Optional orchestration logger.

    Returns:
        Concatenated raw samples in input task order.

    Raises:
        RuntimeError:
            If a submitted worker task fails.
    """
    mp_context = mp.get_context("spawn")
    root_logger = logging.getLogger()
    root_handlers = tuple(
        handler for handler in root_logger.handlers if not isinstance(handler, logging.NullHandler)
    )
    manager_logger_name = logger.name if logger is not None else "typo_generation"

    if logger is not None:
        logger.debug(
            "Using multiprocessing start method %r.",
            mp_context.get_start_method(),
        )

    if not root_handlers:
        if logger is not None:
            logger.debug("No non-null root handlers found; worker log forwarding is disabled.")
        return _multi_worker_typo_generation(
            word_list,
            tasks,
            config,
            n_workers=n_workers,
            mp_context=mp_context,
            proxy_queue=None,
            root_level=root_logger.level,
            manager_logger_name=manager_logger_name,
        )

    if logger is not None:
        logger.debug("Root handlers found; worker log records will be forwarded through a queue.")

    with mp_context.Manager() as manager:
        proxy_queue = manager.Queue(-1)
        listener = QueueListener(
            proxy_queue,
            *root_handlers,
            respect_handler_level=True,
        )
        listener.start()
        try:
            return _multi_worker_typo_generation(
                word_list,
                tasks,
                config,
                n_workers=n_workers,
                mp_context=mp_context,
                proxy_queue=proxy_queue,
                root_level=root_logger.level,
                manager_logger_name=manager_logger_name,
            )
        finally:
            listener.stop()


def _multi_worker_typo_generation(
    word_list: list[str],
    tasks: tuple[TypoGenerationTask, ...],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None,
    mp_context: BaseContext,
    proxy_queue: Any | None,
    root_level: int,
    manager_logger_name: str,
) -> list[RawTypoSample]:
    """Submit every generation task to a process pool and collect results.

    More tasks than workers is expected: `ProcessPoolExecutor` schedules the
    pending tasks onto available worker processes. Results are collected as
    futures finish but are concatenated afterward in original task order.

    Args:
        word_list:
            Shared source words.
        tasks:
            Ordered tasks to submit.
        config:
            Shared generator configuration.
        n_workers:
            Effective pool size.
        mp_context:
            Spawn multiprocessing context.
        proxy_queue:
            Optional queue forwarding worker log records to the parent.
        root_level:
            Parent root logger level reproduced in workers.
        manager_logger_name:
            Logger namespace used for process-specific worker loggers.

    Returns:
        Concatenated worker results in input task order.

    Raises:
        RuntimeError:
            If any submitted generation task raises.
    """
    results_by_index: dict[int, list[RawTypoSample]] = {}

    with ProcessPoolExecutor(
        max_workers=n_workers,
        mp_context=mp_context,
        initializer=_initialize_worker,
        initargs=(
            root_level,
            proxy_queue,
            manager_logger_name,
        ),
    ) as executor:
        future_to_task: dict[Future[list[RawTypoSample]], tuple[int, TypoGenerationTask]] = {
            executor.submit(
                _generate_task_in_worker,
                word_list,
                task,
                config,
            ): (index, task)
            for index, task in enumerate(tasks)
        }

        for future in as_completed(future_to_task):
            index, task = future_to_task[future]
            try:
                results_by_index[index] = future.result()
            except Exception as error:
                raise RuntimeError(
                    f"Failed to execute typo-generation task at index {index}: {task!r}"
                ) from error

    return [sample for index in range(len(tasks)) for sample in results_by_index[index]]


def _worker_logger_initialization(
    root_level: int,
    proxy_queue: Any | None,
    manager_logger_name: str | None,
) -> None:
    """Initialize logging inside one spawned worker process.

    This helper is deliberately separate from `_initialize_worker` so future
    process-global initialization can be added without turning worker logging
    setup into one large initializer.

    Args:
        root_level:
            Parent root logger level to reproduce in the worker.
        proxy_queue:
            Optional queue that forwards worker records to the parent.
        manager_logger_name:
            Optional parent logger namespace for the process-specific logger.
    """
    global _WORKER_LOGGER

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(root_level)

    if proxy_queue is not None:
        root_logger.addHandler(QueueHandler(proxy_queue))

    base_worker_logger_name = f"worker_{os.getpid()}"
    worker_logger_name = (
        base_worker_logger_name
        if not manager_logger_name
        else f"{manager_logger_name}.{base_worker_logger_name}"
    )
    _WORKER_LOGGER = logging.getLogger(worker_logger_name)


def _initialize_worker(
    root_level: int,
    proxy_queue: Any | None = None,
    manager_logger_name: str | None = None,
) -> None:
    """Initialize process-global state inside a spawned worker process.

    Args:
        root_level:
            Parent root logger level.
        proxy_queue:
            Optional queue forwarding worker log records to the parent.
        manager_logger_name:
            Optional logger namespace for the worker logger.
    """
    _worker_logger_initialization(
        root_level,
        proxy_queue,
        manager_logger_name,
    )


def _generate_task_in_worker(
    word_list: list[str],
    task: TypoGenerationTask,
    config: TypoGenerationConfig,
) -> list[RawTypoSample]:
    """Execute one task inside a process-pool worker.

    Args:
        word_list:
            Shared source words.
        task:
            Generation task assigned to this worker invocation.
        config:
            Shared generator configuration.

    Returns:
        Raw samples produced by the task.
    """
    return generate_typos_for_task(
        word_list,
        task,
        config,
        logger=_WORKER_LOGGER,
    )


def _normalize_tasks(
    tasks: Sequence[TypoGenerationTask],
) -> tuple[TypoGenerationTask, ...]:
    """Validate and freeze the task sequence for one execution run.

    Args:
        tasks:
            Caller-supplied task sequence.

    Returns:
        Immutable task tuple preserving input order.

    Raises:
        TypeError:
            If an item is not a `TypoGenerationTask`.
        ValueError:
            If no tasks are supplied.
    """
    task_tuple = tuple(tasks)
    if not task_tuple:
        raise ValueError("At least one typo-generation task must be provided.")

    for index, task in enumerate(task_tuple):
        if not isinstance(task, TypoGenerationTask):
            raise TypeError(
                f"tasks[{index}] must be a TypoGenerationTask, not {type(task).__name__}."
            )

    return task_tuple


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
