"""Define AutoCorrect2-specific hotstring and result models."""

from __future__ import annotations

from dataclasses import dataclass

from ..conflicts import CandidateAssessment
from ..models import CandidateHotstring


@dataclass(frozen=True, slots=True)
class AutoCorrect2CandidateHotstring(CandidateHotstring):
    """Represent a candidate rendered using AutoCorrect2's `f()` helper.

    The semantic replacement is converted to a safe AutoHotkey string
    literal and passed as the single argument to `f()`.
    """

    def compute_content(self, replacement: str) -> str:
        """Compute AutoCorrect2 executable content for a replacement.

        Args:
            replacement:
                Intended replacement text.

        Returns:
            AutoHotkey expression calling `f()` with the replacement.
        """
        return f"f({self.to_ahk_string_literal(replacement)})"


@dataclass(frozen=True, slots=True)
class AutoCorrect2CheckResult:
    """Represent the result of checking candidates against AutoCorrect2.

    Attributes:
        accepted:
            Candidates with no detected conflict.
        rejected:
            Assessments for candidates with one or more conflicts.
    """

    accepted: tuple[AutoCorrect2CandidateHotstring, ...]
    rejected: tuple[CandidateAssessment, ...]

    @property
    def candidate_count(self) -> int:
        """Return the total number of candidates checked.

        Returns:
            Number of accepted plus rejected candidates.
        """
        return len(self.accepted) + len(self.rejected)
