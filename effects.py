"""เอฟเฟกต์อนุภาคตอนปะทะ: ประกายหมัด, ระเบิดการ์ตูน "pow", เศษกระเด็น, ฝุ่น

ทำไมเก็บเป็นพิกัดโลก (x, z) + ความสูง h: วาดผ่าน camera.project() เหมือน object อื่น
จึงย่อตามระยะและสั่นตามกล้องเอง (ดูสัญญาใน GUIDE_TH.md ข้อ 7)
h = สูงจากพื้นเป็นพิกเซลที่ scale 1 (คนสูงราว 25)
"""
import math
import random

import pygame

import config as C

MAX_PARTICLES = 350          # กันเฟรมตกตอนปะทะกองใหญ่
GRAVITY = 260                # เศษที่กระเด็นตกลงพื้น (หน่วย h ต่อวินาที^2)
SPARK_COLORS = [(255, 255, 255), (255, 244, 160), (255, 205, 70), (245, 140, 40)]   # ขาว -> ส้ม ตามอายุ
POW_FILL, POW_CORE, POW_EDGE = (255, 214, 60), (255, 255, 235), (60, 30, 20)
DUST = (225, 214, 200)


class Particle:
    __slots__ = ("kind", "x", "z", "h", "vx", "vz", "vh", "age", "life", "size", "color", "spin")

    def __init__(self, kind, x, z, h, life, size, color=None, vx=0.0, vz=0.0, vh=0.0):
        self.kind, self.x, self.z, self.h = kind, x, z, h
        self.vx, self.vz, self.vh = vx, vz, vh
        self.age, self.life, self.size, self.color = 0.0, life, size, color
        self.spin = random.random() * math.pi


