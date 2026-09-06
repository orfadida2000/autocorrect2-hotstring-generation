"""Define task, configuration, and result models for typo generation."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True, slots=True)
class TypoWeightDistribution:
    """Represent the weight mapping of the MULTYPO typo operations.

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


REPLACE_ONLY_TYPO_DISTRIBUTION = TypoWeightDistribution(replace=1.0)
"""Distribution that selects only replacement errors."""

TRANSPOSE_ONLY_TYPO_DISTRIBUTION = TypoWeightDistribution(transpose=1.0)
"""Distribution that selects only transposition errors."""

DELETE_ONLY_TYPO_DISTRIBUTION = TypoWeightDistribution(delete=1.0)
"""Distribution that selects only deletion errors."""

INSERT_ONLY_TYPO_DISTRIBUTION = TypoWeightDistribution(insert=1.0)
"""Distribution that selects only insertion errors."""

DEFAULT_SINGLE_ERROR_TYPO_DISTRIBUTIONS: tuple[TypoWeightDistribution, ...] = (
    REPLACE_ONLY_TYPO_DISTRIBUTION,
    TRANSPOSE_ONLY_TYPO_DISTRIBUTION,
    DELETE_ONLY_TYPO_DISTRIBUTION,
    INSERT_ONLY_TYPO_DISTRIBUTION,
)
"""Default single-error distributions, one for each supported operation type."""

DEFAULT_MIXED_ERROR_TYPO_DISTRIBUTION = TypoWeightDistribution(
    replace=0.28,
    transpose=0.28,
    delete=0.28,
    insert=0.15,
)
"""Mixed distribution mirroring MULTYPO's built-in operation weights."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TypoGenerationTask:
    """Describe one independently executable typo-generation task.

    A task contains only settings that may reasonably vary between work items.
    The source word list and keyboard/generator environment are shared by all
    tasks in a generation run.

    Attributes:
        distribution:
            Typo-operation distribution used by the task.
        typo_rate:
            MULTYPO typo rate passed directly to `insert_typos`. For a
            single-word input, `1.0` requests one typo operation and `2.0`
            requests two operations.
        generation_attempts_per_word:
            Number of independent MULTYPO samples requested for each eligible
            source word.
        minimum_word_length:
            Minimum source-word length eligible for this task. This allows
            multi-error tasks to exclude short words without duplicating the
            source word collection.
    """

    distribution: TypoWeightDistribution
    typo_rate: float
    generation_attempts_per_word: int
    minimum_word_length: int

    def __post_init__(self) -> None:
        """Validate the task definition.

        Raises:
            TypeError:
                If a field has an invalid type.
            ValueError:
                If the typo rate, attempt count, or minimum length is not
                positive enough to be meaningful.
        """
        if not isinstance(self.distribution, TypoWeightDistribution):
            raise TypeError(
                "distribution must be a TypoDistribution instance, "
                f"not {type(self.distribution).__name__}."
            )

        if isinstance(self.typo_rate, bool) or not isinstance(self.typo_rate, Real):
            raise TypeError("typo_rate must be a real number.")
        if self.typo_rate <= 0:
            raise ValueError("typo_rate must be greater than zero.")

        if isinstance(self.generation_attempts_per_word, bool) or not isinstance(
            self.generation_attempts_per_word, int
        ):
            raise TypeError("generation_attempts_per_word must be an integer.")
        if self.generation_attempts_per_word <= 0:
            raise ValueError("generation_attempts_per_word must be greater than zero.")

        if isinstance(self.minimum_word_length, bool) or not isinstance(
            self.minimum_word_length, int
        ):
            raise TypeError("minimum_word_length must be an integer.")
        if self.minimum_word_length < 2:
            raise ValueError("minimum_word_length must be at least 2.")


@dataclass(frozen=True, slots=True, kw_only=True)
class TypoGenerationConfig:
    """Configure generator settings shared by every task in one run.

    Execution mechanics such as worker count and task-specific sampling
    settings are deliberately kept outside this model.

    Attributes:
        language:
            MULTYPO language identifier.
        use_excluding_set:
            Whether MULTYPO's language excluding set is enabled.
        horizontal_vs_vertical:
            Relative horizontal and vertical keyboard-neighbor weights.
    """

    language: str = "english"
    use_excluding_set: bool = True
    horizontal_vs_vertical: tuple[float, float] = (9.0, 1.0)

    def __post_init__(self) -> None:
        """Validate shared typo-generation configuration.

        Raises:
            TypeError:
                If a configuration value has an invalid type.
            ValueError:
                If the language is empty or keyboard weights are invalid.
        """
        if not isinstance(self.language, str):
            raise TypeError("language must be a string.")
        if not self.language:
            raise ValueError("language cannot be empty.")

        if not isinstance(self.use_excluding_set, bool):
            raise TypeError("use_excluding_set must be a boolean.")

        if not isinstance(self.horizontal_vs_vertical, tuple):
            raise TypeError("horizontal_vs_vertical must be a tuple.")
        if len(self.horizontal_vs_vertical) != 2:
            raise ValueError("horizontal_vs_vertical must contain exactly two weights.")
        for weight in self.horizontal_vs_vertical:
            if isinstance(weight, bool) or not isinstance(weight, Real):
                raise TypeError("Keyboard-neighbor weights must be real numbers.")
            if weight <= 0:
                raise ValueError("Keyboard-neighbor weights must be positive.")


def create_default_typo_generation_tasks(
    *,
    single_error_attempts_per_word: int,
    multi_error_attempts_per_word: int,
    multi_error_minimum_word_length: int,
) -> tuple[TypoGenerationTask, ...]:
    """Create the project's default single- and two-error task set.

    The four single-error tasks force one MULTYPO operation type each with
    `typo_rate=1.0`. A fifth mixed task requests two typo operations per word
    with `typo_rate=2.0`. Sampling budgets and the multi-error minimum word
    length remain caller-controlled rather than being hidden policy constants.

    Args:
        single_error_attempts_per_word:
            Sampling attempts per eligible word for each forced single-error
            task.
        multi_error_attempts_per_word:
            Sampling attempts per eligible word for the mixed two-error task.
        multi_error_minimum_word_length:
            Minimum word length for the mixed two-error task.

    Returns:
        Ordered default task tuple.

    Raises:
        TypeError:
            If an argument has an invalid type.
        ValueError:
            If an argument violates `TypoGenerationTask` validation.
    """
    single_error_tasks = tuple(
        TypoGenerationTask(
            distribution=distribution,
            typo_rate=1.0,
            generation_attempts_per_word=single_error_attempts_per_word,
            minimum_word_length=2,
        )
        for distribution in DEFAULT_SINGLE_ERROR_TYPO_DISTRIBUTIONS
    )

    multi_error_task = TypoGenerationTask(
        distribution=DEFAULT_MIXED_ERROR_TYPO_DISTRIBUTION,
        typo_rate=2.0,
        generation_attempts_per_word=multi_error_attempts_per_word,
        minimum_word_length=multi_error_minimum_word_length,
    )

    return (*single_error_tasks, multi_error_task)


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
            Shared generator configuration used for generation.
        tasks:
            Ordered generation tasks that were executed.
        source_word_count:
            Number of source words supplied before per-task length filtering.
        generated_sample_count:
            Number of successful raw samples before deduplication.
        candidates:
            Unique noisy-word to target-word mappings.
        clashes:
            Noisy words that mapped to more than one target word.
    """

    config: TypoGenerationConfig
    tasks: tuple[TypoGenerationTask, ...]
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
