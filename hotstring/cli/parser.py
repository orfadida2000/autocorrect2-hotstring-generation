"""Construct the command-line parser and its three subcommands.

Parser construction is intentionally separate from runtime resolution. This
module describes syntax and performs scalar validation; [`create_command_config()`]
[hotstring.cli.runtime.create_command_config] resolves files, environment
configuration, and domain objects after parsing succeeds.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final

from .runtime import AUTOCORRECT2_PROJECT_DIR_ENV

_PROGRAM_DESCRIPTION: Final[str] = (
    "Generate keyboard-typo hotstrings and check candidates against AutoCorrect2."
)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create the complete top-level argument parser.

    The parser exposes three independent workflows: typo generation,
    AutoCorrect2 conflict checking, and their composed full pipeline. Shared
    options are added by private helpers so their spelling and validation stay
    consistent across subcommands.

    Returns:
        Configured parser ready to parse a command-line argument sequence.
    """
    parser = argparse.ArgumentParser(description=_PROGRAM_DESCRIPTION)
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        default=0,
        help="increase logging detail; repeat for debug output",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        required=True,
    )

    typo_generation = subparsers.add_parser(
        "typo-generation",
        help="generate and internally validate typo mappings",
        description="Generate typo mappings without inspecting AutoCorrect2.",
    )
    _add_word_source_arguments(typo_generation)
    _add_generation_arguments(typo_generation)
    _add_report_argument(typo_generation)

    autocorrect2_check = subparsers.add_parser(
        "autocorrect2-check",
        help="check supplied candidates against AutoCorrect2",
        description=(
            "Check explicitly supplied candidate hotstrings without running typo generation."
        ),
    )
    _add_candidate_source_arguments(autocorrect2_check)
    _add_autocorrect2_arguments(autocorrect2_check)
    _add_report_argument(autocorrect2_check)

    full_pipeline = subparsers.add_parser(
        "full-pipeline",
        help="generate typos and check them against AutoCorrect2",
        description=(
            "Generate typo candidates, remove internal ambiguity, and check "
            "the survivors against AutoCorrect2."
        ),
    )
    _add_word_source_arguments(full_pipeline)
    _add_generation_arguments(full_pipeline)
    _add_autocorrect2_arguments(full_pipeline)
    _add_report_argument(full_pipeline)

    return parser


def _add_word_source_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the mutually exclusive source-word inputs.

    Args:
        parser:
            Subparser receiving the arguments.
    """
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--word",
        action="append",
        metavar="WORD",
        help="source word to process; repeat to supply multiple words",
    )
    group.add_argument(
        "--words-file",
        type=Path,
        metavar="PATH",
        help="UTF-8 text file containing one source word per line",
    )


def _add_candidate_source_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the mutually exclusive candidate inputs.

    Args:
        parser:
            Subparser receiving the arguments.
    """
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--candidate",
        action="append",
        nargs=3,
        metavar=("TRIGGER", "REPLACEMENT", "OPTIONS"),
        help=(
            "candidate semantic trigger, replacement, and AHK option string; "
            "repeat to supply multiple candidates"
        ),
    )
    group.add_argument(
        "--candidates-file",
        type=Path,
        metavar="PATH",
        help="UTF-8 JSON file containing candidate objects",
    )


def _add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    """Add settings shared by typo-generating commands.

    Args:
        parser:
            Subparser receiving the arguments.
    """
    parser.add_argument(
        "--single-attempts",
        dest="single_error_attempts_per_word",
        type=_positive_integer,
        required=True,
        metavar="COUNT",
        help="attempts per word for each forced single-error task",
    )
    parser.add_argument(
        "--multi-attempts",
        dest="multi_error_attempts_per_word",
        type=_positive_integer,
        required=True,
        metavar="COUNT",
        help="attempts per word for the mixed two-error task",
    )
    parser.add_argument(
        "--multi-min-length",
        dest="multi_error_minimum_word_length",
        type=_minimum_two_integer,
        required=True,
        metavar="LENGTH",
        help="minimum word length eligible for the mixed two-error task",
    )
    parser.add_argument(
        "--language",
        type=_nonempty_text,
        default="english",
        metavar="LANGUAGE",
        help="MULTYPO language identifier (default: %(default)s)",
    )
    parser.add_argument(
        "--excluding-set",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="enable or disable MULTYPO's language excluding set",
    )
    parser.add_argument(
        "--keyboard-weights",
        dest="keyboard_neighbor_weights",
        type=_positive_number,
        nargs=2,
        default=(9.0, 1.0),
        metavar=("HORIZONTAL", "VERTICAL"),
        help="relative keyboard-neighbor weights (default: 9 1)",
    )
    parser.add_argument(
        "--workers",
        type=_positive_integer,
        metavar="COUNT",
        help="process-pool size; omit to let the executor choose",
    )


def _add_autocorrect2_arguments(parser: argparse.ArgumentParser) -> None:
    """Add settings shared by AutoCorrect2-aware commands.

    Args:
        parser:
            Subparser receiving the arguments.
    """
    parser.add_argument(
        "--project-dir",
        dest="autocorrect2_project_dir",
        type=Path,
        metavar="PATH",
        help=(
            "AutoCorrect2 project directory; takes precedence over environment "
            "and .env configuration"
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        metavar="PATH",
        help=(
            f"dotenv file containing {AUTOCORRECT2_PROJECT_DIR_ENV}; used after "
            "the process environment (default fallback: project-root .env)"
        ),
    )
    parser.add_argument(
        "--write-accepted",
        action="store_true",
        help="append accepted candidates to AutoCorrect2's generated include",
    )


def _add_report_argument(parser: argparse.ArgumentParser) -> None:
    """Add the optional report destination.

    Args:
        parser:
            Subparser receiving the argument.
    """
    parser.add_argument(
        "--report",
        type=Path,
        metavar="PATH",
        help="write the workflow report to this path",
    )


def _positive_integer(value: str) -> int:
    """Parse a strictly positive integer for `argparse`.

    Args:
        value:
            Raw argument text.

    Returns:
        Parsed positive integer.

    Raises:
        argparse.ArgumentTypeError:
            If the value is not an integer greater than zero.
    """
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _minimum_two_integer(value: str) -> int:
    """Parse an integer greater than or equal to two.

    Args:
        value:
            Raw argument text.

    Returns:
        Parsed integer.

    Raises:
        argparse.ArgumentTypeError:
            If the value is not an integer of at least two.
    """
    parsed = _positive_integer(value)
    if parsed < 2:
        raise argparse.ArgumentTypeError("must be at least 2")
    return parsed


def _positive_number(value: str) -> float:
    """Parse a strictly positive floating-point value.

    Args:
        value:
            Raw argument text.

    Returns:
        Parsed positive number.

    Raises:
        argparse.ArgumentTypeError:
            If the value is not finite and greater than zero.
    """
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed <= 0 or not parsed < float("inf"):
        raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return parsed


def _nonempty_text(value: str) -> str:
    """Reject an empty or whitespace-only text argument.

    Args:
        value:
            Raw argument text.

    Returns:
        Trimmed text.

    Raises:
        argparse.ArgumentTypeError:
            If the value contains no non-whitespace characters.
    """
    parsed = value.strip()
    if not parsed:
        raise argparse.ArgumentTypeError("must not be empty")
    return parsed
