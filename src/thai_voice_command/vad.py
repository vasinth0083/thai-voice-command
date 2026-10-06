"""Energy-based voice activity detection for 16-bit mono PCM.

Feed fixed-size audio blocks to :meth:`Segmenter.feed`; it returns the
bytes of a complete utterance when speech ends, otherwise ``None``.
Pure Python, no NumPy, so it runs anywhere. The thresholds adapt to the
room's background noise ("noise floor").
"""

from __future__ import annotations

from array import array
from collections import deque
import math
import sys


def rms(block: bytes) -> float:
    """Root-mean-square loudness of 16-bit little-endian PCM, scaled to 0..1."""
    samples = array("h")
    samples.frombytes(block[: len(block) - len(block) % 2])
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        return 0.0
    return math.sqrt(sum(float(x) * x for x in samples) / len(samples)) / 32768.0


class Segmenter:
    """Cut a stream of PCM blocks into utterances.

    :param sample_rate: samples per second.
    :param block_samples: samples per block passed to :meth:`feed`.
    :param end_silence: seconds of quiet that end an utterance.
    :param max_seconds: hard cap on utterance length.
    :param pre_roll: seconds of audio kept from before speech started, so
        the first syllable is not cut off.
    :param start_blocks: consecutive loud blocks needed to start.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        block_samples: int = 1280,
        end_silence: float = 0.72,
        max_seconds: float = 8.0,
        pre_roll: float = 0.40,
        start_blocks: int = 2,
        noise_floor: float = 0.003,
    ):
        if sample_rate <= 0 or block_samples <= 0:
            raise ValueError("sample_rate and block_samples must be positive")
        self.block_seconds = block_samples / sample_rate
        self.end_silence = end_silence
        self.max_seconds = max_seconds
        self.start_blocks = start_blocks
        self.noise_floor = noise_floor
        self._preroll: deque[bytes] = deque(maxlen=max(1, round(pre_roll / self.block_seconds)))
        self._frames: list[bytes] = []
        self._loud = 0
        self._quiet = 0

    @property
    def speaking(self) -> bool:
        return bool(self._frames)

    def feed(self, block: bytes) -> bytes | None:
        level = rms(block)
        if not self._frames:
            self._preroll.append(block)
            self.noise_floor = self.noise_floor * 0.99 + min(level, 0.025) * 0.01
            self._loud = self._loud + 1 if level > max(0.006, self.noise_floor * 1.8) else 0
            if self._loud >= self.start_blocks:
                self._frames = list(self._preroll)
                self._preroll.clear()
                self._quiet = 0
            return None

        self._frames.append(block)
        self._quiet = self._quiet + 1 if level <= max(0.0045, self.noise_floor * 1.45) else 0
        done = (
            self._quiet * self.block_seconds >= self.end_silence
            or len(self._frames) * self.block_seconds >= self.max_seconds
        )
        if not done:
            return None
        utterance = b"".join(self._frames)
        self.reset()
        return utterance

    def reset(self) -> None:
        self._frames = []
        self._preroll.clear()
        self._loud = 0
        self._quiet = 0
