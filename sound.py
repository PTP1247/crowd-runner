"""เสียงประกอบ: สร้างเสียงสังเคราะห์ตอนเริ่มเกม ไม่ต้องมีไฟล์เสียง   [เจ้าของ: A]

ทำไมสังเคราะห์เอง: ไม่ต้องหาไฟล์ที่มีลิขสิทธิ์ใช้ได้ และไม่ต้องติดตั้ง numpy เพิ่ม
แต่ละเสียง = ลำดับโน้ต (ความถี่เริ่ม, ความถี่จบ, วินาที) แปลงเป็นคลื่นด้วย array ธรรมดา
ถ้าเครื่องไม่มีลำโพง/การ์ดเสียง (เช่นตอนรัน test) เกมยังเล่นได้ แค่เงียบ
"""
import array
import math
import random

import pygame

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
_muted = False


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
    if not _muted and name in _sounds:
        _sounds[name].play()


def toggle_mute():
    global _muted
    _muted = not _muted
    return _muted


def is_muted():
    return _muted
