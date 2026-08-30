"""Create human-readable AutoCorrect2 candidate conflict reports."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..conflicts import CandidateAssessment
from .constants import DEFAULT_CONFLICT_REPORT_PATH


def create_conflict_report(
    assessments: Sequence[CandidateAssessment],
) -> str:
    """Create a report separating accepted and rejected candidates.

    Every rejected candidate includes all existing definitions that caused
    rejection, together with their source paths and contradiction reasons.

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
            candidate = assessment.candidate
            lines.append(f"{candidate.trigger!r} -> {candidate.replacement!r}")
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
        candidate = assessment.candidate
        lines.append(f"{candidate.trigger!r} -> {candidate.replacement!r}")

        for conflict in assessment.conflicts:
            lines.extend(
                (
                    f"  Existing: {conflict.existing.declaration}",
                    f"  Source:   {conflict.existing.source}",
                    f"  Type:     {conflict.kind.value}",
                    f"  Reason:   {conflict.reason}",
                    "",
                )
            )

    return "\n".join(lines)


def write_conflict_report(
    report: str,
    path: Path = DEFAULT_CONFLICT_REPORT_PATH,
) -> None:
    """Write a generated conflict report to disk.

    Args:
        report:
            Complete report text.
        path:
            Destination report path.

    Raises:
        OSError:
            If the report cannot be written.
    """
    path.write_text(report, encoding="utf-8")
