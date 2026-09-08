"""Perform low-level typo sampling for one generation task with MULTYPO."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from multypo import MultiTypoGenerator

from .models import RawTypoSample, TypoGenerationConfig, TypoGenerationTask


def generate_typos_for_task(
    word_list: Sequence[str],
    task: TypoGenerationTask,
    config: TypoGenerationConfig,
    *,
    logger: logging.Logger | None = None,
) -> list[RawTypoSample]:
    """Generate noisy samples for all words eligible for one task.

    Args:
        word_list:
            Shared source words to consider.
        task:
            Task-specific distribution and sampling settings.
        config:
            Shared MULTYPO generator configuration.
        logger:
            Optional logger for progress and diagnostics.

    Returns:
        Successful raw typo samples.
    """
    generator = _create_generator(task, config)
    normalized_words = tuple(_normalize_source_word(word) for word in word_list)
    eligible_words = tuple(
        word for word in normalized_words if len(word) >= task.minimum_word_length
    )

    if logger is not None:
        logger.info(
            "Generating typo samples for %d/%d eligible words with typo_rate=%s, "
            "attempts_per_word=%d, distribution=%s",
            len(eligible_words),
            len(normalized_words),
            task.typo_rate,
            task.generation_attempts_per_word,
            task.distribution.distribution,
        )

    generated: list[RawTypoSample] = []
    for target_word in eligible_words:
        for _ in range(task.generation_attempts_per_word):
            noisy_word = generator.insert_typos(
                target_word,
                typo_rate=float(task.typo_rate),
            ).lower()
            if noisy_word == target_word:
                continue
            generated.append(RawTypoSample(noisy_word=noisy_word, target_word=target_word))

    return generated


def _create_generator(
    task: TypoGenerationTask,
    config: TypoGenerationConfig,
) -> MultiTypoGenerator:
    """Create a configured MULTYPO generator for one task."""
    return MultiTypoGenerator(
        language=config.language,
        use_excluding_set=config.use_excluding_set,
        typo_distribution=task.distribution.distribution,
        horizontal_vs_vertical=config.horizontal_vs_vertical,
    )


def _normalize_source_word(source_word: str) -> str:
    """Validate and normalize one source word to lowercase."""
    if not isinstance(source_word, str):
        raise TypeError(f"Source words must be strings, not {type(source_word).__name__}.")
    if not source_word:
        raise ValueError("Source words cannot be empty.")
    if any(character.isspace() for character in source_word):
        raise ValueError(
            f"Source word must contain exactly one word and no whitespace: {source_word!r}"
        )
    return source_word.lower()
