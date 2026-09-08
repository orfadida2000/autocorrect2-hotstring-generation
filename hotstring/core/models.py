"""Define generic AutoHotkey hotstring domain models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import ClassVar, Final

from .options import HotstringOptions
from .trigger import (
    ahk_to_semantic_trigger,
    make_case_insensitive_trigger_key,
    semantic_to_ahk_trigger,
)

CHECK_TRIGGER_ROUND_TRIP: Final[bool] = True
"""Whether hotstring initialization verifies the trigger conversion invariant."""


@dataclass(frozen=True, slots=True)
class Hotstring:
    """Represent the generic declaration portion of an AutoHotkey v2 hotstring.

    `trigger` and `options_input` are constructor-only values. By default,
    `trigger` is interpreted as semantic trigger text. Subclasses whose
    constructor receives AHK source-form trigger text can override the
    `TRIGGER_INPUT_IS_AHK_SOURCE` class policy without replacing the shared
    trigger-resolution algorithm.

    Args:
        trigger:
            Constructor trigger input. For `Hotstring` and candidate classes,
            this is semantic trigger text. Subclasses may declare that the same
            constructor argument is AHK source text by overriding
            `TRIGGER_INPUT_IS_AHK_SOURCE`.
        options_input:
            Parsed hotstring options or a raw option declaration string.

    Attributes:
        TRIGGER_INPUT_IS_AHK_SOURCE:
            Whether the constructor's `trigger` argument is interpreted as
            AutoHotkey source text rather than as a semantic trigger.

            If `False`, `trigger` is treated as the literal semantic text that
            the hotstring should recognize. If `True`, `trigger` is treated as
            AutoHotkey source text and is decoded before the semantic and
            canonical AutoHotkey trigger representations are derived.

            Subclasses may override this class attribute to define the expected
            representation of their constructor trigger input.
        semantic_trigger:
            Semantic trigger text containing the actual characters AutoHotkey
            should recognize.
        ahk_trigger:
            Canonical, minimally escaped trigger source spelling used inside an
            AHK hotstring declaration.
        options:
            Parsed per-hotstring options. This is always a
            [`HotstringOptions`][hotstring.core.options.HotstringOptions]
            instance after initialization, regardless of the constructor input
            type.
        case_insensitive_semantic_trigger_key:
            Cached comparison key derived from `semantic_trigger` and used for
            AutoHotkey-compatible case-insensitive conflict detection. This is
            derived runtime state rather than another trigger representation.
    """

    TRIGGER_INPUT_IS_AHK_SOURCE: ClassVar[bool] = False

    trigger: InitVar[str]
    options_input: InitVar[str | HotstringOptions]

    semantic_trigger: str = field(init=False)
    ahk_trigger: str = field(init=False)
    options: HotstringOptions = field(init=False)
    case_insensitive_semantic_trigger_key: str = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(
        self,
        trigger: str,
        options_input: str | HotstringOptions,
    ) -> None:
        """Resolve constructor inputs and establish immutable hotstring state.

        Trigger initialization follows one shared algorithm for the full
        hierarchy:

        1. interpret the constructor trigger according to
           `TRIGGER_INPUT_IS_AHK_SOURCE`;
        2. derive the semantic trigger;
        3. derive the canonical AHK trigger from the semantic trigger;
        4. optionally verify that decoding the canonical AHK trigger reproduces
           the same semantic trigger.

        Args:
            trigger:
                Constructor trigger input supplied through the `InitVar`.
            options_input:
                Raw or already parsed option input supplied through the
                `InitVar`.

        Raises:
            TypeError:
                If the trigger or options input has an invalid type.
            ValueError:
                If the resolved semantic trigger is empty or cannot be
                represented safely in canonical AHK source form, or if the
                option string is invalid.
            AssertionError:
                If `CHECK_TRIGGER_ROUND_TRIP` is enabled and the canonical AHK
                trigger does not decode back to the derived semantic trigger.
        """
        if not isinstance(trigger, str):
            raise TypeError(
                f"Hotstring trigger input must be a string, not {type(trigger).__name__}"
            )

        semantic_trigger = (
            ahk_to_semantic_trigger(trigger) if self.TRIGGER_INPUT_IS_AHK_SOURCE else trigger
        )
        if not semantic_trigger:
            raise ValueError("Hotstring semantic trigger cannot be empty.")

        ahk_trigger = semantic_to_ahk_trigger(semantic_trigger)

        if CHECK_TRIGGER_ROUND_TRIP:
            round_trip_trigger = ahk_to_semantic_trigger(ahk_trigger)
            if round_trip_trigger != semantic_trigger:
                raise AssertionError(
                    "Canonical AHK trigger does not round-trip to the semantic trigger."
                )

        if isinstance(options_input, str):
            options = HotstringOptions(options_input)
        elif isinstance(options_input, HotstringOptions):
            options = options_input
        else:
            raise TypeError(
                "Hotstring options input must be a string or HotstringOptions "
                f"instance, not {type(options_input).__name__}"
            )

        object.__setattr__(self, "semantic_trigger", semantic_trigger)
        object.__setattr__(self, "ahk_trigger", ahk_trigger)
        object.__setattr__(self, "options", options)
        object.__setattr__(
            self,
            "case_insensitive_semantic_trigger_key",
            make_case_insensitive_trigger_key(semantic_trigger),
        )

    @staticmethod
    def to_ahk_string_literal(value: str) -> str:
        """Convert text to an AutoHotkey v2 double-quoted string literal.

        This helper is intentionally separate from hotstring-trigger source
        encoding. A quoted AHK expression string and a hotstring trigger
        declaration have different escaping rules.

        Literal backticks, double quotes, and every supported AutoHotkey control
        escape are encoded. Unsupported ASCII control characters are rejected
        rather than emitted invisibly into generated source.

        Args:
            value:
                Text to encode as an AutoHotkey string literal.

        Returns:
            Complete double-quoted AHK string literal.

        Raises:
            TypeError:
                If `value` is not a string.
            ValueError:
                If `value` contains an unsupported ASCII control character.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"AHK string literal value must be a string, not {type(value).__name__}"
            )

        supported_control_characters = {
            "\r",
            "\n",
            "\b",
            "\t",
            "\v",
            "\a",
            "\f",
        }
        unsupported = [
            character
            for character in value
            if (ord(character) < 32 and character not in supported_control_characters)
            or ord(character) == 127
        ]
        if unsupported:
            codepoints = ", ".join(f"U+{ord(character):04X}" for character in unsupported)
            raise ValueError(
                f"AHK string literal contains unsupported control characters: {codepoints}"
            )

        escaped = (
            value.replace("`", "``")
            .replace('"', '`"')
            .replace("\r", "`r")
            .replace("\n", "`n")
            .replace("\b", "`b")
            .replace("\t", "`t")
            .replace("\v", "`v")
            .replace("\a", "`a")
            .replace("\f", "`f")
        )
        return f'"{escaped}"'

    def render(self, content: str | None = None) -> str:
        """Render the hotstring declaration with optional trailing content.

        Rendering always uses the canonical `ahk_trigger` representation,
        never the constructor input or semantic trigger. This guarantees that
        triggers containing context-sensitive colons or semicolons, literal
        backticks, or supported control characters are emitted safely and
        consistently.

        `content` means everything emitted after the declaration's second
        `::`. It can therefore represent replacement text, executable inline
        content, or a multiline hotstring function body. If `content` is
        omitted, subclasses may provide their own default through
        [`_default_content()`][hotstring.core.models.Hotstring._default_content].

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
                f"Hotstring content must be a string or None, not {type(content).__name__}"
            )

        declaration = f":{self.options.declaration()}:{self.ahk_trigger}::"
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

    Candidate constructor trigger input is semantic text, so this class keeps
    the inherited `TRIGGER_INPUT_IS_AHK_SOURCE = False` policy. Concrete
    subclasses define how the semantic `replacement` is converted into
    AutoHotkey content. The computed content is cached once during
    initialization.

    Args:
        trigger:
            Semantic trigger text proposed for the candidate.
        options_input:
            Raw or already parsed hotstring options.
        replacement:
            Intended semantic replacement text.

    Attributes:
        replacement:
            Intended semantic replacement text.
        content:
            Derived AutoHotkey content computed by the concrete subclass.
    """

    replacement: str
    content: str = field(init=False)

    def __post_init__(
        self,
        trigger: str,
        options_input: str | HotstringOptions,
    ) -> None:
        """Validate the candidate and derive its AutoHotkey content.

        Args:
            trigger:
                Semantic trigger constructor input.
            options_input:
                Raw or parsed option constructor input.

        Raises:
            TypeError:
                If `replacement` is not a string or `compute_content()` does
                not return a string.
            ValueError:
                If base hotstring initialization rejects an input.
            AssertionError:
                If an enabled base trigger invariant check fails.
        """
        Hotstring.__post_init__(self, trigger, options_input)

        if not isinstance(self.replacement, str):
            raise TypeError(
                f"Candidate replacement must be a string, not {type(self.replacement).__name__}"
            )

        content = self.compute_content(self.replacement)
        if not isinstance(content, str):
            raise TypeError(
                f"Candidate compute_content() must return a string, not {type(content).__name__}"
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
    """Represent an existing hotstring discovered in an AHK source file.

    Unlike the generic and candidate models, `trigger` passed to this class is
    interpreted as AHK source-form trigger text. The class expresses that
    difference only by shadowing `TRIGGER_INPUT_IS_AHK_SOURCE`; the base
    `__post_init__()` still owns the complete resolution algorithm. Existing
    source is decoded to semantic form and re-encoded to the project's
    canonical minimally escaped AHK form, so equivalent source spellings
    produce identical stored trigger state.

    Args:
        trigger:
            Trigger source spelling extracted from the AHK declaration.
        options_input:
            Raw or parsed hotstring options.
        source:
            Source path from which the declaration was extracted.

    Attributes:
        source:
            Source path from which the declaration was extracted.
    """

    TRIGGER_INPUT_IS_AHK_SOURCE: ClassVar[bool] = True

    source: Path

    def __post_init__(
        self,
        trigger: str,
        options_input: str | HotstringOptions,
    ) -> None:
        """Resolve the AHK trigger input and validate the source field.

        Args:
            trigger:
                AHK source-form trigger constructor input.
            options_input:
                Raw or parsed option constructor input.

        Raises:
            TypeError:
                If `source` is not a [`Path`][pathlib.Path].
            ValueError:
                If the trigger or option input is invalid.
            AssertionError:
                If an enabled base trigger invariant check fails.
        """
        Hotstring.__post_init__(self, trigger, options_input)

        if not isinstance(self.source, Path):
            raise TypeError(
                f"Existing hotstring source must be a Path, not {type(self.source).__name__}"
            )
