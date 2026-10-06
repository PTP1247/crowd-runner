"""โหมดไม่รู้จบ (Endless): สร้างถนนต่อไปเรื่อยๆ และยากขึ้นทุก 1000 ระยะ   [เจ้าของ: C]

หลักการ
- ถนนแบ่งเป็น "ช่วง" (chunk) ยาวช่วงละ CHUNK_LEN  ช่วงที่ k (นับจาก 0) มีความยาก k
- แต่ละช่วง = ประตู 2-4 คู่ + สิ่งกีดขวาง 1-3 อัน + ศัตรูปิดท้าย (ยิ่งยาก ยิ่งมีของเยอะ วิ่งเร็วขึ้น)
- คะแนนของโหมดนี้คือ "ระยะทาง" ที่วิ่งได้ ไม่ใช่จำนวนคน

วัดความยากด้วย "สัดส่วนเส้นทางที่ชนะ" (win ratio)
- ประตูแต่ละคู่เลือกได้ 2 ทาง  ช่วงที่มีประตู 3 คู่ = 2^3 = 8 เส้นทาง
- ไล่จำนวนคนตามทุกเส้นทาง ผ่านประตู สิ่งกีดขวาง (สมมติว่าหลบได้หมด) และศัตรู
- เส้นทางที่ยังเหลือคน = ชนะ   win ratio = เส้นทางที่ชนะ / เส้นทางทั้งหมด
- ยิ่ง ratio น้อย ยิ่งต้องเลือกประตูถูกบ่อย = ยากขึ้น

ตัวสร้างช่วงใหม่
1. นับเส้นทางที่เป็นไปได้ทั้งหมดจาก "จำนวนคนจริงตอนนี้" ผ่านของที่สร้างไว้แล้วแต่ยังไม่ถึง
   (ช่วงใหม่ถูกสร้างล่วงหน้า ตอนนั้นยังไม่รู้ว่าผู้เล่นจะเลือกทางไหน จึงต้องคิดทุกทาง)
2. สุ่มประตูทีละคู่ ค่าในประตูคิดจากจำนวนคนที่เป็นไปได้ตอนนั้น (บวก 30% ของ 20 กับของ 500 ต่างกัน)
3. เลือก "ขนาดศัตรู" ท้ายช่วง ให้ win ratio ใกล้เป้าของความยากนั้นที่สุด และต้องมีอย่างน้อย 1 ทางที่ชนะ

ทำไมใช้ Counter {จำนวนคน: จำนวนเส้นทาง}: หลายเส้นทางให้จำนวนคนเท่ากัน รวมเป็นก้อนเดียว
จึงไม่ต้องเก็บ 2^n เส้นทางจริงๆ คำนวณเร็วแม้มองล่วงหน้าหลายช่วง
"""
import math
import random
from collections import Counter

import config as C
from gate import GatePair
from obstacle import Obstacle
from enemy import EnemyGroup

CHUNK_LEN = 1000          # ยากขึ้นทุกๆ ระยะเท่านี้
LOOKAHEAD = C.Z_FAR       # สร้างของล่วงหน้าให้ไกลกว่าที่กล้องมองเห็น จะได้ไม่โผล่กลางจอ
START_COUNT = 20
COUNT_CAP = 800           # ไม่ให้เส้นทางไหนมีคนเกินนี้ (Crowd เก็บคนทีละตัว คนเยอะเกมช้า)

START_RATIO = 0.75        # ช่วงแรก: 75% ของเส้นทางชนะ
RATIO_DECAY = 0.88        # ทุกช่วงถัดไป: เป้าคูณ 0.88
MIN_RATIO = 0.20          # ยากสุดแค่นี้: อย่างน้อย 1 ใน 5 เส้นทางยังชนะ

BASE_SPEED = 300
SPEED_STEP = 12
MAX_SPEED = 500


# ---------------- นับเส้นทาง (ใช้ได้กับด่านปกติด้วย) ----------------

def spread(routes, objects):
    """ไล่ทุกเส้นทางผ่าน objects  routes = Counter {จำนวนคน: จำนวนเส้นทาง}  คืน Counter ใหม่"""
    for obj in objects:
        nxt = Counter()
        for count, ways in routes.items():
            if count <= 0:                       # ตายแล้ว ไปต่อไม่ได้ แต่ยังนับเป็นเส้นทางที่แพ้
                nxt[0] += ways * (2 if isinstance(obj, GatePair) else 1)
            elif isinstance(obj, GatePair):
                nxt[obj.left.apply(count)] += ways
                nxt[obj.right.apply(count)] += ways
            elif isinstance(obj, EnemyGroup):
                nxt[max(0, count - obj.count)] += ways
            else:                                # สิ่งกีดขวาง: สมมติว่าหลบได้
                nxt[count] += ways
        routes = nxt
    return routes


