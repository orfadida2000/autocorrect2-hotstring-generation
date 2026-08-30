"""Extract static hotstring definitions from AutoCorrect2 source files.

The parser scans complete source files with one multiline regular
expression. Only the options and trigger portions are captured because
replacement text and executable bodies are irrelevant to contradiction
detection.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from ..models import ExistingHotstring
from ..options import HotstringOptions
from .constants import (
    AUTOCORRECT2_PROJECT_DIR,
    HOTSTRING_SOURCE_RELATIVE_PATHS,
)

HOTSTRING_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*:([^\r\n:]*):([^\r\n]+?)::",
    re.MULTILINE,
)
"""Pattern capturing a static hotstring's options and trigger."""


def extract_hotstrings(
    file_path: Path,
    *,
    source: Path,
) -> list[ExistingHotstring]:
    """Extract static hotstrings from one source file.

    Args:
        file_path:
            Absolute path of the file to read.
        source:
            Source identifier stored on each extracted hotstring, normally
            relative to the AutoCorrect2 project directory.

    Returns:
        Extracted hotstrings in declaration order.

    Raises:
        OSError:
            If the source file cannot be read.
        ValueError:
            If a captured option string is invalid.
    """
    content = file_path.read_text(encoding="utf-8-sig")

    return [
        ExistingHotstring(
            options=HotstringOptions(match.group(1)),
            trigger=match.group(2),
            source=source,
        )
        for match in HOTSTRING_PATTERN.finditer(content)
    ]


def load_existing_hotstrings(
    project_dir: Path = AUTOCORRECT2_PROJECT_DIR,
    source_paths: Sequence[Path] = HOTSTRING_SOURCE_RELATIVE_PATHS,
) -> list[ExistingHotstring]:
    """Load hotstrings from all configured AutoCorrect2 source files.

    Args:
        project_dir:
            Base AutoCorrect2 project directory.
        source_paths:
            Source paths relative to `project_dir`.

    Returns:
        All extracted definitions in source-file and declaration order.

    Raises:
        FileNotFoundError:
            If a configured source path is not an existing file.
        OSError:
            If a source file cannot be read.
        ValueError:
            If a discovered option string is invalid.
    """
    hotstrings: list[ExistingHotstring] = []

    for relative_path in source_paths:
        file_path = project_dir / relative_path

        if not file_path.is_file():
            raise FileNotFoundError(f"Hotstring source file was not found: {file_path}")

        hotstrings.extend(
            extract_hotstrings(
                file_path,
                source=relative_path,
            )
        )

    return hotstrings
