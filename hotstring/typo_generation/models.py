"""Define configuration and result models for typo generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Real


@dataclass(frozen=True, slots=True)
class TypoDistribution:
    """Represent the relative probabilities of MULTYPO typo operations.

    Values are non-negative weights. MULTYPO normalizes the supplied mapping,
    so they do not need to sum to one.

    Attributes:
        replace:
            Replacement-operation weight.
        transpose:
            Transposition-operation weight.
        delete:
            Deletion-operation weight.
        insert:
            Insertion-operation weight.
    """

    replace: float = 0.0
    transpose: float = 0.0
    delete: float = 0.0
    insert: float = 0.0

    def __post_init__(self) -> None:
        """Validate typo-distribution weights.

        Raises:
            TypeError:
                If a weight is not a real number or is a boolean.
            ValueError:
                If a weight is negative or all weights are zero.
        """
        values = (self.replace, self.transpose, self.delete, self.insert)
        for value in values:
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError("Typo distribution weights must be real numbers.")
            if value < 0:
                raise ValueError("Typo distribution weights cannot be negative.")
        if not any(value > 0 for value in values):
            raise ValueError("At least one typo distribution weight must be positive.")

    @property
    def distribution(self) -> dict[str, float]:
        """Return the mapping expected by `MultiTypoGenerator`.

        Returns:
            Typo-operation weight mapping.
        """
        return {
            "replace": float(self.replace),
            "transpose": float(self.transpose),
            "delete": float(self.delete),
            "insert": float(self.insert),
        }


DEFAULT_TYPO_DISTRIBUTIONS: tuple[TypoDistribution, ...] = (
    TypoDistribution(replace=1.0),
    TypoDistribution(transpose=1.0),
    TypoDistribution(delete=1.0),
    TypoDistribution(insert=1.0),
)
"""Default replace-, transpose-, delete-, and insert-only distributions."""


@dataclass(frozen=True, slots=True)
class TypoGenerationConfig:
    """Configure the semantic behavior of typo generation.

    Execution mechanics such as worker count are deliberately kept outside
    this model because they do not change the requested generated sample set.

    Attributes:
        generation_attempts_per_word:
            Independent MULTYPO sampling attempts for each source word and
            each selected distribution.
        typo_distributions:
            Ordered typo distributions to sample.
        language:
            MULTYPO language identifier.
        use_excluding_set:
            Whether MULTYPO's language excluding set is enabled.
        horizontal_vs_vertical:
            Relative horizontal and vertical keyboard-neighbor weights.
    """

    generation_attempts_per_word: int
    typo_distributions: tuple[TypoDistribution, ...] = field(
        default_factory=lambda: DEFAULT_TYPO_DISTRIBUTIONS
    )
    language: str = "english"
    use_excluding_set: bool = True
    horizontal_vs_vertical: tuple[float, float] = (9.0, 1.0)

    def __post_init__(self) -> None:
        """Validate typo-generation configuration.

        Raises:
            TypeError:
                If configuration values have invalid types.
            ValueError:
                If attempts are non-positive, distributions are empty or
                duplicated, or keyboard weights are invalid.
        """
        if isinstance(self.generation_attempts_per_word, bool) or not isinstance(
            self.generation_attempts_per_word, int
        ):
            raise TypeError("generation_attempts_per_word must be an integer.")
        if self.generation_attempts_per_word <= 0:
            raise ValueError("generation_attempts_per_word must be greater than zero.")
        if not self.typo_distributions:
            raise ValueError("At least one typo distribution must be provided.")
        if len(set(self.typo_distributions)) != len(self.typo_distributions):
            raise ValueError("Duplicate typo distributions are not allowed.")
        if not isinstance(self.language, str):
            raise TypeError("language must be a string.")
        if not self.language:
            raise ValueError("language cannot be empty.")
        if not isinstance(self.use_excluding_set, bool):
            raise TypeError("use_excluding_set must be a boolean.")
        if len(self.horizontal_vs_vertical) != 2:
            raise ValueError("horizontal_vs_vertical must contain exactly two weights.")
        for weight in self.horizontal_vs_vertical:
            if isinstance(weight, bool) or not isinstance(weight, Real):
                raise TypeError("Keyboard-neighbor weights must be real numbers.")
            if weight <= 0:
                raise ValueError("Keyboard-neighbor weights must be positive.")


@dataclass(frozen=True, slots=True)
class RawTypoSample:
    """Represent one successful noisy-word sample.

    Attributes:
        noisy_word:
            Generated typo candidate.
        target_word:
            Correct source word the typo should map back to.
    """

    noisy_word: str
    target_word: str


@dataclass(frozen=True, slots=True)
class TypoGenerationResult:
    """Represent aggregated output of the typo-generation stage.

    Attributes:
        config:
            Semantic configuration used for generation.
        source_word_count:
            Number of source words supplied.
        generated_sample_count:
            Number of successful raw samples before deduplication.
        candidates:
            Unique noisy-word to target-word mappings.
        clashes:
            Noisy words that mapped to more than one target word.
    """

    config: TypoGenerationConfig
    source_word_count: int
    generated_sample_count: int
    candidates: dict[str, str]
    clashes: dict[str, tuple[str, ...]]

    @property
    def unique_noisy_word_count(self) -> int:
        """Return the number of unique noisy forms after aggregation.

        Returns:
            Candidate count plus internal clash count.
        """
        return len(self.candidates) + len(self.clashes)
