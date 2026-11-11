"""สร้างภาพพื้นหลังเมนู assets/menu_bg.png จากตัววาดฉากของเกมเอง (ถนนอิฐ หญ้า ฟ้า ประตู สิ่งกีดขวาง ศัตรู)

รัน:  python tools/make_menu_bg.py      (จากโฟลเดอร์เกม)

มุมกล้องแบบภาพร่าง: ถนนพุ่งเฉียงจากล่างซ้ายขึ้นไปขวาบน ขอบฟ้าเอียงขึ้นทางขวา
  1. วาดพื้น (ฟ้า หญ้า ถนน ประตู สิ่งกีดขวาง) ด้วย Game.draw_world โดยกล้องต่ำและเลื่อนไปทางขวาของถนน
  2. หมุนทั้งภาพ ANGLE องศา (ขยาย 2 เท่าแบบพิกเซลก่อนหมุน แล้วย่อกลับแบบนุ่ม ขอบพิกเซลจะไม่แตกเป็นฟันเลื่อย)
  3. คน (ศัตรูยืนรอ + ผู้เล่นตัวใหญ่ที่กำลังวิ่ง) และเมฆ วาดทีหลังแบบตั้งตรง ไม่เอียงตามพื้น
"""
import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
GAME = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GAME))
os.chdir(GAME)

from game.core import config as C

OUT_W, OUT_H = C.SCREEN_W, C.SCREEN_H
RENDER = 1600              # ขนาดภาพที่วาดก่อนหมุน (ต้องใหญ่พอให้หมุนแล้วยังเต็มกรอบ)
ANGLE = 0                  # ไม่เอียง: ขอบฟ้าตรง ทุกอย่างตั้งตรง
VP_AT = (500, 200)         # จุดที่ถนนไปบรรจบ (บนขอบฟ้า) อยู่ตรงไหนของภาพสุดท้าย
# กล้องอยู่ทางขวาของกลางถนน CAM_X สูง CAM_H: แนวกลางถนนบนภาพเอียง atan(CAM_X / CAM_H) จากแนวตั้ง
# กล้องเข้าใกล้กลางถนน = ถนนบานกว้างลงข้างล่าง
CAM_X = 190
CAM_H = 98
FOCAL = 900                # ซูม (ของในฉากใหญ่ขึ้นตาม)

C.SCREEN_W = C.SCREEN_H = RENDER
C.CENTER_X = C.HORIZON_Y = RENDER // 2
C.CAM_HEIGHT, C.FOCAL = CAM_H, FOCAL

import pygame  # noqa: E402
import main  # noqa: E402
from game.core import sprites  # noqa: E402
from game.world.enemy import ENEMY_TINT  # noqa: E402
from game.world.level import build_object  # noqa: E402

PEOPLE_SCALE = 1.7         # คนในภาพใหญ่กว่าในเกม (แบบโปสเตอร์) มองเห็นชัดบนจอเมนู
ENEMY = {"z": 1050, "x": -10, "count": 11}
OBJECTS = [
    {"type": "obstacle", "z": 640, "x": 75, "width": 120},
    {"type": "gate_pair", "z": 1650, "left": ["+", 20], "right": ["x", 2]},
]
C.GATE_HEIGHT = 90         # ประตูสูงขึ้นตามคนที่ขยาย


def render_ground(game):
    """ฟ้า + หญ้า + ถนน + ประตู + สิ่งกีดขวาง (ยังไม่หมุน) ไม่มีคนและเมฆ"""
    level = game.level
    level.objects = [build_object(d) for d in OBJECTS]
    level.finish_z = 10 ** 6
    game.next_index = 0
    game.crowd.draw = lambda *a, **k: None
    game.clouds = [pygame.Surface((1, 1), pygame.SRCALPHA)] * 2     # เมฆวาดทีหลังแบบตั้งตรง
    camera = game.camera
    camera.z = 0
    project = camera.project
    camera.project = lambda x, z: project(x - CAM_X, z)
    game.draw_world()
    return game.screen.copy(), camera


def rotate(surface):
    big = pygame.transform.scale_by(surface, 2)
    return pygame.transform.smoothscale_by(pygame.transform.rotate(big, ANGLE), 0.5)


def to_final(point, rotated):
    """จุดบนภาพก่อนหมุน -> จุดบนภาพสุดท้าย"""
    center = pygame.Vector2(RENDER, RENDER) / 2
    p = (pygame.Vector2(point) - center).rotate(-ANGLE) + pygame.Vector2(rotated.get_size()) / 2
    vp = (pygame.Vector2(C.CENTER_X, C.HORIZON_Y) - center).rotate(-ANGLE) + pygame.Vector2(rotated.get_size()) / 2
    return p - vp + pygame.Vector2(VP_AT)


def _corner(rotated):
    """ภาพที่หมุนแล้วต้องวางมุมซ้ายบนไว้ตรงไหน จุดบรรจบของถนนจึงตก VP_AT พอดี"""
    center = pygame.Vector2(RENDER, RENDER) / 2
    vp = (pygame.Vector2(C.CENTER_X, C.HORIZON_Y) - center).rotate(-ANGLE) + pygame.Vector2(rotated.get_size()) / 2
    return pygame.Vector2(VP_AT) - vp


