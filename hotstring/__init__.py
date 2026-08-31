"""AutoHotkey hotstring generation and AutoCorrect2 integration package."""

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
]
