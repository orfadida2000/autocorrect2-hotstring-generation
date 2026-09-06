"""Aggregate raw typo samples and remove internally ambiguous candidates."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from .models import (
    RawTypoSample,
    TypoGenerationConfig,
    TypoGenerationResult,
    TypoGenerationTask,
)


def aggregate_typo_samples(
    samples: Sequence[RawTypoSample],
    *,
    config: TypoGenerationConfig,
    tasks: Sequence[TypoGenerationTask],
    source_word_count: int,
) -> TypoGenerationResult:
    """Deduplicate raw samples and separate valid candidates from clashes.

    Repeated generation of the same noisy-word to target-word mapping does
    not create duplicate output. A noisy word becomes an internal clash only
    when it maps to more than one distinct target word.

    Args:
        samples:
            Raw samples produced by all generation tasks.
        config:
            Shared generator configuration.
        tasks:
            Ordered tasks used to produce the samples.
        source_word_count:
            Number of source words supplied before per-task length filtering.

    Returns:
        Aggregated typo-generation result.

    Raises:
        TypeError:
            If `source_word_count` is not an integer or a task has an invalid
            type.
        ValueError:
            If `source_word_count` is negative or no tasks are supplied.
    """
    if isinstance(source_word_count, bool) or not isinstance(source_word_count, int):
        raise TypeError("source_word_count must be an integer.")
    if source_word_count < 0:
        raise ValueError("source_word_count cannot be negative.")

    task_tuple = tuple(tasks)
    if not task_tuple:
        raise ValueError("At least one typo-generation task must be provided.")
    for index, task in enumerate(task_tuple):
        if not isinstance(task, TypoGenerationTask):
            raise TypeError(
                f"tasks[{index}] must be a TypoGenerationTask, not {type(task).__name__}."
            )

    targets_by_noisy: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        targets_by_noisy[sample.noisy_word].add(sample.target_word)

    candidates: dict[str, str] = {}
    clashes: dict[str, tuple[str, ...]] = {}

    for noisy_word in sorted(targets_by_noisy):
        targets = targets_by_noisy[noisy_word]
        if len(targets) == 1:
            candidates[noisy_word] = next(iter(targets))
        else:
            clashes[noisy_word] = tuple(sorted(targets))

    return TypoGenerationResult(
        config=config,
        tasks=task_tuple,
        source_word_count=source_word_count,
        generated_sample_count=len(samples),
        candidates=candidates,
        clashes=clashes,
    )
