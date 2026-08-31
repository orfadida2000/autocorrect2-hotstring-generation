"""Detect trigger-recognition conflicts between candidate and existing hotstrings.

Candidate support is intentionally limited only by matching semantics that
the current algorithm has not implemented. Options unrelated to trigger
recognition, such as backspacing, execution, priority, send mode, or
replacement mode, do not affect whether conflict checking is supported.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum

from .constants import DEFAULT_ENDING_CHARS, DEFAULT_HOTSTRING_OPTIONS
from .models import CandidateHotstring, ExistingHotstring
from .options import CaseMode, ResolvedHotstringOptions, SettingState


class ConflictKind(Enum):
    """Classify why two hotstrings conflict.

    Attributes:
        SAME_TRIGGER:
            Candidate and existing definitions overlap on the same trigger.
        EXISTING_FIRES_DURING_CANDIDATE:
            The existing definition can become eligible while the candidate
            trigger is being typed.
        CANDIDATE_FIRES_DURING_EXISTING:
            The candidate can become eligible while the existing trigger is
            being typed.
    """

    SAME_TRIGGER = "same trigger"
    EXISTING_FIRES_DURING_CANDIDATE = (
        "existing hotstring can activate while candidate is typed"
    )
    CANDIDATE_FIRES_DURING_EXISTING = (
        "candidate can activate while existing hotstring is typed"
    )


@dataclass(frozen=True, slots=True)
class HotstringConflict:
    """Describe one conflict between a candidate and an existing definition.

    Attributes:
        candidate:
            Candidate involved in the conflict.
        existing:
            Existing definition involved in the conflict.
        kind:
            Conflict classification.
        reason:
            Human-readable explanation of the matching overlap.
    """

    candidate: CandidateHotstring
    existing: ExistingHotstring
    kind: ConflictKind
    reason: str


@dataclass(frozen=True, slots=True)
class CandidateAssessment:
    """Represent all conflicts discovered for one candidate.

    Attributes:
        candidate:
            Candidate that was checked.
        conflicts:
            All conflicting existing hotstrings.
    """

    candidate: CandidateHotstring
    conflicts: tuple[HotstringConflict, ...]

    @property
    def is_accepted(self) -> bool:
        """Return whether the candidate has no detected conflicts.

        Returns:
            Whether the candidate is conflict-free.
        """
        return not self.conflicts


@dataclass(frozen=True, slots=True)
class _TriggerOverlap:
    """Describe a trigger occurrence satisfying both recognition boundaries.

    Attributes:
        start:
            Inclusive start index inside the containing trigger.
        end:
            Exclusive end index inside the containing trigger.
        left_reason:
            Explanation of the valid left boundary.
        right_reason:
            Explanation of the valid right boundary.
    """

    start: int
    end: int
    left_reason: str
    right_reason: str

    @property
    def reason(self) -> str:
        """Return the combined boundary explanation.

        Returns:
            Human-readable explanation of both boundaries.
        """
        return f"{self.left_reason}; {self.right_reason}"


def find_conflict(
    candidate: CandidateHotstring,
    existing: ExistingHotstring,
    *,
    ending_chars: frozenset[str] = DEFAULT_ENDING_CHARS,
    option_defaults: ResolvedHotstringOptions = DEFAULT_HOTSTRING_OPTIONS,
) -> HotstringConflict | None:
    """Check one candidate against one existing hotstring.

    Args:
        candidate:
            Candidate to check.
        existing:
            Existing definition to compare against.
        ending_chars:
            Effective AutoHotkey ending-character set.
        option_defaults:
            Fully resolved defaults applicable to inherited hotstring options.

    Returns:
        Detected conflict, or `None` when the pair does not conflict.

    Raises:
        NotImplementedError:
            If the candidate uses unsupported effective matching semantics.
    """
    candidate_options = ResolvedHotstringOptions.from_options(
        candidate.options,
        defaults=option_defaults,
    )
    _ensure_supported_candidate_matching(candidate_options)

    existing_options = ResolvedHotstringOptions.from_options(
        existing.options,
        defaults=option_defaults,
    )

    return _find_supported_candidate_conflict(
        candidate,
        candidate_options,
        existing,
        existing_options,
        ending_chars=ending_chars,
    )


def assess_candidate(
    candidate: CandidateHotstring,
    existing_hotstrings: Sequence[ExistingHotstring],
    *,
    ending_chars: frozenset[str] = DEFAULT_ENDING_CHARS,
    option_defaults: ResolvedHotstringOptions = DEFAULT_HOTSTRING_OPTIONS,
) -> CandidateAssessment:
    """Check one candidate against all existing definitions.

    Args:
        candidate:
            Candidate to evaluate.
        existing_hotstrings:
            Existing definitions to compare against.
        ending_chars:
            Effective AutoHotkey ending-character set.
        option_defaults:
            Fully resolved defaults applicable to inherited hotstring options.

    Returns:
        Complete candidate assessment.

    Raises:
        NotImplementedError:
            If the candidate uses unsupported effective matching semantics.
    """
    candidate_options = ResolvedHotstringOptions.from_options(
        candidate.options,
        defaults=option_defaults,
    )
    _ensure_supported_candidate_matching(candidate_options)

    conflicts: list[HotstringConflict] = []
    for existing in existing_hotstrings:
        existing_options = ResolvedHotstringOptions.from_options(
            existing.options,
            defaults=option_defaults,
        )
        conflict = _find_supported_candidate_conflict(
            candidate,
            candidate_options,
            existing,
            existing_options,
            ending_chars=ending_chars,
        )
        if conflict is not None:
            conflicts.append(conflict)

    return CandidateAssessment(candidate=candidate, conflicts=tuple(conflicts))


def assess_candidates(
    candidates: Sequence[CandidateHotstring],
    existing_hotstrings: Sequence[ExistingHotstring],
    *,
    ending_chars: frozenset[str] = DEFAULT_ENDING_CHARS,
    option_defaults: ResolvedHotstringOptions = DEFAULT_HOTSTRING_OPTIONS,
) -> tuple[CandidateAssessment, ...]:
    """Check multiple candidates against all existing definitions.

    Candidate-to-candidate checking is intentionally not performed here;
    typo-generation aggregation handles internal candidate ambiguity before
    the full pipeline reaches this stage.

    Args:
        candidates:
            Candidates to evaluate.
        existing_hotstrings:
            Existing definitions to compare against.
        ending_chars:
            Effective AutoHotkey ending-character set.
        option_defaults:
            Fully resolved defaults applicable to inherited hotstring options.

    Returns:
        Candidate assessments in input order.

    Raises:
        NotImplementedError:
            If any candidate uses unsupported effective matching semantics.
    """
    return tuple(
        assess_candidate(
            candidate,
            existing_hotstrings,
            ending_chars=ending_chars,
            option_defaults=option_defaults,
        )
        for candidate in candidates
    )


def _ensure_supported_candidate_matching(options: ResolvedHotstringOptions) -> None:
    """Validate that candidate recognition semantics are implemented.

    Args:
        options:
            Fully resolved candidate options.

    Raises:
        NotImplementedError:
            If the candidate omits the ending-character requirement, permits
            inside-word matching, or matches case-sensitively.
    """
    unsupported: list[str] = []
    if options.ending_character_optional is SettingState.ENABLED:
        unsupported.append("ending-character-free matching ('*')")
    if options.trigger_inside_word is SettingState.ENABLED:
        unsupported.append("inside-word matching ('?')")
    if options.case_mode is CaseMode.SENSITIVE:
        unsupported.append("case-sensitive matching ('C')")

    if unsupported:
        raise NotImplementedError(
            "Conflict checking is not yet implemented for candidate matching "
            "semantics using " + ", ".join(unsupported) + "."
        )


def _find_supported_candidate_conflict(
    candidate: CandidateHotstring,
    candidate_options: ResolvedHotstringOptions,
    existing: ExistingHotstring,
    existing_options: ResolvedHotstringOptions,
    *,
    ending_chars: frozenset[str],
) -> HotstringConflict | None:
    """Check one existing definition against a supported candidate.

    Args:
        candidate:
            Candidate whose matching semantics are supported.
        candidate_options:
            Fully resolved candidate options.
        existing:
            Existing definition.
        existing_options:
            Fully resolved existing options.
        ending_chars:
            Effective ending-character set.

    Returns:
        Detected conflict, or `None`.
    """
    if candidate.trigger.casefold() == existing.trigger.casefold():
        return HotstringConflict(
            candidate=candidate,
            existing=existing,
            kind=ConflictKind.SAME_TRIGGER,
            reason=(
                "The candidate and existing hotstring have the same "
                "case-insensitive trigger."
            ),
        )

    existing_overlap = next(
        _iter_trigger_overlaps(
            trigger=existing.trigger,
            container=candidate.trigger,
            allow_alphanumeric_predecessor=(
                existing_options.trigger_inside_word is SettingState.ENABLED
            ),
            require_ending_character=(
                existing_options.ending_character_optional is SettingState.DISABLED
            ),
            case_sensitive=existing_options.case_mode is CaseMode.SENSITIVE,
            ending_chars=ending_chars,
        ),
        None,
    )
    if existing_overlap is not None:
        return HotstringConflict(
            candidate=candidate,
            existing=existing,
            kind=ConflictKind.EXISTING_FIRES_DURING_CANDIDATE,
            reason=(
                "The existing hotstring can activate while the candidate is "
                f"being typed: {existing_overlap.reason}."
            ),
        )

    candidate_overlap = next(
        _iter_trigger_overlaps(
            trigger=candidate.trigger,
            container=existing.trigger,
            allow_alphanumeric_predecessor=(
                candidate_options.trigger_inside_word is SettingState.ENABLED
            ),
            require_ending_character=(
                candidate_options.ending_character_optional is SettingState.DISABLED
            ),
            case_sensitive=candidate_options.case_mode is CaseMode.SENSITIVE,
            ending_chars=ending_chars,
        ),
        None,
    )
    if candidate_overlap is not None:
        return HotstringConflict(
            candidate=candidate,
            existing=existing,
            kind=ConflictKind.CANDIDATE_FIRES_DURING_EXISTING,
            reason=(
                "The candidate can activate while the existing hotstring is "
                f"being typed: {candidate_overlap.reason}."
            ),
        )

    return None


def _iter_trigger_overlaps(
    *,
    trigger: str,
    container: str,
    allow_alphanumeric_predecessor: bool,
    require_ending_character: bool,
    case_sensitive: bool,
    ending_chars: frozenset[str],
) -> Iterator[_TriggerOverlap]:
    """Yield occurrences satisfying both trigger-recognition boundaries.

    Args:
        trigger:
            Trigger whose activation is being tested.
        container:
            Other trigger being typed around it.
        allow_alphanumeric_predecessor:
            Whether an alphanumeric predecessor is permitted.
        require_ending_character:
            Whether activation requires an ending character.
        case_sensitive:
            Whether exact trigger casing is required.
        ending_chars:
            Effective ending-character set.

    Yields:
        Every boundary-valid occurrence.
    """
    if len(trigger) > len(container):
        return

    for start in _iter_occurrence_starts(
        trigger=trigger,
        container=container,
        case_sensitive=case_sensitive,
    ):
        end = start + len(trigger)
        left_reason = _left_boundary_reason(
            container=container,
            start=start,
            allow_alphanumeric_predecessor=allow_alphanumeric_predecessor,
        )
        if left_reason is None:
            continue

        right_reason = _right_boundary_reason(
            container=container,
            end=end,
            require_ending_character=require_ending_character,
            ending_chars=ending_chars,
        )
        if right_reason is None:
            continue

        yield _TriggerOverlap(
            start=start,
            end=end,
            left_reason=left_reason,
            right_reason=right_reason,
        )


def _iter_occurrence_starts(
    *, trigger: str, container: str, case_sensitive: bool
) -> Iterator[int]:
    """Yield every trigger occurrence start, including overlaps.

    Args:
        trigger:
            Trigger to locate.
        container:
            Text in which to locate it.
        case_sensitive:
            Whether exact casing is required.

    Yields:
        Start index of each occurrence.
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(rf"(?={re.escape(trigger)})", flags)
    for match in pattern.finditer(container):
        yield match.start()


