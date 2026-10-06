"""Thai voice command toolkit: wake phrase, command routing and simple VAD.

Works on text from any speech recognizer, so it has no required
dependencies.
"""

from .router import Command, Match, Router
from .text import clean, compact, similarity, strip_polite
from .vad import Segmenter, rms
from .wake import JARVIS_ALIASES, WakeMatch, WakeWord

__all__ = [
    "Command", "Match", "Router",
    "WakeWord", "WakeMatch", "JARVIS_ALIASES",
    "Segmenter", "rms",
    "clean", "compact", "similarity", "strip_polite",
]
__version__ = "0.1.0"
