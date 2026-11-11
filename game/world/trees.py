"""ต้นไม้ + ดอกไม้ข้างถนน: ฉากประกอบให้ทุ่งหญ้าไม่โล่งเกินไป (ไม่มีผลกับการเล่น)

วาดเป็นพิกเซลด้วยโค้ด 3 แบบ (ไม่ต้องมีไฟล์ภาพ) แบบเดียวกับเมฆ/กอหญ้า/อิฐใน main.py
  0 = ต้นเล็ก ลำต้นบิด   1 = ต้นพุ่มกลม ลำต้นสั้น   2 = ต้นใหญ่ ลำต้นหนา รากแผ่
ทรงพุ่ม = วงกลมหลายวงซ้อนกัน แรเงาตามแสงจากซ้ายบน แล้วไล่สีเป็นขั้นๆ แบบพิกเซล (มีจุดสลับสีให้ดูเป็นใบไม้)
"""
import math
import random

import pygame

from game.core import config as C

OUTLINE = (24, 58, 32)
LEAVES = [(28, 76, 40), (42, 108, 44), (64, 142, 48), (100, 178, 56), (150, 208, 80)]   # เข้ม -> สว่าง
BARK_OUT = (64, 28, 26)
BARK = [(104, 44, 36), (156, 70, 46), (200, 106, 68)]                     # เข้ม -> สว่าง
SHADOW = (40, 70, 40, 90)

# แต่ละแบบ: ขนาดภาพ, พุ่ม [(cx, cy, r), ...], ลำต้น [(x, y) จากโคนขึ้นไป], หนา, ราก [(dx, dy)], เงาที่พื้น
KINDS = [
    {"size": (24, 32), "crown": [(12, 9, 7), (7, 12, 5), (17, 12, 5), (11, 5, 4), (15, 15, 4)],
     "trunk": [(12, 29), (10, 25), (13, 21), (11, 17)], "width": 3,
     "roots": [(-4, 1), (4, 1), (-2, 2)], "shadow": (3, 27, 18, 5)},
    {"size": (26, 28), "crown": [(13, 11, 9), (7, 13, 6), (19, 13, 6), (13, 6, 6), (10, 17, 5), (17, 17, 5)],
     "trunk": [(13, 26), (13, 22), (12, 19)], "width": 3,
     "roots": [(-3, 1), (3, 1)], "shadow": (4, 23, 18, 5)},
    {"size": (34, 40), "crown": [(17, 11, 10), (9, 14, 7), (25, 13, 7), (15, 5, 6), (22, 6, 5), (12, 19, 5),
                                 (22, 19, 6)],
     "trunk": [(17, 37), (19, 33), (16, 29), (18, 25), (16, 21)], "width": 4,
     "roots": [(-6, 1), (6, 2), (-3, 2), (3, 2)], "shadow": (4, 34, 26, 6)},
]
TREE_SCALE = 2.8          # 1 พิกเซลของภาพต้นไม้ = กี่ unit ในโลก (คนสูง 32 unit -> ต้นไม้สูง ~2.5-3.5 เท่าคน)
SPACING = (90, 220)       # ระยะ z ระหว่างต้นไม้แต่ละต้นในฝั่งเดียวกัน (สุ่มในช่วงนี้)
SIDE_GAP = (35, 420)      # ห่างจากขอบถนนเท่าไร (สุ่มในช่วงนี้)
BAYER = ((0, 2), (3, 1))  # ลายสลับสีขั้นละ 2x2 แบบพิกเซลอาร์ต

# ดอกไม้: ดอกชมพูไส้ขาว 3 ดอก ก้านดำ ใบเขียว 2 ใบ (วาดตามภาพตัวอย่าง ทีละพิกเซล)
FLOWER = [
    ".......KKK.......",
    "......KPPPK......",
    ".....KPWWWPK.....",
    ".....KPWWWPK.....",
    ".....KPWWWPK.....",
    "..KKK.KPPPK.KKK..",
    ".KPPPK.KKK.KPPPK.",
    "KPWWWPK.K.KPWWWPK",
    "KPWWWPK.K.KPWWWPK",
    "KPWWWPK.K.KPWWWPK",
    ".KPPPK..K..KPPPK.",
    "..KKK...K...KKK..",
    "....KK..K..KK....",
    "......KKKKK......",
    "..KKK...K...KKK..",
    ".KLLGK..K..KGLLK.",
    "KLLGGGK.K.KGGGLLK",
    ".KGGGGKKKKKGGGGK.",
    "..KKKKK...KKKKK..",
]
FLOWER_COLORS = {"K": (22, 22, 26), "P": (236, 136, 160), "W": (255, 250, 250),
                 "G": (78, 160, 56), "L": (150, 212, 84)}
FLOWER_KIND = len(KINDS)  # เลขแบบของดอกไม้ (ต่อจากต้นไม้)
SCALES = [TREE_SCALE] * len(KINDS) + [1.4]    # unit ต่อพิกเซลของแต่ละแบบ (ดอกไม้สูง ~27 unit เกือบเท่าคน)
FLOWER_SPACING = (45, 130)                    # ระยะ z ระหว่างกอดอกไม้ในฝั่งเดียวกัน
FLOWER_GAP = (10, 300)                        # ห่างจากขอบถนนเท่าไร


