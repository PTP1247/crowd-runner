"""บอสท้ายด่าน: ยืนรอหลังเส้นชัย กลุ่มคนวิ่งผ่านเส้นชัยหมดแล้วต้องปะทะกับบอสจนฝ่ายใดฝ่ายหนึ่งหมด

กติกาปะทะเหมือน EnemyGroup ทุกอย่าง (หักทีละคน, main.py หยุดวิ่งระหว่างปะทะ) จึงสืบทอดมาเลย
ต่างกันแค่: ตัวเดียวตัวใหญ่, ปะทะนานกว่า, มีท่าโจมตี และมีจังหวะ "impact" ให้ main.py สั่นกล้อง/เล่นเสียง

เพิ่มบอสในด่าน: ใส่ใน levels/levelN.json  ->  "boss": {"kind": 1, "count": 80}
เพิ่มบอสแบบใหม่: เพิ่ม dict ใน STYLES (kind ถัดไป)
"""
import random

import pygame

import config as C
import sprites
from enemy import EnemyGroup

# ---------- สีบนชีต 16x32 ของผู้เล่น (ใช้หาตา/ปาก/แก้มเพื่อแต่งหน้า) ----------
OUTLINE = (47, 37, 34)
SKIN = (250, 243, 232)
SHADE = (185, 179, 161)
MOUTH = (231, 213, 198)
BLUSH = (209, 157, 167)
FACE_COLORS = (SKIN, SHADE, MOUTH)

RED_EYE = (235, 45, 40)
SCAR = (240, 172, 178)       # แผลเป็นสีชมพูซีด เห็นชัดบนผิวสีน้ำเงิน

# แต่ละ kind = บอสหนึ่งแบบ
#   idle / attack: (ชื่อชีต, แถว)  แถว 0 = หันตรงเข้าหากล้อง, แถว 1 = หันเกือบตรง
#   attack_seq: ลำดับเฟรมในชีตที่เล่นเป็นท่าโจมตี (ไม่ใส่ = เล่นเรียงทุกเฟรม 0..attack_frames-1)
#   impact: ตำแหน่งใน attack_seq ที่ลงพื้น (สั่นกล้อง + คลื่นกระแทก)
#   lunge: ตำแหน่ง -> พุ่งเข้าหากลุ่มคนกี่ unit    lift: ตำแหน่ง -> ลอยจากพื้นกี่พิกเซลของ sprite (กระโดด)
#   face: "angry" (คิ้ว V ตาแดง ปากบึ้ง) / "blank" (ตาปรือ ปากเส้นตรง ไร้อารมณ์)
#   scar: "screen_left" / "screen_right" = แผลเป็นที่ตาข้างซ้าย/ขวาของจอ (ตาขวา/ซ้ายของตัวบอสเอง)
SAMURAI_CUTS = 12           # บอสซามูไร: ฟันกี่ครั้งต่อรอบ (สุ่มทิศ)
SAMURAI_STEPS = 4           # ฟันละกี่ภาพ (ดาบหมุนไปตามวงทีละช่วง ยิ่งมากยิ่งลื่น)
SAMURAI_FRAMES = SAMURAI_CUTS * SAMURAI_STEPS

STYLES = {
    1: {
        "name": "the Grey Brute",
        "idle": ("Idle", 1), "idle_fps": 6,
        "attack": ("Attack", 1), "attack_fps": 11, "attack_frames": 7,   # ไม่ต้องโหลดภาพก็รู้ (test รันได้)
        "impact": 3, "lunge": {2: 10, 3: 45, 4: 30, 5: 10},
        "tint": (150, 150, 158),     # คูณหลังทำเป็นขาวดำ: ได้สีเทาหิน
        "face": "angry",
        "label": (90, 90, 100),
    },
    2: {
        "name": "the Blue Stomper",
        "idle": ("Idle", 0), "idle_fps": 5,
        # ยกขาขวา (ขาซ้ายของจอ) ออกข้างแล้วกระทืบลง: ไม่มีท่านี้ในชีต จึงสร้างเองจากเฟรมยืนหน้าตรง
        # แต่ละท่า = (เหวี่ยงขาออกข้างกี่องศา, ตัวเอนไปทางขาที่ยืน, ตัวยุบลง, กางแขนขึ้นกี่องศา, ยกไหล่ขึ้น)
        # รวบแรง: ขาขึ้น + แขนชูสูง + ไหล่ยก  แล้วกระทืบ: ขาลง + แขนฟาดลง + ตัวยุบ
        "attack": ("Idle", 0),
        "build": {"kind": "leg_stomp", "leg": "screen_left",
                  "poses": [(0, 0, 0, 0, 0), (30, 1, 0, 45, 0), (60, 1, 0, 90, 1), (85, 2, 0, 125, 1),
                            (85, 2, 0, 130, 1), (0, 0, 2, 15, 0), (0, 0, 1, 5, 0), (0, 0, 0, 0, 0)]},
        "attack_fps": 9, "attack_frames": 8,
        "impact": 5,                 # ท่าที่ขากระทืบลงพื้น
        "lunge": {5: 12, 6: 12, 7: 6},       # พุ่งนิดเดียว ไม่งั้นเท้าไปทับป้ายจำนวนของกลุ่มคน มองไม่เห็นขา
        "tint": (110, 150, 245),     # น้ำเงิน
        "face": "blank", "scar": "screen_left",     # ตาขวาของตัวบอสเอง (บอสหันหน้าเข้าหาเรา)
        "shock": 1.35,               # กระทืบพื้น: คลื่นกระแทกใหญ่กว่าหมัด
        "label": (55, 85, 170),
    },
    3: {
        "name": "the Iron Barrage",
        "idle": ("Idle", 0), "idle_fps": 6,
        # หมัดรัวใส่กลุ่มคน: ยืนกางขาย่อตัว แขนวาดทับใน draw_overlay (แขนจริง 2 ข้าง + รอยหมัดเบลอรอบๆ)
        # แต่ละท่า = (กางขากี่องศา, ท่อนบนโยกซ้าย/ขวา, ย่อตัวลง)  เลือกท่าตามไหล่ที่กำลังง้าง (ดู update)
        "attack": ("Idle", 0),
        "build": {"kind": "barrage", "poses": [(24, 0, 2), (28, 1, 2), (24, 0, 3), (28, -1, 2)]},
        "attack_fps": 14, "attack_frames": 4,
        "impact": None,              # ไม่มีจังหวะลงหนักครั้งเดียว: โดนรัวๆ แทน (ดู barrage)
        "barrage": {"hits_per_sec": 9,     # หมัดโดนกี่ครั้งต่อวินาที (แขนซ้าย/ขวาสลับกัน)
                    "trails": 6,           # หมัดบนจอพร้อมกัน: 2 แรก = แขนจริง ที่เหลือ = รอยเบลอ
                    "change_per_sec": 18}, # รอยเบลอเปลี่ยนตำแหน่งกี่ครั้งต่อวินาที
        "impact_strength": 0.35,     # แรงต่อหมัด เทียบกับหมัดทุบพื้นของบอส 1 (= 1)
        "gap": 60,                   # ยืนห่างคนแถวหน้าเท่านี้ (บอสอื่นใช้ C.BOSS_GAP)
        "lunge": {0: 10, 1: 10, 2: 10, 3: 10},     # โน้มตัวเข้าหากลุ่มคนตลอดการรัวหมัด
        "tint": (108, 108, 116),     # เทาเข้มกว่าบอส 1
        "face": "angry",
        "label": (60, 60, 70),
    },
    4: {
        "name": "the Green Boxer",
        # ตัวล่ำ: วาดลำตัว/แขนใหม่เอง (อกกว้าง ไหล่ใหญ่ แขนหนามีข้อศอก) ใช้หัวกับขาจากชีตเดิม
        # ท่ายืนรอ = ตั้งการ์ดเด้งตัวแบบนักมวย  ท่าโจมตี = คอมโบ หมัดแย็บซ้าย -> ฮุกขวา -> อัปเปอร์คัต
        "idle": ("Idle", 0), "idle_fps": 6,
        "idle_build": {"kind": "boxer", "poses": ["guard", "guard_low", "guard_low", "guard"]},
        "attack": ("Idle", 0),
        "build": {"kind": "boxer",
                  "poses": ["guard", "jab", "jab_back", "guard", "hook_load", "hook", "hook_through",
                            "crouch", "uppercut", "uppercut_hold", "guard_low"]},
        "attack_fps": 10, "attack_frames": 11,
        "impact": [1, 5, 8],                           # แย็บ, ฮุก, อัปเปอร์คัต
        "impact_strength": {1: 0.4, 5: 0.7, 8: 1.0},  # แย็บเบาเร็ว ฮุกหนักขึ้น อัปเปอร์คัตปิดคอมโบแรงสุด
        "lunge": {1: 20, 2: 6, 4: 2, 5: 16, 6: 12, 7: 6, 8: 24, 9: 18, 10: 6},
        "lift": {8: 3, 9: 1},                          # อัปเปอร์คัต: ดันตัวขึ้นจนเท้าลอย
        "tint": (110, 205, 115),     # เขียว
        "face": "frown",             # โกรธนิดๆ: คิ้วขมวดเล็กน้อย ตาปกติ ปากตรง
        "headband": True,            # ผ้าคาดหัวสีขาว ชายผ้าปลิวข้างหัว
        "label": (45, 125, 55),
    },
    5: {
        "name": "the Shadow Ninja",
        # ชุดนินจาดำ (ฮู้ด + ผ้าปิดหน้า เห็นแค่ตา, เสื้อป้ายไขว้, เข็มขัด, กางเกงฮากามะ) คุไนเหน็บหลัง
        # สีชุดหลายสี ย้อมทั้งตัวแบบบอสอื่นไม่ได้: วาดด้วยสีจริงเลย ("colored")
        # ยืนรอไกลๆ (stand) -> คนข้ามเส้นชัยหมด: วิ่งแบบนินจา (ตัวโน้ม แขนลู่ไปข้างหลัง) เข้าหา
        #   ระหว่างวิ่งเอื้อมมือไปดึงคุไนจากหลัง -> ถึงแล้วฟันซ้าย-ขวา (ถือคุไนกลับด้าน ใบมีดออกทางนิ้วก้อย)
        "colored": True,
        "idle": ("Idle", 0), "idle_fps": 3,
        "idle_build": {"kind": "ninja", "poses": ["stand", "stand_breath"]},
        "run_build": {"kind": "ninja", "poses": [f"{arms}{leg}" for arms in ("run", "reach", "pull", "armed")
                                                 for leg in range(4)]},
        "run_fps": 14, "stand": 1000, "run_speed": 650,
        "run_parts": [0.4, 0.58, 0.74],          # วิ่งมาได้เท่านี้ (สัดส่วน) -> เปลี่ยนชุดท่า: เอื้อม / ชัก / ถือ
        "attack": ("Idle", 0),
        "build": {"kind": "ninja",
                  "poses": ["ready", "wind_r", "slash_r", "follow_r", "wind_l", "slash_l", "follow_l", "ready"]},
        "attack_fps": 12, "attack_frames": 8,
        "impact": [2, 5],                        # ฟันขวา->ซ้ายจอ และฟันย้อนกลับ
        "impact_strength": {2: 0.6, 5: 0.6},
        "lunge": {1: 4, 2: 20, 3: 14, 4: 6, 5: 20, 6: 14, 7: 4},
        "tint": (54, 56, 70),        # ไม่ได้ใช้ย้อม (colored) ใช้เป็นสีเศษผ้าที่กระเด็นตอนโดนตี
        "label": (40, 42, 56),
    },
    6: {
        "name": "the Iron Knight",
        # อัศวินเกราะเหล็ก หมวกช่องมองตัว T ขนนกแดง ดาบยาวในฝักที่สะโพก (วาดสีจริง เฟรมกว้างเผื่อดาบ)
        # ยืนรอห่างเส้นชัยนิดหน่อย -> คนข้ามเส้นหมด (หยุดรอ): ชักดาบ ตั้งท่า (intro) -> เดินถือดาบเข้าหา -> คอมโบ
        "colored": True,
        "idle": ("Idle", 0), "idle_fps": 2,
        "idle_build": {"kind": "knight", "poses": ["sheathed", "sheathed_breath"]},
        "intro_build": {"kind": "knight",
                        "poses": ["sheathed", "reach", "reach", "draw", "draw_out", "draw_out", "stance",
                                  "stance2", "stance", "stance2", "stance"]},
        "intro_fps": 7,
        "run_build": {"kind": "knight", "poses": [f"advance{i}" for i in range(4)]},
        "run_fps": 8, "stand": 380, "run_speed": 260,
        "attack": ("Idle", 0),
        # ฟันกวาดกว้างซ้าย->ขวา, ฟันเฉียงจากซ้ายล่างขึ้นขวาบน, ฟันตรงลงพื้น
        "build": {"kind": "knight",
                  "poses": ["stance", "wide_load", "wide_swing", "wide_follow", "diag_load", "diag_slash",
                            "over_load", "over_load", "down_slash", "down_hold", "stance2"]},
        "attack_fps": 9, "attack_frames": 11,
        "impact": [2, 5, 8],
        "impact_strength": {2: 0.6, 5: 0.7, 8: 1.0},       # ฟันลงพื้นปิดคอมโบ: สั่นแรง ฝุ่นกระจาย
        "lunge": {1: 4, 2: 18, 3: 12, 4: 6, 5: 18, 6: 8, 7: 8, 8: 24, 9: 22, 10: 6},
        "tint": (88, 110, 124),      # ไม่ได้ใช้ย้อม ใช้เป็นสีเศษเกราะที่กระเด็น
        "label": (60, 78, 92),
    },
    7: {
        "name": "the Wandering Samurai",
        # หมวกฟางบังหน้า (หน้าอยู่ในเงา) กิโมโนแดงซีด ฮากามะเทาอ่อน เกี๊ยะไม้ คาตานะในฝักที่สะโพกขวา (ซ้ายจอ)
        # นั่งคุกเข่ารอ -> คนข้ามเส้นหมด: ลุกขึ้น ชักดาบแบบอิไอ (รอยดาบ + ประกาย) ตั้งท่า -> เดินเข้าหา -> ฟันรัวทุกทิศ
        "colored": True,
        "idle": ("Idle", 0), "idle_fps": 2,
        "idle_build": {"kind": "samurai", "poses": ["seiza", "seiza_breath"]},
        "intro_build": {"kind": "samurai",
                        "poses": ["seiza", "rise", "stand", "grip", "grip", "draw_half", "draw_flash",
                                  "draw_flash", "raise", "stance", "stance_glint", "stance_still"]},
        "intro_fps": 7,
        "run_build": {"kind": "samurai", "poses": [f"walk{i}" for i in range(4)]},
        "run_fps": 8, "stand": 200, "run_speed": 260,       # นั่งใกล้: ลุกแล้วเดินแค่ 1-2 ก้าวก็ถึง
        "attack": ("Idle", 0),
        "build": {"kind": "samurai", "poses": [f"cut{k}" for k in range(SAMURAI_FRAMES)]},
        "attack_fps": 24, "attack_frames": SAMURAI_FRAMES,  # 24 ภาพต่อวินาที = ฟัน 6 ครั้งต่อวินาที
        "impact": list(range(1, SAMURAI_FRAMES, SAMURAI_STEPS)),    # โดนตอนดาบกวาดผ่านกลางตัว
        "impact_strength": {k: 0.4 for k in range(1, SAMURAI_FRAMES, SAMURAI_STEPS)},
        "lunge": {k: 12 for k in range(SAMURAI_FRAMES)},
        "tint": (214, 124, 114),     # ไม่ได้ใช้ย้อม ใช้เป็นสีเศษผ้า
        "label": (150, 70, 66),
    },
}
PUNCH_WIND = 0.45               # หมัดรัว: ช่วงแรกของแต่ละหมัด (0..1) = ง้าง ดึงไหล่กลับ
PUNCH_HIT = 0.65                # พุ่งออกจนถึงตัวคนตรงนี้ (เกิดแรงกระแทก)
PUNCH_HOLD = 0.8                # ค้างแขนไว้ถึงตรงนี้ แล้วดึงกลับ
TRAIL_SMEAR = (205, 205, 212)   # รอยหมัด: แถบเทาอ่อนหนาๆ
TRAIL_CORE = (255, 255, 255)    # แกนกลางสีขาว
TRAIL_LINE = (28, 24, 30)       # เส้นความเร็วสีเข้มบางๆ ขนานกับรอย (เหมือนภาพตัวอย่าง)

