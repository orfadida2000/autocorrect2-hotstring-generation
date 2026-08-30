"""Filesystem constants for the AutoCorrect2 integration."""

from pathlib import Path
from typing import Final

AUTOCORRECT2_PROJECT_DIR: Final[Path] = Path(r"C:\PATH\TO\AutoCorrect2")
"""Base directory of the local AutoCorrect2 project."""

HOTSTRING_SOURCE_RELATIVE_PATHS: Final[tuple[Path, ...]] = (
    Path("Core/AutoCorrectHotstrings.ahk"),
    Path("Core/PersonalHotstrings.ahk"),
    Path("Includes/DateTool.ahk"),
)
"""AutoCorrect2 files that may contain static hotstring definitions."""

DEFAULT_CONFLICT_REPORT_PATH: Final[Path] = Path("hotstring_candidate_report.txt")
"""Default path for the generated candidate conflict report."""
