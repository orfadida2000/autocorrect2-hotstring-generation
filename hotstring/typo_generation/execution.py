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
            max_allowed_workers = min(max_allowed_workers, _MAX_WINDOWS_PROCESS_POOL_WORKERS)
        effective_n_workers = min(n_workers, len(task_tuple), max_allowed_workers)

    if len(task_tuple) == 1 or effective_n_workers == 1:
        return _execute_tasks_serial(words, task_tuple, config, logger=logger)

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
    """Execute every task in the current process."""
    samples: list[RawTypoSample] = []
    for task in tasks:
        samples.extend(generate_typos_for_task(word_list, task, config, logger=logger))
    return samples


def _execute_tasks_parallel(
    word_list: list[str],
    tasks: tuple[TypoGenerationTask, ...],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None,
    logger: logging.Logger | None,
) -> list[RawTypoSample]:
    """Execute tasks with a spawned process pool."""
    mp_context = mp.get_context("spawn")
    root_logger = logging.getLogger()
    root_handlers = tuple(
        handler for handler in root_logger.handlers if not isinstance(handler, logging.NullHandler)
    )
    manager_logger_name = logger.name if logger is not None else "typo_generation"

    if not root_handlers:
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

    with mp_context.Manager() as manager:
        proxy_queue = manager.Queue(-1)
        listener = QueueListener(proxy_queue, *root_handlers, respect_handler_level=True)
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
    """Submit every generation task to a process pool and collect results."""
    results_by_index: dict[int, list[RawTypoSample]] = {}

    with ProcessPoolExecutor(
        max_workers=n_workers,
        mp_context=mp_context,
        initializer=_initialize_worker,
        initargs=(root_level, proxy_queue, manager_logger_name),
    ) as executor:
        future_to_task: dict[Future[list[RawTypoSample]], tuple[int, TypoGenerationTask]] = {
            executor.submit(_generate_task_in_worker, word_list, task, config): (index, task)
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
    """Initialize logging inside one spawned worker process."""
    global _WORKER_LOGGER

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(root_level)
    if proxy_queue is not None:
        root_logger.addHandler(QueueHandler(proxy_queue))

    base_name = f"worker_{os.getpid()}"
    worker_name = base_name if not manager_logger_name else f"{manager_logger_name}.{base_name}"
    _WORKER_LOGGER = logging.getLogger(worker_name)


def _initialize_worker(
    root_level: int,
    proxy_queue: Any | None = None,
    manager_logger_name: str | None = None,
) -> None:
    """Initialize process-global state inside a spawned worker process."""
    _worker_logger_initialization(root_level, proxy_queue, manager_logger_name)


def _generate_task_in_worker(
    word_list: list[str],
    task: TypoGenerationTask,
    config: TypoGenerationConfig,
) -> list[RawTypoSample]:
    """Execute one task inside a process-pool worker."""
    return generate_typos_for_task(word_list, task, config, logger=_WORKER_LOGGER)


def _normalize_tasks(tasks: Sequence[TypoGenerationTask]) -> tuple[TypoGenerationTask, ...]:
    """Validate and freeze the task sequence for one execution run."""
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
    """Validate an optional process-pool worker count."""
    if n_workers is None:
        return
    if isinstance(n_workers, bool) or not isinstance(n_workers, int):
        raise TypeError("n_workers must be an integer or None.")
    if n_workers <= 0:
        raise ValueError("n_workers must be greater than zero.")
