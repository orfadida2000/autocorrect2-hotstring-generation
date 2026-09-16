"""Expose the command-line application entry point.

The implementation is split by responsibility so importing
[`main()`][hotstring.cli.application.main] does not make parser construction,
runtime configuration, and pipeline dispatch one monolithic module.
"""

from .application import main

__all__ = ["main"]
