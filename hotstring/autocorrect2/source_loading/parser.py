"""Parse static AutoCorrect2 hotstring declarations from source text."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Final

from ...models import ExistingHotstring
from ...options import HotstringOptions

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
"""Module logger used for parser diagnostics."""

HOTSTRING_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*:([^\r\n:]*):([^\r\n]+?)::",
    re.MULTILINE,
)
"""Pattern capturing the option string and trigger of a static hotstring."""


def extract_hotstrings(content: str, *, source: str | Path) -> list[ExistingHotstring]:
    """Extract static hotstring declarations from decoded AutoCorrect2 text.

    The function performs no filesystem I/O. The caller is responsible for
    reading and decoding the source file before invoking the parser.

    Args:
        content:
            Decoded AutoCorrect2 source text.
        source:
            Source identifier stored on each extracted definition.

    Returns:
        Existing hotstrings in declaration order.

    Raises:
        TypeError:
            If the supplied source data has an invalid type.
        ValueError:
            If an extracted option string is invalid.
    """
    if not isinstance(content, str):
        raise TypeError(f"Hotstring source content must be a string, got {type(content).__name__}")
    if not isinstance(source, (str, Path)):
        raise TypeError(
            f"Hotstring source identifier must be a string or Path, got {type(source).__name__}"
        )

    source = Path(source)

    LOGGER.debug("Parsing static hotstrings from source %s.", source)

    hotstrings = [
        ExistingHotstring(
            trigger=match.group(2),
            options=HotstringOptions(match.group(1)),
            source=source,
        )
        for match in HOTSTRING_PATTERN.finditer(content)
    ]

    LOGGER.debug(
        "Parsed %d static hotstring(s) from source %s.",
        len(hotstrings),
        source,
    )
    return hotstrings