def _draw_trunk(surf, kind):
    pts = kind["trunk"]
    w = kind["width"]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):           # เส้นขอบเข้ม แล้วเนื้อไม้ทับ
        pygame.draw.line(surf, BARK_OUT, (x0, y0), (x1, y1), w + 2)
    bx, by = pts[0]
    for dx, dy in kind["roots"]:                           # รากแผ่ออกจากโคน
        pygame.draw.line(surf, BARK_OUT, (bx, by - 1), (bx + dx, by + dy), 3)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        pygame.draw.line(surf, BARK[1], (x0, y0), (x1, y1), w)
        pygame.draw.line(surf, BARK[2], (x0 - w // 2, y0), (x1 - w // 2, y1), 1)   # ด้านที่โดนแสง (ซ้าย)
        pygame.draw.line(surf, BARK[0], (x0 + w // 2, y0), (x1 + w // 2, y1), 1)   # ด้านเงา (ขวา)
    for dx, dy in kind["roots"]:
        pygame.draw.line(surf, BARK[0] if dx > 0 else BARK[1], (bx, by - 1), (bx + dx, by + dy), 1)


def _draw_crown(surf, kind, rng):
    """พุ่มไม้: แต่ละพิกเซลในวงกลมใดๆ คิดความสว่างจาก "ผิวโดม" ของวงที่นูนสูงสุดตรงนั้น"""
    w, h = kind["size"]
    light = (-0.55, -0.65, 0.52)                            # แสงจากซ้ายบน หน้า
    inside, top = {}, {}
    for y in range(h):
        for x in range(w):
            best = None
            for k, (cx, cy, r) in enumerate(kind["crown"]):
                d2 = (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2
                if d2 <= r * r:
                    nz = math.sqrt(max(0.0, 1 - d2 / (r * r)))
                    if best is None or nz * r > best[0]:
                        nx, ny = (x + 0.5 - cx) / r, (y + 0.5 - cy) / r
                        best = (nz * r, nx * light[0] + ny * light[1] + nz * light[2], k)
            if best:
                inside[(x, y)] = best[1] - 0.35 * y / h            # ล่างพุ่มมืดกว่า (ใบบังแสงกันเอง)
                top[(x, y)] = best[2]
    for (x, y), shade in inside.items():
        level = (shade + 0.45) / 1.35 * len(LEAVES)             # 0 .. len(LEAVES)
        # รอยต่อระหว่างก้อนใบ (ก้อนบน/ซ้ายซ้อนทับก้อนล่าง): เส้นเงาเข้ม ทำให้เห็นเป็นกระจุกๆ
        for nb in ((x, y - 1), (x - 1, y)):
            if nb in top and top[nb] != top[(x, y)] and inside[nb] > shade:
                level = min(level, 1.2)
        level += (BAYER[y % 2][x % 2] - 1.5) * 0.35 + rng.uniform(-0.3, 0.3)   # สลับสีเป็นจุดๆ = ใบไม้
        surf.set_at((x, y), LEAVES[max(0, min(len(LEAVES) - 1, int(level)))])
    for (x, y) in inside:                                   # เส้นขอบพุ่ม
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (x + dx, y + dy) not in inside:
                surf.set_at((x, y), OUTLINE)
                break


def make_tree_sprites():
    """ภาพต้นไม้ 3 แบบ (ต้องเรียกหลัง pygame.init)  seed คงที่: หน้าตาเดิมทุกครั้ง"""
    out = []
    rng = random.Random(21)
    for kind in KINDS:
        surf = pygame.Surface(kind["size"], pygame.SRCALPHA)
        pygame.draw.ellipse(surf, SHADOW, kind["shadow"])       # เงาใต้ต้น
        _draw_trunk(surf, kind)
        _draw_crown(surf, kind, rng)
        out.append(surf)
    flower = pygame.Surface((len(FLOWER[0]), len(FLOWER)), pygame.SRCALPHA)
    for y, row in enumerate(FLOWER):
        for x, ch in enumerate(row):
            if ch in FLOWER_COLORS:
                flower.set_at((x, y), FLOWER_COLORS[ch])
    out.append(flower)                                      # แบบที่ FLOWER_KIND
    return out


def scatter(finish_z, rng=random):
    """สุ่มตำแหน่งต้นไม้ + กอดอกไม้ (1-3 ดอก) สองข้างถนนตลอดด่าน (+ เลยเส้นชัยไปอีกหน่อย)
    คืน [(z, x, แบบ, กลับซ้ายขวา), ...] เรียงตาม z"""
    trees = []
    for side in (-1, 1):
        z = rng.uniform(0, SPACING[1])
        while z < finish_z + C.Z_FAR:
            x = side * (C.ROAD_HALF_W + rng.uniform(*SIDE_GAP))
            trees.append((z, x, rng.randrange(len(KINDS)), rng.random() < 0.5))
            z += rng.uniform(*SPACING)
        z = rng.uniform(0, FLOWER_SPACING[1])
        while z < finish_z + C.Z_FAR:
            x = side * (C.ROAD_HALF_W + rng.uniform(*FLOWER_GAP))
            for _ in range(rng.choice((1, 1, 2, 3))):       # กอละ 1-3 ดอก ห่างกันนิดหน่อย
                fx = x + rng.uniform(-14, 14)
                if abs(fx) > C.ROAD_HALF_W + 6:              # ไม่ขึ้นบนถนน
                    trees.append((z + rng.uniform(-10, 10), fx, FLOWER_KIND, rng.random() < 0.5))
            z += rng.uniform(*FLOWER_SPACING)
    trees.sort()
    return trees
