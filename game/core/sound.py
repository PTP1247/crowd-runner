"""เสียงประกอบ + เพลงพื้นหลัง   [เจ้าของ: A]

เสียงประกอบ: สร้างเสียงสังเคราะห์ตอนเริ่มเกม ไม่ต้องมีไฟล์เสียง
ทำไมสังเคราะห์เอง: ไม่ต้องหาไฟล์ที่มีลิขสิทธิ์ใช้ได้ และไม่ต้องติดตั้ง numpy เพิ่ม
เพลงพื้นหลัง: ไฟล์ mp3 ในโฟลเดอร์ music (เมนู / ระหว่างวิ่ง / สู้บอส) สลับตามหน้าจอด้วย play_music()
แต่ละเสียง = ลำดับโน้ต (ความถี่เริ่ม, ความถี่จบ, วินาที) แปลงเป็นคลื่นด้วย array ธรรมดา
ถ้าเครื่องไม่มีลำโพง/การ์ดเสียง (เช่นตอนรัน test) เกมยังเล่นได้ แค่เงียบ
"""
import array
import json
import math
import random
from pathlib import Path

import pygame

from game.core import config as C

VOLUME = 0.25

# ชื่อเสียง -> (โน้ต [(ความถี่เริ่ม, ความถี่จบ, วินาที), ...], ใส่เสียงซ่าไหม)
RECIPES = {
    "gate_good": ([(660, 660, 0.06), (990, 990, 0.09)], False),
    "gate_bad":  ([(330, 180, 0.2)], False),
    "hit":       ([(140, 60, 0.18)], True),
    "fight":     ([(110, 70, 0.22)], True),
    "win_fight": ([(784, 784, 0.07), (1047, 1047, 0.1)], False),
    "win":       ([(523, 523, 0.11), (659, 659, 0.11), (784, 784, 0.11), (1047, 1047, 0.3)], False),
    "lose":      ([(392, 392, 0.16), (330, 330, 0.16), (262, 220, 0.4)], False),
}

_sounds = {}

# ตั้งค่าในหน้าหยุดเกม: "music" = เพลงพื้นหลัง, "effect" = เสียงประกอบ  แต่ละอันมีความดัง 0-1 และเปิด/ปิด
SETTINGS_FILE = C.SETTINGS_FILE     # อยู่ใน .gitignore (ค่าของแต่ละเครื่อง)
CHANNELS = ("music", "effect")
settings = {"music": {"volume": 0.6, "on": True}, "effect": {"volume": 1.0, "on": True}}
# เพลงพื้นหลัง: ไฟล์ในโฟลเดอร์ music ข้างไฟล์นี้  main.py เลือกเพลงตามหน้าจอทุกเฟรม (play_music)
MUSIC_DIR = Path(__file__).resolve().parent / "music"
THEMES = {
    "menu": "menu_theme.mp3",        # เมนูเลือกด่าน + หน้าปรับเสียง
    "game": "in-game_theme.mp3",     # ระหว่างวิ่ง (รวมหน้าหยุดเกม)
    "boss": "boss_theme.mp3",        # ตั้งแต่บอสกับกลุ่มคนเริ่มตีกันจริง
}
MUSIC_FADE_MS = 600                  # เพลงใหม่ค่อยๆ ดังขึ้น / จบด่านเพลงค่อยๆ เงียบลง
_music_now = None                    # เพลงที่เล่นอยู่ (ชื่อใน THEMES, None = เงียบ)


def init():
    """สร้างเสียงทั้งหมด เรียกครั้งเดียวหลัง pygame.init()"""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(22050, -16, 1, 512)
        rate, _, channels = pygame.mixer.get_init()
        for name, (notes, noise) in RECIPES.items():
            _sounds[name] = pygame.mixer.Sound(buffer=_synth(notes, noise, rate, channels).tobytes())
    except (pygame.error, TypeError):
        _sounds.clear()          # ไม่มีอุปกรณ์เสียง: เล่นแบบเงียบ
    load_settings()


