"""Listen on the microphone and run Thai commands.

Requires extra packages and a Thai sherpa-onnx transducer model:

    pip install sounddevice sherpa-onnx

Download a Thai model from the sherpa-onnx releases page and pass its folder
(it must contain encoder/decoder/joiner .onnx files and tokens.txt).

    python examples/microphone_sherpa.py path/to/thai_model
"""

import sys
from pathlib import Path

import sherpa_onnx
import sounddevice as sd

from thai_voice_command import JARVIS_ALIASES, Router, Segmenter, WakeWord

SAMPLE_RATE = 16000
BLOCK = 1280  # 80 ms

router = Router(wake=WakeWord(JARVIS_ALIASES))


@router.command(phrases=["สวัสดี"])
def hello(match):
    return "สวัสดีครับ"


def load(model_dir: Path) -> sherpa_onnx.OfflineRecognizer:
    def pick(pattern):
        return str(next(model_dir.glob(pattern)))

    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=pick("encoder*.onnx"),
        decoder=pick("decoder*.onnx"),
        joiner=pick("joiner*.onnx"),
        tokens=str(model_dir / "tokens.txt"),
        num_threads=1,
    )


def main() -> None:
    recognizer = load(Path(sys.argv[1]))
    segmenter = Segmenter(sample_rate=SAMPLE_RATE, block_samples=BLOCK)
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=BLOCK, channels=1, dtype="int16") as mic:
        print("Listening... say 'จาร์วิส สวัสดี'")
        while True:
            block, _ = mic.read(BLOCK)
            utterance = segmenter.feed(bytes(block))
            if utterance is None:
                continue
            stream = recognizer.create_stream()
            pcm = memoryview(utterance).cast("h")
            stream.accept_waveform(SAMPLE_RATE, [s / 32768.0 for s in pcm])
            recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            print("heard:", text, "->", router.handle(text))


if __name__ == "__main__":
    main()