class Effects:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.parts = []

    def add(self, p):
        if len(self.parts) < MAX_PARTICLES:
            self.parts.append(p)

    # ---------- ตัวสร้างเอฟเฟกต์ ----------
    def hit(self, x, z, h, colors=(C.WHITE, (230, 90, 80)), big=False):
        """หมัดโดนกันหนึ่งครั้ง: ประกาย + เศษสองสี (ฝั่งเรา / ฝั่งศัตรู) + ฝุ่นนิดหน่อย"""
        r = self.rng
        self.add(Particle("spark", x, z, h, life=r.uniform(0.18, 0.28), size=r.uniform(5, 8) * (1.6 if big else 1)))
        if big:
            self.add(Particle("pow", x, z, h + 4, life=0.32, size=r.uniform(10, 13)))
        for i in range(r.randint(2, 4) + (3 if big else 0)):
            self.add(Particle("chip", x, z, h, life=r.uniform(0.4, 0.7), size=r.choice((2, 2, 3)),
                              color=colors[i % 2], vx=r.uniform(-90, 90), vz=r.uniform(-60, 60),
                              vh=r.uniform(60, 140)))
        if r.random() < 0.35 or big:
            self.add(Particle("dust", x + r.uniform(-8, 8), z, 2, life=r.uniform(0.35, 0.55),
                              size=r.uniform(3, 5), vh=r.uniform(8, 20)))

    def puff(self, x, z):
        """ฝุ่นก้อนเล็กจากเท้าคนที่วิ่ง (ศัตรูวิ่งพุ่งเข้ามา)"""
        r = self.rng
        self.add(Particle("dust", x, z, 1, life=r.uniform(0.3, 0.5), size=r.uniform(2.5, 4),
                          vz=r.uniform(20, 60), vh=r.uniform(6, 16)))

    def slam(self, x, z, radius=60):
        """หมัดบอสทุบพื้น: ระเบิด pow ใหญ่ตรงกลาง + ฝุ่นพุ่งเป็นวง + เศษหินกระเด็น"""
        r = self.rng
        self.add(Particle("pow", x, z, 10, life=0.4, size=22))
        for i in range(14):
            a = i / 14 * math.tau + r.uniform(-0.2, 0.2)
            d = radius * r.uniform(0.5, 1.0)
            self.add(Particle("dust", x + math.cos(a) * d, z + math.sin(a) * d * 0.5, 2,
                              life=r.uniform(0.4, 0.7), size=r.uniform(5, 9),
                              vx=math.cos(a) * 60, vz=math.sin(a) * 30, vh=r.uniform(10, 30)))
        for _ in range(10):
            self.add(Particle("chip", x + r.uniform(-20, 20), z, 4, life=r.uniform(0.5, 0.8), size=3,
                              color=(150, 150, 158), vx=r.uniform(-120, 120), vz=r.uniform(-60, 60),
                              vh=r.uniform(90, 180)))

    # ---------- ต่อเฟรม ----------
    def update(self, dt):
        alive = []
        for p in self.parts:
            p.age += dt
            if p.age >= p.life:
                continue
            p.x += p.vx * dt
            p.z += p.vz * dt
            p.h += p.vh * dt
            if p.kind == "chip":
                p.vh -= GRAVITY * dt
                if p.h < 0:                  # ตกถึงพื้น: เด้งต่ำๆ ครั้งเดียวแล้วนิ่ง
                    p.h, p.vh, p.vx, p.vz = 0, -p.vh * 0.3, p.vx * 0.5, p.vz * 0.5
            alive.append(p)
        self.parts = alive

    def draw(self, screen, camera):
        # ไกลก่อน ใกล้ทับ (ของน้อย เรียงทุกเฟรมได้สบาย)
        for p in sorted(self.parts, key=lambda q: -q.z):
            if not camera.visible(p.z):
                continue
            sx, sy, s = camera.project(p.x, p.z)
            y = sy - p.h * s
            t = p.age / p.life
            if p.kind == "spark":
                self.draw_spark(screen, sx, y, p, t, s)
            elif p.kind == "pow":
                self.draw_pow(screen, sx, y, p, t, s)
            elif p.kind == "chip":
                k = max(1, round(p.size * s))
                pygame.draw.rect(screen, p.color, (int(sx) - k // 2, int(y) - k // 2, k, k))
            else:   # dust: โตขึ้นแล้วจางเป็นสีพื้น
                rad = max(1, int(p.size * s * (0.6 + t)))
                shade = tuple(int(c * (1 - 0.35 * t)) for c in DUST)
                pygame.draw.circle(screen, shade, (int(sx), int(y)), rad)

    @staticmethod
    def draw_spark(screen, x, y, p, t, s):
        """ประกายรูปกากบาท 4 แฉก + แฉกเฉียงสั้นๆ โผล่วาบแล้วหด สีขาว -> เหลือง -> ส้ม"""
        grow = 1 - abs(1 - 2 * min(1.0, t * 1.6))          # 0 -> 1 -> 0
        r = max(1, int(p.size * s * (0.4 + 0.6 * grow)))
        w = max(1, int(r / 3))
        color = SPARK_COLORS[min(len(SPARK_COLORS) - 1, int(t * len(SPARK_COLORS)))]
        x, y = int(x), int(y)
        pygame.draw.rect(screen, color, (x - r, y - w // 2, 2 * r + 1, w))
        pygame.draw.rect(screen, color, (x - w // 2, y - r, w, 2 * r + 1))
        d = int(r * 0.55)
        for dx, dy in ((d, d), (-d, d), (d, -d), (-d, -d)):
            pygame.draw.rect(screen, color, (x + dx - w // 2, y + dy - w // 2, w, w))

    @staticmethod
    def draw_pow(screen, x, y, p, t, s):
        """ระเบิดแบบการ์ตูน: ดาวหยัก 10 แฉก ขอบเข้ม ไส้ขาว ขยายเร็วแล้วจาง"""
        pop = min(1.0, t * 5)                                 # ขยายเต็มใน 20% แรกของอายุ
        r = p.size * s * (0.5 + 0.7 * pop) * (1 - 0.4 * t)
        if r < 2:
            return
        pts = []
        for i in range(20):
            a = p.spin + i / 20 * math.tau
            rr = r if i % 2 == 0 else r * 0.55
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr * 0.8))
        fill = POW_FILL if t < 0.6 else SPARK_COLORS[3]
        pygame.draw.polygon(screen, fill, pts)
        pygame.draw.polygon(screen, POW_EDGE, pts, max(1, int(r / 8)))
        core = [((px - x) * 0.45 + x, (py - y) * 0.45 + y) for px, py in pts]
        pygame.draw.polygon(screen, POW_CORE, core)