def play_music(theme):
    """เปลี่ยนเพลงพื้นหลัง (เล่นวนไม่จบ)  theme: ชื่อใน THEMES หรือ None = ค่อยๆ เงียบลง
    เรียกซ้ำด้วยเพลงเดิม = เล่นต่อ ไม่เริ่มใหม่ (main.py เรียกทุกเฟรมได้)
    stop() ก่อน load เสมอ: ถ้าเพลงเก่ากำลัง fadeout อยู่ play() จะรอจน fade จบ เกมค้างไปครึ่งวินาที
    ไม่มีไฟล์ / ไม่มีการ์ดเสียง = เงียบ เกมยังเล่นได้"""
    global _music_now
    if theme == _music_now:
        return
    _music_now = theme
    if not pygame.mixer.get_init():
        return
    try:
        if theme is None:
            pygame.mixer.music.fadeout(MUSIC_FADE_MS)
            return
        pygame.mixer.music.stop()
        pygame.mixer.music.load(str(MUSIC_DIR / THEMES[theme]))
        pygame.mixer.music.play(-1, fade_ms=MUSIC_FADE_MS)
        apply_music()
    except pygame.error:
        pass


def apply_music():
    """ตั้งความดังเพลงตามค่าปัจจุบัน (ปิดกล่อง = 0)"""
    if pygame.mixer.get_init():
        pygame.mixer.music.set_volume(level("music"))


def level(channel):
    """ความดังที่ใช้จริง 0-1: ปิดกล่องอยู่ = 0"""
    c = settings[channel]
    return c["volume"] if c["on"] else 0.0


def set_volume(channel, volume):
    settings[channel]["volume"] = round(max(0.0, min(1.0, volume)), 3)
    apply_music()


def toggle(channel):
    settings[channel]["on"] = not settings[channel]["on"]
    apply_music()


def load_settings(path=None):
    """อ่านค่าที่บันทึกไว้ ไฟล์ไม่มี/เสีย ใช้ค่าเริ่มต้น"""
    try:
        with open(path or SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        for channel in CHANNELS:
            c = data.get(channel, {})
            settings[channel]["volume"] = max(0.0, min(1.0, float(c.get("volume", settings[channel]["volume"]))))
            settings[channel]["on"] = bool(c.get("on", settings[channel]["on"]))
    except (OSError, ValueError, TypeError, AttributeError):
        pass


def save_settings(path=None):
    try:
        with open(path or SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass


def _synth(notes, noise, rate, channels):
    """คลื่นเสียง 16 บิต: sine ผสม square นิดหน่อยให้ออกแนวเกมเก่า + เสียงซ่าสำหรับเสียงชน"""
    rng = random.Random(1)
    samples = array.array("h")
    phase = 0.0
    for f0, f1, dur in notes:
        n = int(rate * dur)
        for i in range(n):
            t = i / n
            freq = f0 + (f1 - f0) * t
            phase += 2 * math.pi * freq / rate
            wave = 0.7 * math.sin(phase) + 0.3 * (1 if math.sin(phase) > 0 else -1)
            if noise:
                wave = 0.5 * wave + 0.5 * rng.uniform(-1, 1)
            envelope = min(1.0, i / (rate * 0.005)) * (1 - t) ** 1.5    # เริ่มเร็ว จางหายตอนท้าย
            value = int(32767 * VOLUME * wave * envelope)
            samples.extend([value] * channels)
    return samples


def play(name):
    volume = level("effect")
    if volume > 0 and name in _sounds:
        _sounds[name].set_volume(volume)
        _sounds[name].play()


def toggle_mute():
    """ปุ่ม N: เปิดอยู่สักอัน -> ปิดทั้งหมด,  ปิดหมดแล้ว -> เปิดทั้งหมด"""
    on = not any(settings[c]["on"] for c in CHANNELS)
    for c in CHANNELS:
        settings[c]["on"] = on
    apply_music()
    save_settings()
    return not on

