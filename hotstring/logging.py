import logging
import sys
from pathlib import Path
from typing import Any, TextIO


def configure_root_logger(
    root_level: int = logging.DEBUG,
    use_stderr: bool | None = True,
    console_level: int = logging.INFO,
    file_path: Path | str | None = None,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure the root logger with a optional console handler and an optional file handler.

    If both `use_stderr` and `file_path` are `None`, a null handler will be added to the root logger to prevent "No handlers could be found" warnings.

    Args:
        root_level: Logging level for the root logger.
        use_stderr: `True` to use stderr for the console handler, `False` to use stdout, or `None` to disable the console handler.
        console_level: Logging level for the console handler (if applicable).
        file_path: Optional path to a log file. If provided, a file handler will be added with the specified level.
        file_level: Logging level for the file handler (if applicable).
    """
    root_logger = logging.getLogger()

    root_logger.handlers.clear()  # Clear existing handlers

    root_logger.setLevel(root_level)

    if use_stderr is None and file_path is None:
        # Add a null handler to prevent "No handlers could be found" warnings
        root_logger.addHandler(logging.NullHandler())
        return

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    if use_stderr is not None:
        console_stream: TextIO | Any = sys.stderr if use_stderr else sys.stdout
        console_handler = logging.StreamHandler(console_stream)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if file_path:
        # Create file handler
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
