"""Extract static hotstring declarations from AutoCorrect2 source files."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from ..models import ExistingHotstring
from ..options import HotstringOptions
from .constants import (
    AUTOCORRECT2_PROJECT_DIR,
    OPTIONAL_HOTSTRING_SOURCE_RELATIVE_PATHS,
    REQUIRED_HOTSTRING_SOURCE_RELATIVE_PATHS,
)

HOTSTRING_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*:([^\r\n:]*):([^\r\n]+?)::",
    re.MULTILINE,
)
"""Pattern capturing the option string and trigger of a static hotstring."""


def extract_hotstrings(file_path: Path, *, source: Path) -> list[ExistingHotstring]:
    """Extract hotstring declarations from one AutoCorrect2 source file.

    Args:
        file_path:
            File to scan.
        source:
            Source identifier stored on each extracted definition.

    Returns:
        Existing hotstrings in declaration order.

    Raises:
        OSError:
            If the file cannot be read.
        ValueError:
            If an extracted option string is invalid.
    """
    content = file_path.read_text(encoding="utf-8-sig")
    return [
        ExistingHotstring(
            trigger=match.group(2),
            options=HotstringOptions(match.group(1)),
            source=source,
        )
        for match in HOTSTRING_PATTERN.finditer(content)
    ]


def load_existing_hotstrings(
    project_dir: Path = AUTOCORRECT2_PROJECT_DIR,
    *,
    required_source_paths: Sequence[Path] = REQUIRED_HOTSTRING_SOURCE_RELATIVE_PATHS,
    optional_source_paths: Sequence[Path] = OPTIONAL_HOTSTRING_SOURCE_RELATIVE_PATHS,
) -> list[ExistingHotstring]:
    """Load all configured active static AutoCorrect2 hotstrings.

    Required sources must exist. Optional sources, including the project-owned
    generated include file, are scanned only when present.

    Args:
        project_dir:
            AutoCorrect2 project directory.
        required_source_paths:
            Relative source paths that must exist.
        optional_source_paths:
            Relative source paths scanned when present.

    Returns:
        Existing hotstrings in source-file and declaration order.

    Raises:
        FileNotFoundError:
            If a required source does not exist.
        OSError:
            If a source cannot be read.
    """
    hotstrings: list[ExistingHotstring] = []

    for relative_path in required_source_paths:
        file_path = project_dir / relative_path
        if not file_path.is_file():
            raise FileNotFoundError(f"Hotstring source file was not found: {file_path}")
        hotstrings.extend(extract_hotstrings(file_path, source=relative_path))

    for relative_path in optional_source_paths:
        file_path = project_dir / relative_path
        if file_path.is_file():
            hotstrings.extend(extract_hotstrings(file_path, source=relative_path))

    return hotstrings