_frames = {}
FISTS = {}        # ชื่อบอส -> จุดกำปั้นที่ต่อย (พิกเซลบนเฟรม 32x32) ของแต่ละท่า หรือ None


def find_eyes(frame):
    """หาตาจากพิกเซล: ตา = จุดสีเส้นขอบที่มีผิวอยู่ซ้าย-ขวา (ใช้ได้ทุกเฟรมแม้หัวขยับ)
    คืน ((x, บน, ล่าง) ตาซ้ายจอ, (x, บน, ล่าง) ตาขวาจอ) หรือ None ถ้าหลับตา/เบลอ"""
    w, h = frame.get_size()
    rgb = lambda x, y: tuple(frame.get_at((x, y)))[:3] if frame.get_at((x, y)).a else None
    top = head_top(frame)
    # ตาอยู่ราว 5-8 พิกเซลใต้ขอบหัว (จำกัดช่วงไว้ ไม่งั้นเส้นมือที่ยกมาหน้าอกจะถูกนับเป็นตา)
    # ตาอยู่ใกล้กลางหัว (ห่างกลางไม่เกิน 4 พิกเซล) ไม่งั้นแขนที่ยกขึ้นข้างหัว (ผิวติดเส้นขอบหัว) จะถูกนับเป็นตา
    cap = [x for x in range(w) if frame.get_at((x, top)).a]
    cx = (cap[0] + cap[-1]) / 2
    columns = {}
    for y in range(top + 4, top + 10):
        for x in range(1, w - 1):
            if abs(x - cx) <= 4 and rgb(x, y) == OUTLINE \
                    and rgb(x - 1, y) in FACE_COLORS and rgb(x + 1, y) in FACE_COLORS:
                columns.setdefault(x, []).append(y)
    if len(columns) != 2 or abs(min(columns) - max(columns)) < 3:
        return None
    return tuple((x, min(ys), max(ys)) for x, ys in sorted(columns.items()))


def head_top(frame):
    w, h = frame.get_size()
    return next(y for y in range(h) if any(frame.get_at((x, y)).a for x in range(w)))


def guess_eyes(frame):
    """ตำแหน่งตาโดยประมาณจากกรอบหัว (เฟรมที่หลับตา: แผลเป็นต้องอยู่ที่เดิม ไม่กระพริบหาย)
    ในชีตนี้ ตาอยู่ 6-8 พิกเซลใต้ขอบหัว และห่างขอบหัวซ้าย/ขวาเข้ามา 3 พิกเซล"""
    w, _ = frame.get_size()
    y = head_top(frame) + 6
    xs = [x for x in range(w) if frame.get_at((x, y)).a]
    return (xs[0] + 3, y, y + 2), (xs[-1] - 3, y, y + 2)


def decorate(frame, style):
    """แต่งหน้าบนเฟรม 32x32 (ก่อนย่อขยาย) ตาม style["face"] / style["scar"]
    แก้ภาพตรงๆ สำหรับสิ่งที่ควรเป็นสีเทาตามตัว (คิ้ว ปาก) แล้วคืน [(x, y, สี), ...]
    ที่ต้องทาทับหลังย้อมสีตัว (ตาแดง แผลเป็น) ไม่งั้นสีจะถูกย้อมไปด้วย"""
    w, h = frame.get_size()
    rgb = lambda x, y: tuple(frame.get_at((x, y)))[:3] if frame.get_at((x, y)).a else None
    for y in range(h):
        for x in range(w):
            if rgb(x, y) == BLUSH:                       # ลบแก้มแดง บอสไม่เขิน
                frame.set_at((x, y), SKIN)
    eyes = find_eyes(frame)
    paint = []
    face = style.get("face")
    if eyes:
        (lx, ly, lb), (rx, ry, rb) = eyes
        bottom = max(lb, rb)
        # ปากเดิม (สีอ่อน) อยู่แถวเดียวกับปลายตา ถ้าทำเป็นสีเข้มจะต่อกับตาเป็นรูปตัว U ดูเหมือนยิ้ม
        # จึงลบทิ้งก่อน แล้ววาดปากใหม่ต่ำลงมา 1 แถว
        for y in range(ly, bottom + 1):
            for x in range(lx + 1, rx):
                if rgb(x, y) == MOUTH:
                    frame.set_at((x, y), SKIN)
        r = bottom + 1
        if face == "angry":
            for x, y in ((lx - 1, ly - 3), (lx, ly - 2), (lx + 1, ly - 2),      # คิ้วซ้าย  \
                         (rx + 1, ry - 3), (rx, ry - 2), (rx - 1, ry - 2)):     # คิ้วขวา   /
                frame.set_at((x, y), OUTLINE)
            for x in range(lx + 1, rx):                                         # ปากบึ้งรูป ^
                frame.set_at((x, r + (1 if x in (lx + 1, rx - 1) else 0)), OUTLINE)
            paint += [(x, y, RED_EYE) for x in (lx, rx) for y in range(ly, bottom + 1)
                      if rgb(x, y) == OUTLINE]
        elif face == "frown":
            # โกรธนิดๆ: คิ้วสั้นเอียงลงหาหัวตา (แค่ขมวด ไม่ถึงตัว V แบบบอส 1) ตาสีเดิม ปากขีดตรง
            for x, y in ((lx - 1, ly - 2), (lx, ly - 2), (lx + 1, ly - 1),
                         (rx + 1, ry - 2), (rx, ry - 2), (rx - 1, ry - 1)):
                frame.set_at((x, y), OUTLINE)
            for x in range(lx + 2, rx - 1):
                frame.set_at((x, r), OUTLINE)
        elif face == "blank":
            # ตาจุดเล็ก (เหลือ 2 พิกเซลบน) + ปากขีดสั้นตรงกลาง = หน้านิ่งไร้อารมณ์
            # ต้องไม่ให้ปากแตะปลายตา ไม่งั้นต่อกันเป็นรูป ◡ ดูเหมือนยิ้ม (หน้าตรงแถว 0 หน้าอยู่ต่ำ ชิดคาง)
            for x, top_y, bot_y in ((lx, ly, lb), (rx, ry, rb)):
                for y in range(top_y + 2, bot_y + 1):
                    frame.set_at((x, y), SKIN)
            mid = (lx + rx) // 2
            for x in (mid, mid + 1):
                frame.set_at((x, r), OUTLINE)
    if style.get("scar"):
        right = style["scar"] == "screen_right"
        (ex, ey, eb) = (eyes or guess_eyes(frame))[1 if right else 0]
        s = 1 if right else -1            # ปลายบนของแผลเอียงออกไปทางขอบหน้า (สะท้อนตามข้าง)
        lid = []
        if eyes:
            # ตาข้างที่มีแผล บอด/ปิดสนิท: ลบลูกตา แล้ววาดเปลือกตาปิดเป็นขีดแนวนอน 3 พิกเซล
            # (เฟรมที่หลับตาทั้งสองข้างอยู่แล้ว ไม่ต้องทำ)
            for y in range(ey, eb + 1):
                frame.set_at((ex, y), SKIN)
            lid = [(x, ey + 1) for x in (ex - 1, ex, ex + 1) if rgb(x, ey + 1) in FACE_COLORS]
            for x, y in lid:
                frame.set_at((x, y), OUTLINE)
        # แผลเป็นแนวดิ่งเอียงนิดๆ พาดยาวตลอดตา: เหนือคิ้ว -> ทับเปลือกตาที่ปิด -> ใต้ตา
        # (ไม่ลงต่ำกว่านี้ ไม่งั้นแตะปาก) ตรงกลางเปลือกตาให้แผลทับ ดูเหมือนแผลผ่าเปลือกตา
        for x, y in ((ex + s, ey - 3), (ex + s, ey - 2), (ex, ey - 1), (ex, ey), (ex, ey + 1), (ex, ey + 2)):
            if rgb(x, y) in FACE_COLORS or (x, y) == (ex, ey + 1) and (x, y) in lid:
                paint.append((x, y, SCAR))
    return paint


def swing(out, piece, rect, pivot, angle, outward_left):
    """วาด piece (ตัดมาจาก rect) หมุนรอบจุด pivot ไป angle องศา
    outward_left=True: เหวี่ยงไปทางซ้ายของจอ (หมุนตามเข็ม)  False: ไปทางขวา (ทวนเข็ม)"""
    turned = pygame.transform.rotate(piece, -angle if outward_left else angle)
    to_center = pygame.math.Vector2(rect.centerx - pivot[0], rect.centery - pivot[1])
    center = pygame.math.Vector2(pivot) + to_center.rotate(angle if outward_left else -angle)
    out.blit(turned, turned.get_rect(center=(round(center.x), round(center.y))))


def body_parts(base, cut_arms=True):
    """ตัดเฟรมยืนหน้าตรง 32x32 เป็นชิ้น: ขาซ้าย/ขวา, แขนซ้าย/ขวา และตัวที่เหลือ (หัว+ลำตัว)
    ขา = 5 แถวล่างสุดของ sprite แบ่งซ้าย/ขวาตรงกลางระหว่างขาสองข้าง
      (ตัดเฉพาะคอลัมน์ของขาจริง ดูจากแถวใต้แถวบนสุด ไม่งั้นปลายมือที่ห้อยลงมาแถวเดียวกันจะติดไปกับขา)
    แขน = แถว 10..4 จากล่าง ข้างนอกเส้นตะเข็บสีเงา (เส้นแบ่งแขนกับลำตัว)
    คืน dict: rest (ตัวที่เหลือ ใส่เส้นขอบข้างลำตัวแทนแขนแล้ว), legs/arms {True=ซ้ายจอ: (ชิ้น, rect, จุดหมุน)},
    top (แถวบนสุดของขา), shoulder_y"""
    w, h = base.get_size()
    bottom = max(y for y in range(h) if any(base.get_at((x, y)).a for x in range(w)))
    top = bottom - 4
    xs = [x for x in range(w) if base.get_at((x, bottom - 2)).a]       # แถวกลางแข้ง: เห็นขาสองข้างชัด
    split = (xs[0] + xs[-1] + 1) // 2
    rest = base.copy()
    legs = {}
    for left in (True, False):
        cols = [x for y in range(top + 1, bottom + 1) for x in range(w)
                if base.get_at((x, y)).a and (x < split if left else x >= split)]
        rect = pygame.Rect(min(cols), top, max(cols) + 1 - min(cols), h - top)
        used = [x for x in range(rect.x, rect.right) if base.get_at((x, bottom - 2)).a]
        legs[left] = (base.subsurface(rect).copy(), rect, ((used[0] + used[-1] + 1) / 2, top))   # หมุนรอบสะโพก
        rest.fill((0, 0, 0, 0), rect)

    a_top, a_bottom = bottom - 10, bottom - 4
    seam_row = [x for x in range(w) if rgb_of(base, x, bottom - 8) == SHADE]
    seam_l, seam_r = seam_row[0], seam_row[-1]
    arms = {}
    for left in ((True, False) if cut_arms else ()):     # ไม่ขยับแขน: ไม่ต้องตัด (ไม่งั้นมีเส้นขอบโผล่ระหว่างแขนกับตัว)
        xs_ = [x for y in range(a_top, a_bottom + 1) for x in range(w) if base.get_at((x, y)).a
               and (x < seam_l if left else x > seam_r)]
        rect = pygame.Rect(min(xs_), a_top, max(xs_) - min(xs_) + 1, a_bottom - a_top + 1)
        arms[left] = (base.subsurface(rect).copy(), rect, (rect.right if left else rect.x, a_top))  # หมุนรอบหัวไหล่
        rest.fill((0, 0, 0, 0), rect)
    for y in (range(a_top, a_bottom) if cut_arms else ()):   # ลำตัวที่เหลือ: ใส่เส้นขอบด้านข้างแทนแขนที่ตัดออก
        for x in (seam_l, seam_r):
            if rest.get_at((x, y)).a:
                rest.set_at((x, y), OUTLINE)
    return {"rest": rest, "legs": legs, "arms": arms, "top": top, "shoulder_y": a_top}


