# thai-voice-command

Thai voice commands made simple. Give it text from **any** speech recognizer
(sherpa-onnx, Whisper, Google, the browser's Web Speech API) and it will:

- detect a wake phrase even when the ASR misspells it (`จาร์วิส`, `จาวิส`, `จาวิทย์` …)
- route the command to your function, ignoring spaces and polite particles (`ครับ`, `ค่ะ`)
- pull out arguments (`ค้นหา แมว` → `"แมว"`)
- use fuzzy matching **safely**: unclear speech is ignored, never guessed
- cut microphone audio into utterances with a tiny pure-Python VAD

No required dependencies. Python 3.9+.

> Extracted from JARVIS, a Thai desktop voice assistant, where real ASR
> mis-hearings were collected and tuned.

## Install

```bash
pip install thai-voice-command
```

## Quick start

```python
from thai_voice_command import Router, WakeWord, JARVIS_ALIASES

router = Router(wake=WakeWord(JARVIS_ALIASES))

@router.command(phrases=["เปิดยูทูบ", "เปิด youtube"])
def youtube(match):
    return "opening YouTube"

@router.command(prefixes=["ค้นหา"])
def search(match):
    return f"searching for {match.arg}"

router.handle("จาร์วิส เปิด ยูทูบ ครับ")   # 'opening YouTube'
router.handle("จาวิทย์ ค้นหา Roblox")      # 'searching for Roblox'
router.handle("เปิดยูทูบ")                 # None (no wake phrase)
router.handle("จาร์วิส ทำกับข้าว")          # None (unknown, ignored)
```

## How matching works

Checked in this order; the first hit wins.

| Step | Example rule | Matches |
|---|---|---|
| Exact phrase | `phrases=["เปิดโน้ตแพด"]` | `เปิด โน้ตแพด ครับ` |
| Prefix + argument | `prefixes=["ค้นหา"]` | `ค้นหา แมว` → `arg="แมว"` |
| Keyword groups | `keywords=[["เวลา","กี่โมง"]]` | `ตอนนี้กี่โมง` |
| Fuzzy phrase | automatic | `เปิดยูทูป` → `เปิดยูทูบ` |

Fuzzy matching accepts a command only when its score is at least
`min_score` (default 0.78) **and** beats every other command by
`min_margin` (default 0.065). So `เปิดโน๊ตแพด` is *rejected* when both
"open Notepad" and "close Notepad" exist: the two scores (0.909 vs 0.857)
are too close to be sure. For an assistant that launches programs, doing
nothing is safer than doing the wrong thing.

## Microphone

`Segmenter` turns 16-bit mono PCM blocks into whole utterances:

```python
from thai_voice_command import Segmenter

seg = Segmenter(sample_rate=16000, block_samples=1280)
for block in mic_blocks:
    utterance = seg.feed(block)
    if utterance:
        text = my_asr(utterance)
        router.handle(text)
```

See `examples/microphone_sherpa.py` for a full offline Thai example.

## Contributing

New wake-word aliases, Thai command phrases, and bug reports are very
welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Thai or English is fine.

## License

MIT
