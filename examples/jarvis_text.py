"""Type Thai commands instead of speaking them.

    python examples/jarvis_text.py
    > จาร์วิส ค้นหา Roblox Studio
"""

import datetime
import urllib.parse
import webbrowser

from thai_voice_command import JARVIS_ALIASES, Router, WakeWord

router = Router(wake=WakeWord(JARVIS_ALIASES))


@router.command(phrases=["เปิดยูทูบ", "เปิด youtube"])
def youtube(match):
    webbrowser.open("https://www.youtube.com")
    return "เปิด YouTube ให้แล้วครับ"


@router.command(prefixes=["ค้นหา", "ค้นเว็บ"])
def search(match):
    if not match.arg:
        return "อยากค้นหาเรื่องอะไรครับ"
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(match.arg))
    return f"ค้นหา {match.arg} ให้แล้วครับ"


@router.command(keywords=[["เวลา", "กี่โมง"]], fuzzy=False)
def time_now(match):
    return "ตอนนี้เวลา " + datetime.datetime.now().strftime("%H:%M") + " ครับ"


if __name__ == "__main__":
    print("พิมพ์คำสั่งที่ขึ้นต้นด้วย 'จาร์วิส' (Ctrl+C เพื่อออก)")
    while True:
        try:
            heard = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        print(router.handle(heard) or "(ไม่เข้าใจคำสั่ง จึงไม่ทำอะไร)")
