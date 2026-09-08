"""Parse, normalize, and resolve AutoHotkey v2 hotstring option strings.

[`HotstringOptions`][hotstring.core.options.HotstringOptions] is the single source
of truth for interpreting per-hotstring option strings in this project.
Omitted inheritable options are represented by the enum member `INHERIT` of
[`InheritedState`][hotstring.core.options.InheritedState].
[`ResolvedHotstringOptions`][hotstring.core.options.ResolvedHotstringOptions]
represents the corresponding fully resolved semantic state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields, replace
from enum import Enum, auto
from typing import Final, Self, cast

_OPTION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[ \t]*(\*0?|\?0?|B0?|C[01]?|K[+-]?[0-9]+|O0?|P[+-]?[0-9]+|R0?|S[IPE0]?|T0?|X0?|Z0?)",
    re.IGNORECASE | re.ASCII,
)

_INT32_MIN: Final[int] = -(2**31)
_INT32_MAX: Final[int] = 2**31 - 1


class InheritedState(Enum):
    """Represent an option value inherited from the applicable defaults.

    Attributes:
        INHERIT:
            The option is not explicitly set and should inherit from the
            applicable default.
    """

    INHERIT = auto()


class SettingState(Enum):
    """Represent the explicit state of a two-state option.

    Attributes:
        ENABLED:
            The option behavior is explicitly enabled.
        DISABLED:
            The option behavior is explicitly disabled.
    """

    ENABLED = auto()
    DISABLED = auto()


class CaseMode(Enum):
    """Represent AutoHotkey hotstring case-matching behavior.

    Attributes:
        SENSITIVE:
            Match the trigger case-sensitively.
        INSENSITIVE_CONFORMING:
            Match case-insensitively and allow replacement case conformation.
        INSENSITIVE_FIXED:
            Match case-insensitively without replacement case conformation.
    """

    SENSITIVE = auto()
    INSENSITIVE_CONFORMING = auto()
    INSENSITIVE_FIXED = auto()


class ReplacementMode(Enum):
    """Represent AutoHotkey replacement-text interpretation behavior.

    Attributes:
        NORMAL:
            Use normal replacement processing.
        RAW:
            Use raw replacement processing.
        TEXT:
            Use text-mode replacement processing.
    """

    NORMAL = auto()
    RAW = auto()
    TEXT = auto()


class SendMode(Enum):
    """Represent the explicitly selected hotstring send mode.

    Attributes:
        INPUT:
            Explicitly select SendInput.
        PLAY:
            Explicitly select SendPlay.
        EVENT:
            Explicitly select SendEvent.
    """

    INPUT = auto()
    PLAY = auto()
    EVENT = auto()


class ResolvedSendMode(Enum):
    """Represent the fully resolved hotstring send behavior.

    Attributes:
        INPUT_WITH_PLAY_FALLBACK:
            Explicit `SI`: use SendInput with SendPlay fallback.
        INPUT_WITH_EVENT_FALLBACK:
            Built-in default: use SendInput with SendEvent fallback.
        PLAY:
            Use SendPlay.
        EVENT:
            Use SendEvent.
    """

    INPUT_WITH_PLAY_FALLBACK = auto()
    INPUT_WITH_EVENT_FALLBACK = auto()
    PLAY = auto()
    EVENT = auto()


_NON_NUMERIC_OPTION_FIELD_NAME: Final[dict[str, str]] = {
    "*": "ending_character_optional",
    "*0": "ending_character_optional",
    "?": "trigger_inside_word",
    "?0": "trigger_inside_word",
    "B": "automatic_backspacing",
    "B0": "automatic_backspacing",
    "C": "case_mode",
    "C0": "case_mode",
    "C1": "case_mode",
    "O": "omit_ending_character",
    "O0": "omit_ending_character",
    "T": "replacement_mode",
    "R": "replacement_mode",
    "T0": "replacement_mode",
    "R0": "replacement_mode",
    "S": "suspend_exempt",
    "S0": "suspend_exempt",
    "SI": "send_mode",
    "SP": "send_mode",
    "SE": "send_mode",
    "X": "execute",
    "X0": "execute",
    "Z": "reset_recognizer",
    "Z0": "reset_recognizer",
}


@dataclass(slots=True, frozen=True)
class HotstringOptions:
    """Represent a validated per-hotstring AutoHotkey option declaration.

    The original option string is retained in `options`. Every omitted option
    is represented by the singleton `InheritedState.INHERIT`, preserving the
    distinction between an inherited value and an explicitly selected value.

    Attributes:
        options:
            Original validated option string with surrounding horizontal
            whitespace removed.
        ending_character_optional:
            Whether the hotstring may activate without an ending character,
            or `InheritedState.INHERIT` if not explicitly set.
        trigger_inside_word:
            Explicit inside-word matching state, or `InheritedState.INHERIT`.
        automatic_backspacing:
            Explicit automatic-backspacing state, or `InheritedState.INHERIT`.
        case_mode:
            Explicit case-matching mode, or `InheritedState.INHERIT`.
        key_delay:
            Explicit key delay, or `InheritedState.INHERIT`.
        omit_ending_character:
            Explicit ending-character omission state, or `InheritedState.INHERIT`.
        priority:
            Explicit priority, or `InheritedState.INHERIT`.
        replacement_mode:
            Explicit replacement-processing mode, or `InheritedState.INHERIT`.
        suspend_exempt:
            Explicit suspension-exemption state, or `InheritedState.INHERIT`.
        send_mode:
            Explicit send mode, or `InheritedState.INHERIT`.
        execute:
            Explicit execute state, or `InheritedState.INHERIT`.
        reset_recognizer:
            Explicit recognizer-reset state, or `InheritedState.INHERIT`.
    """

    options: str = field(init=True, compare=False)

    ending_character_optional: SettingState | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {SettingState.ENABLED: "*", SettingState.DISABLED: "*0"},
            "str_to_value": {"*": SettingState.ENABLED, "*0": SettingState.DISABLED},
        },
    )
    trigger_inside_word: SettingState | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {SettingState.ENABLED: "?", SettingState.DISABLED: "?0"},
            "str_to_value": {"?": SettingState.ENABLED, "?0": SettingState.DISABLED},
        },
    )
    automatic_backspacing: SettingState | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {SettingState.ENABLED: "B", SettingState.DISABLED: "B0"},
            "str_to_value": {"B": SettingState.ENABLED, "B0": SettingState.DISABLED},
        },
    )
    case_mode: CaseMode | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {
                CaseMode.SENSITIVE: "C",
                CaseMode.INSENSITIVE_CONFORMING: "C0",
                CaseMode.INSENSITIVE_FIXED: "C1",
            },
            "str_to_value": {
                "C": CaseMode.SENSITIVE,
                "C0": CaseMode.INSENSITIVE_CONFORMING,
                "C1": CaseMode.INSENSITIVE_FIXED,
            },
        },
    )
    key_delay: int | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={"value_to_str": {}, "str_to_value": {}},
    )
    omit_ending_character: SettingState | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {SettingState.ENABLED: "O", SettingState.DISABLED: "O0"},
            "str_to_value": {"O": SettingState.ENABLED, "O0": SettingState.DISABLED},
        },
    )
    priority: int | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={"value_to_str": {}, "str_to_value": {}},
    )
    replacement_mode: ReplacementMode | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {
                ReplacementMode.NORMAL: "R0",
                ReplacementMode.RAW: "R",
                ReplacementMode.TEXT: "T",
            },
            "str_to_value": {
                "R0": ReplacementMode.NORMAL,
                "T0": ReplacementMode.NORMAL,
                "R": ReplacementMode.RAW,
                "T": ReplacementMode.TEXT,
            },
        },
    )
    suspend_exempt: SettingState | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {SettingState.ENABLED: "S", SettingState.DISABLED: "S0"},
            "str_to_value": {"S": SettingState.ENABLED, "S0": SettingState.DISABLED},
        },
    )
    send_mode: SendMode | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {
                SendMode.INPUT: "SI",
                SendMode.PLAY: "SP",
                SendMode.EVENT: "SE",
            },
            "str_to_value": {
                "SI": SendMode.INPUT,
                "SP": SendMode.PLAY,
                "SE": SendMode.EVENT,
            },
        },
    )
    execute: SettingState | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {SettingState.ENABLED: "X", SettingState.DISABLED: "X0"},
            "str_to_value": {"X": SettingState.ENABLED, "X0": SettingState.DISABLED},
        },
    )
    reset_recognizer: SettingState | InheritedState = field(
        init=False,
        default=InheritedState.INHERIT,
        metadata={
            "value_to_str": {SettingState.ENABLED: "Z", SettingState.DISABLED: "Z0"},
            "str_to_value": {"Z": SettingState.ENABLED, "Z0": SettingState.DISABLED},
        },
    )

    def __post_init__(self) -> None:
        """Validate and parse the supplied option string.

        Raises:
            TypeError:
                If `options` is not a string.
            ValueError:
                If the string contains an unsupported option or an invalid
                numeric value.
        """
        if not isinstance(self.options, str):
            raise TypeError(
                f"Hotstring options must be a string, not {type(self.options).__name__}"
            )

        object.__setattr__(self, "options", self.options.strip(" \t"))

        field_name_to_info = {field_info.name: field_info for field_info in fields(self)}
        options = self.options
        position = 0

        while position < len(options):
            match = _OPTION_PATTERN.match(options, position)
            if match is None:
                raise ValueError(
                    f"Invalid hotstring option at position {position}: {options[position:]!r}"
                )

            option = match.group(1).upper()

            if option.startswith("K"):
                key_delay = int(option[1:])
                if not -1 <= key_delay <= _INT32_MAX:
                    raise ValueError(
                        f"Hotstring key delay must be between -1 and {_INT32_MAX}: {option!r}"
                    )
                object.__setattr__(self, "key_delay", key_delay)

            elif option.startswith("P"):
                priority = int(option[1:])
                if not _INT32_MIN <= priority <= _INT32_MAX:
                    raise ValueError(
                        f"Hotstring priority is outside the signed 32-bit range: {option!r}"
                    )
                object.__setattr__(self, "priority", priority)

            else:
                field_name = _NON_NUMERIC_OPTION_FIELD_NAME.get(option)
                if field_name is None:
                    raise AssertionError(f"Unhandled hotstring option: {option!r}")

                field_info = field_name_to_info[field_name]
                str_to_value = field_info.metadata.get("str_to_value", {})
                value = str_to_value.get(option)
                if value is None:
                    raise RuntimeError(
                        f"Failed to map hotstring option {option!r} to a value for "
                        f"field {field_name!r}; this should never happen."
                    )
                object.__setattr__(self, field_name, value)

            position = match.end()

    def declaration(self) -> str:
        """Return a canonical option string for the parsed semantic state.

        Returns:
            Canonical option text in dataclass field order. Inherited options
            are omitted.
        """
        options_str = ""

        for field_info in fields(self):
            name = field_info.name
            if name == "options":
                continue

            value = getattr(self, name)
            if value is InheritedState.INHERIT:
                continue

            if name == "key_delay":
                option_str = f"K{value}"
            elif name == "priority":
                option_str = f"P{value}"
            else:
                value_to_str = field_info.metadata.get("value_to_str", {})
                option_str = value_to_str.get(value)
                if option_str is None:
                    raise RuntimeError(
                        f"Failed to map value {value!r} of field {name!r} to a string; "
                        "this should never happen."
                    )

            options_str += option_str

        return options_str


@dataclass(slots=True, frozen=True, kw_only=True)
class ResolvedHotstringOptions:
    """Represent a fully resolved AutoHotkey hotstring option state.

    Unlike [`HotstringOptions`][hotstring.core.options.HotstringOptions], every
    field contains a concrete semantic value. `InheritedState` is therefore
    absent from every field annotation.

    Attributes:
        ending_character_optional:
            Whether the hotstring may activate without an ending character.
        trigger_inside_word:
            Whether the trigger may begin after an alphanumeric character.
        automatic_backspacing:
            Whether AutoHotkey automatically erases the typed trigger.
        case_mode:
            Effective case-matching mode.
        key_delay:
            Effective hotstring key delay.
        omit_ending_character:
            Whether an ending character is omitted from replacement output.
        priority:
            Effective hotstring thread priority.
        replacement_mode:
            Effective replacement-text processing mode.
        suspend_exempt:
            Whether the hotstring is exempt from suspension.
        send_mode:
            Effective replacement send mode.
        execute:
            Whether inline content is executed rather than used as literal
            replacement text.
        reset_recognizer:
            Whether the recognizer resets after activation.
    """

    ending_character_optional: SettingState
    trigger_inside_word: SettingState
    automatic_backspacing: SettingState
    case_mode: CaseMode
    key_delay: int
    omit_ending_character: SettingState
    priority: int
    replacement_mode: ReplacementMode
    suspend_exempt: SettingState
    send_mode: ResolvedSendMode
    execute: SettingState
    reset_recognizer: SettingState

    def __post_init__(self) -> None:
        """Validate the resolved option state.

        Raises:
            TypeError:
                If any field has an invalid type.
            ValueError:
                If any numeric field is outside its accepted range.
        """
        binary_field_names = (
            "ending_character_optional",
            "trigger_inside_word",
            "automatic_backspacing",
            "omit_ending_character",
            "suspend_exempt",
            "execute",
            "reset_recognizer",
        )

        if not isinstance(self.case_mode, CaseMode):
            raise TypeError(
                f"case_mode must be a CaseMode member, got {type(self.case_mode).__name__}"
            )
        if isinstance(self.key_delay, bool) or not isinstance(self.key_delay, int):
            raise TypeError(f"key_delay must be an int, got {type(self.key_delay).__name__}")
        if not -1 <= self.key_delay <= _INT32_MAX:
            raise ValueError(f"key_delay must be between -1 and {_INT32_MAX}, got {self.key_delay}")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError(f"priority must be an int, got {type(self.priority).__name__}")
        if not _INT32_MIN <= self.priority <= _INT32_MAX:
            raise ValueError(
                f"priority must not be outside the signed 32-bit range, got {self.priority}"
            )
        if not isinstance(self.replacement_mode, ReplacementMode):
            raise TypeError(
                "replacement_mode must be a ReplacementMode member, got "
                f"{type(self.replacement_mode).__name__}"
            )
        if not isinstance(self.send_mode, ResolvedSendMode):
            raise TypeError(
                f"send_mode must be a ResolvedSendMode member, got {type(self.send_mode).__name__}"
            )

        for field_name in binary_field_names:
            value = getattr(self, field_name)
            if not isinstance(value, SettingState):
                raise TypeError(
                    f"{field_name} must be a SettingState member, got {type(value).__name__}"
                )

    @classmethod
    def from_options(
        cls,
        options: HotstringOptions,
        *,
        defaults: ResolvedHotstringOptions,
    ) -> Self:
        """Resolve one parsed declaration against concrete applicable defaults.

        Each explicitly set value in `options` overrides the corresponding
        value in `defaults`; each `InheritedState.INHERIT` value leaves the
        applicable default unchanged.

        Explicit `SI` is resolved to SendInput with SendPlay fallback, while
        an inherited built-in default can remain SendInput with SendEvent
        fallback. This preserves AutoHotkey's distinction between those cases.

        Args:
            options:
                Parsed per-hotstring declaration to resolve.
            defaults:
                Fully resolved defaults applicable to the declaration.

        Returns:
            New fully resolved option state.

        Raises:
            TypeError:
                If either argument has an invalid type.
            RuntimeError:
                If the parsed and resolved option models stop exposing the
                same option field names.
        """
        if not isinstance(options, HotstringOptions):
            raise TypeError(
                f"options must be a HotstringOptions instance, got {type(options).__name__}"
            )
        if not isinstance(defaults, cls):
            raise TypeError(
                f"defaults must be a {cls.__name__} instance, got {type(defaults).__name__}"
            )

        parsed_field_names = {
            field_info.name for field_info in fields(options) if field_info.name != "options"
        }
        resolved_field_names = {field_info.name for field_info in fields(cls)}
        if parsed_field_names != resolved_field_names:
            raise RuntimeError(
                "HotstringOptions and ResolvedHotstringOptions option fields are inconsistent."
            )

        overrides: dict[str, object] = {}
        for name in resolved_field_names:
            value = getattr(options, name)
            if value is InheritedState.INHERIT:
                continue

            if name == "send_mode":
                if value is SendMode.INPUT:
                    overrides[name] = ResolvedSendMode.INPUT_WITH_PLAY_FALLBACK
                elif value is SendMode.PLAY:
                    overrides[name] = ResolvedSendMode.PLAY
                elif value is SendMode.EVENT:
                    overrides[name] = ResolvedSendMode.EVENT
                else:
                    raise RuntimeError(f"Unhandled explicit send mode: {value!r}")
            else:
                overrides[name] = value

        return cast(Self, replace(defaults, **overrides))
