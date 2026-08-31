"""Define generic AutoHotkey hotstring domain models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from .options import HotstringOptions


@dataclass(frozen=True, slots=True)
class Hotstring:
    """Represent the generic declaration portion of an AHK v2 hotstring.

    Attributes:
        trigger:
            Trigger text recognized by AutoHotkey.
        options:
            Parsed per-hotstring options.
    """

    trigger: str
    options: HotstringOptions

    def __post_init__(self) -> None:
        """Validate the generic hotstring fields.

        Raises:
            TypeError:
                If `trigger` or `options` has an invalid type.
            ValueError:
                If the trigger is empty or contains a line break.
        """
        if not isinstance(self.trigger, str):
            raise TypeError(
                f"Hotstring trigger must be a string, not {type(self.trigger).__name__}"
            )
        if not self.trigger:
            raise ValueError("Hotstring trigger cannot be empty.")
        if "\n" in self.trigger or "\r" in self.trigger:
            raise ValueError("Hotstring trigger cannot contain a line break.")
        if not isinstance(self.options, HotstringOptions):
            raise TypeError(
                "Hotstring options must be a HotstringOptions instance, "
                f"not {type(self.options).__name__}"
            )

    @staticmethod
    def to_ahk_string_literal(value: str) -> str:
        """Convert text to an AutoHotkey v2 double-quoted string literal.

        The helper escapes AutoHotkey's backtick escape character, embedded
        double quotes, and the common control characters that can be safely
        represented with AHK escape sequences. Other control characters are
        rejected rather than silently producing invalid source code.

        Args:
            value:
                Text to encode as an AutoHotkey string literal.

        Returns:
            Complete double-quoted AHK string literal.

        Raises:
            TypeError:
                If `value` is not a string.
            ValueError:
                If `value` contains an unsupported control character.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"AHK string literal value must be a string, not {type(value).__name__}"
            )

        unsupported = [
            char
            for char in value
            if ord(char) < 32 and char not in {"\r", "\n", "\t"}
        ]
        if unsupported:
            codepoints = ", ".join(f"U+{ord(char):04X}" for char in unsupported)
            raise ValueError(
                "AHK string literal contains unsupported control characters: "
                f"{codepoints}"
            )

        escaped = (
            value.replace("`", "``")
            .replace('"', '`"')
            .replace("\r", "`r")
            .replace("\n", "`n")
            .replace("\t", "`t")
        )
        return f'"{escaped}"'

    def render(self, content: str | None = None) -> str:
        """Render the hotstring declaration with optional trailing content.

        `content` means everything emitted after the declaration's second
        `::`. It can therefore represent replacement text, executable inline
        content, or a multiline hotstring function body.

        If `content` is omitted, subclasses may provide their own default
        content through `_default_content()`.

        Args:
            content:
                Optional content to emit after the second `::`.

        Returns:
            Complete hotstring source text.

        Raises:
            TypeError:
                If the supplied or subclass-provided content is neither a
                string nor `None`.
        """
        if content is None:
            content = self._default_content()

        if content is not None and not isinstance(content, str):
            raise TypeError(
                "Hotstring content must be a string or None, "
                f"not {type(content).__name__}"
            )

        declaration = f":{self.options.declaration()}:{self.trigger}::"
        return declaration if content is None else declaration + content

    def _default_content(self) -> str | None:
        """Return subclass-provided content used by `render()` when omitted.

        Returns:
            Default content, or `None` when the generic hotstring has none.
        """
        return None


@dataclass(frozen=True, slots=True)
class CandidateHotstring(Hotstring, ABC):
    """Represent an abstract proposed hotstring correction.

    Concrete subclasses define how the semantic `replacement` is converted
    into AutoHotkey content. The computed content is cached once during
    initialization so the default rendering remains tied to the stored
    replacement.

    Attributes:
        replacement:
            Intended semantic replacement text.
        content:
            Derived AutoHotkey content computed by the concrete subclass.
    """

    replacement: str
    content: str = field(init=False)

    def __post_init__(self) -> None:
        """Validate the candidate and derive its AutoHotkey content.

        Raises:
            TypeError:
                If `replacement` is not a string or `compute_content()` does
                not return a string.
        """
        Hotstring.__post_init__(self)
        if not isinstance(self.replacement, str):
            raise TypeError(
                "Candidate replacement must be a string, "
                f"not {type(self.replacement).__name__}"
            )

        content = self.compute_content(self.replacement)
        if not isinstance(content, str):
            raise TypeError(
                "Candidate compute_content() must return a string, "
                f"not {type(content).__name__}"
            )
        object.__setattr__(self, "content", content)

    @abstractmethod
    def compute_content(self, replacement: str) -> str:
        """Convert semantic replacement text into concrete AHK content.

        Args:
            replacement:
                Stored candidate replacement.

        Returns:
            Content suitable for the concrete candidate type.
        """
        raise NotImplementedError

    def _default_content(self) -> str:
        """Return the candidate's precomputed content for default rendering.

        Returns:
            Precomputed candidate content.
        """
        return self.content


@dataclass(frozen=True, slots=True)
class ExistingHotstring(Hotstring):
    """Represent an existing hotstring discovered in a source file.

    Attributes:
        source:
            Source path from which the declaration was extracted.
    """

    source: Path

    def __post_init__(self) -> None:
        """Validate the existing-hotstring source field.

        Raises:
            TypeError:
                If `source` is not a [`Path`][pathlib.Path].
        """
        Hotstring.__post_init__(self)
        if not isinstance(self.source, Path):
            raise TypeError(
                f"Existing hotstring source must be a Path, not {type(self.source).__name__}"
            )
