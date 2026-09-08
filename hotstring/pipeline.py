"""Expose the three independent project execution pipelines.

The full workflow is deliberately implemented as composition of the typo-
generation-only and AutoCorrect2-only workflows. Neither subsystem depends
on the other, which keeps generation policy separate from AutoHotkey source
inspection and conflict detection.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .autocorrect2.constants import AUTOCORRECT2_PROJECT_DIR
from .autocorrect2.models import AutoCorrect2CandidateHotstring, AutoCorrect2CheckResult
from .autocorrect2.source_loading import load_existing_hotstrings
from .autocorrect2.writer import append_candidates
from .core.conflicts import assess_candidates
from .core.options import HotstringOptions
from .file_io import write_text
from .report import (
    build_report_document,
    create_autocorrect2_report,
    create_full_pipeline_report,
    create_typo_generation_report,
)
from .typo_generation.aggregation import aggregate_typo_samples
from .typo_generation.execution import execute_typo_generation_tasks
from .typo_generation.models import TypoGenerationConfig, TypoGenerationResult, TypoGenerationTask

GENERATED_CANDIDATE_OPTIONS: Final[HotstringOptions] = HotstringOptions("B0X")
"""Options assigned when the full pipeline converts typo mappings to hotstrings."""


@dataclass(frozen=True, slots=True)
class FullPipelineResult:
    """Represent the two results produced by the composed full pipeline.

    Attributes:
        typo_generation:
            Result of typo generation and internal ambiguity filtering.
        autocorrect2:
            Result of checking the surviving candidates against AutoCorrect2.
    """

    typo_generation: TypoGenerationResult
    autocorrect2: AutoCorrect2CheckResult


def run_typo_generation(
    word_list: Sequence[str],
    tasks: Sequence[TypoGenerationTask],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None = None,
    report_path: Path | None = None,
    logger: logging.Logger | None = None,
) -> TypoGenerationResult:
    """Run typo generation and internal ambiguity filtering only.

    Args:
        word_list:
            Source words to corrupt.
        tasks:
            Ordered typo-generation tasks to execute.
        config:
            Shared MULTYPO generator configuration.
        n_workers:
            Optional process-pool size. `None` uses the executor default when
            parallel execution is selected.
        report_path:
            Optional destination for a typo-generation-only report.
        logger:
            Optional orchestration logger forwarded to the execution layer.

    Returns:
        Aggregated typo-generation result containing valid mappings and
        internally ambiguous noisy forms.

    Raises:
        TypeError:
            If task/execution inputs have invalid types.
        ValueError:
            If no generation tasks are supplied or a generation setting is
            invalid.
        RuntimeError:
            If a parallel generation task fails.
        OSError:
            If a requested report cannot be written.
    """
    words = list(word_list)
    task_tuple = tuple(tasks)
    samples = execute_typo_generation_tasks(
        words,
        task_tuple,
        config,
        n_workers=n_workers,
        logger=logger,
    )
    result = aggregate_typo_samples(
        samples,
        config=config,
        tasks=task_tuple,
        source_word_count=len(words),
    )

    if report_path is not None:
        _write_report(
            report_path,
            "TYPO GENERATION REPORT",
            create_typo_generation_report(result),
        )

    return result


def run_autocorrect2_check(
    candidates: Sequence[AutoCorrect2CandidateHotstring],
    *,
    project_dir: Path = AUTOCORRECT2_PROJECT_DIR,
    report_path: Path | None = None,
    write_accepted: bool = False,
) -> AutoCorrect2CheckResult:
    """Check manually supplied candidates against active AutoCorrect2 hotstrings.

    Trigger conflict detection supports every combination of the recognition
    options currently modeled by the project: ending-character-free matching
    (`*`), inside-word matching (`?`), and case-sensitive matching (`C`). No
    candidate is rejected merely for using one of those semantics.

    Args:
        candidates:
            AutoCorrect2 candidates supplied directly by the caller.
        project_dir:
            AutoCorrect2 project directory containing the configured source
            files.
        report_path:
            Optional destination for an AutoCorrect2-only report.
        write_accepted:
            Append accepted candidates to the generated include file when
            `True`.

    Returns:
        Conflict-check result partitioning candidates into accepted and
        rejected groups.

    Raises:
        FileNotFoundError:
            If a required AutoCorrect2 source file is missing.
        UnicodeDecodeError:
            If a source requiring parsing is not valid UTF-8 text.
        ValueError:
            If source data is invalid or writing is requested for a candidate
            that violates the writer's explicit `B0X` contract.
        OSError:
            If authoritative sources, reports, or generated files cannot be
            read or written.
    """
    candidate_tuple = tuple(candidates)
    existing_hotstrings = load_existing_hotstrings(project_dir)
    assessments = assess_candidates(candidate_tuple, existing_hotstrings)

    accepted: list[AutoCorrect2CandidateHotstring] = []
    rejected = []
    for candidate, assessment in zip(candidate_tuple, assessments, strict=True):
        if assessment.is_accepted:
            accepted.append(candidate)
        else:
            rejected.append(assessment)

    result = AutoCorrect2CheckResult(
        accepted=tuple(accepted),
        rejected=tuple(rejected),
    )

    if write_accepted:
        append_candidates(result.accepted, project_dir=project_dir)

    if report_path is not None:
        _write_report(
            report_path,
            "AUTOCORRECT2 CONFLICT CHECK REPORT",
            create_autocorrect2_report(result),
        )

    return result


def run_full_pipeline(
    word_list: Sequence[str],
    tasks: Sequence[TypoGenerationTask],
    config: TypoGenerationConfig,
    *,
    n_workers: int | None = None,
    project_dir: Path = AUTOCORRECT2_PROJECT_DIR,
    report_path: Path | None = None,
    write_accepted: bool = False,
    logger: logging.Logger | None = None,
) -> FullPipelineResult:
    """Run typo generation followed by AutoCorrect2 conflict checking.

    The function composes the two independent stage pipelines without asking
    either stage to emit its own report. Surviving typo mappings are converted
    to [`AutoCorrect2CandidateHotstring`]
    [hotstring.autocorrect2.models.AutoCorrect2CandidateHotstring] objects with
    the project's fixed generated `B0X` option set.

    Args:
        word_list:
            Source words to corrupt.
        tasks:
            Ordered typo-generation tasks to execute.
        config:
            Shared MULTYPO generator configuration.
        n_workers:
            Optional process-pool size.
        project_dir:
            AutoCorrect2 project directory.
        report_path:
            Optional destination for the combined report.
        write_accepted:
            Append final accepted candidates to the generated include file.
        logger:
            Optional typo-generation orchestration logger.

    Returns:
        Combined result containing both stage results.

    Raises:
        TypeError:
            If generation or source-loading inputs have invalid types.
        ValueError:
            If generation/source data is invalid or a writable candidate
            violates the generated-file contract.
        FileNotFoundError:
            If a required AutoCorrect2 source file is missing.
        UnicodeDecodeError:
            If an authoritative source requiring parsing is not valid UTF-8.
        RuntimeError:
            If a parallel generation task fails.
        OSError:
            If source, report, or generated files cannot be read or written.
    """
    typo_result = run_typo_generation(
        word_list,
        tasks,
        config,
        n_workers=n_workers,
        report_path=None,
        logger=logger,
    )

    candidates = tuple(
        AutoCorrect2CandidateHotstring(
            trigger=noisy_word,
            options_input=GENERATED_CANDIDATE_OPTIONS,
            replacement=target_word,
        )
        for noisy_word, target_word in typo_result.candidates.items()
    )

    autocorrect2_result = run_autocorrect2_check(
        candidates,
        project_dir=project_dir,
        report_path=None,
        write_accepted=write_accepted,
    )
    result = FullPipelineResult(
        typo_generation=typo_result,
        autocorrect2=autocorrect2_result,
    )

    if report_path is not None:
        _write_report(
            report_path,
            "AUTOHOTKEY HOTSTRING GENERATION REPORT",
            create_full_pipeline_report(typo_result, autocorrect2_result),
        )

    return result


def _write_report(path: Path, title: str, body_lines: Sequence[str]) -> None:
    """Build and write one complete report document.

    Args:
        path:
            Destination report file.
        title:
            Top-level report title.
        body_lines:
            Pipeline-specific report body lines.

    Raises:
        ValueError:
            If the report title is empty.
        OSError:
            If the report cannot be written.
    """
    document_lines = build_report_document(title, body_lines)
    write_text(path, "\n".join(document_lines) + "\n")
