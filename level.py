"""โหลดด่านจากไฟล์ JSON   [เจ้าของ: C]

ทำไมใช้ JSON: แยก "ข้อมูลด่าน" ออกจาก "โค้ด" เพิ่มด่านใหม่ได้โดยไม่ต้องแก้ Python
"""
import json
import math
import random
from pathlib import Path

import config as C
from gate import GatePair
from obstacle import Obstacle
from enemy import EnemyGroup, Boss

LEVEL_DIR = Path(__file__).parent / "levels"


class Level:
    def __init__(self, name, start_count, speed, finish_z, objects):
        self.name = name
        self.start_count = start_count
        self.speed = speed          # ความเร็ววิ่งไปข้างหน้า (units/วินาที)
        self.finish_z = finish_z
        self.objects = objects      # เรียงตาม z น้อยไปมาก


def build_object(data):
    """แปลง dict หนึ่งก้อนจาก JSON -> object ในเกม"""
    kind = data["type"]
    if kind == "gate_pair":
        return GatePair(data["z"], tuple(data["left"]), tuple(data["right"]))
    if kind == "obstacle":
        return Obstacle(data["x"], data["z"], data["width"], data["damage"])
    if kind == "enemy":
        return EnemyGroup(data["z"], data["count"], data.get("x", 0))
    if kind == "boss":
        return Boss(data["z"], data["count"], data.get("x", 0))
    raise ValueError(f"unknown object type: {kind!r}")


def load_level(filename, rng=None):
    """rng=None: ได้ด่านตามไฟล์ JSON เป๊ะ (ใช้ใน test / ดูชื่อด่าน)
    ส่ง rng มา (random หรือ random.Random(seed)): สุ่มสิ่งกีดขวาง + เลขประตูใหม่ โดยความยากเท่าเดิม"""
    with open(LEVEL_DIR / filename, encoding="utf-8") as f:
        data = json.load(f)
    objects = sorted((build_object(o) for o in data["objects"]), key=lambda o: o.z)
    level = Level(data["name"], data["start_count"], data["speed"], data["finish_z"], objects)
    if rng is not None:
        randomize_gates(level, rng)
        randomize_obstacles(level, rng)   # หลังประตู เพราะต้องรู้จำนวนคน (ความกว้างก้อนคน) ตอนถึงแต่ละอัน
    return level


def list_levels():
    """คืนชื่อไฟล์ด่านทั้งหมดใน levels/ เรียงตามเลข (level2 มาก่อน level10)

    ทำไมไม่ใช้ sorted() ธรรมดา: เรียงแบบตัวอักษรจะได้ level1, level10, level2, ...
    """
    def number(path):
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return int(digits) if digits else 0
    return [p.name for p in sorted(LEVEL_DIR.glob("*.json"), key=lambda p: (number(p), p.name))]


def best_count(level):
    """จำนวนคนมากที่สุดที่เป็นไปได้ตอนถึงเส้นชัย (เลือกประตูดีที่สุดทุกบาน, หลบสิ่งกีดขวางได้หมด)

    ทำไมเลือกบานที่ได้มากสุดทีละบานแล้วได้คำตอบที่ดีที่สุด: ทุกตัวดำเนินการ (+ - x /)
    และการปะทะศัตรู ยิ่งเริ่มด้วยคนมาก ผลก็ยิ่งมาก (ไม่มีทางที่คนน้อยกว่าตอนนี้แล้วจะได้มากกว่าทีหลัง)
    ใช้เป็นฐานคิดดาว และใช้ใน test ตรวจว่าทุกด่านชนะได้จริง
    """
    count = level.start_count
    for obj in level.objects:
        if isinstance(obj, GatePair):
            count = max(obj.left.apply(count), obj.right.apply(count))
        elif isinstance(obj, EnemyGroup):
            count = max(0, count - obj.count)
    return count


# ---------- ความยากของด่าน ----------
# คะแนนความยาก 0-100 = ประตูอันตราย (40) + ความเข้มงวด (25) + ความเร็ว (15) + จำนวนสิ่งกีดขวาง (20)
FATAL_WEIGHT = 40
TIGHT_WEIGHT = 25
SPEED_WEIGHT = 15
OBSTACLE_WEIGHT = 20
SPEED_EASY, SPEED_HARD = 300, 500   # ความเร็วที่นับเป็น 0 และเต็มคะแนน
OBSTACLE_FULL = 10                  # สิ่งกีดขวางเท่านี้อันขึ้นไป = เต็มคะแนน