def _left_boundary_reason(
    *, container: str, start: int, allow_alphanumeric_predecessor: bool
) -> str | None:
    """Evaluate the left boundary of one occurrence.

    Args:
        container:
            Trigger containing the occurrence.
        start:
            Occurrence start index.
        allow_alphanumeric_predecessor:
            Whether an alphanumeric predecessor is allowed.

    Returns:
        Explanation of a valid boundary, or `None` when invalid.
    """
    if start == 0:
        return "the occurrence starts at the beginning"

    preceding_char = container[start - 1]
    if not preceding_char.isalnum():
        return f"the preceding character {preceding_char!r} is non-alphanumeric"
    if allow_alphanumeric_predecessor:
        return (
            f"the preceding character {preceding_char!r} is alphanumeric, "
            "but the hotstring permits an alphanumeric predecessor"
        )
    return None


def _right_boundary_reason(
    *,
    container: str,
    end: int,
    require_ending_character: bool,
    ending_chars: frozenset[str],
) -> str | None:
    """Evaluate the right boundary of one occurrence.

    Args:
        container:
            Trigger containing the occurrence.
        end:
            Exclusive occurrence end index.
        require_ending_character:
            Whether activation requires an ending character.
        ending_chars:
            Effective ending-character set.

    Returns:
        Explanation of a valid boundary, or `None` when invalid.
    """
    if not require_ending_character:
        return "the hotstring does not require an ending character"
    if end == len(container):
        return (
            "the occurrence reaches the end of the containing trigger, so a "
            "subsequently typed ending character can activate it"
        )

    following_char = container[end]
    if following_char in ending_chars:
        return f"the following character {following_char!r} is an ending character"
    return None
