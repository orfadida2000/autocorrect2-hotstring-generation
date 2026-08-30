import logging
import math
from dataclasses import InitVar, dataclass, field
from typing import Any, ClassVar

type ErrorType = str
type Probability = float
type TypoDistributionLabel = str
type TriggerWord = str
type NoisyWord = str
TypoData = tuple[NoisyWord, TriggerWord]  # (noisy_word, lowercase_target_word)


@dataclass(frozen=True, slots=True, kw_only=True)
class TypoDistribution:
    """Distribution of typo types for generating typos.

    A distribution is defined by the probabilities of generating each of the four types of typos: replacement, transposition, deletion, and insertion.
    When at least one of the four fields is not provided, the probabilities of the non-provided fields are computed as the complement of the sum of the provided fields, distributed uniformly among the non-provided fields.
    If all four fields are provided, the sum of the probabilities must equal 1.0 within a tolerance defined by [`ABSOLUTE_TOLERANCE`][].

    In order to make sure the final distribution is valid (i.e., the sum of probabilities equals exactly 1.0), the following rules are applied:
    1. Validate that all provided probabilities are between 0.0 and 1.0.
    2. Compute the sum of the provided probabilities, if equals 1.0 set the non-provided fields to 0.0 and skip to step 9.
    2. If not all four fields are provided skip to step 6.
    3. Validate that the sum of the probabilities equals 1.0 within the tolerance defined by [`ABSOLUTE_TOLERANCE`][].
    5. Find the field with the largest probability and adjust it to make the sum exactly 1.0 (i.e., `largest_field = 1.0 - sum(other_fields)`) and skip to step 9.
    6. If the sum of the provided probabilities does not exceed 1.0 skip to step 8, otherwise check if the sum is equal to 1.0 within the tolerance defined by [`ABSOLUTE_TOLERANCE`][], if not raise a ValueError.
    7. Perform the same logic as in step 5 but only for the provided fields, set the non-provided fields to 0.0, and skip to step 9.
    8. Compute the complement of the sum of the provided probabilities, divide it by n (number of non-provided fields), assign that value to the first n-1 non-provided fields, and assign the remaining to the last non-provided field (i.e., `non_provided_field_n = 1.0 - sum(other_fields)`).
    9. Store the final distribution in a private attribute [`_distribution`][] for later use.

    Attributes:
        ABSOLUTE_TOLERANCE: Tolerance for floating-point comparisons when checking if the sum of probabilities equals 1.0.
            Meaningful only when all 4 fields are provided.
        ORDER: The order of the error types in the distribution (used for consistent representation and comparison).
        replace: Probability of generating a replacement typo (init-only).
        transpose: Probability of generating a transposition typo (init-only).
        delete: Probability of generating a deletion typo (init-only).
        insert: Probability of generating an insertion typo (init-only).
        _distribution: Internal representation of the final distribution of typo types.
    """

    ABSOLUTE_TOLERANCE: ClassVar[float] = 1e-9
    ORDER: ClassVar[tuple[ErrorType, ...]] = ("replace", "transpose", "delete", "insert")

    replace: InitVar[Probability | None] = field(default=None)
    transpose: InitVar[Probability | None] = field(default=None)
    delete: InitVar[Probability | None] = field(default=None)
    insert: InitVar[Probability | None] = field(default=None)
    _distribution: dict[ErrorType, Probability] = field(init=False)

    def __post_init__(
        self,
        replace: Probability | None,
        transpose: Probability | None,
        delete: Probability | None,
        insert: Probability | None,
    ) -> None:
        provided: dict[ErrorType, Probability] = {}
        non_provided: set[ErrorType] = set()

        def process_field(err_type: ErrorType, value: Any) -> None:
            if value is None:
                non_provided.add(err_type)
                return

            if not isinstance(value, float):
                raise TypeError(
                    f"{err_type!r} must be a 'float' or 'None', got {type(value).__name__!r}."
                )

            if value is not None and not (0.0 <= value <= 1.0):
                raise ValueError(f"{err_type!r} must be between 0.0 and 1.0, got {value}.")

            provided[err_type] = value

        for err_type, value in (
            ("replace", replace),
            ("transpose", transpose),
            ("delete", delete),
            ("insert", insert),
        ):
            process_field(err_type, value)

        total_provided: Probability = sum(provided.values())

        if total_provided == 1.0:
            distribution = dict(provided)
            for err_type in non_provided:
                distribution[err_type] = 0.0
        elif len(provided) == 4:
            if not math.isclose(total_provided, 1.0, rel_tol=0.0, abs_tol=self.ABSOLUTE_TOLERANCE):
                raise ValueError(
                    f"Sum of provided probabilities must equal 1.0 within tolerance {self.ABSOLUTE_TOLERANCE}, got {total_provided}."
                )

            highest_error_type = max(provided, key=lambda k: provided[k])

            distribution = {
                err_type: provided[err_type]
                for err_type in provided
                if err_type != highest_error_type
            }
            distribution[highest_error_type] = 1.0 - sum(distribution.values())
        else:
            # len(provided) < 4 -> len(non_provided) > 0
            if total_provided < 1.0:
                distribution = dict(provided)
                non_provided_list = list(non_provided)

                complement = 1.0 - total_provided
                n_non_provided = len(non_provided)
                uniform_value = complement / n_non_provided

                distribution = dict.fromkeys(non_provided_list[:-1], uniform_value)

                distribution[non_provided_list[-1]] = 1.0 - sum(distribution.values())
            else:
                # total_provided > 1.0, since we already checked for total_provided == 1.0
                if not math.isclose(
                    total_provided, 1.0, rel_tol=0.0, abs_tol=self.ABSOLUTE_TOLERANCE
                ):
                    raise ValueError(
                        f"Sum of provided probabilities must equal 1.0 within tolerance {self.ABSOLUTE_TOLERANCE}, got {total_provided}."
                    )

                highest_error_type = max(provided, key=lambda k: provided[k])

                distribution = {
                    err_type: provided[err_type]
                    for err_type in provided
                    if err_type != highest_error_type
                }
                distribution[highest_error_type] = 1.0 - sum(distribution.values())
                for err_type in non_provided:
                    distribution[err_type] = 0.0

        distribution = {err_type: distribution[err_type] for err_type in self.ORDER}
        object.__setattr__(self, "_distribution", distribution)

    @property
    def distribution(self) -> dict[ErrorType, Probability]:
        return dict(self._distribution)

    def _items(self) -> tuple[tuple[ErrorType, Probability], ...]:
        return tuple((err_type, self._distribution[err_type]) for err_type in self.ORDER)

    def __repr__(self) -> str:
        value_pairs_str = ", ".join(
            f"{err_type}={self._distribution[err_type]:.3g}" for err_type in self.ORDER
        )

        return f"{type(self).__name__}({value_pairs_str})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypoDistribution):
            return NotImplemented

        return self._items() == other._items()

    def __hash__(self) -> int:
        return hash(self._items())


