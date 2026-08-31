"""Aggregate raw typo samples and remove internally ambiguous candidates."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from .models import RawTypoSample, TypoGenerationConfig, TypoGenerationResult


def aggregate_typo_samples(
    samples: Sequence[RawTypoSample],
    *,
    config: TypoGenerationConfig,
    source_word_count: int,
) -> TypoGenerationResult:
    """Deduplicate raw samples and separate valid candidates from clashes.

    Repeated generation of the same noisy-word to target-word mapping does
    not create duplicate output. A noisy word becomes an internal clash only
    when it maps to more than one distinct target word.

    Args:
        samples:
            Raw samples from all generation distributions.
        config:
            Semantic generation configuration.
        source_word_count:
            Number of source words supplied to generation.

    Returns:
        Aggregated typo-generation result.

    Raises:
        ValueError:
            If `source_word_count` is negative.
    """
    if source_word_count < 0:
        raise ValueError("source_word_count cannot be negative.")

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
        source_word_count=source_word_count,
        generated_sample_count=len(samples),
        candidates=candidates,
        clashes=clashes,
    )
