"""Dispatch validated CLI commands to the public pipeline APIs.

The runtime layer resolves all user input before this module is called. Each
handler therefore performs only workflow dispatch and concise terminal
reporting; report generation and optional writes remain owned by
[`hotstring.pipeline`][].
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TextIO, assert_never

from ..autocorrect2.constants import GENERATED_HOTSTRINGS_RELATIVE_PATH
from ..autocorrect2.models import AutoCorrect2CheckResult
from ..pipeline import run_autocorrect2_check, run_full_pipeline, run_typo_generation
from ..typo_generation.models import TypoGenerationResult
from .runtime import (
    AutoCorrect2CheckCommand,
    CommandConfig,
    FullPipelineCommand,
    TypoGenerationCommand,
)


def execute_command(
    command: CommandConfig,
    *,
    logger: logging.Logger | None = None,
    output: TextIO | None = None,
) -> int:
    """Execute one validated command and print its summary.

    Args:
        command:
            Runtime command created by
            [`create_command_config()`][hotstring.cli.runtime.create_command_config].
        logger:
            Optional orchestration logger forwarded to typo-generation
            pipelines.
        output:
            Optional output stream. `None` uses the current `sys.stdout`.

    Returns:
        Zero after successful pipeline execution.
    """
    stream = sys.stdout if output is None else output

    if isinstance(command, TypoGenerationCommand):
        generation = command.generation
        result = run_typo_generation(
            generation.words,
            generation.tasks,
            generation.config,
            n_workers=generation.n_workers,
            report_path=command.report_path,
            logger=logger,
        )
        _print_typo_summary(result, output=stream)
        _print_report_path(command.report_path, output=stream)
        return 0

    if isinstance(command, AutoCorrect2CheckCommand):
        autocorrect2 = command.autocorrect2
        result = run_autocorrect2_check(
            command.candidates,
            project_dir=autocorrect2.project_dir,
            report_path=command.report_path,
            write_accepted=autocorrect2.write_accepted,
        )
        _print_autocorrect2_summary(result, output=stream)
        _print_write_destination(
            write_accepted=autocorrect2.write_accepted,
            project_dir=autocorrect2.project_dir,
            output=stream,
        )
        _print_report_path(command.report_path, output=stream)
        return 0

    if isinstance(command, FullPipelineCommand):
        generation = command.generation
        autocorrect2 = command.autocorrect2
        result = run_full_pipeline(
            generation.words,
            generation.tasks,
            generation.config,
            n_workers=generation.n_workers,
            project_dir=autocorrect2.project_dir,
            report_path=command.report_path,
            write_accepted=autocorrect2.write_accepted,
            logger=logger,
        )
        _print_typo_summary(result.typo_generation, output=stream)
        _print_autocorrect2_summary(result.autocorrect2, output=stream)
        _print_write_destination(
            write_accepted=autocorrect2.write_accepted,
            project_dir=autocorrect2.project_dir,
            output=stream,
        )
        _print_report_path(command.report_path, output=stream)
        return 0

    assert_never(command)


def _print_typo_summary(result: TypoGenerationResult, *, output: TextIO) -> None:
    """Print the stable summary fields of a typo-generation result.

    Args:
        result:
            Typo-generation result returned by the pipeline.
        output:
            Destination stream.
    """
    print("Typo generation complete.", file=output)
    print(f"  Source words: {result.source_word_count}", file=output)
    print(f"  Raw samples: {result.generated_sample_count}", file=output)
    print(f"  Candidates: {len(result.candidates)}", file=output)
    print(f"  Internal clashes: {len(result.clashes)}", file=output)


def _print_autocorrect2_summary(
    result: AutoCorrect2CheckResult,
    *,
    output: TextIO,
) -> None:
    """Print the stable summary fields of an AutoCorrect2 check result.

    Args:
        result:
            AutoCorrect2 result returned by the pipeline.
        output:
            Destination stream.
    """
    print("AutoCorrect2 check complete.", file=output)
    print(f"  Candidates checked: {result.candidate_count}", file=output)
    print(f"  Accepted: {len(result.accepted)}", file=output)
    print(f"  Rejected: {len(result.rejected)}", file=output)


def _print_write_destination(
    *,
    write_accepted: bool,
    project_dir: Path,
    output: TextIO,
) -> None:
    """Print the generated-file destination when writing was enabled.

    Args:
        write_accepted:
            Whether the selected command enabled writing.
        project_dir:
            AutoCorrect2 project directory.
        output:
            Destination stream.
    """
    if write_accepted:
        print(
            f"  Generated include: {project_dir / GENERATED_HOTSTRINGS_RELATIVE_PATH}",
            file=output,
        )


def _print_report_path(report_path: Path | None, *, output: TextIO) -> None:
    """Print the report destination when one was requested.

    Args:
        report_path:
            Optional report destination.
        output:
            Destination stream.
    """
    if report_path is not None:
        print(f"  Report: {report_path}", file=output)