def draw_clouds(out, game, pad):
    clouds = game.make_clouds()
    for cloud, (x, y) in ((clouds[0], (-10, 40)), (clouds[1], (170, 12)), (clouds[1], (330, 60))):
        out.blit(cloud, (x + pad, y + pad))


def draw_enemies(out, camera, rotated, pad):
    """ศัตรูยืนรอหน้าประตู: วางเป็นก้อนแบบในเกม (ก้นหอย) หันหน้ามาทางเรา ตัวตั้งตรง"""
    frames = sprites.frames("Idle", tint=ENEMY_TINT)
    n = ENEMY["count"]
    spots = []
    for i in range(n):
        r = 34 * ((i + 0.5) / n) ** 0.5
        a = i * 2.39996
        spots.append((ENEMY["x"] + r * 2.2 * math.cos(a), ENEMY["z"] + r * math.sin(a), i))
    for x, z, i in sorted(spots, key=lambda s: -s[1]):
        sx, sy, s = camera.project(x, z)
        fx, fy = to_final((sx, sy), rotated)
        frame = frames[i % len(frames)]
        w, h = int(frame.get_width() * s * PEOPLE_SCALE), int(frame.get_height() * s * PEOPLE_SCALE)
        img = pygame.transform.scale(frame, (w, h))
        out.blit(img, (fx - w // 2 + pad, fy - h + pad))


def draw_player(out):
    """ผู้เล่นตัวใหญ่ใกล้กล้อง: ท่าวิ่งก้าวยาว หันหลังเฉียงขวา (วิ่งไปทางประตู) ตัวโน้มไปข้างหน้า
    + เงาจางๆ ตามหลัง (บอกความเร็ว) + เงาที่พื้น + ฝุ่นจากเท้า"""
    frame = sprites.frames("Run", row=3)[0]
    k = 10
    img = pygame.transform.scale(frame, (frame.get_width() * k, frame.get_height() * k))
    img = pygame.transform.rotate(img, -LEAN)              # ตัวเอนไปทางที่วิ่ง (ขวาบน)
    feet = pygame.Vector2(170, 772)
    shadow = pygame.Surface((200, 46), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 70), shadow.get_rect())
    out.blit(shadow, shadow.get_rect(center=feet + (10, -6)))
    rng = random.Random(4)
    for _ in range(9):                                     # ฝุ่นจากเท้าลอยไปข้างหลัง (ซ้ายล่าง)
        p = feet + pygame.Vector2(rng.uniform(-160, -50), rng.uniform(-40, 20))
        r = rng.randint(7, 16)
        pygame.draw.circle(out, (226, 214, 196), p, r)
        pygame.draw.circle(out, (196, 182, 160), p + (r * 0.3, r * 0.3), r * 0.6)
    ghost = img.copy()
    ghost.set_alpha(70)
    rect = img.get_rect(midbottom=feet + (0, 12))
    out.blit(ghost, rect.move(-34, 22))
    out.blit(img, rect)


LEAN = 0                   # ผู้เล่นโน้มตัวกี่องศา (0 = ตั้งตรง)
PAD = 400                  # ผืนฉากหลังกว้างกว่าจอข้างละเท่านี้ หมุนแล้วมุมจอจะไม่โหว่
ROLL = 0                   # หมุนฉากหลังทั้งหมดตามเข็มนาฬิกากี่องศา (0 = ไม่หมุน)
ROLL_SHIFT = (40, 10)      # เลื่อนฉากหลังทั้งหมดไปทางขวา/ลง ให้ผู้เล่นวิ่งอยู่บนถนน


def make():
    pygame.init()
    game = main.Game()
    game.selected = 0
    game.start_level()
    ground, camera = render_ground(game)
    rotated = rotate(ground)
    # ฉากหลังทั้งหมด (พื้น ถนน ประตู สิ่งกีดขวาง ศัตรู เมฆ) วาดบนผืนใหญ่กว่าจอ แล้วหมุนทั้งผืนอีก ROLL องศา
    # ให้ถนนชี้ไปทางเดียวกับที่ผู้เล่นวิ่ง  ผู้เล่นวาดทีหลังสุด ไม่หมุนตาม
    world = pygame.Surface((OUT_W + 2 * PAD, OUT_H + 2 * PAD))
    world.blit(rotated, _corner(rotated) + (PAD, PAD))    # วางให้จุดบรรจบของถนนตก VP_AT
    draw_enemies(world, camera, rotated, PAD)
    big = pygame.transform.scale_by(world, 2)
    world = pygame.transform.smoothscale_by(pygame.transform.rotate(big, -ROLL), 0.5)   # ลบ = ตามเข็มนาฬิกา (หมุนลง)
    out = pygame.Surface((OUT_W, OUT_H))
    out.blit(world, world.get_rect(center=(OUT_W // 2 + ROLL_SHIFT[0], OUT_H // 2 + ROLL_SHIFT[1])))
    draw_clouds(out, game, 0)                             # เมฆวาดหลังหมุน: ตั้งตรงเสมอ
    draw_player(out)
    return out


if __name__ == "__main__":
    image = make()
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else GAME / "assets" / "menu_bg.png"
    pygame.image.save(image, str(target))
    print("saved", target)
