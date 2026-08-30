"""Inspect AutoCorrect2 hotstring definitions for candidate contradictions.

This module extracts statically defined AutoHotkey hotstrings from the configured
AutoCorrect2 source files and checks proposed autocorrection candidates against
those definitions.

Candidates are supplied as a mapping whose keys are typo triggers and whose
values are their intended replacements. Each candidate is assumed to use the
AutoCorrect2 ``B0X`` form and therefore has the following matching semantics:

- Matching is case-insensitive.
- An alphanumeric character may not immediately precede the trigger.
- An ending character is required after the trigger.

Existing hotstrings are represented by [`HotstringDefinition`][] instances.
Only the existing options that affect trigger boundaries, ``?`` and ``*``, are
normalized because they are the only options relevant to contradiction
detection.

The checker currently assumes AutoHotkey's default ending-character set. It also
considers only options explicitly present in each hotstring declaration; it does
not yet resolve positional ``#Hotstring`` defaults or runtime changes made with
the ``Hotstring`` function.

The generated report separates accepted and rejected candidates. Every rejected
candidate lists all existing hotstrings that contradict it together with the
reason for each contradiction.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import InitVar, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Final

from .options import CaseMode, HotstringOptions

# =============================================================================
# Configuration
# =============================================================================


HOTSTRING_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*:([^\r\n:]*):([^\r\n]+?)::",
    re.MULTILINE,
)

_BOUNDARY_OPTION_PATTERN: Final[re.Pattern[str]] = re.compile(r"([?*])(0?)")


# =============================================================================
# Enumerations
# =============================================================================


class ContradictionKind(Enum):
    """Classify the relationship causing a candidate contradiction.

    Attributes:
        SAME_TRIGGER:
            The candidate and existing hotstring use the same trigger.
        EXISTING_FIRES_DURING_CANDIDATE:
            The existing trigger can activate while the candidate is being
            typed.
        CANDIDATE_FIRES_DURING_EXISTING:
            The candidate can activate while the existing trigger is being
            typed.
    """

    SAME_TRIGGER = "same trigger"
    EXISTING_FIRES_DURING_CANDIDATE = "existing hotstring can fire while candidate is typed"
    CANDIDATE_FIRES_DURING_EXISTING = "candidate can fire while existing hotstring is typed"


# =============================================================================
# Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class HotstringDefinition:
    """Represent one statically defined AutoHotkey hotstring.

    The original option text is retained so the declaration can be reproduced
    exactly in reports. The options string is normalized once during initialization and stored in
    [`options`][HotstringDefinition.options].

    Case-sensitive existing definitions are intentionally compared
    case-insensitively for contradiction detection. A proposed ``B0X`` candidate
    is itself case-insensitive, so a case-sensitive existing definition still
    overlaps at least one casing accepted by the candidate.

    Attributes:
        options:
            Normalized options object derived from the original options string.
        trigger:
            Trigger string captured from the declaration.
        source:
            Optional source file in which the hotstring was found.
    """

    raw_options: InitVar[str] = field(init=True)
    trigger: str = field(init=True)
    source: Path | None = field(init=True, default=None, compare=False, repr=True)
    options: HotstringOptions = field(
        init=False,
        repr=True,
        compare=True,
    )

    _normalized_trigger: str = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self, raw_options: str) -> None:
        """Initialize normalized state derived from the declaration.

        The original option text remains unchanged. Only options relevant to
        trigger-boundary matching are normalized.

        Args:
            raw_options:
                Original option string from the hotstring declaration.

        Raises:
            ValueError:
                If the hotstring trigger is empty.
        """
        if not isinstance(raw_options, str):
            raise TypeError(f"Expected str for raw_options, got {type(raw_options).__name__}")

        if not isinstance(self.trigger, str):
            raise TypeError(f"Expected str for trigger, got {type(self.trigger).__name__}")
        if not self.trigger:
            raise ValueError("Hotstring trigger cannot be empty.")

        if self.source is not None and not isinstance(self.source, (str, Path)):
            raise TypeError(
                f"Expected str or Path or None for source, got {type(self.source).__name__}"
            )

        object.__setattr__(
            self,
            "options",
            HotstringOptions(raw_options),
        )

        if self.source is not None:
            object.__setattr__(self, "source", Path(self.source))

        object.__setattr__(
            self,
            "_normalized_trigger",
            self.trigger.casefold(),
        )

    @property
    def declaration(self) -> str:
        """Return the declaration prefix used by the hotstring.

        The returned text contains the options, trigger, and terminating
        double-colon delimiter, but not the replacement or executable body.

        Returns:
            The reconstructed hotstring declaration prefix.
        """
        return f":{self.options.declaration()}:{self.trigger}::"

    def find_contradiction(
        self,
        candidate_hotstring: HotstringDefinition,
    ) -> Contradiction | None:
        """Find a contradiction with a proposed candidate.

        Currently the candidate is assumed to be case-insensitive, to disallow an
        alphanumeric predecessor, and to require an ending character.
        Other candidate options are not yet supported.

        Both contradiction directions are checked:

        1. Whether this existing hotstring can activate while the candidate is
           being typed.
        2. Whether the candidate can activate while this existing hotstring is
           being typed.

        Exact trigger equality is handled separately because it represents a
        direct overlap regardless of the existing boundary options.

        Args:
            candidate_hotstring:
                Proposed candidate hotstring.

        Returns:
            A [`Contradiction`][] describing the first detected contradiction,
            or `None` when the definitions do not contradict each other.

        Raises:
            NotImplementedError:
                If the candidate hotstring uses options that are not yet supported by the checker.
            ValueError:
                If the candidate trigger is empty.
        """
        if not isinstance(candidate_hotstring, HotstringDefinition):
            raise TypeError(
                f"Expected HotstringDefinition for candidate_hotstring, got "
                f"{type(candidate_hotstring).__name__}"
            )

        if candidate_hotstring.options.ending_character_required is False:
            raise NotImplementedError(
                "Candidate hotstrings that do not require an ending character are not yet supported."
            )
        if candidate_hotstring.options.trigger_inside_word is True:
            raise NotImplementedError(
                "Candidate hotstrings that allow an alphanumeric predecessor are not yet supported."
            )

        if candidate_hotstring.options.case_mode is CaseMode.SENSITIVE:
            raise NotImplementedError(
                "Candidate hotstrings that are case-sensitive are not yet supported."
            )

        if not candidate_hotstring.trigger:
            raise ValueError("Candidate's trigger cannot be empty.")

        if self._normalized_trigger == candidate_hotstring._normalized_trigger:
            return Contradiction(
                kind=ContradictionKind.SAME_TRIGGER,
                hotstring=self,
                reason=(
                    "The existing hotstring and candidate have the same case-insensitive trigger."
                ),
            )

        existing_overlap_reason = _find_trigger_overlap_reason(
            trigger=self.trigger,
            container=candidate_hotstring.trigger,
            allow_alphanumeric_predecessor=self.options.trigger_inside_word is True,
            require_ending_character=self.options.ending_character_required is True,
        )

        if existing_overlap_reason is not None:
            return Contradiction(
                kind=(ContradictionKind.EXISTING_FIRES_DURING_CANDIDATE),
                hotstring=self,
                reason=(
                    "The existing hotstring can activate while the candidate "
                    f"is being typed: {existing_overlap_reason}."
                ),
            )

        candidate_overlap_reason = _find_trigger_overlap_reason(
            trigger=candidate_hotstring.trigger,
            container=self.trigger,
            allow_alphanumeric_predecessor=False,
            require_ending_character=True,
        )

        if candidate_overlap_reason is not None:
            return Contradiction(
                kind=(ContradictionKind.CANDIDATE_FIRES_DURING_EXISTING),
                hotstring=self,
                reason=(
                    "The candidate can activate while the existing hotstring "
                    f"is being typed: {candidate_overlap_reason}."
                ),
            )

        return None


@dataclass(frozen=True, slots=True)
class Contradiction:
    """Describe one contradiction with an existing hotstring.

    A contradiction always belongs to one [`HotstringDefinition`][] and records
    both a machine-friendly classification and a human-readable explanation.

    Attributes:
        kind:
            Classification of the contradiction.
        hotstring:
            Existing hotstring responsible for the contradiction.
        reason:
            Detailed explanation suitable for the generated report.
    """

    kind: ContradictionKind
    hotstring: HotstringDefinition
    reason: str


@dataclass(frozen=True, slots=True)
class CandidateAssessment:
    """Represent the result of checking one candidate.

    A candidate is accepted when no contradictions were found. Otherwise,
    `contradictions` contains every existing hotstring that caused it to be
    rejected.

    Attributes:
        trigger:
            Candidate typo trigger.
        replacement:
            Intended replacement text.
        contradictions:
            Contradictions found against existing hotstrings.
    """

    trigger: str
    replacement: str
    contradictions: tuple[Contradiction, ...]

    @property
    def is_accepted(self) -> bool:
        """Return whether the candidate has no contradictions.

        Returns:
            Whether the candidate is safe according to the current checks.
        """
        return not self.contradictions


# =============================================================================
# Boundary matching
# =============================================================================


def _find_trigger_overlap_reason(
    *,
    trigger: str,
    container: str,
    allow_alphanumeric_predecessor: bool,
    require_ending_character: bool,
) -> str | None:
    """Find a valid occurrence of one trigger inside another string.

    Each case-insensitive occurrence is evaluated according to the supplied
    left- and right-boundary behavior. The first occurrence satisfying both
    boundaries is sufficient to establish an overlap.

    Args:
        trigger:
            Trigger whose activation is being tested.
        container:
            Longer text within which the trigger may occur.
        allow_alphanumeric_predecessor:
            Whether the trigger may follow an alphanumeric character.
        require_ending_character:
            Whether the trigger requires an ending character after it.

    Returns:
        A boundary-based explanation for the first valid overlap, or `None`
        when no occurrence can activate.
    """
    if len(trigger) > len(container):
        return None

    for start in _iter_occurrence_starts(
        container=container,
        trigger=trigger,
    ):
        end = start + len(trigger)

        left_reason = _left_boundary_reason(
            container=container,
            start=start,
            allow_alphanumeric_predecessor=(allow_alphanumeric_predecessor),
        )

        if left_reason is None:
            continue

        right_reason = _right_boundary_reason(
            container=container,
            end=end,
            require_ending_character=require_ending_character,
        )

        if right_reason is None:
            continue

        return f"{left_reason}; {right_reason}"

    return None


def _iter_occurrence_starts(
    *,
    container: str,
    trigger: str,
) -> Iterator[int]:
    """Yield case-insensitive occurrence positions, including overlaps.

    A zero-width lookahead is used so overlapping occurrences are retained.
    This matters for repeated trigger patterns where a later occurrence may
    satisfy different boundary conditions from an earlier occurrence.

    Args:
        container:
            Text to search.
        trigger:
            Trigger to locate.

    Yields:
        Start index of each case-insensitive occurrence.
    """
    pattern = re.compile(
        rf"(?={re.escape(trigger)})",
        re.IGNORECASE,
    )

    for match in pattern.finditer(container):
        yield match.start()


def _left_boundary_reason(
    *,
    container: str,
    start: int,
    allow_alphanumeric_predecessor: bool,
) -> str | None:
    """Evaluate whether an occurrence satisfies its left boundary.

    A normal hotstring is valid at the start of the containing text or after a
    non-alphanumeric character. The ``?`` option additionally permits an
    alphanumeric predecessor.

    Args:
        container:
            Text containing the occurrence.
        start:
            Start index of the occurrence.
        allow_alphanumeric_predecessor:
            Whether an alphanumeric predecessor is permitted.

    Returns:
        An explanation when the boundary is valid, or `None` when it is not.
    """
    if start == 0:
        return "the match starts at the beginning"

    preceding_char = container[start - 1]

    if not preceding_char.isalnum():
        return f"the preceding character {preceding_char!r} is non-alphanumeric"

    if allow_alphanumeric_predecessor:
        return (
            f"the preceding character {preceding_char!r} is alphanumeric, "
            "but the '?' option permits it"
        )

    return None


def _right_boundary_reason(
    *,
    container: str,
    end: int,
    require_ending_character: bool,
) -> str | None:
    """Evaluate whether an occurrence satisfies its right boundary.

    A hotstring using ``*`` needs no right-side ending character. Otherwise,
    the occurrence is valid when it reaches the end of the containing trigger
    or when the immediately following character belongs to
    [`DEFAULT_ENDING_CHARS`][].

    Reaching the end of the containing trigger represents a potential overlap
    because the next ending character typed by the user can activate the
    shorter trigger.

    Args:
        container:
            Text containing the occurrence.
        end:
            Exclusive end index of the occurrence.
        require_ending_character:
            Whether an ending character is required.

    Returns:
        An explanation when the boundary is valid, or `None` when it is not.
    """
    if not require_ending_character:
        return "no ending character is required because '*' is enabled"

    if end == len(container):
        return (
            "the match reaches the end of the containing trigger, so the "
            "next ending character typed can activate it"
        )

    following_char = container[end]

    if following_char in DEFAULT_ENDING_CHARS:
        return f"the following character {following_char!r} is an ending character"

    return None


# =============================================================================
# Source-file inspection
# =============================================================================


def extract_hotstrings(
    file_path: Path,
    *,
    source: Path,
) -> list[HotstringDefinition]:
    """Extract static hotstring declarations from one source file.

    The complete file is searched using [`HOTSTRING_PATTERN`][] in multiline
    mode. Only the option string and trigger are captured; replacement text and
    executable hotstring bodies are intentionally ignored.

    Args:
        file_path:
            Absolute path to the source file being read.
        source:
            Source identifier stored on each extracted definition, normally the
            path relative to the AutoCorrect2 project directory.

    Returns:
        Hotstring definitions found in source order.
    """
    content = file_path.read_text(encoding="utf-8-sig")

    return [
        HotstringDefinition(
            raw_options=match.group(1),
            trigger=match.group(2),
            source=source,
        )
        for match in HOTSTRING_PATTERN.finditer(content)
    ]


def load_existing_hotstrings(
    project_dir: Path = AUTOCORRECT2_PROJECT_DIR,
    source_paths: Sequence[Path] = HOTSTRING_SOURCE_RELATIVE_PATHS,
) -> list[HotstringDefinition]:
    """Load hotstrings from all configured AutoCorrect2 source files.

    Relative source paths are resolved against `project_dir`. Definitions are
    returned in source-file order and declaration order within each file.

    Args:
        project_dir:
            AutoCorrect2 project directory used as the path base.
        source_paths:
            Relative paths containing static hotstring definitions.

    Returns:
        All discovered existing hotstrings.

    Raises:
        FileNotFoundError:
            If one of the configured source paths is not an existing file.
    """
    hotstrings: list[HotstringDefinition] = []

    for relative_path in source_paths:
        file_path = project_dir / relative_path

        if not file_path.is_file():
            raise FileNotFoundError(f"Hotstring source file was not found: {file_path}")

        hotstrings.extend(
            extract_hotstrings(
                file_path,
                source=relative_path,
            )
        )

    return hotstrings


# =============================================================================
# Candidate assessment
# =============================================================================


def assess_candidates(
    candidates: Mapping[str, str],
    existing_hotstrings: Sequence[HotstringDefinition],
) -> list[CandidateAssessment]:
    """Check all candidates against all existing hotstrings.

    Candidates are assessed independently. No candidate-to-candidate comparison
    is performed because the input mapping is assumed to have already resolved
    such contradictions.

    Every existing contradiction is retained so a rejected candidate's report
    shows all definitions that caused the rejection rather than only the first.

    Args:
        candidates:
            Candidate triggers mapped to their intended replacements.
        existing_hotstrings:
            Existing definitions against which candidates are checked.

    Returns:
        Candidate assessments in mapping iteration order.

    Raises:
        ValueError:
            If a candidate trigger is empty.
    """
    assessments: list[CandidateAssessment] = []

    for trigger, replacement in candidates.items():
        if not trigger:
            raise ValueError("Candidate trigger cannot be empty.")

        contradictions: list[Contradiction] = []

        for hotstring in existing_hotstrings:
            contradiction = hotstring.find_contradiction(trigger)

            if contradiction is not None:
                contradictions.append(contradiction)

        assessments.append(
            CandidateAssessment(
                trigger=trigger,
                replacement=replacement,
                contradictions=tuple(contradictions),
            )
        )

    return assessments


# =============================================================================
# Reporting
# =============================================================================


def create_report(
    assessments: Sequence[CandidateAssessment],
) -> str:
    """Create the accepted-and-rejected candidate report.

    Rejected candidates include every conflicting existing hotstring, its
    source file, contradiction classification, and detailed reason.

    Args:
        assessments:
            Candidate assessments to render.

    Returns:
        Complete report text.
    """
    accepted = [assessment for assessment in assessments if assessment.is_accepted]
    rejected = [assessment for assessment in assessments if not assessment.is_accepted]

    lines: list[str] = [
        "AUTOHOTKEY HOTSTRING CANDIDATE REPORT",
        "=" * 80,
        "",
        f"Accepted candidates: {len(accepted)}",
        f"Rejected candidates: {len(rejected)}",
        "",
        "ACCEPTED",
        "-" * 80,
    ]

    if accepted:
        for assessment in accepted:
            lines.append(f"{assessment.trigger!r} -> {assessment.replacement!r}")
    else:
        lines.append("None")

    lines.extend(
        (
            "",
            "REJECTED",
            "-" * 80,
        )
    )

    if not rejected:
        lines.append("None")
        return "\n".join(lines)

    for assessment in rejected:
        lines.append(f"{assessment.trigger!r} -> {assessment.replacement!r}")

        for contradiction in assessment.contradictions:
            hotstring = contradiction.hotstring

            lines.extend(
                (
                    f"  Existing: {hotstring.declaration}",
                    f"  Source:   {hotstring.source}",
                    f"  Type:     {contradiction.kind.value}",
                    f"  Reason:   {contradiction.reason}",
                    "",
                )
            )

    return "\n".join(lines)


def write_report(
    report: str,
    path: Path = REPORT_PATH,
) -> None:
    """Write a generated report to disk.

    Args:
        report:
            Complete report text.
        path:
            Destination report file.
    """
    path.write_text(
        report,
        encoding="utf-8",
    )


# =============================================================================
# Candidates
# =============================================================================

CANDIDATES: dict[str, str] = {
    # "recieve": "receive",
    # "adress": "address",
}


# =============================================================================
# Entry point
# =============================================================================


def main() -> None:
    """Inspect existing hotstrings and generate the candidate report.

    The function loads the configured AutoCorrect2 definitions, assesses the
    contents of [`CANDIDATES`][], writes the resulting report to
    [`REPORT_PATH`][], and prints the same report to standard output.
    """
    existing_hotstrings = load_existing_hotstrings()

    assessments = assess_candidates(
        CANDIDATES,
        existing_hotstrings,
    )

    report = create_report(assessments)

    write_report(report)

    print(report)


if __name__ == "__main__":
    main()
