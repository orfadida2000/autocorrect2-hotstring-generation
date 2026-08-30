"""AutoCorrect2-specific source inspection and conflict reporting."""

from .parser import extract_hotstrings, load_existing_hotstrings
from .report import create_conflict_report, write_conflict_report

__all__ = [
    "create_conflict_report",
    "extract_hotstrings",
    "load_existing_hotstrings",
    "write_conflict_report",
]
