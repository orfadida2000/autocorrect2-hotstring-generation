"""AutoCorrect2-specific models, source parsing, and generated-file writing."""

from .models import AutoCorrect2CandidateHotstring, AutoCorrect2CheckResult
from .parser import extract_hotstrings, load_existing_hotstrings
from .writer import append_candidates

__all__ = [
    "AutoCorrect2CandidateHotstring",
    "AutoCorrect2CheckResult",
    "append_candidates",
    "extract_hotstrings",
    "load_existing_hotstrings",
]
