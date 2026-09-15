"""Define filesystem constants for the AutoCorrect2 integration."""

from pathlib import Path
from typing import Final

AUTOCORRECT2_MAIN_RELATIVE_PATH: Final[Path] = Path("Core/AutoCorrect2.ahk")
"""Relative path to AutoCorrect2's main script."""

AUTOCORRECT_HOTSTRINGS_RELATIVE_PATH: Final[Path] = Path("Core/AutoCorrectHotstrings.ahk")
"""Relative path to AutoCorrect2's main autocorrection hotstring source."""

BOILERPLATE_HOTSTRINGS_RELATIVE_PATH: Final[Path] = Path("Core/PersonalHotstrings.ahk")
"""Relative path to AutoCorrect2's personal boilerplate hotstring source."""

DATE_TOOL_HOTSTRINGS_RELATIVE_PATH: Final[Path] = Path("Includes/DateTool.ahk")
"""Relative path to AutoCorrect2's date-tool hotstring source."""

REQUIRED_HOTSTRING_SOURCE_RELATIVE_PATHS: Final[tuple[Path, ...]] = (
    AUTOCORRECT_HOTSTRINGS_RELATIVE_PATH,
    BOILERPLATE_HOTSTRINGS_RELATIVE_PATH,
    DATE_TOOL_HOTSTRINGS_RELATIVE_PATH,
)
"""Existing AutoCorrect2 files expected to contain static hotstrings."""

GENERATED_HOTSTRINGS_RELATIVE_PATH: Final[Path] = Path("Core/GeneratedHotstrings.ahk")
"""Project-owned generated include file appended by the writer."""

OPTIONAL_HOTSTRING_SOURCE_RELATIVE_PATHS: Final[tuple[Path, ...]] = (
    GENERATED_HOTSTRINGS_RELATIVE_PATH,
)
"""Additional active sources checked when they already exist."""
