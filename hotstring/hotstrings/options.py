import re
from collections.abc import Callable
from dataclasses import dataclass, field, fields
from enum import Enum, auto
from typing import Final

_OPTION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"[ \t]*(\*0?|\?0?|B0?|C[01]?|K[+-]?[0-9]+|O0?|P[+-]?[0-9]+|R0?|S[IPE0]?|T0?|X0?|Z0?)",
    re.IGNORECASE | re.ASCII,
)

_INT32_MIN: Final[int] = -(2**31)
_INT32_MAX: Final[int] = 2**31 - 1


class CaseMode(Enum):
    SENSITIVE = auto()
    INSENSITIVE_CONFORMING = auto()
    INSENSITIVE_FIXED = auto()


class ReplacementMode(Enum):
    NORMAL = auto()
    RAW = auto()
    TEXT = auto()


class SendMode(Enum):
    INPUT_WITH_PLAY_FALLBACK = auto()
    PLAY = auto()
    EVENT = auto()


_NON_K_P_OPTION_TO_HANDLER: dict[str, Callable[..., None]] = {
    "*": lambda self: object.__setattr__(self, "ending_character_required", False),
    "*0": lambda self: object.__setattr__(self, "ending_character_required", True),
    "?": lambda self: object.__setattr__(self, "trigger_inside_word", True),
    "?0": lambda self: object.__setattr__(self, "trigger_inside_word", False),
    "B": lambda self: object.__setattr__(self, "automatic_backspacing", True),
    "B0": lambda self: object.__setattr__(self, "automatic_backspacing", False),
    "C": lambda self: object.__setattr__(self, "case_mode", CaseMode.SENSITIVE),
    "C0": lambda self: object.__setattr__(self, "case_mode", CaseMode.INSENSITIVE_CONFORMING),
    "C1": lambda self: object.__setattr__(self, "case_mode", CaseMode.INSENSITIVE_FIXED),
    "O": lambda self: object.__setattr__(self, "omit_ending_character", True),
    "O0": lambda self: object.__setattr__(self, "omit_ending_character", False),
    "R": lambda self: object.__setattr__(self, "replacement_mode", ReplacementMode.RAW),
    "R0": lambda self: object.__setattr__(self, "replacement_mode", ReplacementMode.NORMAL),
    "T0": lambda self: object.__setattr__(self, "replacement_mode", ReplacementMode.NORMAL),
    "S": lambda self: object.__setattr__(self, "suspend_exempt", True),
    "S0": lambda self: object.__setattr__(self, "suspend_exempt", False),
    "SI": lambda self: object.__setattr__(self, "send_mode", SendMode.INPUT_WITH_PLAY_FALLBACK),
    "SP": lambda self: object.__setattr__(self, "send_mode", SendMode.PLAY),
    "SE": lambda self: object.__setattr__(self, "send_mode", SendMode.EVENT),
    "T": lambda self: object.__setattr__(self, "replacement_mode", ReplacementMode.TEXT),
    "X": lambda self: object.__setattr__(self, "execute", True),
    "X0": lambda self: object.__setattr__(self, "execute", False),
    "Z": lambda self: object.__setattr__(self, "reset_recognizer", True),
    "Z0": lambda self: object.__setattr__(self, "reset_recognizer", False),
}


@dataclass(slots=True, frozen=True)
class HotstringOptions:
    options: str = field(init=True, compare=False)

    ending_character_required: bool | None = field(
        init=False, default=None, metadata={"value_to_str": {True: "*0", False: "*", None: ""}}
    )
    trigger_inside_word: bool | None = field(
        init=False, default=None, metadata={"value_to_str": {True: "?", False: "?0", None: ""}}
    )
    automatic_backspacing: bool | None = field(
        init=False, default=None, metadata={"value_to_str": {True: "B", False: "B0", None: ""}}
    )
    case_mode: CaseMode | None = field(
        init=False,
        default=None,
        metadata={
            "value_to_str": {
                CaseMode.SENSITIVE: "C",
                CaseMode.INSENSITIVE_CONFORMING: "C0",
                CaseMode.INSENSITIVE_FIXED: "C1",
                None: "",
            }
        },
    )
    key_delay: int | None = field(init=False, default=None)
    omit_ending_character: bool | None = field(
        init=False, default=None, metadata={"value_to_str": {True: "O", False: "O0", None: ""}}
    )
    priority: int | None = field(init=False, default=None)
    replacement_mode: ReplacementMode | None = field(
        init=False,
        default=None,
        metadata={
            "value_to_str": {
                ReplacementMode.NORMAL: "R0",
                ReplacementMode.RAW: "R",
                ReplacementMode.TEXT: "T",
                None: "",
            }
        },
    )
    suspend_exempt: bool | None = field(
        init=False, default=None, metadata={"value_to_str": {True: "S", False: "S0", None: ""}}
    )
    send_mode: SendMode | None = field(
        init=False,
        default=None,
        metadata={
            "value_to_str": {
                SendMode.INPUT_WITH_PLAY_FALLBACK: "SI",
                SendMode.PLAY: "SP",
                SendMode.EVENT: "SE",
                None: "",
            }
        },
    )
    execute: bool = field(
        init=False, default=False, metadata={"value_to_str": {True: "X", False: "X0"}}
    )
    reset_recognizer: bool | None = field(
        init=False, default=None, metadata={"value_to_str": {True: "Z", False: "Z0", None: ""}}
    )

    def __post_init__(self) -> None:
        if not isinstance(self.options, str):
            raise TypeError(
                f"Hotstring options must be a string, not {type(self.options).__name__}"
            )

        object.__setattr__(self, "options", self.options.strip(" \t"))

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
                if option not in _NON_K_P_OPTION_TO_HANDLER:
                    raise AssertionError(f"Unhandled hotstring option: {option!r}")

                _NON_K_P_OPTION_TO_HANDLER[option](self)

            position = match.end()

    def declaration(self) -> str:
        options_str = ""

        for field_info in fields(self):
            name = field_info.name

            if name == "options":
                continue

            value = getattr(self, name)

            if name == "key_delay":
                options_str += f"K{value}" if value is not None else ""
            elif name == "priority":
                options_str += f"P{value}" if value is not None else ""
            else:
                value_to_str = field_info.metadata.get("value_to_str", {})
                options_str += value_to_str.get(value, "")

        return options_str