def run_count(level, wrong_at=()):
    """จำนวนคนตอนถึงเส้นชัย ถ้าเลือกบานที่แย่กว่าที่ประตูลำดับใน wrong_at (นับจาก 0) ที่เหลือเลือกบานดี
    หลบสิ่งกีดขวางได้หมด  คืน 0 ถ้าคนหมดกลางทาง (เกมจบทันที ประตู + ข้างหน้าช่วยไม่ได้)"""
    count = level.start_count
    gate_i = 0
    for obj in level.objects:
        if isinstance(obj, GatePair):
            left, right = obj.left.apply(count), obj.right.apply(count)
            count = min(left, right) if gate_i in wrong_at else max(left, right)
            gate_i += 1
        elif isinstance(obj, EnemyGroup):
            count = max(0, count - obj.count)
        if count <= 0:
            return 0
    return count


def gate_count(level):
    return sum(isinstance(o, GatePair) for o in level.objects)


def fatal_gates(level):
    """ประตูลำดับไหนบ้าง (นับจาก 0) ที่เลือกผิดแค่ครั้งเดียว (ที่เหลือถูกหมด) ก็แพ้"""
    return [i for i in range(gate_count(level)) if run_count(level, {i}) == 0]


def max_wrong_picks(level):
    """เลือกผิดได้มากสุดกี่ครั้งแล้วยังชนะ ลองทุกเส้นทาง (-1 = ชนะไม่ได้เลย)
    "ผิด" = เลือกบานที่ได้คนน้อยกว่าในตอนนั้น  ประตูที่สองบานได้เท่ากันไม่นับ"""
    objects = level.objects

    def go(i, count):
        if count <= 0:
            return -1
        if i == len(objects):
            return 0
        obj = objects[i]
        if isinstance(obj, GatePair):
            left, right = obj.left.apply(count), obj.right.apply(count)
            best = go(i + 1, max(left, right))
            if left != right:
                wrong = go(i + 1, min(left, right))
                if wrong >= 0:
                    best = max(best, wrong + 1)
            return best
        if isinstance(obj, EnemyGroup):
            return go(i + 1, max(0, count - obj.count))
        return go(i + 1, count)

    return go(0, level.start_count)


def obstacle_count(level):
    return sum(isinstance(o, Obstacle) for o in level.objects)


def difficulty(level, obstacles=True):
    """คะแนนความยาก 0-100 ใช้ใน test ตรวจว่าด่านหลังๆ ยากขึ้นจริง

    - ประตูอันตราย: สัดส่วนประตูที่เลือกผิดครั้งเดียวก็แพ้ (ผู้เล่นรู้สึกถึงข้อนี้มากที่สุด)
    - ความเข้มงวด: 1 / (เลือกผิดได้มากสุด + 1)  ผิดไม่ได้เลย = เต็ม
    - ความเร็ว: วิ่งเร็ว = มีเวลาคิดเลขและเลื่อนตัวน้อยลง
    - จำนวนสิ่งกีดขวาง: ยิ่งเยอะยิ่งต้องหลบบ่อย พลาดได้หลายจุด
    obstacles=False: ไม่นับส่วนสิ่งกีดขวาง (obstacle_style ใช้ ไม่งั้นด่านที่สิ่งกีดขวางเยอะจะโดนโหดซ้ำสอง)
    ทำไมไม่ใช้ "% เส้นทางที่ชนะ": ด่านที่ประตูเยอะ % จะต่ำเองทั้งที่ผู้เล่นไม่ได้สุ่มเลือก
    """
    gates = gate_count(level)
    fatal = len(fatal_gates(level)) / gates if gates else 0
    slack = max_wrong_picks(level)
    tight = 1 / (slack + 1) if slack >= 0 else 1
    speed = min(1, max(0, (level.speed - SPEED_EASY) / (SPEED_HARD - SPEED_EASY)))
    score = FATAL_WEIGHT * fatal + TIGHT_WEIGHT * tight + SPEED_WEIGHT * speed
    if obstacles:
        score += OBSTACLE_WEIGHT * min(1, obstacle_count(level) / OBSTACLE_FULL)
    return round(score, 1)


# ---------- สุ่มเลขประตู ----------
GATE_TRIES = 6        # ลองสุ่มเลขใหม่ได้กี่ครั้งต่อบาน ก่อนยอมใช้เลขเดิม
GATE_SPREAD = 0.4     # เลข + / - เปลี่ยนได้ ±40% จากในไฟล์


def random_gate_value(op, value, rng):
    """เลขใหม่ของประตูหนึ่งบาน: x / สุ่ม 2 หรือ 3, + - สุ่มรอบเลขเดิม (ปัดเป็นทีละ 5 ถ้าเลขเดิม >= 10)"""
    if op in ("x", "/"):
        return rng.choice((2, 3))
    step = 5 if value >= 10 else 1
    new = value * rng.uniform(1 - GATE_SPREAD, 1 + GATE_SPREAD)
    return max(step, round(new / step) * step)


