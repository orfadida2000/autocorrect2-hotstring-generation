"""Perform low-level single-distribution typo sampling with MULTYPO."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from multypo import MultiTypoGenerator

from .models import RawTypoSample, TypoDistribution, TypoGenerationConfig


def generate_typos_for_distribution(
    word_list: Sequence[str],
    typo_distribution: TypoDistribution,
    config: TypoGenerationConfig,
    *,
    logger: logging.Logger | None = None,
) -> list[RawTypoSample]:
    """Generate noisy samples for every source word using one distribution.

    Each input is deliberately treated as one word and MULTYPO is always
    called with `typo_rate=1.0`. The project-level sampling budget is instead
    represented explicitly by `generation_attempts_per_word`.

    Args:
        word_list:
            Source words to corrupt.
        typo_distribution:
            Typo-operation distribution used for this sampling pass.
        config:
            Typo-generation configuration.
        logger:
            Optional logger for progress messages.

    Returns:
        Successful noisy-word samples. Repeated identical samples are kept
        here and deduplicated later by aggregation.

    Raises:
        TypeError:
            If a source word is not a string.
        ValueError:
            If a source word is empty or contains whitespace.
    """
    generator = _create_generator(typo_distribution, config)
    if logger is not None:
        logger.info(
            "Generating typo samples for %d words with distribution %s",
            len(word_list),
            typo_distribution.distribution,
        )

    generated: list[RawTypoSample] = []
    for source_word in word_list:
        target_word = _normalize_source_word(source_word)

        for _ in range(config.generation_attempts_per_word):
            noisy_word = generator.insert_typos(target_word, typo_rate=1.0).lower()
            if noisy_word == target_word:
                if logger is not None:
                    logger.debug(
                        "MULTYPO returned the unchanged word %r; skipping this sample.",
                        target_word,
                    )
                continue
            generated.append(
                RawTypoSample(noisy_word=noisy_word, target_word=target_word)
            )

    if logger is not None:
        logger.info(
            "Completed distribution %s with %d successful samples.",
            typo_distribution.distribution,
            len(generated),
        )
    return generated


def _create_generator(
    typo_distribution: TypoDistribution,
    config: TypoGenerationConfig,
) -> MultiTypoGenerator:
    """Create a configured MULTYPO generator for one distribution.

    Args:
        typo_distribution:
            Distribution to pass to MULTYPO.
        config:
            Shared generation configuration.

    Returns:
        Configured [`MultiTypoGenerator`][multypo.MultiTypoGenerator].
    """
    return MultiTypoGenerator(
        language=config.language,
        use_excluding_set=config.use_excluding_set,
        typo_distribution=typo_distribution.distribution,
        horizontal_vs_vertical=config.horizontal_vs_vertical,
    )


def _normalize_source_word(source_word: str) -> str:
    """Validate and normalize a source word to lowercase.

    Args:
        source_word:
            Source item supplied by the caller.

    Returns:
        Lowercase source word.

    Raises:
        TypeError:
            If `source_word` is not a string.
        ValueError:
            If it is empty or contains whitespace.
    """
    if not isinstance(source_word, str):
        raise TypeError(
            f"Source words must be strings, not {type(source_word).__name__}."
        )
    if not source_word:
        raise ValueError("Source words cannot be empty.")
    if any(char.isspace() for char in source_word):
        raise ValueError(
            f"Source word must contain exactly one word and no whitespace: {source_word!r}"
        )
    return source_word.lower()
