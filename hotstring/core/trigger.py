"""Normalize AutoHotkey hotstring trigger source and matching representations.

The project keeps two distinct trigger representations:

- a *semantic trigger*, containing the actual characters AutoHotkey should
  recognize;
- an *AHK trigger*, containing a deterministic, minimally escaped source
  spelling suitable for use inside a hotstring declaration.

The conversion helpers in this module are the single source of truth for
moving between those representations. The conversion is intentionally
asymmetric with respect to source spelling: multiple valid AHK spellings may
decode to the same semantic trigger, while semantic-to-AHK conversion always
emits one canonical minimally escaped spelling.

Case-insensitive matching also lives here because it must operate on semantic
trigger text rather than escaped AHK source spelling.
"""

from __future__ import annotations

import atexit
import ctypes
import locale
import sys
from collections.abc import Callable
from typing import Final

_SEMANTIC_TO_AHK_ESCAPE: Final[dict[str, str]] = {
    "`": "``",
    "\n": "`n",
    "\r": "`r",
    "\b": "`b",
    "\t": "`t",
    "\v": "`v",
    "\a": "`a",
    "\f": "`f",
}
"""AHK source escapes for semantic characters that always require escaping."""

_AHK_ESCAPE_TO_SEMANTIC: Final[dict[str, str]] = {
    "`": "`",
    "n": "\n",
    "r": "\r",
    "b": "\b",
    "t": "\t",
    "s": " ",
    "v": "\v",
    "a": "\a",
    "f": "\f",
    ":": ":",
    ";": ";",
}
"""Known AHK escape suffixes and the semantic characters they represent."""


def semantic_to_ahk_trigger(trigger: str) -> str:
    """Convert a semantic hotstring trigger to canonical AutoHotkey source text.

    The semantic trigger contains the actual characters that AutoHotkey should
    recognize. This function converts that value into a minimally escaped,
    deterministic representation suitable for use as the trigger portion of an
    AutoHotkey hotstring declaration.

    Conversion is performed in two stages.

    First, characters which always require AutoHotkey escaping are converted
    according to `_SEMANTIC_TO_AHK_ESCAPE`. All other ordinary characters are
    preserved unchanged.

    Second, characters whose escaping requirements depend on their surrounding
    AutoHotkey source are handled:

    - A semicolon is escaped only when immediately preceded by a literal space,
      because in that position it would otherwise begin an AutoHotkey comment.
      Semantic tab characters do not require special handling here because they
      were already converted to `` `t `` during the first stage.

    - Colons are escaped only where necessary to prevent an unescaped ``::``
      sequence from appearing in the trigger or between the trigger and the
      hotstring declaration delimiter. A temporary trailing colon represents
      the first colon of that delimiter while the trigger is processed.
      Consecutive colons are then scanned from right to left, alternating
      between literal and escaped forms. The temporary colon is removed before
      returning the result.

    This produces a canonical representation without unnecessarily escaping
    colons or semicolons.

    The supported round-trip invariant is:

    ```python
    ahk_to_semantic_trigger(semantic_to_ahk_trigger(value)) == value
    ```

    for every semantic trigger accepted by this function. The reverse source
    round trip is intentionally not required because AutoHotkey can accept
    multiple equivalent source spellings.

    Args:
        trigger:
            The semantic hotstring trigger containing the actual characters
            that should be recognized.

    Returns:
        The trigger encoded for use in an AutoHotkey hotstring declaration.

    Raises:
        TypeError:
            If `trigger` is not a string.
        ValueError:
            If `trigger` is empty or contains an unsupported ASCII control
            character which has no explicitly supported AutoHotkey escape
            representation.

    Examples:
        An ordinary colon does not require escaping:

        ```text
        foo:bar -> foo:bar
        ```

        A trailing colon must be escaped because the hotstring declaration's
        closing ``::`` immediately follows it:

        ```text
        foo: -> foo`:
        ```

        Consecutive colons are escaped only as needed to prevent an unescaped
        ``::`` sequence:

        ```text
        foo::bar -> foo`::bar
        ```

        A semicolon following a space must be escaped:

        ```text
        foo ;bar -> foo `;bar
        ```

        A semicolon without a preceding space remains literal:

        ```text
        foo;bar -> foo;bar
        ```
    """
    if not isinstance(trigger, str):
        raise TypeError(
            f"Semantic hotstring trigger must be a string, not {type(trigger).__name__}"
        )
    if not trigger:
        raise ValueError("Semantic hotstring trigger cannot be empty.")

    encoded_parts: list[str] = []

    def escape_contextual_characters() -> str:
        """Apply context-dependent colon and semicolon escaping.

        `encoded_parts` contains the trigger after all unconditional escapes
        have already been applied. A temporary colon is appended to represent
        the first colon of the hotstring declaration's closing ``::``
        delimiter. Processing from right to left then makes the colon escaping
        rule identical for internal and trailing colon runs.

        Returns:
            Fully encoded canonical AutoHotkey trigger text.
        """
        encoded_parts.append(":")

        reversed_parts: list[str] = []
        escape_colon = False

        for index in range(len(encoded_parts) - 1, -1, -1):
            part = encoded_parts[index]

            if part == ":":
                reversed_parts.append("`:" if escape_colon else ":")
                escape_colon = not escape_colon
                continue

            escape_colon = False

            if (
                part == ";"
                and index > 0
                and encoded_parts[index - 1] == " "
            ):
                reversed_parts.append("`;")
            else:
                reversed_parts.append(part)

        encoded_trigger = "".join(reversed(reversed_parts))

        # The temporary delimiter colon is always the final literal character.
        return encoded_trigger[:-1]

    for character in trigger:
        escaped = _SEMANTIC_TO_AHK_ESCAPE.get(character)
        if escaped is not None:
            encoded_parts.append(escaped)
            continue

        codepoint = ord(character)
        if codepoint < 32 or codepoint == 127:
            raise ValueError(
                "Semantic hotstring trigger contains an unsupported control "
                f"character U+{codepoint:04X}."
            )

        encoded_parts.append(character)

    return escape_contextual_characters()


