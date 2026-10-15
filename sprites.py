"""โหลด / ตัดเฟรม / ย้อมสี / ย่อ sprite คนจาก assets/16x32   [เจ้าของ: B]

ใช้ร่วมกันได้หลายไฟล์ (ตอนนี้ใช้กับศัตรู) และเก็บผลไว้ใช้ซ้ำ เพราะโหลดไฟล์และย่อภาพทุกเฟรมช้า
ต้องเรียกหลังเปิดหน้าต่างแล้ว (convert_alpha ต้องมี display) จึงโหลดตอนวาดครั้งแรก ไม่ใช่ตอน import
"""
from pathlib import Path

import pygame

SHEET_DIR = Path(__file__).resolve().parent / "assets" / "16x32"
ROWS = 5                    # ทุกชีตมี 5 แถว = 5 ทิศ  แถว 0 = หันหน้าเข้ากล้อง
FRONT = 0

_frames = {}
_scaled = {}


def frames(sheet, row=FRONT, tint=None):
    """เฟรมทั้งหมดของแถว row ในชีต "16x32 <sheet>-Sheet.png"  tint = (r, g, b) คูณสีทับ (เช่น ย้อมแดง)
    หาไฟล์ไม่เจอ: คืนสี่เหลี่ยมสีเดียวแทน เกมจะได้ไม่พัง"""
    key = (sheet, row, tint)
    if key not in _frames:
        try:
            image = pygame.image.load(str(SHEET_DIR / f"16x32 {sheet}-Sheet.png")).convert_alpha()
            h = image.get_height() // ROWS
            w = h                                    # เฟรมเป็นสี่เหลี่ยมจัตุรัส (32x32)
            cut = [image.subsurface((x, row * h, w, h)).copy() for x in range(0, image.get_width() - w + 1, w)]
        except (pygame.error, FileNotFoundError, OSError):
            dummy = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.rect(dummy, (200, 200, 200), (10, 4, 12, 26))
            cut = [dummy]
        if tint:
            for surf in cut:
                surf.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _frames[key] = cut
    return _frames[key]


def scaled(surface, w, h):
    """ภาพที่ย่อเป็น w x h แล้ว (เก็บไว้ใช้ซ้ำ)"""
    key = (id(surface), w, h)
    image = _scaled.get(key)
    if image is None:
        if len(_scaled) > 3000:
            _scaled.clear()
        image = _scaled[key] = pygame.transform.scale(surface, (max(1, w), max(1, h)))
    return image
