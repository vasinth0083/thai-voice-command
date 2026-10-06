"""Route transcribed Thai text to command handlers.

Matching runs in a fixed, safe order and stops at the first hit:

1. exact phrase (compact form)
2. prefix command with an argument, e.g. "ค้นหา แมว" -> ``arg="แมว"``
3. keyword groups: every group must have at least one keyword present
4. fuzzy phrase match, accepted only if the best score is high enough AND
   clearly ahead of the runner-up (``min_margin``)

Unknown text returns ``None`` instead of guessing. For a voice assistant
that can launch programs, ignoring unclear speech is the safe default.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from .text import best_similarity, clean, compact, strip_polite
from .wake import WakeWord

Handler = Callable[["Match"], Any]


@dataclass(frozen=True)
class Match:
    command: str
    text: str
    arg: str = ""
    score: float = 1.0
    how: str = "exact"


@dataclass
class Command:
    name: str
    handler: Handler
    phrases: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    keywords: tuple[tuple[str, ...], ...] = ()
    fuzzy: bool = True
    _compact_phrases: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compact_phrases = tuple(compact(p) for p in self.phrases)


class Router:
    """Collection of commands plus the matching logic.

    :param wake: optional :class:`WakeWord`. When given, :meth:`handle`
        requires the wake phrase unless ``require_wake=False`` is passed.
    :param min_score: minimum fuzzy similarity (0..1) to accept.
    :param min_margin: required lead of the best fuzzy score over the
        best score of any *other* command.
    """

    def __init__(self, wake: WakeWord | None = None, min_score: float = 0.78, min_margin: float = 0.065):
        self.wake = wake
        self.min_score = min_score
        self.min_margin = min_margin
        self.commands: list[Command] = []

    def add(
        self,
        name: str,
        handler: Handler,
        *,
        phrases: Iterable[str] = (),
        prefixes: Iterable[str] = (),
        keywords: Sequence[Iterable[str]] = (),
        fuzzy: bool = True,
    ) -> Command:
        if any(c.name == name for c in self.commands):
            raise ValueError(f"duplicate command name: {name!r}")
        cmd = Command(
            name,
            handler,
            tuple(phrases),
            tuple(sorted((compact(p) for p in prefixes), key=len, reverse=True)),
            tuple(tuple(compact(k) for k in group) for group in keywords),
            fuzzy,
        )
        if not (cmd.phrases or cmd.prefixes or cmd.keywords):
            raise ValueError("a command needs phrases, prefixes or keywords")
        self.commands.append(cmd)
        return cmd

    def command(self, name: str | None = None, **options: Any) -> Callable[[Handler], Handler]:
        """Decorator form of :meth:`add`; ``name`` defaults to the function name."""

        def register(func: Handler) -> Handler:
            self.add(name or func.__name__, func, **options)
            return func

        return register

    def match(self, text: str) -> Match | None:
        """Find the command for ``text`` (wake phrase already removed)."""
        text = strip_polite(text)
        spoken = compact(text)
        if not spoken:
            return None

        for cmd in self.commands:
            if spoken in cmd._compact_phrases:
                return Match(cmd.name, text)

        for cmd in self.commands:
            for prefix in cmd.prefixes:
                if spoken.startswith(prefix):
                    return Match(cmd.name, text, _arg_after(text, prefix), how="prefix")

        for cmd in self.commands:
            if cmd.keywords and all(any(k in spoken for k in group) for group in cmd.keywords):
                return Match(cmd.name, text, how="keywords")

        scored = sorted(
            ((best_similarity(spoken, c._compact_phrases), c) for c in self.commands if c.fuzzy and c.phrases),
            key=lambda pair: pair[0],
            reverse=True,
        )
        if scored:
            best_score, best = scored[0]
            runner_up = scored[1][0] if len(scored) > 1 else 0.0
            if best_score >= self.min_score and best_score - runner_up >= self.min_margin:
                return Match(best.name, text, score=best_score, how="fuzzy")
        return None

    def handle(self, text: str, require_wake: bool | None = None) -> Any:
        """Strip the wake phrase, match, and run the handler.

        Returns the handler's result, or ``None`` when there is no wake
        phrase (if required) or no command matched.
        """
        if require_wake is None:
            require_wake = self.wake is not None
        if self.wake is not None:
            found = self.wake.match(text)
            if found is not None:
                text = _text_after_compact(text, len(compact(text)) - len(found.remainder))
            elif require_wake:
                return None
        found_cmd = self.match(text)
        if found_cmd is None:
            return None
        handler = next(c.handler for c in self.commands if c.name == found_cmd.command)
        return handler(found_cmd)


def _arg_after(text: str, compact_prefix: str) -> str:
    """Return the original text after a prefix given in compact form."""
    return clean(_text_after_compact(text, len(compact_prefix))).lstrip(" ,:")


def _text_after_compact(text: str, n: int) -> str:
    """Skip ``n`` non-space characters of ``text`` and return the rest."""
    seen = 0
    for i, ch in enumerate(text):
        if seen == n:
            return text[i:].lstrip(" ,:")
        if not ch.isspace():
            seen += 1
    return ""

