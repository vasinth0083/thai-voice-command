"""Wake-phrase detection on transcribed text.

Thai ASR rarely spells a foreign wake word the same way twice ("จาร์วิส",
"จาวิส", "จาวิทย์" ...). :class:`WakeWord` accepts a list of known
mis-hearings and, optionally, a fuzzy match on the start of the utterance.
The wake phrase must come first: "เปิดโน้ตแพด จาร์วิส" is not a wake.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .text import compact, similarity


@dataclass(frozen=True)
class WakeMatch:
    alias: str
    remainder: str
    score: float


class WakeWord:
    """Detect a wake phrase at the start of an utterance.

    :param aliases: spellings to accept, e.g. ``["จาร์วิส", "จาวิส"]``.
    :param fuzzy_threshold: if set (0..1), also accept a prefix whose
        similarity to an alias is at least this value. ``None`` disables it.
    """

    def __init__(self, aliases: Iterable[str], fuzzy_threshold: float | None = None):
        self.aliases = tuple(sorted({compact(a) for a in aliases if a.strip()}, key=len, reverse=True))
        if not self.aliases:
            raise ValueError("at least one alias is required")
        if fuzzy_threshold is not None and not 0.0 < fuzzy_threshold <= 1.0:
            raise ValueError("fuzzy_threshold must be in (0, 1]")
        self.fuzzy_threshold = fuzzy_threshold

    def match(self, text: str) -> WakeMatch | None:
        """Return the matched alias and the rest of the utterance, or ``None``."""
        spoken = compact(text)
        for alias in self.aliases:
            if spoken.startswith(alias):
                return WakeMatch(alias, spoken[len(alias):], 1.0)
        if self.fuzzy_threshold is None:
            return None
        best: WakeMatch | None = None
        for alias in self.aliases:
            # Compare prefixes one character shorter/longer than the alias too,
            # because ASR often adds or drops a tone mark or vowel.
            for size in (len(alias) - 1, len(alias), len(alias) + 1):
                if size <= 0 or size > len(spoken):
                    continue
                score = similarity(spoken[:size], alias)
                if score >= self.fuzzy_threshold and (best is None or score > best.score):
                    best = WakeMatch(alias, spoken[size:], score)
        return best

    def __contains__(self, text: str) -> bool:
        return self.match(text) is not None


JARVIS_ALIASES: tuple[str, ...] = (
    "จาร์วิส", "จาวิส", "จาวิทย์", "จาวิท", "ชาวิทย์", "จาวิก", "จาริก",
    "จาวิป", "เจ้าวิ", "ยาวิทย์", "กาวิทย์", "jarvis",
)
"""Mis-hearings of "Jarvis" collected from a real Thai ASR model."""