def ahk_to_semantic_trigger(trigger: str) -> str:
    """Convert an AutoHotkey source trigger to its semantic trigger text.

    The input is the trigger portion exactly as represented in AutoHotkey
    source syntax. Escape sequences are decoded so the returned string contains
    the actual characters AutoHotkey recognizes as the hotstring trigger.

    The function scans the source from left to right. Ordinary characters are
    copied unchanged. When an AutoHotkey escape character (`` ` ``) is
    encountered, it is consumed together with the character immediately
    following it.

    Recognized AutoHotkey escape sequences are converted to their corresponding
    semantic characters according to `_AHK_ESCAPE_TO_SEMANTIC`. This includes
    control-character escapes such as `` `n `` and `` `t ``, as well as source
    escapes such as `` `` ``, `` `: ``, and `` `; ``.

    AutoHotkey's `` `s `` escape is also decoded to a literal space, even
    though `semantic_to_ahk_trigger()` does not emit `` `s `` when producing
    its canonical source representation.

    If the escaped character does not have a special entry in
    `_AHK_ESCAPE_TO_SEMANTIC`, the escape character itself is discarded and
    the following character is preserved literally. This allows valid
    unnecessary escaping in existing AutoHotkey source to normalize to the
    same semantic trigger.

    Because multiple valid AutoHotkey source spellings can represent the same
    semantic trigger, this conversion is intentionally not the exact inverse
    of `semantic_to_ahk_trigger()` with respect to source spelling. Instead,
    the important round-trip invariant is:

    ```python
    ahk_to_semantic_trigger(semantic_to_ahk_trigger(value)) == value
    ```

    Converting existing AutoHotkey source to semantic form and then back to
    source form may therefore change its spelling by canonicalizing unnecessary
    or optional escapes.

    Args:
        trigger:
            The trigger text as written in an AutoHotkey hotstring declaration,
            excluding the surrounding option and ``::`` delimiters.

    Returns:
        The semantic trigger containing the actual characters recognized by
        AutoHotkey.

    Raises:
        TypeError:
            If `trigger` is not a string.
        ValueError:
            If `trigger` is empty or ends with an unmatched AutoHotkey escape
            character.

    Examples:
        Ordinary characters require no decoding:

        ```text
        foo.bar -> foo.bar
        ```

        An escaped colon becomes a literal semantic colon:

        ```text
        foo`:bar -> foo:bar
        ```

        An unescaped isolated colon has the same semantic meaning:

        ```text
        foo:bar -> foo:bar
        ```

        An escaped semicolon becomes a literal semicolon:

        ```text
        foo `;bar -> foo ;bar
        ```

        AutoHotkey control-character escapes are converted to the actual
        semantic character. For example, `` `t `` becomes a tab:

        ```text
        foo`tbar -> foo<TAB>bar
        ```

        The AutoHotkey space escape is accepted and normalized to an ordinary
        semantic space:

        ```text
        foo`sbar -> foo bar
        ```

        A doubled backtick represents one semantic backtick:

        ```text
        foo``bar -> foo`bar
        ```

        Different valid source spellings can therefore produce the same
        semantic value:

        ```text
        foo:bar  -> foo:bar
        foo`:bar -> foo:bar
        ```
    """
    if not isinstance(trigger, str):
        raise TypeError(
            f"AHK hotstring trigger must be a string, not {type(trigger).__name__}"
        )
    if not trigger:
        raise ValueError("AHK hotstring trigger cannot be empty.")

    decoded_parts: list[str] = []
    index = 0

    while index < len(trigger):
        character = trigger[index]

        if character != "`":
            decoded_parts.append(character)
            index += 1
            continue

        if index + 1 >= len(trigger):
            raise ValueError(
                "AutoHotkey hotstring trigger ends with an unmatched escape character."
            )

        escaped_character = trigger[index + 1]
        decoded_parts.append(
            _AHK_ESCAPE_TO_SEMANTIC.get(
                escaped_character,
                escaped_character,
            )
        )
        index += 2

    return "".join(decoded_parts)


