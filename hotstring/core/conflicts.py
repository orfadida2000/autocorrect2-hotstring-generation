"""Detect trigger-recognition conflicts between candidate and existing hotstrings.

Conflict detection models the three trigger-recognition dimensions relevant to
whether two hotstrings can activate on overlapping typed text:

- case sensitivity (`C` / `C0` / `C1`);
- whether an alphanumeric predecessor is permitted (`?` / `?0`);
- whether an ending character is required (`*` / `*0`).

Other hotstring options affect replacement or execution behavior rather than
trigger recognition and therefore do not restrict conflict checking.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from enum import Enum

from .constants import DEFAULT_ENDING_CHARS, DEFAULT_HOTSTRING_OPTIONS
from .models import CandidateHotstring, ExistingHotstring, Hotstring
from .options import CaseMode, ResolvedHotstringOptions, SettingState
from .trigger import make_case_insensitive_trigger_key


class ConflictKind(Enum):
    """Classify why two hotstrings conflict.

    Attributes:
        SAME_TRIGGER:
            Candidate and existing definitions can recognize the same complete
            trigger text.
        EXISTING_FIRES_DURING_CANDIDATE:
            The existing definition can become eligible while a valid typed
            form of the candidate trigger is being entered.
        CANDIDATE_FIRES_DURING_EXISTING:
            The candidate can become eligible while a valid typed form of the
            existing trigger is being entered.
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
            Inclusive start index inside the containing semantic trigger.
        end:
            Exclusive end index inside the containing semantic trigger.
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

    All combinations of case sensitivity, inside-word recognition, and
    ending-character requirements are supported for both definitions.

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
    """
    candidate_options = ResolvedHotstringOptions.from_options(
        candidate.options,
        defaults=option_defaults,
    )
    existing_options = ResolvedHotstringOptions.from_options(
        existing.options,
        defaults=option_defaults,
    )

    return _find_candidate_conflict(
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
    """
    candidate_options = ResolvedHotstringOptions.from_options(
        candidate.options,
        defaults=option_defaults,
    )

    conflicts: list[HotstringConflict] = []
    for existing in existing_hotstrings:
        existing_options = ResolvedHotstringOptions.from_options(
            existing.options,
            defaults=option_defaults,
        )
        conflict = _find_candidate_conflict(
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
            Effective ending-character set.
        option_defaults:
            Fully resolved defaults applicable to inherited hotstring options.

    Returns:
        Candidate assessments in input order.
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


def _find_candidate_conflict(
    candidate: CandidateHotstring,
    candidate_options: ResolvedHotstringOptions,
    existing: ExistingHotstring,
    existing_options: ResolvedHotstringOptions,
    *,
    ending_chars: frozenset[str],
) -> HotstringConflict | None:
    """Check one existing definition against one candidate.

    Args:
        candidate:
            Candidate definition.
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
    candidate_case_sensitive = candidate_options.case_mode is CaseMode.SENSITIVE
    existing_case_sensitive = existing_options.case_mode is CaseMode.SENSITIVE

    if _same_trigger_can_match(
        candidate,
        candidate_case_sensitive=candidate_case_sensitive,
        existing=existing,
        existing_case_sensitive=existing_case_sensitive,
    ):
        return HotstringConflict(
            candidate=candidate,
            existing=existing,
            kind=ConflictKind.SAME_TRIGGER,
            reason=(
                "The candidate and existing hotstring can recognize the same "
                "complete trigger text."
            ),
        )

    existing_overlap = next(
        _iter_trigger_overlaps(
            trigger=existing,
            container=candidate,
            allow_alphanumeric_predecessor=(
                existing_options.trigger_inside_word is SettingState.ENABLED
            ),
            require_ending_character=(
                existing_options.ending_character_optional is SettingState.DISABLED
            ),
            trigger_case_sensitive=existing_case_sensitive,
            container_case_sensitive=candidate_case_sensitive,
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
            trigger=candidate,
            container=existing,
            allow_alphanumeric_predecessor=(
                candidate_options.trigger_inside_word is SettingState.ENABLED
            ),
            require_ending_character=(
                candidate_options.ending_character_optional is SettingState.DISABLED
            ),
            trigger_case_sensitive=candidate_case_sensitive,
            container_case_sensitive=existing_case_sensitive,
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


def _same_trigger_can_match(
    candidate: Hotstring,
    *,
    candidate_case_sensitive: bool,
    existing: Hotstring,
    existing_case_sensitive: bool,
) -> bool:
    """Return whether two complete trigger definitions share a typed form.

    If both hotstrings are case-sensitive, their semantic triggers must match
    exactly. If either definition is case-insensitive, a shared casing exists
    whenever their AutoHotkey-compatible case-insensitive keys are equal.

    Args:
        candidate:
            First hotstring.
        candidate_case_sensitive:
            Whether the first hotstring requires exact case.
        existing:
            Second hotstring.
        existing_case_sensitive:
            Whether the second hotstring requires exact case.

    Returns:
        Whether the two complete trigger definitions can recognize the same
        typed text.
    """
    if candidate_case_sensitive and existing_case_sensitive:
        return candidate.semantic_trigger == existing.semantic_trigger

    return (
        candidate.case_insensitive_semantic_trigger_key
        == existing.case_insensitive_semantic_trigger_key
    )


def _iter_trigger_overlaps(
    *,
    trigger: Hotstring,
    container: Hotstring,
    allow_alphanumeric_predecessor: bool,
    require_ending_character: bool,
    trigger_case_sensitive: bool,
    container_case_sensitive: bool,
    ending_chars: frozenset[str],
) -> Iterator[_TriggerOverlap]:
    """Yield occurrences satisfying trigger recognition and both boundaries.

    `trigger` is the hotstring whose ability to activate is being tested.
    `container` is the other hotstring whose trigger is being typed.

    Case handling must consider *both* definitions. If both are case-sensitive,
    only the exact source-defined casing of the container is a valid typed
    form. If either is case-insensitive, a shared casing can exist for an
    occurrence whenever the corresponding case-insensitive keys match.

    Args:
        trigger:
            Hotstring whose activation is being tested.
        container:
            Other hotstring whose semantic trigger is being typed around it.
        allow_alphanumeric_predecessor:
            Whether the tested hotstring permits an alphanumeric predecessor.
        require_ending_character:
            Whether the tested hotstring requires an ending character.
        trigger_case_sensitive:
            Whether the tested hotstring requires exact trigger casing.
        container_case_sensitive:
            Whether the containing hotstring requires exact trigger casing.
        ending_chars:
            Effective ending-character set.

    Yields:
        Every boundary-valid occurrence.
    """
    if len(trigger.semantic_trigger) > len(container.semantic_trigger):
        return

    require_exact_case = trigger_case_sensitive and container_case_sensitive

    for start in _iter_hotstring_occurrence_starts(
        trigger=trigger,
        container=container,
        require_exact_case=require_exact_case,
    ):
        end = start + len(trigger.semantic_trigger)

        left_reason = _left_boundary_reason(
            container=container.semantic_trigger,
            start=start,
            allow_alphanumeric_predecessor=allow_alphanumeric_predecessor,
        )
        if left_reason is None:
            continue

        right_reason = _right_boundary_reason(
            container=container.semantic_trigger,
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


def _iter_hotstring_occurrence_starts(
    *,
    trigger: Hotstring,
    container: Hotstring,
    require_exact_case: bool,
) -> Iterator[int]:
    """Yield semantic occurrence starts under the required case semantics.

    The normal Windows path searches the already cached semantic or
    case-insensitive trigger strings directly. A defensive fallback preserves
    original semantic indices if a non-Windows `str.lower()` transformation
    changes Unicode string length.

    Args:
        trigger:
            Hotstring whose semantic trigger is being located.
        container:
            Hotstring whose semantic trigger is being searched.
        require_exact_case:
            Whether both definitions require exact casing.

    Yields:
        Start index of each occurrence in `container.semantic_trigger`.
    """
    if require_exact_case:
        yield from _iter_occurrence_starts(
            trigger=trigger.semantic_trigger,
            container=container.semantic_trigger,
        )
        return

    trigger_key = trigger.case_insensitive_semantic_trigger_key
    container_key = container.case_insensitive_semantic_trigger_key

    if (
        len(trigger_key) == len(trigger.semantic_trigger)
        and len(container_key) == len(container.semantic_trigger)
    ):
        yield from _iter_occurrence_starts(
            trigger=trigger_key,
            container=container_key,
        )
        return

    trigger_length = len(trigger.semantic_trigger)
    for start in range(len(container.semantic_trigger) - trigger_length + 1):
        segment = container.semantic_trigger[start : start + trigger_length]
        if make_case_insensitive_trigger_key(segment) == trigger_key:
            yield start


def _iter_occurrence_starts(*, trigger: str, container: str) -> Iterator[int]:
    """Yield every exact string occurrence start, including overlaps.

    Repeated `str.find()` is used instead of a regex lookahead. Advancing the
    next search by one character, rather than by the matched trigger length,
    preserves overlapping occurrences such as both `ana` matches in
    `banana`.

    Args:
        trigger:
            Exact string to locate.
        container:
            String in which to locate it.

    Yields:
        Start index of each occurrence.
    """
    start = container.find(trigger)
    while start != -1:
        yield start
        start = container.find(trigger, start + 1)


def _left_boundary_reason(
    *, container: str, start: int, allow_alphanumeric_predecessor: bool
) -> str | None:
    """Evaluate the left boundary of one occurrence.

    Args:
        container:
            Semantic trigger containing the occurrence.
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
            Semantic trigger containing the occurrence.
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
