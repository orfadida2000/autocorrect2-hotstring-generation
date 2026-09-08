"""Generic AutoHotkey hotstring domain model and recognition logic."""

from .conflicts import CandidateAssessment, ConflictKind, HotstringConflict
from .models import CandidateHotstring, ExistingHotstring, Hotstring
from .options import (
    CaseMode,
    HotstringOptions,
    InheritedState,
    ReplacementMode,
    ResolvedHotstringOptions,
    ResolvedSendMode,
    SendMode,
    SettingState,
)
from .trigger import (
    ahk_to_semantic_trigger,
    make_case_insensitive_trigger_key,
    semantic_to_ahk_trigger,
)

__all__ = [
    "CandidateAssessment",
    "CandidateHotstring",
    "CaseMode",
    "ConflictKind",
    "ExistingHotstring",
    "Hotstring",
    "HotstringConflict",
    "HotstringOptions",
    "InheritedState",
    "ReplacementMode",
    "ResolvedHotstringOptions",
    "ResolvedSendMode",
    "SendMode",
    "SettingState",
    "ahk_to_semantic_trigger",
    "make_case_insensitive_trigger_key",
    "semantic_to_ahk_trigger",
]
