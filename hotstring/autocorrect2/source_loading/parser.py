"""Parse static AutoCorrect2 hotstring declarations from source text.

The parser treats trigger source spelling as AutoHotkey syntax rather than as
plain text. In particular, an escaped colon (`` `: ``) is part of the trigger
and must not be mistaken for the closing ``::`` delimiter. Parsed trigger text
is passed to [`ExistingHotstring`][hotstring.core.models.ExistingHotstring] in AHK
source form; the model then derives semantic and canonical source forms.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Final

from ...core.models import ExistingHotstring

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
"""Module logger used for parser diagnostics."""

HOTSTRING_PREFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[ \t]*:([^\r\n:]*):"
)
"""Pattern capturing a static declaration's indentation and option prefix."""


def extract_hotstrings(content: str, *, source: str | Path) -> list[ExistingHotstring]:
    """Extract static hotstring declarations from decoded AutoCorrect2 text.

    The function performs no filesystem I/O. Each source line is checked for a
    leading ``:options:`` prefix. The trigger is then scanned character by
    character so escaped characters cannot terminate it accidentally.

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
            If a recognized declaration contains invalid options or invalid
            AHK trigger escaping.
    """
    if not isinstance(content, str):
        raise TypeError(
            f"Hotstring source content must be a string, got {type(content).__name__}"
        )
    if not isinstance(source, (str, Path)):
        raise TypeError(
            "Hotstring source identifier must be a string or Path, "
            f"got {type(source).__name__}"
        )

    source_path = Path(source)
    LOGGER.debug("Parsing static hotstrings from source %s.", source_path)

    hotstrings: list[ExistingHotstring] = []
    for line in content.splitlines():
        prefix_match = HOTSTRING_PREFIX_PATTERN.match(line)
        if prefix_match is None:
            continue

        trigger_start = prefix_match.end()
        trigger_end = _find_trigger_delimiter(line, start=trigger_start)
        if trigger_end is None:
            continue

        hotstrings.append(
            ExistingHotstring(
                trigger=line[trigger_start:trigger_end],
                options_input=prefix_match.group(1),
                source=source_path,
            )
        )

    LOGGER.debug(
        "Parsed %d static hotstring(s) from source %s.",
        len(hotstrings),
        source_path,
    )
    return hotstrings


def _find_trigger_delimiter(line: str, *, start: int) -> int | None:
    """Locate the first unescaped ``::`` trigger delimiter on one source line.

    A backtick escapes the next source character, so a colon immediately after
    a backtick cannot begin the delimiter. Two consecutive backticks represent
    one literal backtick; scanning the pair as one escaped unit naturally lets
    a following ``::`` terminate the trigger.

    An unescaped semicolon preceded by horizontal whitespace begins an
    AutoHotkey comment. If such a comment starts before a closing delimiter,
    the line does not contain a complete static hotstring declaration.

    Args:
        line:
            One source line without its newline terminator.
        start:
            Index immediately after the ``:options:`` prefix.

    Returns:
        Index of the first colon in the closing delimiter, or `None` when no
        valid delimiter occurs before the end of the source line.
    """
    index = start

    while index < len(line):
        character = line[index]

        if character == "`":
            if index + 1 >= len(line):
                return None
            index += 2
            continue

        if (
            character == ";"
            and index > 0
            and line[index - 1] in {" ", "\t"}
        ):
            return None

        if character == ":" and index + 1 < len(line) and line[index + 1] == ":":
            return index

        index += 1

    return None
