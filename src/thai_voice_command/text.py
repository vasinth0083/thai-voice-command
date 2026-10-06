"""Text helpers for Thai speech-recognition output.

ASR engines often insert or drop spaces in Thai and English, so matching is
done on a "compact" form: lower-case with all whitespace removed.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

POLITE_SUFFIXES: tuple[str, ...] = ("นะครับ", "นะคะ", "ครับผม", "ครับ", "ค่ะ", "คะ", "จ้า", "จ้ะ")


def compact(text: str) -> str:
    """Lower-case ``text`` and remove all whitespace."""
    return "".join(text.strip().lower().split())


def clean(text: str) -> str:
    """Collapse runs of whitespace and trim the ends."""
    return " ".join(text.strip().split())


def strip_polite(text: str, suffixes: Iterable[str] = POLITE_SUFFIXES) -> str:
    """Remove one trailing polite particle such as ``ครับ`` or ``ค่ะ``."""
    text = clean(text)
    for suffix in sorted(suffixes, key=len, reverse=True):
        if text.endswith(suffix):
            return text[: -len(suffix)].rstrip()
    return text


def similarity(a: str, b: str) -> float:
    """Return a 0..1 similarity ratio between two strings (difflib)."""
    return SequenceMatcher(None, a, b).ratio()


def best_similarity(text: str, choices: Iterable[str]) -> float:
    """Return the highest :func:`similarity` between ``text`` and any choice."""
    return max((similarity(text, choice) for choice in choices), default=0.0)