def winning_routes(start_count, objects):
    """คืน (จำนวนเส้นทางที่ชนะ, จำนวนเส้นทางทั้งหมด)"""
    routes = spread(Counter({start_count: 1}), objects)
    return sum(w for c, w in routes.items() if c > 0), sum(routes.values())


# ---------------- กติกาความยากต่อช่วง ----------------

def target_ratio(d):
    return max(MIN_RATIO, START_RATIO * RATIO_DECAY ** d)


def speed_for(d):
    return min(MAX_SPEED, BASE_SPEED + SPEED_STEP * d)


def layout(d):
    """ตำแหน่ง (offset ในช่วง) ของประตู สิ่งกีดขวาง และศัตรู ตามความยาก d

    เรียง ประตู, สิ่งกีดขวาง, ประตู, ... , ศัตรู  แล้วกระจายห่างเท่าๆ กันตั้งแต่ 150 ถึง 900
    ของเยอะสุด 6 ชิ้น = ห่างกันอย่างน้อย 150 (ถ้าชิดกว่านี้ วิ่งเร็วๆ คนเลี้ยวหลบไม่ทัน)
    """
    n_gates = 2 if d < 2 else 3
    n_obstacles = 1 if d < 4 else 2
    order = []
    for i in range(n_gates):
        order.append("gate")
        if i < n_obstacles:
            order.append("obstacle")
    order.append("enemy")
    step = 750 // (len(order) - 1)
    at = [150 + i * step for i in range(len(order))]
    gates = [z for z, kind in zip(at, order) if kind == "gate"]
    obstacles = [z for z, kind in zip(at, order) if kind == "obstacle"]
    return gates, obstacles, at[-1]


def pick_enemy(finals, target, rng):
    """เลือกขนาดศัตรูให้สัดส่วนเส้นทางที่รอดใกล้ target ที่สุด  คืน (ขนาดศัตรู, wins, total)

    finals = Counter จำนวนคนก่อนถึงศัตรูของทุกเส้นทาง  เส้นทางที่มีคน > ขนาดศัตรู = รอด
    เรียงจำนวนคนจากมากไปน้อย แล้วลองตัดทีละขั้น ดูว่าตัดตรงไหนได้สัดส่วนใกล้เป้าที่สุด
    """
    total = sum(finals.values())
    alive = sorted((c for c in finals if c > 0), reverse=True)
    if not alive:
        return 0, 0, total
    best = None
    wins = 0
    for i, c in enumerate(alive):
        wins += finals[c]
        gap = abs(wins / total - target)
        if best is None or gap < best[0]:
            best = (gap, i, wins)
    _, i, wins = best
    lowest_alive = alive[i]
    below = alive[i + 1] if i + 1 < len(alive) else 0
    # ศัตรูขนาดใดก็ได้ใน [below, lowest_alive - 1] ให้ผลเหมือนกัน สุ่มให้ตัวเลขไม่ซ้ำซาก
    return rng.randint(below, lowest_alive - 1), wins, total


def random_gate(good, c, c_max, rng):
    """ประตูหนึ่งบาน  c = จำนวนคนโดยประมาณ (ค่ากลาง), c_max = มากสุดที่เป็นไปได้ (ใช้คุมไม่ให้เกิน COUNT_CAP)"""
    room = COUNT_CAP - c_max
    if good and room >= 1:                       # เต็มเพดานแล้ว ประตูดีไม่ได้ -> กลายเป็นประตูเสีย
        opts = [("+", max(1, min(room, int(c * rng.uniform(0.3, 1.0)) + rng.randint(1, 10))))]
        if c_max * 2 <= COUNT_CAP:
            opts.append(("x", 2))
        if c_max * 3 <= COUNT_CAP and c < 80:
            opts.append(("x", 3))
    else:
        opts = [("-", max(1, int(c * rng.uniform(0.2, 0.6)))), ("/", 2)]
        if c >= 30:
            opts.append(("/", 3))
    return rng.choice(opts)


def random_pair(d, routes, rng):
    """ประตูคู่หนึ่ง  ช่วงแรกๆ เป็น ดี/เสีย (เลือกง่าย) ยิ่งยากยิ่งมี ดี/ดี และ เสีย/เสีย ที่ต้องคิดเลข"""
    alive = [c for c in routes if c > 0] or [1]
    c_max = max(alive)
    # ค่ากลางถ่วงน้ำหนักตามจำนวนเส้นทาง
    expanded = sorted(alive)
    weights = [routes[c] for c in expanded]
    half, acc, c_mid = sum(weights) / 2, 0, expanded[-1]
    for c, w in zip(expanded, weights):
        acc += w
        if acc >= half:
            c_mid = c
            break
    mixed = rng.random() < max(0.3, 0.9 - 0.08 * d)
    kinds = (True, False) if mixed else ((True, True) if rng.random() < 0.5 else (False, False))
    for _ in range(10):                          # สุ่มใหม่ถ้าได้สองบานเหมือนกันเป๊ะ
        a = random_gate(kinds[0], c_mid, c_max, rng)
        b = random_gate(kinds[1], c_mid, c_max, rng)
        if a != b:
            break
    return (a, b) if rng.random() < 0.5 else (b, a)


