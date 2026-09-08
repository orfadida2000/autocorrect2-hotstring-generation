"""Define generic project constants for AutoHotkey hotstring semantics."""

from typing import Final

from .options import (
    CaseMode,
    ReplacementMode,
    ResolvedHotstringOptions,
    ResolvedSendMode,
    SettingState,
)

DEFAULT_ENDING_CHARS: Final[frozenset[str]] = frozenset("-()[]{}':;\"/\\,.?!\n \t")
"""AutoHotkey v2's built-in hotstring ending-character set."""

DEFAULT_HOTSTRING_OPTIONS: Final[ResolvedHotstringOptions] = ResolvedHotstringOptions(
    ending_character_optional=SettingState.DISABLED,
    trigger_inside_word=SettingState.DISABLED,
    automatic_backspacing=SettingState.ENABLED,
    case_mode=CaseMode.INSENSITIVE_CONFORMING,
    key_delay=0,
    omit_ending_character=SettingState.DISABLED,
    priority=0,
    replacement_mode=ReplacementMode.NORMAL,
    suspend_exempt=SettingState.DISABLED,
    send_mode=ResolvedSendMode.INPUT_WITH_EVENT_FALLBACK,
    execute=SettingState.DISABLED,
    reset_recognizer=SettingState.DISABLED,
)
"""AutoHotkey's built-in fully resolved hotstring option defaults."""