def leg_pose(base, leg, angle, lean, drop, arms=0, rise=0):
    """ท่ายกขาข้างเดียวออกด้านข้าง (แบบกระทืบซูโม่) มองหน้าตรง สร้างจากเฟรมยืน 32x32
    leg: "screen_left"/"screen_right" ขาที่ยก   angle: เหวี่ยงขาออกข้างกี่องศา หมุนรอบข้อสะโพก (0 = ยืน)
    lean: ตัวท่อนบนเอนไปทางขาที่ยืนกี่พิกเซล (ทรงตัว)   drop: ตัวยุบลงกี่พิกเซล (ตอนกระทืบ)
    arms: กางแขนทั้งสองข้างขึ้นกี่องศา หมุนรอบหัวไหล่ (0 = แขนห้อย, 90 = กางตรง, >90 = ชูขึ้น)
    rise: ยกไหล่/ท่อนบนขึ้นกี่พิกเซล (ตอนรวบแรงก่อนกระทืบ)
    ทำไมยกออกข้าง ไม่ยกเข่ามาข้างหน้า: มองหน้าตรง ขาที่ยกมาข้างหน้าทับตัวเองจนดูไม่ออก"""
    p = body_parts(base, cut_arms=bool(arms))
    w, h = base.get_size()
    rest, top = p["rest"], p["top"]
    left = leg == "screen_left"
    shift = lean if left else -lean                  # เอนไปทางขาที่ยืน (ฝั่งตรงข้ามกับขาที่ยก)
    dy = drop - rise
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    piece, rect, _ = p["legs"][not left]
    out.blit(piece, rect)                            # ขาที่ยืนอยู่กับที่
    # แขนหมุนรอบหัวไหล่ วาดก่อนตัว = อยู่หลังตัวและหัว
    # ทำไม: ตอนชูแขนสูง แขนเฉียงเข้ามาที่ข้างหัว ถ้าวาดทับ เส้นขอบแขนจะทับหน้า (เคยทับตาที่บอดจนดูเหมือนลืมตา)
    for side_left, (apiece, arect, (px, py)) in p["arms"].items():
        swing(out, apiece, arect.move(shift, dy), (px + shift, py + dy), arms, side_left)
    out.blit(rest.subsurface((0, 0, w, top)), (shift, dy))              # ตัวท่อนบน (ทับแขน)
    out.blit(rest.subsurface((0, top, w, h - top)), (0, top))           # ส่วนที่เหลือใต้เอว (ถ้ามี)
    if dy < 0:
        # ยกไหล่ขึ้น: ตัวท่อนบนลอยขึ้นแต่ขาอยู่ที่เดิม เกิดช่องว่างที่เอว -> ยืดแถวขอบกางเกงลงมาปิด
        waist = rest.subsurface((0, top - 1, w, 1))
        for y in range(top - 1 + dy, top):
            out.blit(waist, (shift, y))
    # หมุนขารอบข้อสะโพก ขาซ้ายจอเหวี่ยงไปทางซ้าย  (วาดทีหลัง อยู่หน้าตัว)
    piece, rect, (hx, hy) = p["legs"][left]
    swing(out, piece, rect.move(shift, drop), (hx + shift, hy + drop), angle, left)
    close_outline(out, top - 2)          # เฉพาะเอวลงมา (แขนที่หมุนมีเส้นขอบของมันเองอยู่แล้ว)
    return out


def stance_pose(base, spread, shift, drop, arms=None, pull=None, punch=None):
    """ท่ายืนกางขาย่อตัวออกหมัด มองหน้าตรง สร้างจากเฟรมยืน 32x32
    spread: กางขาทั้งสองออกข้างกี่องศา   shift: ตัวท่อนบนเอนซ้าย/ขวากี่พิกเซล (บิดตัวตามไหล่ที่ง้าง)
    drop: ย่อตัวลงกี่พิกเซล (ย่อเฉพาะท่อนบน ไม่งั้นเท้าจมใต้ขอบภาพ)
    arms: {"L"/"R": มุมแขน} หมุนรอบหัวไหล่   pull: ข้างที่ดึงไหล่กลับ (ไหล่ยกขึ้น 2 + ถอยออกข้าง 1 พิกเซล)
    punch: ข้างที่ต่อยถึง: แขนวาดทับหน้าตัว (ต่อยมาข้างหน้า) + กำปั้นใหญ่ที่ปลาย (พุ่งเข้าหากล้อง)
    คืน (ภาพ, จุดกำปั้นที่ต่อยบนเฟรม หรือ None)"""
    arms = arms or {}
    p = body_parts(base, cut_arms=True)
    w, h = base.get_size()
    rest, top = p["rest"], p["top"]
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    for left, (piece, rect, pivot) in p["legs"].items():
        swing(out, piece, rect, pivot, spread, left)
    out.blit(rest.subsurface((0, top, w, h - top)), (0, top))

    def place(left):
        """(ชิ้นแขน, rect ที่ย้ายแล้ว, จุดหมุน, มุม) ของแขนข้างนี้ในท่านี้"""
        key = "L" if left else "R"
        piece, rect, (px, py) = p["arms"][left]
        dx = (-1 if left else 1) if pull == key else 0        # ไหล่ที่ง้าง ถอยออกข้าง
        dy = drop - (2 if pull == key else 0)                 # และยกขึ้น
        return piece, rect.move(shift + dx, dy), (px + shift + dx, py + dy), arms[key]

    sides = [left for left in (True, False) if ("L" if left else "R") in arms]
    for left in sides:                                    # แขนง้าง/ตั้งการ์ด: อยู่หลังตัวและหัว
        if ("L" if left else "R") != punch:
            piece, rect, pivot, angle = place(left)
            swing(out, piece, rect, pivot, angle, left)
    out.blit(rest.subsurface((0, 0, w, top)), (shift, drop))
    fist = None
    for left in sides:
        if ("L" if left else "R") != punch:
            continue
        piece, rect, pivot, angle = place(left)
        swing(out, piece, rect, pivot, angle, left)       # แขนที่ต่อย: อยู่หน้าตัว
        tip = pygame.math.Vector2(pivot) + pygame.math.Vector2(0, rect.height - 1).rotate(angle if left else -angle)
        fist = (round(tip.x), round(tip.y))
        pygame.draw.circle(out, OUTLINE, fist, 3)          # กำปั้นใหญ่ขึ้น = พุ่งมาทางกล้อง/กลุ่มคน
        pygame.draw.circle(out, SKIN, fist, 2)
    close_outline(out, top - 2)
    return out, fist