@dataclass(frozen=True, slots=True)
class LoggingContext:
    """Snapshot of process-wide logging state needed by worker processes.

    A context captures the global logging disable threshold, exception behavior,
    and root logger level in the parent process. Call [`apply`][]
    inside a spawned worker to restore those settings before fitting begins.

    Attributes:
        disable_level: Global logging disable threshold captured from the parent.
        raise_exceptions: Whether logging handler exceptions should propagate.
        root_logger_level: Effective root logger level to apply in the worker.
    """

    disable_level: int = field(init=False)
    raise_exceptions: bool = field(init=False)
    root_logger_level: int = field(init=False)

    def __post_init__(self) -> None:
        # Captures current global state from the logging module
        """Capture the current process-wide logging state.

        The captured values are stored on the frozen instance so they can later be
        reapplied inside spawned worker processes.
        """
        object.__setattr__(self, "disable_level", logging.root.manager.disable)
        object.__setattr__(self, "raise_exceptions", logging.raiseExceptions)
        object.__setattr__(self, "root_logger_level", logging.getLogger().level)

    def apply(self) -> None:
        """Apply the captured logging state to the current process.

        This restores the global disable threshold, logging exception behavior, and
        root logger level recorded when the context was created.
        """
        logging.disable(self.disable_level)
        logging.raiseExceptions = self.raise_exceptions
        logging.getLogger().setLevel(self.root_logger_level)
