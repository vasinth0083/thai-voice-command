import math
import struct
import unittest

from thai_voice_command import JARVIS_ALIASES, Router, Segmenter, WakeWord, compact, rms, strip_polite


def make_router(wake=None):
    router = Router(wake=wake)
    router.add("notepad_open", lambda m: ("open", m), phrases=["เปิดโน้ตแพด", "เปิด notepad"])
    router.add("notepad_close", lambda m: ("close", m), phrases=["ปิดโน้ตแพด", "ปิด notepad"])
    router.add("search", lambda m: ("search", m.arg), prefixes=["ค้นหา", "ค้นเว็บ"])
    router.add("time", lambda m: ("time", m), keywords=[["เวลา", "กี่โมง"], ["บอก", "ตอนนี้", "กี่โมง"]], fuzzy=False)
    return router


class TextTests(unittest.TestCase):
    def test_compact_removes_spaces_and_case(self):
        self.assertEqual(compact("  เปิด  VS Code "), "เปิดvscode")

    def test_strip_polite(self):
        self.assertEqual(strip_polite("เปิดยูทูบครับ"), "เปิดยูทูบ")
        self.assertEqual(strip_polite("เปิดยูทูบนะคะ"), "เปิดยูทูบ")
        self.assertEqual(strip_polite("เปิดยูทูบ"), "เปิดยูทูบ")


class WakeTests(unittest.TestCase):
    def setUp(self):
        self.wake = WakeWord(JARVIS_ALIASES)

    def test_alias_at_start(self):
        found = self.wake.match("จาวิก เปิดโน้ตแพด")
        self.assertEqual((found.alias, found.remainder), ("จาวิก", "เปิดโน้ตแพด"))

    def test_alias_not_at_start_is_ignored(self):
        self.assertIsNone(self.wake.match("เปิดโน้ตแพด จาวิก"))

    def test_longest_alias_wins(self):
        self.assertEqual(self.wake.match("จาวิทย์").alias, "จาวิทย์")

    def test_fuzzy_off_by_default(self):
        self.assertIsNone(self.wake.match("จ่าวิส เปิด"))

    def test_fuzzy_threshold(self):
        wake = WakeWord(["จาร์วิส"], fuzzy_threshold=0.8)
        self.assertIsNotNone(wake.match("จาร์วิด เปิด"))
        self.assertIsNone(wake.match("สวัสดี"))

    def test_rejects_empty_aliases(self):
        with self.assertRaises(ValueError):
            WakeWord([" "])


class RouterTests(unittest.TestCase):
    def test_exact_phrase_ignores_spaces_and_polite(self):
        self.assertEqual(make_router().handle("เปิด โน้ตแพด ครับ")[0], "open")

    def test_prefix_keeps_argument(self):
        self.assertEqual(make_router().handle("ค้นหา Roblox Studio"), ("search", "Roblox Studio"))

    def test_keyword_groups(self):
        self.assertEqual(make_router().handle("ตอนนี้กี่โมงแล้ว")[0], "time")
        self.assertIsNone(make_router().handle("เวลาว่าง"))

    def test_fuzzy_accepts_close_mishearing(self):
        router = make_router()
        router.add("youtube", lambda m: ("youtube", m), phrases=["เปิดยูทูบ"])
        result = router.handle("เปิดยูทูป")
        self.assertEqual(result[0], "youtube")
        self.assertEqual(result[1].how, "fuzzy")

    def test_fuzzy_rejects_open_close_near_tie(self):
        # 0.909 vs 0.857: similar enough to "close" that guessing is unsafe.
        self.assertIsNone(make_router().handle("เปิดโน๊ตแพด"))

    def test_fuzzy_rejects_ambiguous(self):
        router = Router(min_score=0.5, min_margin=0.2)
        router.add("a", lambda m: "a", phrases=["เปิดไฟ"])
        router.add("b", lambda m: "b", phrases=["ปิดไฟ"])
        self.assertIsNone(router.handle("ติดไฟ"))

    def test_unknown_returns_none(self):
        self.assertIsNone(make_router().handle("ทำกับข้าวให้หน่อย"))

    def test_wake_required(self):
        router = make_router(WakeWord(JARVIS_ALIASES))
        self.assertIsNone(router.handle("เปิดโน้ตแพด"))
        self.assertEqual(router.handle("จาร์วิส เปิดโน้ตแพด")[0], "open")
        self.assertEqual(router.handle("จาร์วิส, ค้นหา แมว"), ("search", "แมว"))
        self.assertEqual(router.handle("เปิดโน้ตแพด", require_wake=False)[0], "open")

    def test_decorator(self):
        router = Router()

        @router.command(phrases=["สวัสดี"])
        def hello(match):
            return "hi"

        self.assertEqual(router.handle("สวัสดีครับ"), "hi")
        self.assertEqual(router.commands[0].name, "hello")

    def test_duplicate_name_rejected(self):
        router = make_router()
        with self.assertRaises(ValueError):
            router.add("search", lambda m: None, prefixes=["หา"])

    def test_command_needs_a_matcher(self):
        with self.assertRaises(ValueError):
            Router().add("x", lambda m: None)


def tone(amplitude, samples=1280):
    return b"".join(
        struct.pack("<h", int(amplitude * 32767 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(samples)
    )


class VadTests(unittest.TestCase):
    def test_rms(self):
        self.assertEqual(rms(b"\x00\x00" * 10), 0.0)
        self.assertAlmostEqual(rms(tone(0.5)), 0.5 / math.sqrt(2), places=2)

    def test_segments_one_utterance(self):
        seg = Segmenter()
        quiet, loud = tone(0.0), tone(0.3)
        outputs = [seg.feed(quiet) for _ in range(10)]
        outputs += [seg.feed(loud) for _ in range(10)]
        self.assertTrue(seg.speaking)
        outputs += [seg.feed(quiet) for _ in range(12)]
        utterances = [o for o in outputs if o]
        self.assertEqual(len(utterances), 1)
        self.assertFalse(seg.speaking)
        # pre-roll (3 quiet + 2 loud) + 8 more loud + 9 quiet blocks (0.72 s)
        self.assertEqual(len(utterances[0]) // len(loud), 5 + 8 + 9)

    def test_max_length_cap(self):
        seg = Segmenter(max_seconds=1.0)
        outputs = [seg.feed(tone(0.3)) for _ in range(30)]
        self.assertTrue(any(outputs))


if __name__ == "__main__":
    unittest.main()