# ---------------- ด่านไม่รู้จบ ----------------

class EndlessLevel:
    """หน้าตาเหมือน level.Level (name, start_count, speed, finish_z, objects) main.py จึงใช้ร่วมกันได้

    ต่างกันตรง: objects เพิ่มเรื่อยๆ ผ่าน advance() และ finish_z = อนันต์ (ไม่มีเส้นชัย)
    """

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.start_count = START_COUNT
        self.speed = speed_for(0)
        self.finish_z = math.inf
        self.objects = []
        self.chunks = []          # ข้อมูลต่อช่วง: dict(start, difficulty, wins, total, target) ใช้ debug/test
        self.next_chunk = 0
        self.advance(C.CROWD_OFFSET, START_COUNT, 0)

    @staticmethod
    def distance(crowd_z):
        """ระยะทางที่วิ่งมาแล้ว (เริ่ม 0)"""
        return max(0.0, crowd_z - C.CROWD_OFFSET)

    def difficulty(self, crowd_z):
        return int(self.distance(crowd_z) // CHUNK_LEN)

    @property
    def name(self):
        return f"Endless  Lv {self.difficulty(self.crowd_z) + 1}" if hasattr(self, "crowd_z") else "Endless"

    def progress(self, crowd_z):
        """0-1 ภายในช่วงปัจจุบัน (หลอด HUD = ใกล้ถึงระดับยากถัดไปแค่ไหน)"""
        return (self.distance(crowd_z) % CHUNK_LEN) / CHUNK_LEN

    def chunk_start(self, k):
        return C.CROWD_OFFSET + k * CHUNK_LEN

    def advance(self, crowd_z, count, next_index):
        """เรียกทุกเฟรม: สร้างช่วงใหม่ให้ทัน, ทิ้งของที่ผ่านไปแล้ว, ปรับความเร็ว  คืน next_index ที่ปรับแล้ว"""
        self.crowd_z = crowd_z
        self.speed = speed_for(self.difficulty(crowd_z))
        while self.chunk_start(self.next_chunk) < crowd_z + LOOKAHEAD:
            self.make_chunk(count, next_index)
        # ทิ้งของที่วิ่งผ่านไปไกลแล้ว ไม่งั้น list ยาวขึ้นเรื่อยๆ จนเกมช้า
        drop = 0
        while drop < next_index and self.objects[drop].z < crowd_z - 2 * C.CROWD_OFFSET:
            drop += 1
        del self.objects[:drop]
        return next_index - drop

    def make_chunk(self, count, next_index):
        k = self.next_chunk
        rng = self.rng
        start = self.chunk_start(k)
        gates, obstacles, enemy_at = layout(k)

        # 1. ทุกจำนวนคนที่เป็นไปได้ตอนเข้าช่วงนี้ (จากจำนวนจริงตอนนี้ ผ่านของที่ยังไม่ถึง)
        routes = spread(Counter({count: 1}), self.objects[next_index:])
        routes = Counter({c: w for c, w in routes.items() if c > 0}) or Counter({max(1, count): 1})

        # 2. สุ่มประตูทีละคู่ แล้วไล่เส้นทางต่อ (ประตูคู่ถัดไปจะได้คิดจากจำนวนที่เป็นไปได้จริง)
        new = []
        for off in gates:
            pair = GatePair(start + off, *random_pair(k, routes, rng))
            routes = spread(routes, [pair])
            new.append(pair)
        width = min(C.ROAD_HALF_W, 80 + 5 * k)
        for off in obstacles:
            x = rng.uniform(-C.ROAD_HALF_W + width / 2, C.ROAD_HALF_W - width / 2)
            new.append(Obstacle(x, start + off, width, 10))

        # 3. ศัตรูท้ายช่วง ขนาดพอให้สัดส่วนทางชนะใกล้เป้า
        target = target_ratio(k)
        size, wins, total = pick_enemy(routes, target, rng)
        if size > 0:
            new.append(EnemyGroup(start + enemy_at, size))

        self.objects.extend(sorted(new, key=lambda o: o.z))
        self.chunks.append({"start": start, "difficulty": k, "wins": wins, "total": total,
                            "target": target, "enemy": size})
        self.next_chunk += 1