def randomize_gates(level, rng):
    """สุ่มเลขบนประตูใหม่ + สลับซ้าย/ขวาบ้าง โดยคะแนนความยาก (difficulty) ต้องเท่าเดิมเป๊ะ

    ทำทีละบานแบบสุ่มลำดับ: ลองเลขใหม่ได้ GATE_TRIES ครั้ง ถ้าความยากเปลี่ยนทุกครั้งก็คืนเลขเดิม
    ทำไมไม่สุ่มทั้งด่านพร้อมกันแล้วลองใหม่: บางด่าน (เช่นด่าน 6) ช่วงตัวเลขที่ความยากเท่าเดิมแคบมาก
    สุ่มทุกบานพร้อมกันแทบไม่เคยตรง แต่ทีละบานเปลี่ยนได้เกือบทุกบาน
    การสลับซ้าย/ขวาไม่กระทบความยาก (ผู้เล่นเลือกได้ทั้งสองฝั่งเหมือนเดิม)
    """
    target = difficulty(level)
    pairs = [o for o in level.objects if isinstance(o, GatePair)]
    gates = [g for pair in pairs for g in (pair.left, pair.right)]
    for gate in rng.sample(gates, len(gates)):
        old = gate.value
        for _ in range(GATE_TRIES):
            gate.value = random_gate_value(gate.op, old, rng)
            if difficulty(level) == target:
                break
        else:
            gate.value = old
    for pair in pairs:
        if rng.random() < 0.5:
            l, r = pair.left, pair.right
            l.op, l.value, r.op, r.value = r.op, r.value, l.op, l.value


# ---------- สุ่มสิ่งกีดขวาง: ยากตามด่าน แต่หลบพ้นได้เสมอ ----------
# กติกาสิ่งกีดขวาง: คนที่ทับหายหมด  "ผ่านได้" = มีช่องว่างกว้างพอให้ทั้งก้อนลอดตอนวิ่งถึง
# และผู้เล่นเลี้ยวไปถึงช่องนั้นทัน (นับต่อเนื่องจากประตู/สิ่งกีดขวางก่อนหน้า บนเส้นทางเลือกประตูดีที่สุด)
DIFFICULTY_FULL = 50                  # คะแนน difficulty(obstacles=False) เท่านี้ขึ้นไป = สิ่งกีดขวางโหดสุด
WIDTH_MIN = 50
WIDTH_MAX_EASY, WIDTH_MAX_HARD = 100, 150
PATTERNS_EASY = (5, 4, 1)             # โอกาสได้ลาย still / slow / fast (ดู obstacle.PATTERNS)
PATTERNS_HARD = (1, 4, 5)
REACT_EASY, REACT_HARD = 0.5, 0.8     # สมมติผู้เล่นเลี้ยวได้กี่ส่วนของความเร็วเต็ม (น้อย = เผื่อเวลาคิดเยอะ)
ROOM_EASY, ROOM_HARD = 60, 20         # ช่องปลอดภัยต้องกว้างรวมอย่างน้อยเท่านี้ (ตำแหน่งศูนย์กลางก้อน)
CROWD_HALF_CAP = 60                   # ก้อนใหญ่กว่านี้ (~1000 คน) หลบหมดไม่ได้อยู่แล้ว เสียคนขอบๆ ตามกติกา
OBSTACLE_TRIES = 15
TIME_SLACK = 0.05                     # เผื่อจังหวะเฟรม ± วินาที


def crowd_half_width(count):
    """ก้อนคนแผ่จากศูนย์กลางไปข้างละเท่าไร (วัดจาก crowd.py: 10 คน ~11, 1000 คน ~60 นับ 90% ของคน)"""
    return min(CROWD_HALF_CAP, 1.8 * math.sqrt(count) + 5)


def crowd_limit(count):
    """ศูนย์กลางก้อนไปได้ไกลสุดเท่าไร (สูตรเดียวกับ Crowd.radius ใน crowd.py ที่กันตกถนน)"""
    return C.ROAD_HALF_W - C.PERSON_SPACING * math.sqrt(min(count, C.MAX_DRAWN_PEOPLE))


def obstacle_style(level):
    """ความโหดของสิ่งกีดขวาง ไล่ตามคะแนนความยากของด่าน (0 = ง่ายสุด, DIFFICULTY_FULL = ยากสุด)
    ไม่นับจำนวนสิ่งกีดขวาง: ด่านที่มีเยอะยากขึ้นจากจำนวนอยู่แล้ว ไม่ต้องให้แต่ละอันโหดขึ้นอีก
    คืน (ช่วงความกว้าง, โอกาสแต่ละลาย, react, room)"""
    d = min(1, difficulty(level, obstacles=False) / DIFFICULTY_FULL)

    def lerp(easy, hard):
        return easy + (hard - easy) * d

    return ((WIDTH_MIN, lerp(WIDTH_MAX_EASY, WIDTH_MAX_HARD)),
            tuple(lerp(e, h) for e, h in zip(PATTERNS_EASY, PATTERNS_HARD)),
            lerp(REACT_EASY, REACT_HARD),
            lerp(ROOM_EASY, ROOM_HARD))


