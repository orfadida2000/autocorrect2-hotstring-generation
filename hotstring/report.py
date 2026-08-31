"""Build composable line-oriented reports for all supported pipelines.

Section builders deliberately omit run-level metadata such as dates or
timestamps. This allows the full pipeline to reuse the typo-generation and
AutoCorrect2 report bodies without duplicating document metadata.
"""

from __future__ import annotations

from collections.abc import Sequence

from .autocorrect2.models import AutoCorrect2CheckResult
from .typo_generation.models import TypoGenerationResult


def create_typo_generation_report(result: TypoGenerationResult) -> list[str]:
    """Create the typo-generation report body.

    Args:
        result:
            Aggregated typo-generation result.

    Returns:
        Report body as individual text lines.
    """
    lines = [
        "TYPO GENERATION",
        "-" * 80,
        f"Source words: {result.source_word_count}",
        f"Generation attempts per word per distribution: "
        f"{result.config.generation_attempts_per_word}",
        f"Typo distributions: {len(result.config.typo_distributions)}",
        f"Successful raw samples: {result.generated_sample_count}",
        f"Unique noisy words: {result.unique_noisy_word_count}",
        f"Valid candidates: {len(result.candidates)}",
        f"Internal clashes: {len(result.clashes)}",
        "",
        "DISTRIBUTIONS",
    ]

    for index, distribution in enumerate(result.config.typo_distributions, start=1):
        lines.append(f"{index}. {distribution.distribution}")

    lines.extend(("", "VALID TYPO CANDIDATES", "-" * 80))
    if result.candidates:
        lines.extend(
            f"{noisy!r} -> {target!r}"
            for noisy, target in result.candidates.items()
        )
    else:
        lines.append("None")

    lines.extend(("", "INTERNAL CLASHES", "-" * 80))
    if result.clashes:
        for noisy_word, targets in result.clashes.items():
            lines.append(f"{noisy_word!r}")
            lines.extend(f"  -> {target!r}" for target in targets)
    else:
        lines.append("None")

    return lines


def create_autocorrect2_report(result: AutoCorrect2CheckResult) -> list[str]:
    """Create the AutoCorrect2 conflict-check report body.

    Args:
        result:
            AutoCorrect2 candidate-check result.

    Returns:
        Report body as individual text lines.
    """
    lines = [
        "AUTOCORRECT2 CONFLICT CHECK",
        "-" * 80,
        f"Candidates checked: {result.candidate_count}",
        f"Accepted candidates: {len(result.accepted)}",
        f"Rejected candidates: {len(result.rejected)}",
        "",
        "ACCEPTED",
        "-" * 80,
    ]

    if result.accepted:
        lines.extend(
            f"{candidate.trigger!r} -> {candidate.replacement!r}"
            for candidate in result.accepted
        )
    else:
        lines.append("None")

    lines.extend(("", "REJECTED", "-" * 80))
    if not result.rejected:
        lines.append("None")
        return lines

    for assessment in result.rejected:
        candidate = assessment.candidate
        lines.append(f"{candidate.trigger!r} -> {candidate.replacement!r}")
        for conflict in assessment.conflicts:
            lines.extend(
                (
                    f"  Existing: {conflict.existing.render()}",
                    f"  Source:   {conflict.existing.source}",
                    f"  Type:     {conflict.kind.value}",
                    f"  Reason:   {conflict.reason}",
                    "",
                )
            )
    return lines


def create_full_pipeline_report(
    typo_result: TypoGenerationResult,
    autocorrect2_result: AutoCorrect2CheckResult,
) -> list[str]:
    """Create a full report by composing both stage-specific report bodies.

    Args:
        typo_result:
            Typo-generation stage result.
        autocorrect2_result:
            AutoCorrect2 conflict-check stage result.

    Returns:
        Combined report body with a final pipeline summary.
    """
    lines = create_typo_generation_report(typo_result)
    lines.extend(("", "=" * 80, ""))
    lines.extend(create_autocorrect2_report(autocorrect2_result))
    lines.extend(
        (
            "",
            "FINAL SUMMARY",
            "-" * 80,
            f"Internal typo clashes removed: {len(typo_result.clashes)}",
            f"AutoCorrect2 conflicts removed: {len(autocorrect2_result.rejected)}",
            f"Final accepted hotstrings: {len(autocorrect2_result.accepted)}",
        )
    )
    return lines


def build_report_document(title: str, body_lines: Sequence[str]) -> list[str]:
    """Wrap a report body with run-level document framing.

    No timestamp or other volatile metadata is currently added. Future
    document-level metadata belongs here so it appears exactly once even for
    composed full-pipeline reports.

    Args:
        title:
            Top-level report title.
        body_lines:
            Already formatted body lines.

    Returns:
        Complete document lines.

    Raises:
        ValueError:
            If `title` is empty.
    """
    if not title:
        raise ValueError("Report title cannot be empty.")
    return [title, "=" * 80, "", *body_lines]