def _python_case_insensitive_key(value: str) -> str:
    """Return the non-Windows fallback case-insensitive comparison key.

    Args:
        value:
            Semantic trigger text.

    Returns:
        Python lowercase representation used when the Microsoft CRT is not
        available.
    """
    return value.lower()


if sys.platform == "win32":
    _UCRT = ctypes.CDLL("ucrtbase.dll")

    _CREATE_LOCALE = _UCRT._create_locale
    _CREATE_LOCALE.argtypes = [ctypes.c_int, ctypes.c_char_p]
    _CREATE_LOCALE.restype = ctypes.c_void_p

    _FREE_LOCALE = _UCRT._free_locale
    _FREE_LOCALE.argtypes = [ctypes.c_void_p]
    _FREE_LOCALE.restype = None

    _WCSLWR_L = _UCRT._wcslwr_l
    _WCSLWR_L.argtypes = [ctypes.POINTER(ctypes.c_wchar), ctypes.c_void_p]
    _WCSLWR_L.restype = ctypes.c_void_p

    _C_LOCALE = _CREATE_LOCALE(locale.LC_CTYPE, b"C")
    if not _C_LOCALE:
        raise OSError("Failed to create the Microsoft CRT C locale.")

    atexit.register(_FREE_LOCALE, _C_LOCALE)

    def _windows_case_insensitive_key(value: str) -> str:
        """Return a Microsoft CRT C-locale lowercase comparison key.

        AutoHotkey's Unicode build compares case-insensitive hotstring text
        through the Microsoft CRT ``_wcsicmp`` family. Lowering each semantic
        trigger once with ``_wcslwr_l`` under an explicit ``C`` locale gives a
        reusable key with the same lowercase basis while avoiding repeated FFI
        comparisons during conflict detection.

        Args:
            value:
                Semantic trigger text.

        Returns:
            Lowercased trigger key produced by the Microsoft CRT.
        """
        buffer = ctypes.create_unicode_buffer(value)
        _WCSLWR_L(buffer, _C_LOCALE)
        return buffer.value

    _PLATFORM_CASE_INSENSITIVE_KEY: Final[Callable[[str], str]] = (
        _windows_case_insensitive_key
    )
else:
    _PLATFORM_CASE_INSENSITIVE_KEY = _python_case_insensitive_key


def make_case_insensitive_trigger_key(trigger: str) -> str:
    """Create the reusable case-insensitive matching key for a semantic trigger.

    On Windows the key is produced with the Microsoft CRT ``_wcslwr_l``
    function under an explicit ``C`` locale so comparisons reproduce
    AutoHotkey's CRT-based case-insensitive behavior as closely as possible.
    On non-Windows systems, where AutoHotkey itself does not run, Python's
    `str.lower()` is used as a deterministic fallback.

    Args:
        trigger:
            Semantic hotstring trigger text.

    Returns:
        Case-insensitive comparison key.

    Raises:
        TypeError:
            If `trigger` is not a string.
    """
    if not isinstance(trigger, str):
        raise TypeError(
            f"Semantic hotstring trigger must be a string, not {type(trigger).__name__}"
        )

    return _PLATFORM_CASE_INSENSITIVE_KEY(trigger)