# ช่วงตำแหน่ง = list ของ [ซ้าย, ขวา] ไม่ทับกัน เรียงจากซ้ายไปขวา
def _merge(spans):
    out = []
    for a, b in sorted(spans):
        if a > b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _clip(spans, lo, hi):
    return _merge([(max(lo, a), min(hi, b)) for a, b in spans])


def _cut(spans, lo, hi):
    """ตัดช่วง (lo, hi) ออก"""
    return _merge([s for a, b in spans for s in ((a, min(b, lo)), (max(a, hi), b))])


def _safe_spans(spans, obstacle, t, half):
    """ตำแหน่งศูนย์กลางก้อนที่ไม่มีใครโดนสิ่งกีดขวาง ตอนวิ่งถึงที่เวลา t"""
    xs = [obstacle.x_at(t + dt) for dt in (-TIME_SLACK, 0, TIME_SLACK)]
    gap = obstacle.width / 2 + half
    return _cut(spans, min(xs) - gap, max(xs) + gap)


def dodge_spans(level, style=None, pick=None):
    """เดินตามเส้นทางเลือกประตูดีที่สุด เก็บช่วงตำแหน่งที่ก้อนคนไปถึงได้โดยไม่โดนสิ่งกีดขวางเลย
    คืนช่วงที่เหลือตอนเส้นชัย  [] = มีสิ่งกีดขวางที่หลบไม่ทัน / ช่องแคบเกิน
    pick(obstacle, spans, t, half): เรียกก่อนเช็กสิ่งกีดขวางแต่ละอัน (randomize_obstacles ใช้สุ่มตรงนี้)"""
    _, _, react, room = style or obstacle_style(level)
    side_speed = max(C.CROWD_SIDE_SPEED, level.speed * C.CROWD_SIDE_RATIO) * react
    count, t, spans = level.start_count, 0.0, [[0.0, 0.0]]
    for obj in level.objects:
        t_obj = (obj.z - C.CROWD_OFFSET) / level.speed     # crowd.z เริ่มที่ CROWD_OFFSET
        limit = crowd_limit(count)
        move = side_speed * (t_obj - t)
        spans = _clip([(a - move, b + move) for a, b in spans], -limit, limit)
        t = t_obj
        if isinstance(obj, GatePair):
            left, right = obj.left.apply(count), obj.right.apply(count)
            if left > right:
                spans = _clip(spans, -limit, -0.01)        # Gate.contains: บานซ้ายคือ x < 0
            elif right > left:
                spans = _clip(spans, 0, limit)
            count = max(left, right)
        elif isinstance(obj, EnemyGroup):
            count = max(0, count - obj.count)
        elif isinstance(obj, Obstacle):
            half = crowd_half_width(count)
            if pick:
                pick(obj, spans, t, half)
            spans = _safe_spans(spans, obj, t, half)
            if sum(b - a for a, b in spans) < room:
                return []
        if not spans:
            return []
    return spans


def randomize_obstacles(level, rng):
    """สุ่มความกว้าง/ตำแหน่ง/ลายขยับของสิ่งกีดขวางทีละอันตามลำดับ z ให้โหดตามความยากของด่าน
    สุ่มได้ OBSTACLE_TRIES ครั้ง ต้องเหลือช่องหลบกว้างรวม >= room ที่ผู้เล่นเลี้ยวไปถึงทัน
    ถ้าไม่ได้สักครั้ง: วางอันแคบสุดแบบนิ่ง ชิดขอบฝั่งตรงข้ามกับก้อนคน"""
    style = obstacle_style(level)
    width_range, weights, _, room = style

    def pick(obstacle, spans, t, half):
        for _ in range(OBSTACLE_TRIES):
            obstacle.randomize(rng, width_range, weights)
            if sum(b - a for a, b in _safe_spans(spans, obstacle, t, half)) >= room:
                return
        obstacle.width, obstacle.amplitude, obstacle.swing_speed = WIDTH_MIN, 0, 0
        side = -1 if spans and spans[0][0] + spans[-1][1] > 0 else 1
        obstacle.start_x = obstacle.x = side * (C.ROAD_HALF_W - WIDTH_MIN / 2)

    dodge_spans(level, style, pick)