def close_outline(surface, from_y):
    """ใส่เส้นขอบเข้มให้ขอบที่เพิ่งโผล่ (ตรงที่ตัดขา/แขนออก หรือตัวเอนจนขอบไม่ตรงกัน) ตั้งแต่แถว from_y ลงไป
    พิกเซลทึบที่อยู่ติดช่องว่าง (บน/ล่าง/ซ้าย/ขวา) ต้องเป็นสีเส้นขอบ  sprite เดิมมีเส้นขอบรอบตัวอยู่แล้ว
    จึงเปลี่ยนเฉพาะขอบใหม่"""
    w, h = surface.get_size()
    # นอกกรอบภาพนับว่าทึบ: แถวล่างสุด (ฝ่าเท้า) ชนขอบภาพ ไม่ใช่ขอบที่โผล่ใหม่
    solid = lambda x, y: not (0 <= x < w and 0 <= y < h) or surface.get_at((x, y)).a > 0
    edges = [(x, y) for y in range(from_y, h) for x in range(w)
             if solid(x, y) and rgb_of(surface, x, y) != OUTLINE
             and not all(solid(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in edges:
        surface.set_at((x, y), OUTLINE)


def rgb_of(surface, x, y):
    c = surface.get_at((x, y))
    return tuple(c)[:3] if c.a else None


# ---------- บอสนักมวย (kind 4): ลำตัว/แขนวาดเอง ----------
# พิกัดบนเฟรม 32x32 ตอนยืนปกติ  R = แขนขวาของบอส (ซ้ายจอ)  L = แขนซ้ายของบอส (ขวาจอ)  บอสหันหน้าเข้าหาเรา
BOXER_SHOULDER = {"R": (10, 21), "L": (23, 21)}
# ลำตัวทรง V: ไหล่กว้าง เอวแคบ (กว้างกว่าตัวในชีตเกือบเท่าตัว)
BOXER_TORSO = [(13, 18), (10, 19), (8, 21), (8, 23), (10, 25), (11, 26), (22, 26), (23, 25), (25, 23),
               (25, 21), (23, 19), (20, 18)]
# เส้นกล้ามเนื้อ (สีเงา): ร่องกลางอก, ใต้อกซ้าย/ขวา, ซิกแพ็ก
BOXER_MUSCLE = [(12, 22), (13, 23), (14, 23), (15, 23), (18, 23), (19, 23), (20, 23), (21, 22),
                (16, 21), (17, 21), (15, 25), (18, 25)]
BAND = (250, 250, 250)          # ผ้าคาดหัว (ทาหลังย้อมสีตัว ไม่งั้นกลายเป็นสีเขียว)
BAND_SHADE = (212, 214, 222)
# ชายผ้าที่ผูกไว้ด้านหลังหัว ปลิวออกทางขวาจอ (พิกัดเทียบกับขอบหัว: ห่างขอบขวา, ใต้ขอบบน) 2 แบบสลับกัน = ปลิว
BAND_TAILS = ([(1, 3), (2, 3), (3, 4), (4, 4), (5, 5), (1, 4), (2, 5), (3, 6)],
              [(1, 3), (2, 2), (3, 2), (4, 3), (5, 3), (1, 4), (2, 4), (3, 5), (4, 6)])

# ท่าทั้งหมด: shift = ตัวท่อนบนเลื่อนซ้าย/ขวา (บิดสะโพก-ไหล่), drop = ย่อตัว, spread = กางขา
#   arms: ข้าง -> (ศอก, กำปั้น, ขนาดกำปั้น)  กำปั้นใหญ่ = ยื่นเข้าหากล้อง (ต่อยเข้าหากลุ่มคน)
#   speed: เส้นความเร็วสีขาว [(จุดเริ่ม, จุดปลาย), ...]   tail: แบบชายผ้า (สลับกันให้ดูปลิว)
#   ตัวเลขทั้งหมดเป็นพิกัดตอนยืนปกติ ขยับตาม shift/drop ให้เอง
_GUARD = {"R": ((12, 26), (12, 19), 2), "L": ((21, 26), (21, 19), 2)}   # ศอกหุบหน้าซี่โครง กำปั้นใต้คาง
BOXER_POSES = {
    "guard": {"arms": _GUARD, "spread": 10, "tail": 0},
    "guard_low": {"arms": _GUARD, "spread": 10, "drop": 1, "tail": 1},
    # แย็บ: หมัดซ้ายพุ่งตรงเข้าหากล้องเร็วๆ  แขนสั้นลง (ชี้เข้าหาเรา) กำปั้นใหญ่ขึ้น ไหล่ซ้ายยื่นตาม
    "jab": {"arms": {"R": _GUARD["R"], "L": ((22, 22), (19, 22), 4)}, "shift": -1, "spread": 12, "tail": 1,
            "speed": [((13, 21), (11, 20)), ((14, 26), (12, 27)), ((23, 26), (25, 27)), ((22, 19), (24, 18))]},
    "jab_back": {"arms": {"R": _GUARD["R"], "L": ((23, 25), (21, 20), 2)}, "spread": 10, "tail": 0},
    # ฮุกขวา: ง้าง = บิดตัวหนี ศอกกางออกข้างระดับไหล่ (งอ 90 องศา กำปั้นชี้มาข้างหน้า อยู่ระดับเดียวกับศอก)
    "hook_load": {"arms": {"R": ((4, 21), (6, 20), 3), "L": _GUARD["L"]}, "shift": 1, "spread": 12, "tail": 0},
    # ฮุก: บิดสะโพก+ไหล่หมุนกลับ แขนเหวี่ยงเป็นแนวนอนขวางหน้าอก ศอกกับกำปั้นระดับเดียวกัน
    "hook": {"arms": {"R": ((8, 19), (16, 19), 3), "L": ((24, 26), (24, 17), 2)}, "shift": -2, "spread": 12,
             "tail": 1, "speed": [((6, 16), (10, 16)), ((7, 23), (11, 23)), ((20, 15), (22, 14)),
                                  ((20, 23), (22, 24))]},
    "hook_through": {"arms": {"R": ((11, 20), (20, 21), 2), "L": ((24, 26), (23, 17), 2)}, "shift": -2,
                     "spread": 12, "tail": 0},
    # อัปเปอร์คัต: ย่อตัวลงต่ำ กำปั้นซ้ายลดลงข้างสะโพก -> ดันตัวขึ้น กำปั้นพุ่งขึ้นข้างหน้า (ผ่านข้างแก้ม)
    "crouch": {"arms": {"R": ((10, 26), (12, 19), 2), "L": ((25, 25), (23, 26), 2)}, "shift": 1, "drop": 3,
               "spread": 18, "tail": 1},
    "uppercut": {"arms": {"R": ((10, 26), (12, 19), 2), "L": ((25, 22), (24, 14), 3)}, "shift": -1,
                 "spread": 8, "tail": 0,
                 "speed": [((23, 24), (23, 21)), ((26, 25), (26, 22)), ((21, 22), (21, 19))]},
    "uppercut_hold": {"arms": {"R": ((10, 26), (12, 19), 2), "L": ((25, 22), (24, 15), 2)}, "shift": -1,
                      "spread": 8, "tail": 1},
}


def limb(out, points, radius, color):
    """แขนหนาๆ จากจุดต่อจุด (ไหล่ -> ศอก -> กำปั้น) ประทับวงกลมไปตามเส้น ข้อต่อจึงกลมไม่แตก"""
    for a, b in zip(points, points[1:]):
        a, b = pygame.math.Vector2(a), pygame.math.Vector2(b)
        steps = max(1, int(a.distance_to(b) * 2))
        for k in range(steps + 1):
            p = a.lerp(b, k / steps)
            pygame.draw.circle(out, color, (round(p.x), round(p.y)), radius)


def boxer_pose(base, head, band, pose):
    """ท่าหนึ่งของบอสนักมวย: ขาจากชีต (กางได้) + ลำตัวล่ำวาดเอง + หัวที่แต่งหน้าแล้ว + แขนงอศอกได้
    คืน (ภาพ, [(x, y, สี) ที่ต้องทาหลังย้อมสี])  = ผ้าคาดหัว + เส้นความเร็ว"""
    w, h = base.get_size()
    dx, dy = pose.get("shift", 0), pose.get("drop", 0)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    for left, (piece, rect, pivot) in body_parts(base, cut_arms=False)["legs"].items():
        swing(out, piece, rect, pivot, pose.get("spread", 0), left)
    move = lambda p: (p[0] + dx, p[1] + dy)
    torso = [move(p) for p in BOXER_TORSO]
    pygame.draw.polygon(out, SKIN, torso)
    pygame.draw.polygon(out, OUTLINE, torso, 1)
    for p in BOXER_MUSCLE:
        out.set_at(move(p), SHADE)
    out.blit(head, (dx, dy))
    arms = []
    for side in ("R", "L"):
        elbow, fist, size = pose["arms"][side]
        arms.append(([move(BOXER_SHOULDER[side]), move(elbow), move(fist)], size))
    for pts, size in arms:                      # เส้นขอบทั้งสองแขนก่อน แล้วค่อยลงสีผิว: แขนที่ไขว้กันไม่มีเส้นขอบทับกลาง
        limb(out, pts[:2], 3, OUTLINE)          # ต้นแขน (กล้ามใหญ่)
        limb(out, pts[1:], 2, OUTLINE)          # แขนท่อนล่าง
        pygame.draw.circle(out, OUTLINE, pts[2], size + 1)
    for pts, size in arms:
        limb(out, pts[:2], 2, SKIN)
        limb(out, pts[1:], 1, SKIN)
        sx, sy = pts[0]
        out.set_at((sx, sy + 1), SHADE)         # เงากล้ามต้นแขน
    wraps = []
    for pts, size in arms:                      # กำปั้นวาดทับแขนพร้อมเส้นขอบของมันเอง: เห็นชัดแม้อยู่หน้าตัว
        fx, fy = pts[2]
        pygame.draw.circle(out, OUTLINE, (fx, fy), size + 1)
        pygame.draw.circle(out, SKIN, (fx, fy), size)
        # พันมือผ้าขาวแบบเดียวกับผ้าคาดหัว (ทาหลังย้อมสี): กำปั้นไม่กลืนกับแขน/ตัวที่เป็นสีเขียวเหมือนกัน
        wraps += [(x, y, BAND_SHADE if y == fy + size - 1 else BAND)
                  for y in range(fy - size, fy + size + 1) for x in range(fx - size, fx + size + 1)
                  if 0 <= x < w and 0 <= y < h and rgb_of(out, x, y) == SKIN]
    front, tail = band(pose.get("tail", 0))
    paint = [(x + dx, y + dy, color) for x, y, color in front] + wraps
    tail = [(x + dx, y + dy) for x, y in tail if 0 <= x + dx < w and not out.get_at((x + dx, y + dy)).a]
    for x, y in tail:                           # ชายผ้าอยู่หลังหัว: วาดเฉพาะที่ว่าง + เส้นขอบรอบๆ
        out.set_at((x, y), SKIN)
    for x, y in tail:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and not out.get_at((nx, ny)).a:
                out.set_at((nx, ny), OUTLINE)
    paint += [(x, y, BAND) for x, y in tail]
    for (x0, y0), (x1, y1) in pose.get("speed", ()):
        for k in range(4):
            x, y = round(x0 + (x1 - x0) * k / 3) + dx, round(y0 + (y1 - y0) * k / 3) + dy
            if 0 <= x < w and 0 <= y < h and not out.get_at((x, y)).a:
                paint.append((x, y, BAND))      # เส้นความเร็วอยู่นอกตัวเท่านั้น
    return out, paint


def boxer_head(base, style):
    """หัว (+คอ) จากเฟรมยืน แต่งหน้าแล้ว และฟังก์ชันคืนพิกเซลผ้าคาดหัวตามแบบชายผ้า
    แต่งหน้าก่อนต่อตัว: ตอนกำปั้นยกมาใกล้หน้า การหาตาจากพิกเซลจะสับสน"""
    w, h = base.get_size()
    head = base.copy()
    neck = head_top(base) + 11                  # แถวคอ (หัวสูง 11 แถว ในชีตนี้)
    head.fill((0, 0, 0, 0), (0, neck + 1, w, h - neck - 1))
    decorate(head, style)
    top = head_top(head)
    band = []
    for y, color in ((top + 2, BAND), (top + 3, BAND_SHADE)):
        band += [(x, y, color) for x in range(w) if rgb_of(head, x, y) in FACE_COLORS]
    right = max(x for x in range(w) if head.get_at((x, top + 3)).a)

    def with_tail(variant):
        """(พิกเซลผ้าคาดหน้าผาก, พิกเซลชายผ้า)"""
        return band, [(right + ox, top + oy) for ox, oy in BAND_TAILS[variant]]
    return head, with_tail


def build_boxer(style, base, poses):
    head, band = boxer_head(base, style)
    return [boxer_pose(base, head, band, BOXER_POSES[name]) for name in poses]


# ---------- บอสนินจา (kind 5): วาดสีจริงทั้งตัว ----------
N_OUT = (16, 16, 22)            # เส้นขอบ
N_CLOTH = (54, 56, 70)          # ผ้าดำ (ดำสนิทจะมองไม่เห็นรอยพับ จึงอมน้ำเงินเทานิดๆ)
N_SHADE = (37, 38, 50)          # รอยพับ / เงา
N_HI = (88, 92, 112)            # ขอบผ้าที่โดนแสง (สาบเสื้อ ปมเข็มขัด)
K_BLADE = (98, 106, 128)        # ใบมีดคุไน
K_EDGE = (176, 184, 202)        # คมมีดสะท้อนแสง
K_WRAP = (236, 232, 220)        # ด้ามพันผ้าขาว
TRAIL = ((160, 172, 198), (238, 242, 252))      # รอยฟัน: ขอบนอก, แกนกลาง
NINJA_SHOULDER = {"R": (11, 20), "L": (22, 20)}
NINJA_TORSO = [(13, 18), (11, 19), (9, 20), (9, 25), (24, 25), (24, 20), (22, 19), (20, 18)]
NINJA_LEGS = {True: [(9, 26), (16, 26), (16, 29), (15, 30), (11, 30), (8, 28)],     # กางเกงฮากามะ ป่องกลาง
              False: [(17, 26), (24, 26), (25, 28), (22, 30), (18, 30), (17, 29)]}  # รวบแคบที่ข้อเท้า
NINJA_KUNAI_BACK = ((12, 19), (-0.6, -1))      # คุไนเหน็บหลัง: โผล่ด้ามข้างไหล่ขวา (ซ้ายจอ)

# แขนแต่ละข้าง = (ศอก, มือ, ถือคุไน: ทิศใบมีด หรือ None, วาดหลังตัวไหม)
_HANG = {"R": ((10, 24), (10, 27), None, False), "L": ((23, 24), (23, 27), None, False)}
_TRAIL_ARMS = {"R": ((8, 24), (6, 28), None, True), "L": ((25, 24), (27, 28), None, True)}  # วิ่งนินจา: แขนลู่หลัง
_LEG_CYCLE = [(3, 0), (1, 1), (0, 3), (1, 1)]   # วิ่ง: ยกขาซ้าย/ขวาจอสลับกัน (กี่พิกเซล)
_GUARD_L = ((23, 24), (21, 21), None, False)    # มือซ้ายตั้งการ์ดข้างหน้า
NINJA_POSES = {
    "stand": {"arms": _HANG, "kunai_back": True},
    "stand_breath": {"arms": _HANG, "kunai_back": True, "drop": 1},
    # ฟัน: ย่อตัว กางขา มือขวา (ซ้ายจอ) กำคุไนกลับด้าน ใบมีดชี้ลงออกทางนิ้วก้อย (แบบภาพตัวอย่าง)
    "ready": {"arms": {"R": ((10, 25), (13, 22), (-0.45, 1), False), "L": _GUARD_L}, "drop": 1, "spread": 1},
    "wind_r": {"arms": {"R": ((6, 18), (8, 14), (0.5, 1), False), "L": _GUARD_L},
               "drop": 1, "spread": 1, "shift": 1},
    "slash_r": {"arms": {"R": ((12, 23), (17, 24), (1, 0.35), False), "L": ((24, 23), (23, 20), None, False)},
                "drop": 2, "spread": 1, "shift": -1, "trail": [(8, 14), (10, 20), (17, 24), (24, 25)]},
    "follow_r": {"arms": {"R": ((17, 24), (24, 26), (1, -0.2), False), "L": ((24, 23), (23, 19), None, False)},
                 "drop": 2, "spread": 1, "shift": -2, "trail": [(12, 22), (18, 25), (24, 26), (28, 25)]},
    "wind_l": {"arms": {"R": ((18, 21), (23, 17), (0.45, 1), False), "L": ((24, 24), (25, 21), None, False)},
               "drop": 1, "spread": 1, "shift": -2},
    "slash_l": {"arms": {"R": ((17, 21), (14, 23), (-1, 0.35), False), "L": _GUARD_L},
                "drop": 2, "spread": 1, "trail": [(23, 17), (21, 22), (14, 23), (7, 23)]},
    "follow_l": {"arms": {"R": ((12, 22), (7, 24), (-1, -0.2), False), "L": _GUARD_L},
                 "drop": 2, "spread": 1, "shift": 1, "trail": [(20, 22), (13, 24), (7, 24), (3, 22)]},
}
for _i, (_a, _b) in enumerate(_LEG_CYCLE):      # ท่าวิ่ง 4 จังหวะขา x 4 แบบแขน
    _run = {"drop": 2 if _a != _b else 1, "head_drop": 2, "lift": (_a, _b)}   # หัวมุดต่ำ = โน้มตัวไปข้างหน้า
    NINJA_POSES[f"run{_i}"] = dict(_run, arms=_TRAIL_ARMS, kunai_back=True)
    # เอื้อมมือขวาข้ามไหล่ไปจับด้ามคุไนที่หลัง
    NINJA_POSES[f"reach{_i}"] = dict(_run, kunai_back=True, arms={"R": ((6, 17), (9, 15), None, False),
                                                                  "L": _TRAIL_ARMS["L"]})
    # ชักออกมาแล้ว: ชูขึ้นเหนือไหล่ ใบมีดชี้ลง
    NINJA_POSES[f"pull{_i}"] = dict(_run, arms={"R": ((6, 16), (8, 11), (0.35, 1), False), "L": _TRAIL_ARMS["L"]})
    # ถือคุไนวิ่งต่อ แขนลู่หลัง ใบมีดชี้ออกข้าง
    NINJA_POSES[f"armed{_i}"] = dict(_run, arms={"R": ((8, 24), (6, 28), (-1, 0.3), False),
                                                 "L": _TRAIL_ARMS["L"]})


def ninja_head(base):
    """หัวจากเฟรมยืน กลายเป็นฮู้ดผ้าดำ เหลือช่องตาสีผิว คิ้วขมวด (ฮู้ดตกลงกลางหน้าผากเป็นรูป V)"""
    w, h = base.get_size()
    eyes = find_eyes(base)
    top = head_top(base)
    neck = top + 11
    head = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(top, neck + 1):
        xs = [x for x in range(w) if base.get_at((x, y)).a]
        for x in xs:
            border = x in (xs[0], xs[-1]) or y == top or not all(
                base.get_at((x + dx, y + dy)).a for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            c = rgb_of(base, x, y)
            head.set_at((x, y), N_OUT if border else N_SHADE if c == SHADE else N_CLOTH)
    (lx, ly, _), (rx, _, _) = eyes
    for x in range(lx - 2, rx + 3):             # ช่องตา 2 แถว + มุมนอกสูงขึ้นอีกแถว (ฮู้ดตกกลาง = หน้าดุ)
        for y in (ly, ly + 1):
            head.set_at((x, y), SKIN)
        if x <= lx - 1 or x >= rx + 1:
            head.set_at((x, ly - 1), SKIN)
    for x in range(lx - 2, rx + 3):             # ขอบผ้าปิดหน้าใต้ตา
        head.set_at((x, ly + 2), N_HI)
    for x, y in ((lx, ly), (lx, ly + 1), (rx, ly), (rx, ly + 1)):
        head.set_at((x, y), N_OUT)              # ตา
    for x, y in ((lx + 1, ly), (rx - 1, ly)):
        head.set_at((x, y), N_CLOTH)            # ผ้าฮู้ดกดลงที่หัวตา: ตาเฉียงดุ
    for x in range(lx, rx + 1):                 # รอยพับผ้าปิดปาก
        head.set_at((x, ly + 4), N_SHADE)
    return head


def draw_kunai(out, hand, direction, length=6, wrap=1):
    """คุไนถือกลับด้าน: ใบมีดยื่นออกจากใต้กำปั้นตาม direction  ห่วงท้ายด้ามโผล่อีกฝั่งของกำปั้น"""
    V = pygame.math.Vector2
    d = V(direction).normalize()
    h = V(hand)
    tip, base = h + d * length, h + d * 1.5
    pygame.draw.line(out, N_OUT, base, tip, 3)
    pygame.draw.line(out, K_BLADE, base, h + d * (length - 1), 1)
    edge = base + d * 1 + V(-d.y, d.x)
    if 0 <= edge.x < out.get_width() and 0 <= edge.y < out.get_height():
        out.set_at((round(edge.x), round(edge.y)), K_EDGE)
    ring = h - d * (2 + wrap)
    pygame.draw.line(out, N_OUT, h - d * 1, ring, 3)
    pygame.draw.line(out, K_WRAP, h - d * 1, h - d * (1 + wrap), 1)    # ด้ามพันผ้าขาว (ในมือโผล่นิดเดียว)
    r = (round(ring.x), round(ring.y))
    pygame.draw.circle(out, N_OUT, r, 2)
    pygame.draw.circle(out, K_BLADE, r, 1)
    out.set_at(r, N_OUT)                        # รูห่วง


def draw_ninja_leg(out, left, lift, spread):
    """ขากางเกงฮากามะ 1 ข้าง  lift: ยกเข่า (ปลายขาสั้นขึ้น เท้าลอย)  spread: ขยับออกข้าง (ย่อตัวกางขา)"""
    move = -spread if left else spread
    pts = [(x + move, y - (lift * (y - 26) // 4 if y > 26 else 0)) for x, y in NINJA_LEGS[left]]
    pygame.draw.polygon(out, N_CLOTH, pts)
    pygame.draw.polygon(out, N_OUT, pts, 1)
    cx = (pts[0][0] + pts[1][0]) // 2
    for y in range(27, 29 - lift // 2):         # รอยจีบกางเกง
        out.set_at((cx, y), N_SHADE)
    ankle = 30 - lift
    fx0, fx1 = (11 + move, 15 + move) if left else (18 + move, 22 + move)
    for x in range(fx0, fx1 + 1):               # ผ้าพันข้อเท้า + รองเท้าทาบิ
        out.set_at((x, ankle), N_SHADE)
        out.set_at((x, ankle + 1), N_OUT)


def ninja_pose(base, head, pose):
    w, h = base.get_size()
    dx, dy = pose.get("shift", 0), pose.get("drop", 0)
    spread = pose.get("spread", 0)
    move = lambda p: (p[0] + dx, p[1] + dy)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    arms = {side: (move(NINJA_SHOULDER[side]), move(e), move(hd), blade, back)
            for side, (e, hd, blade, back) in pose["arms"].items()}

    def arm(side):
        s, e, hd, blade, _ = arms[side]
        limb(out, [s, e], 2, N_OUT)
        limb(out, [e, hd], 2, N_OUT)
        limb(out, [s, e, hd], 1, N_CLOTH)
        pygame.draw.circle(out, N_OUT, hd, 2)
        pygame.draw.circle(out, SKIN, hd, 1)    # มือ (ถุงมือเปิดนิ้ว เห็นผิว)
        if blade:
            draw_kunai(out, hd, blade)

    if pose.get("kunai_back"):                  # ด้ามคุไนโผล่ข้างไหล่ (ใบมีดซ่อนอยู่หลังตัว) วาดก่อนตัว
        (kx, ky), d = NINJA_KUNAI_BACK
        draw_kunai(out, move((kx + 4 * d[0], ky + 4 * d[1])), (-d[0], -d[1]), 5, wrap=3)
    for side in arms:
        if arms[side][4]:
            arm(side)                           # แขนลู่หลัง: อยู่หลังตัว
    lift = pose.get("lift", (0, 0))
    for left in (True, False):
        draw_ninja_leg(out, left, lift[0 if left else 1], spread)
    torso = [move(p) for p in NINJA_TORSO]
    pygame.draw.polygon(out, N_CLOTH, torso)
    pygame.draw.polygon(out, N_OUT, torso, 1)
    pygame.draw.line(out, N_SHADE, move((12, 19)), move((16, 23)))      # สาบเสื้อขวาทับซ้าย (ป้ายไขว้)
    pygame.draw.line(out, N_HI, move((21, 19)), move((15, 24)))
    for x in range(10, 24):                     # เข็มขัดผ้า
        out.set_at(move((x, 25)), N_SHADE)
    out.set_at(move((16, 25)), N_HI)
    out.set_at(move((17, 25)), N_HI)
    out.blit(head, (dx, dy + pose.get("head_drop", 0)))
    pts = pose.get("trail")
    if pts:                                     # รอยฟันโค้งตามมือ วาดก่อนแขน ให้แขน/มีดอยู่บนรอย
        pts = [move(p) for p in pts]
        curve = [pygame.math.Vector2(p) for p in pts]
        for color, width in zip(TRAIL, (3, 1)):
            for k, (a, b) in enumerate(zip(curve, curve[1:])):
                pygame.draw.line(out, color, a, b, max(1, width - (k == 0)))
    for side in arms:
        if not arms[side][4]:
            arm(side)
    return out, []


# ---------- บอสอัศวิน (kind 6): วาดสีจริงทั้งตัว ----------
# เฟรมกว้าง 48 สูง 40 (ไม่ใช่ 32x32) เผื่อที่ให้ดาบยาวเหวี่ยงออกข้าง/ชูเหนือหัว
# ออกแบบตัวในพิกัด 32x32 แบบบอสอื่น (เท้าแถว 31) แล้วเลื่อนลงกลางเฟรมด้วย KNIGHT_ORIGIN
KNIGHT_SIZE = (48, 40)
KNIGHT_ORIGIN = (8, 8)
KN_OUT = (38, 30, 40)           # เส้นขอบ
KN_ARMOR = (88, 110, 124)       # เกราะเหล็กสีเทาอมฟ้า (แบบภาพตัวอย่าง)
KN_HI = (132, 156, 170)         # ขอบเกราะที่โดนแสง
KN_SHADE = (64, 80, 94)         # เงาเกราะ
KN_SHINE = (228, 236, 236)      # จุดแสงสะท้อนบนหมวก
KN_PLUME = (226, 72, 58)        # ขนนกสีแดงบนหมวก
KN_PLUME_SH = (172, 46, 42)
KN_BLADE = (214, 222, 232)      # ใบดาบ
KN_BLADE_SH = (150, 164, 180)
KN_GOLD = (222, 168, 56)        # โกร่ง + ปุ่มท้ายด้าม
KN_LEATHER = (104, 66, 46)      # เข็มขัด + ฝักดาบ
KN_LEATHER_SH = (74, 46, 34)
KN_TRAIL = ((168, 190, 214), (244, 248, 255))
KNIGHT_SHOULDER = {"R": (9, 18), "L": (23, 18)}
KNIGHT_HILT_SHEATHED = (21, 23)                # ด้ามดาบที่เหน็บอยู่สะโพกซ้ายของอัศวิน (ขวาจอ)
KNIGHT_SHEATH = ((22, 24), (27, 31))           # ฝักดาบห้อยเฉียงลงไปข้างหลัง

_KN_IDLE_ARMS = {"R": (8, 26), "L": (24, 26)}    # มือ: ห้อยข้างตัว
# ท่าทั้งหมด: hands = จุดมือข้างขวา/ซ้ายของอัศวิน ("both" = สองมือกำด้ามเดียวกัน)
#   sword = (จุดมือที่กำด้าม, ทิศใบดาบ, ความยาวที่เห็น) หรือ "sheathed"   trail = รอยฟัน   lift = ยกขาเดิน
KNIGHT_POSES = {
    "sheathed": {"hands": _KN_IDLE_ARMS, "sword": "sheathed", "plume": 0},
    "sheathed_breath": {"hands": _KN_IDLE_ARMS, "sword": "sheathed", "drop": 1, "plume": 1},
    # ชักดาบ: มือขวาข้ามตัวไปจับด้ามที่สะโพกซ้าย -> ดึงขึ้นเฉียง -> ชูดาบขึ้นข้างตัว -> ตั้งท่า
    "reach": {"hands": {"R": (20, 23), "L": (24, 26)}, "sword": "sheathed", "plume": 1},
    "draw": {"hands": {"R": (15, 19), "L": (24, 26)}, "sword": ((15, 19), (0.8, 0.9), 9), "sheath_empty": True,
             "plume": 0},
    "draw_out": {"hands": {"R": (7, 15), "L": (24, 25)}, "sword": ((7, 15), (0.25, -1), 12), "sheath_empty": True,
                 "trail": [(20, 24), (13, 22), (8, 18), (6, 13)], "plume": 1},
    # ตั้งท่าเตรียมฟัน (แบบภาพที่ 2): สองมือกำด้ามหน้าอกด้านขวาของตัว ดาบตั้งตรงชี้ฟ้า
    "stance": {"hands": "both", "sword": ((12, 21), (0.12, -1), 13), "sheath_empty": True, "spread": 1, "plume": 0},
    "stance2": {"hands": "both", "sword": ((12, 21), (0.12, -1), 13), "sheath_empty": True, "spread": 1, "drop": 1,
                "plume": 1},
    # คอมโบ 1: ง้างไปซ้ายจอสุด -> กวาดแนวนอนกว้างจากซ้ายไปขวา
    "wide_load": {"hands": "both", "sword": ((7, 21), (-1, -0.2), 12), "sheath_empty": True, "spread": 2,
                  "shift": 1, "plume": 1},
    "wide_swing": {"hands": "both", "sword": ((17, 22), (1, 0.12), 12), "sheath_empty": True, "spread": 2,
                   "shift": -1, "plume": 0, "trail": [(-4, 19), (4, 24), (16, 26), (28, 24)]},
    "wide_follow": {"hands": "both", "sword": ((24, 21), (1, -0.35), 11), "sheath_empty": True, "spread": 2,
                    "shift": -2, "plume": 1, "trail": [(8, 25), (20, 26), (32, 22), (37, 16)]},
    # คอมโบ 2: ลดดาบลงต่ำซ้ายล่าง -> ฟันเฉียงขึ้นไปขวาบน
    "diag_load": {"hands": "both", "sword": ((9, 26), (-0.75, 0.65), 10), "sheath_empty": True, "spread": 2,
                  "drop": 1, "shift": 1, "plume": 0},
    "diag_slash": {"hands": "both", "sword": ((22, 15), (0.7, -0.75), 13), "sheath_empty": True, "spread": 2,
                   "shift": -1, "plume": 1, "trail": [(0, 33), (8, 28), (17, 19), (26, 10), (32, 3)]},
    # คอมโบ 3: ชูดาบเหนือหัว -> ฟันตรงลงพื้น
    "over_load": {"hands": "both", "sword": ((16, 2), (0.05, -1), 9), "sheath_empty": True, "spread": 1,
                  "plume": 0, "elbow_out": 6},     # ศอกกางออกข้างหัว: แขนไม่บังหมวก
    "down_slash": {"hands": "both", "sword": ((16, 23), (0, 1), 10), "sheath_empty": True, "spread": 3,
                   "drop": 2, "plume": 1, "trail": [(16, 15), (16, 24), (16, 33)]},
    "down_hold": {"hands": "both", "sword": ((16, 24), (0, 1), 9), "sheath_empty": True, "spread": 3,
                  "drop": 2, "plume": 0},
}
for _i, (_a, _b) in enumerate(_LEG_CYCLE):      # เดินเข้าหาโดยตั้งท่าถือดาบไว้ (ยกขาสลับ)
    KNIGHT_POSES[f"advance{_i}"] = dict(KNIGHT_POSES["stance"], lift=(_a, _b), drop=0 if _a != _b else 1,
                                        plume=_i % 2)


def draw_sword(out, hand, direction, length, two_hands):
    """ดาบยาว: ใบดาบ (ขอบเข้ม + ใบสว่าง + สันเงา), โกร่งสีทองตั้งฉาก, ด้าม, ปุ่มท้ายด้าม"""
    V = pygame.math.Vector2
    d = V(direction).normalize()
    n = V(-d.y, d.x)
    h = V(hand)
    base, tip = h + d * 2, h + d * length
    pygame.draw.line(out, KN_OUT, base, tip, 4)
    pygame.draw.line(out, KN_BLADE, base, h + d * (length - 1), 2)
    pygame.draw.line(out, KN_BLADE_SH, base + n * 0.6, h + d * (length - 2) + n * 0.6, 1)
    for k in (-2, 2):                           # โกร่ง
        pygame.draw.line(out, KN_OUT, h + d * 1.5, h + d * 1.5 + n * k, 3)
    pygame.draw.line(out, KN_GOLD, h + d * 1.5 - n * 2, h + d * 1.5 + n * 2, 1)
    end = h - d * (3 if two_hands else 2)       # สองมือ: ด้ามยาวกว่า
    pygame.draw.line(out, KN_OUT, h, end, 3)
    pygame.draw.line(out, KN_LEATHER, h, end, 1)
    pygame.draw.circle(out, KN_OUT, (round(end.x), round(end.y)), 2)
    pygame.draw.circle(out, KN_GOLD, (round(end.x), round(end.y)), 1)


def knight_pose(pose):
    W, H = KNIGHT_SIZE
    ox, oy = KNIGHT_ORIGIN
    dx, dy = pose.get("shift", 0), pose.get("drop", 0)
    spread = pose.get("spread", 0)
    out = pygame.Surface((W, H), pygame.SRCALPHA)
    up = lambda p: (p[0] + ox + dx, p[1] + oy + dy)       # ท่อนบน (ขยับตาม shift/drop)
    at = lambda p: (p[0] + ox, p[1] + oy)                 # ส่วนที่ติดพื้น

    def blob(points, fill, outline=KN_OUT):
        pygame.draw.polygon(out, fill, points)
        pygame.draw.polygon(out, outline, points, 1)

    # ---- ขา (เกราะขา + สนับเข่า + รองเท้าเหล็ก) ----
    lift = pose.get("lift", (0, 0))
    for left in (True, False):
        s = -spread if left else spread
        x0 = (12 if left else 17) + s
        top, foot = 25, 31 - lift[0 if left else 1]
        blob([at((x0, top)), at((x0 + 3, top)), at((x0 + 3, foot - 1)), at((x0, foot - 1))], KN_ARMOR)
        knee = (top + foot) // 2
        blob([at((x0 - 1, knee - 1)), at((x0 + 4, knee - 1)), at((x0 + 4, knee + 1)), at((x0 - 1, knee + 1))], KN_HI)
        fx = x0 - 1 if left else x0
        blob([at((fx, foot - 1)), at((fx + 4, foot - 1)), at((fx + 4, foot)), at((fx, foot))], KN_SHADE)
    # ---- ฝักดาบ (ห้อยสะโพกซ้ายของอัศวิน = ขวาจอ) อยู่หลังขา/ตัว ----
    (sx0, sy0), (sx1, sy1) = KNIGHT_SHEATH
    pygame.draw.line(out, KN_OUT, up((sx0, sy0)), up((sx1, sy1)), 4)
    pygame.draw.line(out, KN_LEATHER, up((sx0, sy0)), up((sx1 - 1, sy1 - 1)), 2)
    out.set_at(up((sx1 - 1, sy1 - 1)), KN_GOLD)
    # ---- ลำตัว: เกราะอก + กระโปรงเกราะ + เข็มขัด ----
    blob([up(p) for p in [(11, 23), (21, 23), (22, 26), (10, 26)]], KN_SHADE)                  # กระโปรงเกราะ
    blob([up(p) for p in [(12, 16), (20, 16), (23, 18), (22, 23), (10, 23), (9, 18)]], KN_ARMOR)  # เกราะอก
    pygame.draw.line(out, KN_HI, up((12, 18)), up((15, 21)))                                    # สันเกราะอก
    pygame.draw.line(out, KN_HI, up((20, 18)), up((17, 21)))
    pygame.draw.line(out, KN_LEATHER, up((10, 23)), up((22, 23)))                              # เข็มขัด
    out.set_at(up((16, 23)), KN_GOLD)
    # ---- หมวกเหล็ก: ทรงกลมใหญ่ ช่องมองรูปตัว T จุดแสงสะท้อน ขนนกแดง ----
    helm = [(13, 5), (19, 5), (21, 7), (22, 10), (22, 15), (10, 15), (10, 10), (11, 7)]
    plume = [[(20, 6), (22, 3), (25, 1), (26, 2), (24, 5), (22, 8)],
             [(20, 6), (23, 2), (26, 1), (27, 3), (24, 6), (22, 8)]][pose.get("plume", 0)]
    blob([up(p) for p in plume], KN_PLUME)
    pygame.draw.line(out, KN_PLUME_SH, up((21, 7)), up(plume[3]))
    blob([up(p) for p in helm], KN_ARMOR)
    pygame.draw.line(out, KN_OUT, up((12, 10)), up((20, 10)))                                  # ช่องมองแนวนอน
    pygame.draw.line(out, KN_OUT, up((12, 11)), up((20, 11)))
    pygame.draw.line(out, KN_OUT, up((15, 12)), up((15, 14)))                                  # ช่องหายใจแนวตั้ง
    pygame.draw.line(out, KN_OUT, up((17, 12)), up((17, 14)))
    out.set_at(up((16, 12)), KN_OUT)
    pygame.draw.line(out, KN_HI, up((11, 9)), up((21, 9)))                                     # ขอบหมวกเหนือช่องมอง
    for p in ((18, 7), (19, 7), (19, 8)):
        out.set_at(up(p), KN_SHINE)
    # ---- ดาบ ----
    sword = pose["sword"]
    if sword == "sheathed":                     # เหน็บอยู่: เห็นแค่ด้าม + โกร่งที่สะโพก
        draw_sword(out, up(KNIGHT_HILT_SHEATHED), (0.55, 0.8), 2, False)
    # ---- แขน (เกราะแขน + ถุงมือเหล็ก) ----
    hands = pose["hands"]
    if hands == "both":                         # สองมือกำด้ามเดียวกัน: มือซ้ายอยู่ต่ำกว่ามือขวาบนด้าม
        (hx, hy), d = sword[0], pygame.math.Vector2(sword[1]).normalize()
        hands = {"R": (hx, hy), "L": (hx - d.x * 2, hy - d.y * 2)}
    V = pygame.math.Vector2
    for side in ("R", "L"):
        sh, hd = V(up(KNIGHT_SHOULDER[side])), V(up(hands[side]))
        outward = -1 if side == "R" else 1
        elbow = (sh + hd) / 2 + V(outward * pose.get("elbow_out", 2), 1)
        limb(out, [sh, elbow, hd], 2, KN_OUT)
        limb(out, [sh, elbow, hd], 1, KN_ARMOR)
        pygame.draw.circle(out, KN_OUT, (round(sh.x), round(sh.y)), 3)     # เกราะไหล่ทรงกลมใหญ่
        pygame.draw.circle(out, KN_HI, (round(sh.x), round(sh.y)), 2)
        pygame.draw.circle(out, KN_OUT, (round(hd.x), round(hd.y)), 2)     # ถุงมือเหล็ก
        pygame.draw.circle(out, KN_SHADE, (round(hd.x), round(hd.y)), 1)
    if pose.get("trail"):                       # รอยดาบ (อยู่ใต้ดาบ ทับตัว)
        pts = [V(up(p)) for p in pose["trail"]]
        for color, width in zip(KN_TRAIL, (4, 2)):
            for a, b in zip(pts, pts[1:]):
                pygame.draw.line(out, color, a, b, width)
    if sword != "sheathed":
        hand, d, length = sword
        draw_sword(out, up(hand), d, length, pose["hands"] == "both")
        R = V(up(hands["R"]))                   # มือทับด้ามดาบ (กำอยู่)
        pygame.draw.circle(out, KN_OUT, (round(R.x), round(R.y)), 2)
        pygame.draw.circle(out, KN_SHADE, (round(R.x), round(R.y)), 1)
    return out, []


# ---------- บอสซามูไร (kind 7): วาดสีจริง เฟรม 48x40 แบบอัศวิน ----------
SA_OUT = (40, 30, 34)
SA_KIMONO = (214, 124, 114)     # กิโมโนแดงซีด
SA_KIMONO_SH = (172, 90, 86)
SA_HAKAMA = (196, 198, 206)     # ฮากามะเทาอ่อน
SA_HAKAMA_SH = (150, 152, 164)
SA_HAT = (218, 184, 116)        # หมวกสานฟาง
SA_HAT_SH = (170, 136, 78)
SA_SHADOW = (44, 34, 38)        # เงาใต้หมวกที่บังหน้า
SA_SKIN = (204, 160, 128)       # ผิวที่โดนเงาหมวก (คาง/อก)
SA_OBI = (66, 52, 64)           # ผ้าคาดเอว
SA_GETA = (150, 104, 62)        # เกี๊ยะไม้
SA_SAYA = (34, 30, 40)          # ฝักดาบเคลือบดำ
SA_SAYA_HI = (86, 80, 100)
SA_TSUKA = (30, 26, 34)         # ด้ามพันเชือก
SA_TSUKA_HI = (210, 200, 180)   # ลายข้าวหลามตัดบนด้าม
SA_TSUBA = (196, 152, 60)       # กระบังดาบ
SA_BLADE = (226, 232, 240)
SA_BLADE_SH = (156, 168, 184)
SA_SHINE = ((255, 255, 255), (255, 244, 180))   # ประกายบนใบดาบ: กลาง, แฉก
SA_TRAIL = ((176, 196, 222), (248, 250, 255))
SAMURAI_SHOULDER = {"R": (11, 17), "L": (21, 17)}
SAMURAI_SAYA = ((11, 23), (3, 30))              # ฝักดาบที่สะโพกขวาของซามูไร (ซ้ายจอ) ปากฝัก -> ปลายฝัก

_SA_REST = {"R": (9, 25), "L": (23, 25)}
SAMURAI_POSES = {
    # นั่งคุกเข่า (เซซะ) มือวางบนต้นขา
    "seiza": {"seated": True, "hands": {"R": (11, 23), "L": (21, 23)}, "sword": "sheathed"},
    "seiza_breath": {"seated": True, "hands": {"R": (11, 22), "L": (21, 22)}, "sword": "sheathed", "drop": 1},
    "rise": {"half": True, "hands": {"R": (11, 26), "L": (21, 26)}, "sword": "sheathed"},
    "stand": {"hands": _SA_REST, "sword": "sheathed"},
    # ชักดาบแบบดั้งเดิม (อิไอ): มือซ้ายข้ามตัวไปจับด้ามที่สะโพกขวา มือขวาจับฝัก -> ดึงออกแนวนอน -> ฟันกวาดออก
    "grip": {"hands": {"R": (10, 24), "L": (13, 21)}, "sword": "sheathed", "lean": 1},
    "draw_half": {"hands": {"R": (10, 24), "L": (19, 20)}, "sword": ((19, 20), (-1, 0.15), 9), "lean": 1},
    "draw_flash": {"hands": {"R": (10, 24), "L": (28, 19)}, "sword": ((28, 19), (1, -0.1), 13), "shift": -1,
                   "trail": [(4, 23), (12, 21), (22, 19), (36, 17)], "shine": [(38, 17)]},
    "raise": {"hands": "both", "sword": ((17, 18), (0.3, -1), 12), "shine": [(20, 7)]},
    "stance": {"hands": "both", "sword": ((16, 23), (0.15, -1), 13), "shine": [(18, 11)]},
    "stance_glint": {"hands": "both", "sword": ((16, 23), (0.15, -1), 13), "shine": [(17, 15)]},
    "stance_still": {"hands": "both", "sword": ((16, 23), (0.15, -1), 13)},
}
for _i, (_a, _b) in enumerate(_LEG_CYCLE):      # เดินเกี๊ยะเข้าหาโดยตั้งท่าถือดาบ
    SAMURAI_POSES[f"walk{_i}"] = dict(SAMURAI_POSES["stance_still"], lift=(_a, _b))


def _samurai_cuts():
    """ท่าฟันรัว: สุ่มฟันแนวทแยง / แนวตั้ง / แนวนอน (8 ทิศ ทีละ 45 องศา) ต่อกันลื่นๆ
    ฟันแต่ละครั้ง: มือเลื่อนผ่านกลางตัวจากฝั่งหนึ่งไปอีกฝั่งตามแนวฟัน ดาบหมุนจากง้างไปข้างหลังจนชี้ไปทางที่ฟัน
      รอยฟัน = เส้นตรงตามแนวฟัน (เห็นชัดว่าทแยง/ตั้ง/นอน) + เส้นโค้งตามปลายดาบ
    ต่อกันลื่น: ฟันถัดไปเริ่มจากฝั่งที่ฟันก่อนจบ (กลับทาง ±45 องศา จึงเปลี่ยนแนวได้แบบสุ่ม)
    seed คงที่ ได้ท่าเดิมทุกครั้ง และฟันสุดท้ายต่อเข้าฟันแรกพอดี (วนลูปไม่สะดุด)"""
    V = pygame.math.Vector2
    center = V(16, 21)
    rng = random.Random(77)
    while True:                                 # สุ่มจนได้ชุดที่ฟันสุดท้ายต่อเข้าฟันแรกได้
        angles = [rng.randrange(8) * 45]
        for _ in range(SAMURAI_CUTS - 1):
            angles.append((angles[-1] + 180 + rng.choice((-45, 0, 45))) % 360)
        back = (angles[0] + 180 - angles[-1]) % 360          # ฟันแรกต้องเริ่มจากฝั่งที่ฟันสุดท้ายจบ
        kinds = {a % 180 for a in angles}
        if back in (0, 45, 315) and len(kinds) == 4:         # ครบทั้งนอน ตั้ง ทแยงสองแบบ
            break
    ease = lambda t: t * t * (3 - 2 * t)

    def cutline(d, upto):
        return [tuple(center - d * 15), tuple(center + d * (-15 + 30 * upto))]

    n = 0
    prev_line = cutline(V(1, 0).rotate(angles[-1]), 1)
    for k, a in enumerate(angles):
        d = V(1, 0).rotate(a)
        spin = rng.choice((-1, 1))              # ดาบหมุนผ่านด้านไหน (สุ่ม)
        tip = lambda e: center + d * (-6 + 12 * e) + V(1, 0).rotate(a + 180 * (1 - e) * spin) * 12
        for step in range(1, SAMURAI_STEPS + 1):
            e = ease(step / SAMURAI_STEPS)
            hand = center + d * (-6 + 12 * e)
            blade = V(1, 0).rotate(a + 180 * (1 - e) * spin)
            cut = {"hands": "both", "sword": ((round(hand.x), round(hand.y)), (blade.x, blade.y), 12),
                   "trail": [tuple(tip(e * j / 6)) for j in range(7)],
                   "cutline": cutline(d, e), "old_trail": prev_line, "shift": round(d.x), "spread": 1}
            if step == SAMURAI_STEPS and k % 3 == 0:
                cut["shine"] = [tuple(center + d * 14)]
            SAMURAI_POSES[f"cut{n}"] = cut
            n += 1
        prev_line = cutline(d, 1)


_samurai_cuts()


def draw_katana(out, hand, direction, length):
    """คาตานะ: ใบดาบเรียว + กระบังกลมสีทอง + ด้ามดำลายข้าวหลามตัด (สองมือจับ ด้ามยาว)"""
    V = pygame.math.Vector2
    d = V(direction).normalize()
    h = V(hand)
    base, tip = h + d * 2, h + d * length
    pygame.draw.line(out, SA_OUT, base, tip, 3)
    pygame.draw.line(out, SA_BLADE, base, h + d * (length - 1), 1)
    t = h + d * 1.5
    pygame.draw.circle(out, SA_OUT, (round(t.x), round(t.y)), 2)
    pygame.draw.circle(out, SA_TSUBA, (round(t.x), round(t.y)), 1)
    end = h - d * 4
    pygame.draw.line(out, SA_OUT, h + d, end, 3)
    pygame.draw.line(out, SA_TSUKA, h + d, end, 1)
    for k in (1, 3):
        p = h - d * k
        if 0 <= p.x < out.get_width() and 0 <= p.y < out.get_height():
            out.set_at((round(p.x), round(p.y)), SA_TSUKA_HI)


def draw_shine(out, point):
    """ประกาย 4 แฉกบนใบดาบ"""
    x, y = round(point[0]), round(point[1])
    w, h = out.get_size()
    for k, color in ((0, SA_SHINE[0]), (1, SA_SHINE[1]), (2, SA_SHINE[1])):
        for px, py in ((x + k, y), (x - k, y), (x, y + k), (x, y - k)):
            if 0 <= px < w and 0 <= py < h:
                out.set_at((px, py), color)
    for px, py in ((x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1)):
        if 0 <= px < w and 0 <= py < h:
            out.set_at((px, py), SA_SHINE[1])


def samurai_pose(pose):
    W, H = KNIGHT_SIZE
    ox, oy = KNIGHT_ORIGIN
    seated, half = pose.get("seated"), pose.get("half")
    sink = 5 if seated else 3 if half else 0             # นั่ง: ท่อนบนลดลง
    dx, dy = pose.get("shift", 0), pose.get("drop", 0) + sink
    spread = pose.get("spread", 0)
    out = pygame.Surface((W, H), pygame.SRCALPHA)
    up = lambda p: (p[0] + ox + dx, p[1] + oy + dy)
    at = lambda p: (p[0] + ox, p[1] + oy)
    V = pygame.math.Vector2

    def blob(points, fill):
        pygame.draw.polygon(out, fill, points)
        pygame.draw.polygon(out, SA_OUT, points, 1)

    # ---- ฝักดาบ (ซ้ายจอ) อยู่หลังตัว ----
    (s0, s1) = SAMURAI_SAYA
    pygame.draw.line(out, SA_OUT, up(s0), up(s1), 4)
    pygame.draw.line(out, SA_SAYA, up(s0), up(s1), 2)
    pygame.draw.line(out, SA_SAYA_HI, up((s0[0] - 1, s0[1] + 1)), up((s0[0] - 4, s0[1] + 4)))
    # ---- ฮากามะ + เกี๊ยะ ----
    if seated:
        pass                                    # ฮากามะตอนนั่งวาดทีหลังลำตัว (เข่าอยู่หน้าตัว)
    else:
        lift = pose.get("lift", (0, 0))
        top = 23 + (3 if half else 0)
        for left in (True, False):
            s = -spread if left else spread
            l = lift[0 if left else 1]
            foot = 29 - l
            x0, x1 = ((11, 16) if left else (16, 21))           # ฮากามะแคบลง ทรงตรง
            pts = [(x0 + s, top), (x1 + s, top), (x1 + s, foot), (x0 + s, foot)]
            blob([at(p) for p in pts], SA_HAKAMA)
            pygame.draw.line(out, SA_HAKAMA_SH, at(((x0 + x1) // 2 + s, top + 2)), at(((x0 + x1) // 2 + s, foot - 1)))
            gx = (11 if left else 18) + s
            for x in range(gx, gx + 4):                      # เท้า + สายเกี๊ยะ + ไม้เกี๊ยะ
                out.set_at(at((x, foot + 1)), SA_SKIN if x not in (gx + 1, gx + 2) else SA_OUT)
                out.set_at(at((x, foot + 2)), SA_GETA)
            out.set_at(at((gx, foot + 2)), SA_OUT)
            out.set_at(at((gx + 3, foot + 2)), SA_OUT)
    # ---- ลำตัว: กิโมโนคอวี เห็นอกนิดๆ + ผ้าคาดเอว ----
    blob([up(p) for p in [(13, 15), (19, 15), (21, 17), (20, 23), (12, 23), (11, 17)]], SA_KIMONO)
    pygame.draw.polygon(out, SA_SKIN, [up((15, 15)), up((17, 15)), up((16, 18))])
    pygame.draw.line(out, SA_KIMONO_SH, up((14, 15)), up((16, 19)))
    pygame.draw.line(out, SA_KIMONO_SH, up((18, 15)), up((16, 19)))
    pygame.draw.line(out, SA_KIMONO_SH, up((16, 19)), up((16, 22)))
    for x in range(12, 21):
        out.set_at(up((x, 22)), SA_OBI)
        out.set_at(up((x, 23)), SA_OBI)
    # ---- ดาบในฝัก: ด้ามโผล่ที่ปากฝัก ชี้ขึ้นมาข้างหน้า ----
    if pose["sword"] == "sheathed":
        draw_katana(out, up((s0[0] + 2, s0[1] - 2)), (-0.8, 0.7), 2)
    # ---- หัว: หมวกฟางทรงกรวยปีกกว้าง หน้าอยู่ในเงา เห็นแค่คาง ----
    lean = pose.get("lean", 0)
    hu = lambda p: up((p[0], p[1] + lean))
    blob([hu(p) for p in [(14, 10), (18, 10), (19, 14), (13, 14)]], SA_SHADOW)    # หน้าในเงา
    pygame.draw.line(out, SA_SKIN, hu((14, 14)), hu((18, 14)))                     # คาง
    out.set_at(hu((16, 14)), SA_SHADOW)
    hat = [(16, 2), (20, 5), (25, 9), (25, 10), (7, 10), (7, 9), (12, 5)]
    blob([hu(p) for p in hat], SA_HAT)
    for (a, b) in (((13, 6), (19, 6)), ((10, 8), (22, 8))):                       # ลายสาน
        pygame.draw.line(out, SA_HAT_SH, hu(a), hu(b))
    pygame.draw.line(out, SA_HAT_SH, hu((8, 10)), hu((24, 10)))
    out.set_at(hu((16, 3)), SA_HAT_SH)
    # ---- แขน: แขนเสื้อกิโมโนกว้างห้อย ----
    hands = pose["hands"]
    sword = pose["sword"]
    if hands == "both":
        (hx, hy), d = sword[0], V(sword[1]).normalize()
        hands = {"L": (hx, hy), "R": (hx - d.x * 3, hy - d.y * 3)}
    arms = {}
    for side in ("R", "L"):
        sh, hd = V(up(SAMURAI_SHOULDER[side])), V(up(hands[side]))
        out_dir = -1 if side == "R" else 1
        elbow = (sh + hd) / 2 + V(out_dir * 2, 1)
        arms[side] = (sh, elbow, hd)
    for side, (sh, elbow, hd) in arms.items():
        drape = elbow + V(0, 2)                 # แขนเสื้อห้อยใต้ศอกนิดหน่อย
        pygame.draw.circle(out, SA_OUT, (round(drape.x), round(drape.y)), 2)
        pygame.draw.circle(out, SA_KIMONO_SH, (round(drape.x), round(drape.y)), 1)
        limb(out, [sh, elbow, hd], 2, SA_OUT)
    for side, (sh, elbow, hd) in arms.items():
        limb(out, [sh, elbow, hd], 1, SA_KIMONO)
    if seated:                                  # คุกเข่า: ฮากามะแผ่เป็นฐานกว้าง เข่าอยู่หน้าแขนเสื้อ มือวางบนเข่า
        blob([at(p) for p in [(11, 25), (21, 25), (24, 29), (24, 31), (8, 31), (8, 29)]], SA_HAKAMA)
        pygame.draw.line(out, SA_HAKAMA_SH, at((16, 26)), at((16, 31)))
        for x in (11, 21):
            pygame.draw.line(out, SA_HAKAMA_SH, at((x, 28)), at((x, 30)))
        for x in range(12, 21):                 # ผ้าคาดเอวเหนือฮากามะ
            out.set_at(at((x, 25)), SA_OBI)
    if pose.get("old_trail"):                   # รอยฟันท่าก่อน (จาง) = ฟันมาแล้วหลายทาง
        pts = [V(up(p)) for p in pose["old_trail"]]
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(out, SA_TRAIL[0], a, b, 1)
    if pose.get("trail"):                       # เส้นโค้งตามปลายดาบ (บางๆ)
        pts = [V(up(p)) for p in pose["trail"]]
        for a, b in zip(pts, pts[1:]):
            pygame.draw.line(out, SA_TRAIL[0], a, b, 1)
    if pose.get("cutline"):                     # แนวฟันตรง: ทแยง / ตั้ง / นอน
        a, b = (V(up(p)) for p in pose["cutline"])
        for color, width in zip(SA_TRAIL, (3, 1)):
            pygame.draw.line(out, color, a, b, width)
    if sword != "sheathed":
        hand, d, length = sword
        draw_katana(out, up(hand), d, length)
    for side, (sh, elbow, hd) in arms.items():  # มือ (ทับด้าม)
        pygame.draw.circle(out, SA_OUT, (round(hd.x), round(hd.y)), 2)
        pygame.draw.circle(out, SA_SKIN, (round(hd.x), round(hd.y)), 1)
    for p in pose.get("shine", ()):
        draw_shine(out, up(p))
    return out, []


def build_frames(style, sheet, row, spec=None):
    """เฟรมท่าที่ไม่มีในชีต สร้างจากเฟรมแรกของ (sheet, row) ตาม spec (ไม่ใส่ = style["build"])
    kind "boxer" คืน [(ภาพที่แต่งหน้าแล้ว, พิกเซลที่ต้องทาหลังย้อมสี), ...]  แบบอื่นคืนภาพเปล่า"""
    spec = spec or style["build"]
    base = sprites.frames(sheet, row)[0]
    if spec["kind"] == "boxer":
        return build_boxer(style, base, spec["poses"])
    if spec["kind"] == "samurai":
        return [samurai_pose(SAMURAI_POSES[name]) for name in spec["poses"]]
    if spec["kind"] == "knight":
        return [knight_pose(KNIGHT_POSES[name]) for name in spec["poses"]]
    if spec["kind"] == "ninja":
        head = ninja_head(base)
        return [ninja_pose(base, head, NINJA_POSES[name]) for name in spec["poses"]]
    if spec["kind"] == "leg_stomp":
        return [leg_pose(base, spec["leg"], *pose) for pose in spec["poses"]]
    if spec["kind"] == "barrage":
        made = [stance_pose(base, **pose) if isinstance(pose, dict) else stance_pose(base, *pose)
                for pose in spec["poses"]]
        FISTS[style["name"]] = [fist for _, fist in made]     # จุดกำปั้นที่ต่อย ให้ draw_overlay ต่อรอยหมัด
        return [frame for frame, _ in made]
    raise ValueError(f"unknown build kind: {spec['kind']!r}")


def boss_frames(kind, part):
    """เฟรมของบอส kind ท่า part ("idle"/"attack"/"run") ที่แต่งแล้ว เก็บไว้ใช้ซ้ำ (ต้องเรียกหลังเปิดหน้าต่าง)"""
    key = (kind, part)
    if key not in _frames:
        style = STYLES[kind]
        sheet, row = style.get(part, style["idle"])
        out = []
        spec = style.get("build" if part == "attack" else part + "_build")
        for src in (build_frames(style, sheet, row, spec) if spec else sprites.frames(sheet, row)):
            if isinstance(src, tuple):             # แต่งหน้ามาแล้วตอนสร้าง
                frame, paint = src[0].copy(), src[1]
            else:
                frame = src.copy()                 # sprites.frames แชร์ภาพกับศัตรู ห้ามแก้ตัวจริง
                paint = decorate(frame, style)
            if not style.get("colored"):           # colored = วาดสีจริงมาแล้ว ไม่ต้องย้อม
                frame = pygame.transform.grayscale(frame)
                frame.fill((*style["tint"], 255), special_flags=pygame.BLEND_RGBA_MULT)
            for x, y, color in paint:
                frame.set_at((x, y), color)
            out.append(frame)
        _frames[key] = out
    return _frames[key]


class Boss(EnemyGroup):
    can_rush = False     # บอสยืนรอหลังเส้นชัย แล้วเดินเข้าหาเองตอนเริ่มปะทะ (ดู on_reach)

    def __init__(self, z, count, kind=1):
        """z = ขอบหลังแถบเส้นชัย: เริ่มปะทะเมื่อคนท้ายสุดข้ามตรงนี้ (main.py เช็ก)
        ตัวบอสยืนรอไกลออกไปที่ stand_z แล้วเดินเข้ามาหาคนแถวหน้าตอนเริ่มปะทะ"""
        super().__init__(z, count)
        self.kind = kind
        self.style = STYLES[kind]
        self.name = self.style["name"]   # main.py ใช้บอกสาเหตุที่แพ้
        self.attack_t = 0.0
        self.frame_i = 0
        self.impact = False              # True เฉพาะเฟรมที่หมัดลงพื้น (main.py สั่นกล้อง + เล่นเสียง)
        self.chip_color = self.style["tint"]           # main.py: สีเศษที่กระเด็นจากตัวบอส
        self.stand_z = z + self.style.get("stand", C.BOSS_STAND)  # ตำแหน่งตัวบอสตอนนี้
        self.approaching = False         # บอสที่วิ่งเข้าหา (run_speed): ยังไม่เริ่มหักจำนวนจนกว่าจะถึง
        self.run_from = self.stand_z
        self.run_t = 0.0
        self.target_z = self.stand_z     # เดินไปหยุดตรงนี้
        strength = self.style.get("impact_strength", 1.0)
        self.impact_strength = 1.0 if isinstance(strength, dict) else strength   # main.py: แรงสั่นกล้องต่อครั้ง
        self.placed = None               # ตำแหน่งที่วาดตัวบอสเฟรมนี้ (draw_overlay ใช้ต่อรอยหมัดจากไหล่)
        self.shoulders = None
        self.layer = None

    @property
    def contact_z(self):
        """main.py: ประกายหมัดเกิดตรงนี้ (กลางระหว่างคนแถวหน้ากับบอส)"""
        front = self.crowd.front_z() if self.crowd else self.stand_z - C.BOSS_GAP
        return (front + self.stand_z) / 2

    def on_reach(self, crowd):
        super().on_reach(crowd)
        # บอสปะทะนานกว่าศัตรูธรรมดา จะได้เห็นท่าต่อยหลายหมัด
        self.rate = max(C.FIGHT_MIN_RATE, min(self.count, crowd.count) / C.BOSS_FIGHT_TIME)
        # ก้อนคนเล็กหยุดห่างบอสมาก ก้อนใหญ่หยุดใกล้: บอสเดินเข้ามาหยุดตรงหน้าคนแถวแรกเสมอ
        self.target_z = crowd.front_z() + self.style.get("gap", C.BOSS_GAP)
        if "run_speed" in self.style:    # ยืนรอไกลๆ แล้ววิ่งเข้ามา: fighting = True (หยุดวิ่ง) แต่ยังไม่ตีกัน
            self.approaching = True
            self.run_from = self.stand_z
            # intro: เล่นท่าเปิดตัวจนจบก่อน (เช่น ชักดาบ ตั้งท่า) ยืนอยู่กับที่ แล้วค่อยเดิน/วิ่งเข้าหา
            self.intro_t = 0.0 if "intro_build" in self.style else None

    @property
    def engaged(self):
        """main.py: ตีกันจริงแล้ว (ไม่ใช่ช่วงบอสกำลังวิ่งเข้ามา) ใช้เปิดประกายหมัด/ท่าต่อยของกลุ่มคน"""
        return self.fighting and not self.approaching

    def run_part(self):
        """ชุดท่าวิ่งชุดที่เท่าไร ตามระยะที่วิ่งมาแล้วเทียบกับ style["run_parts"]
        (นินจา: วิ่งเฉยๆ -> เอื้อมไปจับคุไน -> ชักออก -> ถือคุไนวิ่ง)"""
        total = max(1.0, self.run_from - self.target_z)
        done = 1 - (self.stand_z - self.target_z) / total
        return sum(done >= t for t in self.style.get("run_parts", ()))

    def intro_frames(self):
        return boss_frames(self.kind, "intro")

    @property
    def intro_length(self):
        return len(self.style["intro_build"]["poses"]) / self.style["intro_fps"]

    def finish(self):
        self.approaching = False
        super().finish()

    def update(self, dt):
        self.impact = False
        if self.approaching:
            self.anim_t += dt
            if getattr(self, "intro_t", None) is not None:          # ท่าเปิดตัวยังไม่จบ: ยืนอยู่กับที่
                self.intro_t += dt
                if self.intro_t >= self.intro_length:
                    self.intro_t = None
                return
            self.run_t += dt
            self.stand_z = max(self.target_z, self.stand_z - self.style["run_speed"] * dt)
            if self.stand_z <= self.target_z:
                self.approaching = False     # ถึงแล้ว: เริ่มตีกันเฟรมถัดไป
            return
        super().update(dt)
        self.stand_z += (self.target_z - self.stand_z) * min(1.0, C.BOSS_STEP_SPEED * dt)
        if self.fighting:
            self.attack_t += dt
            i = int(self.attack_t * self.style["attack_fps"]) % self.style["attack_frames"]
            imp = self.style["impact"]
            hits = imp if isinstance(imp, list) else ([] if imp is None else [imp])
            self.impact = i in hits and i != self.frame_i      # เพิ่งเข้าท่าที่โดน
            strength = self.style.get("impact_strength", 1.0)
            if isinstance(strength, dict):                     # คอมโบ: แต่ละหมัดแรงไม่เท่ากัน
                self.impact_strength = strength.get(i, 1.0)
            if "hits_per_sec" in self.style.get("barrage", {}):
                # หมัดรัว: โดนตอนแขนข้างใดข้างหนึ่งต่อยถึงตัวคน (sync กับภาพ)
                self.impact = any(self.punch_landed(left, self.attack_t - dt) for left in (True, False))
                # ตัวโยกตามไหล่ที่ดึงกลับ: ง้างซ้าย -> ท่อนบนเอนซ้าย (ท่า 3), ง้างขวา -> เอนขวา (ท่า 1)
                if self.punch_phase(True)[1] < PUNCH_WIND:
                    i = 3
                elif self.punch_phase(False)[1] < PUNCH_WIND:
                    i = 1
                else:
                    i = 2                                 # ช่วงหมัดถึงตัว: ย่อลึกสุด
            self.frame_i = i

    def punch_phase(self, left, t=None):
        """หมัดรัว: แขนจริงข้างนี้อยู่ที่หมัดที่เท่าไร และช่วงไหนของหมัด (0..1)
        0..PUNCH_WIND ง้าง (ดึงไหล่กลับ) -> ..PUNCH_HIT พุ่งออก -> ค้าง -> ดึงกลับ  ซ้าย/ขวาสลับกันครึ่งจังหวะ"""
        cycle = 2 / self.style["barrage"]["hits_per_sec"]          # แขนแต่ละข้างต่อยครึ่งหนึ่งของจำนวนหมัด
        x = (self.attack_t if t is None else t) / cycle + (0 if left else 0.5)
        return int(x), x - int(x)

    def punch_landed(self, left, t_before):
        """แขนข้างนี้เพิ่งต่อยถึงตัวคน (ผ่านจุด PUNCH_HIT) ระหว่าง t_before กับตอนนี้ไหม"""
        k0, p0 = self.punch_phase(left, t_before)
        k1, p1 = self.punch_phase(left)
        hit_before = k0 + (PUNCH_HIT if p0 < PUNCH_HIT else 1 + PUNCH_HIT)   # จุดถึงตัวคนครั้งถัดไป
        return k1 + p1 >= hit_before

    def current(self):
        """(ภาพเฟรมนี้, พุ่งเข้าหาคนกี่ unit, ลอยจากพื้นกี่พิกเซล sprite)"""
        if self.approaching:
            if getattr(self, "intro_t", None) is not None:
                frames = self.intro_frames()
                return frames[min(len(frames) - 1, int(self.intro_t * self.style["intro_fps"]))], 0, 0
            frames = boss_frames(self.kind, "run")      # จังหวะขา x ชุดท่า (ดู run_part)
            steps = len(frames) // (len(self.style.get("run_parts", ())) + 1)
            step = int(self.run_t * self.style["run_fps"]) % steps
            return frames[self.run_part() * steps + step], 0, 0
        if self.fighting:
            frames = boss_frames(self.kind, "attack")
            i = self.frame_i
            seq = self.style.get("attack_seq")
            frame = frames[(seq[i] if seq else i) % len(frames)]
            return frame, self.style["lunge"].get(i, 0), self.style.get("lift", {}).get(i, 0)
        frames = boss_frames(self.kind, "idle")
        return frames[int(self.anim_t * self.style["idle_fps"]) % len(frames)], 0, 0

    def draw(self, screen, camera, font):
        if self.used:
            return
        frame, lunge, lift = self.current()
        z = self.stand_z - lunge
        if not camera.visible(z):
            return
        sx, sy, scale = camera.project(self.x, z)
        size = scale * C.BOSS_SCALE                       # 1 พิกเซลของ sprite = กี่พิกเซลบนจอ
        w, h = int(frame.get_width() * size), int(frame.get_height() * size)
        up = lift * size                                  # กระโดด: ยกภาพขึ้น เงายังอยู่ที่พื้น
        self.draw_shadow(screen, sx, sy, int(32 * size), lift)   # เงาตามขนาดตัว (เฟรมกว้างกว่า 32 ได้ เผื่อดาบ)
        impact = self.style["impact"]
        if self.fighting and isinstance(impact, int) and self.frame_i in (impact, impact + 1):
            self.draw_shockwave(screen, camera, z)
        screen.blit(sprites.scaled(frame, w, h), (sx - w // 2, sy - h - up))
        self.placed = (sx - w / 2, sy - h - up, size)

        # ชื่อ + จำนวนเหนือหัว (ชีตมีที่ว่างเหนือหัวราว 7/32 ของความสูง)
        # เฟรมสูงกว่า 32 (อัศวิน: เผื่อที่ดาบชูเหนือหัว): ป้ายอยู่บนสุดของเฟรม ไม่บังดาบ
        top = sy - (h * 25 / 32 if frame.get_height() <= 32 else h - 2 * size) - up
        text = font.render(str(self.count), True, C.WHITE)
        bg = text.get_rect(center=(sx, top - 14)).inflate(12, 4)
        pygame.draw.rect(screen, self.style["label"], bg, border_radius=6)
        pygame.draw.rect(screen, C.BLACK, bg, 2, border_radius=6)
        screen.blit(text, text.get_rect(center=bg.center))

    def draw_overlay(self, screen, camera):
        """main.py เรียกหลังวาดกลุ่มคน: หมัดรัวพุ่งจากไหล่บอสลงไปที่คนแถวหน้า (ต้องอยู่ทับกลุ่มคน
        ไม่งั้นหมัดที่ลงถึงตัวคนจะถูกคนบังหมด)
        แขนจริง 2 ข้างต่อยเป็นจังหวะ: ง้าง (ดึงไหล่กลับ) -> พุ่งลงหาคน -> ค้าง -> ดึงกลับ  แขนจางที่โคนไหล่ไม่บังตัว
        รอบๆ เป็นรอยหมัดเบลอแบบภาพตัวอย่าง: แถบเทา + แกนขาว + เส้นความเร็วสีเข้ม ปลายเป็นกำปั้นพร้อมเงา"""
        bar = self.style.get("barrage")
        if not (bar and "hits_per_sec" in bar and self.fighting and self.placed and self.crowd):
            return
        if self.shoulders is None:                 # จุดหัวไหล่บนเฟรม 32x32 (ตรงที่แขนถูกตัดออก)
            parts = body_parts(sprites.frames(*self.style["attack"])[0])
            self.shoulders = [parts["arms"][side][2] for side in (True, False)]
        if self.layer is None:
            self.layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        ox, oy, size = self.placed
        _, shift, drop = self.style["build"]["poses"][self.frame_i]
        rng = random.Random(int(self.attack_t * bar["change_per_sec"]) * 7919 + self.kind)
        front = self.crowd.front_z()
        width = max(4, int(size * 3.2))
        skin = tuple(int(c * SKIN[0] / 255) for c in self.style["tint"])   # สีผิวบอสหลังย้อม (ให้แขนสีเดียวกับตัว)
        V = pygame.math.Vector2

        def shoulder(left):
            px, py = self.shoulders[0 if left else 1]
            return V(ox + (px + shift) * size, oy + (py + drop + 1) * size)

        def target(r):
            """จุดที่หมัดลง: คนแถวหน้า (ต่ำกว่าบอสบนจอ = ต่อยลงหาคน) ระยะสั้น ไม่พุ่งไกลเข้าไปกลางกลุ่ม"""
            ex, ey, s = camera.project(self.x + r.uniform(-55, 55), front - r.uniform(0, 25))
            return V(ex, ey - r.uniform(8, 20) * s)

        def curve(a, ctrl, b):
            return [a * (1 - t) ** 2 + ctrl * 2 * (1 - t) * t + b * t * t for t in (k / 14 for k in range(15))]

        for n in range(bar["trails"] - 2):         # รอยเบลอรอบๆ (สุ่มใหม่ถี่ๆ)  แขนจริง 2 ข้างวาดทีหลัง
            left = n % 2 == 0                      # สลับหมัดซ้าย/ขวา
            start, end = shoulder(left), target(rng)
            out_dir = -1 if left else 1
            # เหวี่ยงออกข้างก่อนแล้วกวาดลงหาคน (แบบภาพตัวอย่าง)
            ctrl = V(start.x + out_dir * rng.uniform(7, 13) * size, start.y - rng.uniform(0, 5) * size)
            pts = curve(start, ctrl, end)
            # ทุกชั้นเริ่มจางแทบมองไม่เห็นที่ไหล่ แล้วหนาขึ้นชัดขึ้นจนถึงกำปั้น (ภาพเบลอตามความเร็ว ไม่ใช่ท่อ)
            for k in range(14):                    # แถบเทาหนา
                t = (k + 1) / 14
                pygame.draw.line(layer, (*TRAIL_SMEAR, int(15 + 165 * t * t)), pts[k], pts[k + 1],
                                 max(1, int(width * (0.15 + 1.1 * t))))
            for k in range(7, 14):                 # แกนขาว: เฉพาะครึ่งหลังที่ใกล้กำปั้น
                t = (k + 1) / 14
                pygame.draw.line(layer, (*TRAIL_CORE, int(90 + 165 * t)), pts[k], pts[k + 1],
                                 max(1, int(width * 0.4 * t)))
            for k in range(4, 13):                 # เส้นความเร็วสีเข้ม 2 เส้นขนานด้านนอกโค้ง
                d = pts[k + 1] - pts[k]
                if d.length() == 0:
                    continue
                t = (k + 1) / 14
                side = 1 if left else -1
                nrm = V(-d.y, d.x).normalize() * width * side
                for off, a in ((0.75, 190), (1.25, 110)):
                    pygame.draw.line(layer, (*TRAIL_LINE, int(a * t)), pts[k] + nrm * off * t,
                                     pts[k + 1] + nrm * off * t, max(1, int(size * 0.45)))
            fist_r = max(2, int(size * 2.4))       # กำปั้น + เงาตามหลัง 2 ชั้น
            for t, alpha in ((10 / 14, 70), (12 / 14, 130)):
                g = pts[int(t * 14)]
                pygame.draw.circle(layer, (*self.style["tint"], alpha), g, fist_r)
            pygame.draw.circle(layer, (*self.style["tint"], 255), end, fist_r)
            pygame.draw.circle(layer, (*OUTLINE, 255), end, fist_r, max(1, int(size * 0.6)))

        # ---- แขนจริง 2 ข้าง: แต่ละข้างต่อยเป็นจังหวะ ง้าง (ดึงไหล่กลับ) -> พุ่ง -> ค้าง -> ดึงกลับ ----
        arm_w = max(3, int(size * 3))
        ol = max(1, int(size * 0.8))
        fist_r = max(3, int(size * 2.8))
        ease_io = lambda u: u * u * (3 - 2 * u)
        ease_out = lambda u: 1 - (1 - u) ** 3
        for left in (True, False):
            k, p = self.punch_phase(left)
            r = random.Random(k * 131 + (0 if left else 7) + self.kind)   # เป้าหมายคงที่ตลอดหมัดนี้
            out_dir = -1 if left else 1
            rest = shoulder(left)
            pulled = rest + V(out_dir * 1.2, -1.8) * size     # ไหล่ถูกดึงไปข้างหลัง (บนจอ: ขึ้นและออกข้าง)
            forward = rest + V(-out_dir * 0.6, 1.2) * size    # ตอนหมัดถึง: ไหล่ยื่นตามไปข้างหน้า (ลงและเข้าใน)
            cocked = pulled + V(out_dir * 2.5, -2.0) * size   # กำปั้นง้างอยู่ข้างไหล่
            end = target(r)
            ghosts = []
            if p < PUNCH_WIND:                     # ง้าง
                u = ease_io(p / PUNCH_WIND)
                sh = rest.lerp(pulled, u)
                fist = rest.lerp(cocked, 0.5).lerp(cocked, u)
            elif p < PUNCH_HIT:                    # พุ่งออก (เร็ว + เงาตามหลัง)
                u = ease_out((p - PUNCH_WIND) / (PUNCH_HIT - PUNCH_WIND))
                sh = pulled.lerp(forward, u)
                fist = cocked.lerp(end, u)
                ghosts = [cocked.lerp(end, u * f) for f in (0.45, 0.7)]
            elif p < PUNCH_HOLD:                   # ค้างแขนที่ตัวคน
                sh, fist = forward, end
            else:                                  # ดึงกลับ
                u = ease_io((p - PUNCH_HOLD) / (1 - PUNCH_HOLD))
                sh = forward.lerp(rest, u)
                fist = end.lerp(rest.lerp(cocked, 0.5), u)
            for g, a in zip(ghosts, (60, 110)):    # เงากำปั้นตามหลังตอนพุ่ง
                pygame.draw.circle(layer, (*skin, a), g, fist_r)
            pts = curve(sh, (sh + fist) / 2 + V(out_dir * 1.5 * size, 0), fist)
            # แขนจางที่โคนไหล่ (ไม่บังตัว) แล้วชัดขึ้นเรื่อยๆ จนถึงกำปั้น
            for color, wdt in ((OUTLINE, arm_w + 2 * ol), (skin, arm_w)):
                for j in range(14):
                    a = int(90 + 165 * ((j + 1) / 14) ** 1.5)
                    pygame.draw.line(layer, (*color, a), pts[j], pts[j + 1], wdt)
                    pygame.draw.circle(layer, (*color, a), pts[j + 1], wdt // 2)   # ข้อต่อกลม ไม่ให้เส้นแตก
            pygame.draw.circle(layer, (*OUTLINE, 255), fist, fist_r + ol)
            pygame.draw.circle(layer, (*skin, 255), fist, fist_r)
        screen.blit(layer, (0, 0))

    @staticmethod
    def draw_shadow(screen, sx, sy, w, lift):
        """เงาวงรีใต้เท้า: ลอยสูงขึ้น เงาเล็กลงและจางลง (ช่วยให้รู้ว่ากระโดดอยู่)"""
        k = max(0.35, 1 - lift / 30)
        sw, sh = max(2, int(w * 0.42 * k)), max(2, int(w * 0.1 * k))
        shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, int(90 * k)), shadow.get_rect())
        screen.blit(shadow, (sx - sw // 2, sy - sh // 2))

    def draw_shockwave(self, screen, camera, z):
        """คลื่นกระแทกบนพื้นตรงหน้าบอส ตอนหมัดทุบ / เท้ากระทืบลง"""
        big = self.frame_i != self.style["impact"]     # เฟรมถัดไป: วงกว้างขึ้น
        cz = z - 25
        s = self.style.get("shock", 1.0)
        for r, color in ((95 * s if big else 60 * s, (230, 230, 235)), (65 * s if big else 35 * s, (160, 160, 170))):
            x1, y1, _ = camera.project(self.x - r, cz - r * 0.35)
            x2, y2, _ = camera.project(self.x + r, cz + r * 0.35)
            rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), max(4, abs(y2 - y1)))
            pygame.draw.ellipse(screen, color, rect, 3)
