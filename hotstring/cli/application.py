"""Define the command-line application's process boundary.

This module coordinates argument parsing, runtime configuration, logging, and
command execution. Domain work remains in [`hotstring.pipeline`][], while
parser and input-resolution details live in sibling CLI modules.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from typing import Final

from .commands import execute_command
from .parser import create_argument_parser
from .runtime import CliConfigurationError, create_command_config

_LOGGER: Final[logging.Logger] = logging.getLogger("hotstring.cli")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv:
            Optional argument sequence excluding the executable name. `None`
            reads arguments from `sys.argv`, matching normal command-line use.

    Returns:
        Process exit status: zero for success, one for a runtime failure, or
        130 when execution is interrupted. Invalid command-line input is
        reported by `argparse` with status two.
    """
    parser = create_argument_parser()
    namespace = parser.parse_args(argv)
    _configure_logging(namespace.verbosity)

    try:
        command = create_command_config(namespace)
    except CliConfigurationError as exc:
        parser.error(str(exc))

    try:
        return execute_command(command, logger=_LOGGER)
    except KeyboardInterrupt:
        print(f"{parser.prog}: interrupted", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001 - this is the process boundary.
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.exception("Command execution failed")
        else:
            print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 1


def _configure_logging(verbosity: int) -> None:
    """Configure application logging for the requested verbosity.

    Logging is left untouched at the default verbosity so library consumers
    and multiprocessing workers do not inherit an unnecessary root handler.

    Args:
        verbosity:
            Number of `-v` occurrences supplied to the top-level parser.
    """
    if verbosity <= 0:
        return

    level = logging.INFO if verbosity == 1 else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
    )
