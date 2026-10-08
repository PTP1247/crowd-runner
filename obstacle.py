"""สิ่งกีดขวางระหว่างประตู ลดจำนวนคน (จำเป็นสำหรับระดับ 1)   [เจ้าของ: B]"""
import pygame
import config as C
import random
import math

# ลายการขยับที่สุ่มได้: (ชื่อ, ความเร็วแกว่ง ต่ำสุด-สูงสุด)  ความเร็ว 0 = อยู่นิ่ง
PATTERNS = [("still", 0, 0), ("slow", 1.0, 1.8), ("fast", 2.2, 3.2)]


class Obstacle:
    def __init__(self, x, z, width, damage):
        self.x, self.z = x, z
        self.width = width
        self.damage = damage        # ไม่ได้ใช้แล้ว: คนที่ทับสิ่งกีดขวางหายหมด (ดู on_reach)
        self.used = False
        self.start_x = x
        self.amplitude = 0          # แกว่งซ้าย-ขวาได้ไกลแค่ไหนจาก start_x (0 = นิ่ง)
        self.swing_speed = 0
        self.start_time = 0.0       # time_accumulator ตอนเริ่มด่าน (กำหนดจังหวะแกว่ง)
        self.time_accumulator = 0.0

    def randomize(self, rng=random, width_range=None, weights=(1, 1, 1)):
        """สุ่มความกว้าง + ตำแหน่ง + ลายการขยับใหม่ เรียกตอนโหลดด่าน ทำให้เล่นแต่ละรอบไม่ซ้ำกัน

        width_range: (แคบสุด, กว้างสุด) ถ้าไม่ส่งมาใช้ความกว้างเดิม
        weights: โอกาสได้ลาย still / slow / fast  (level.py ปรับตามความยากของด่าน)
        ทำไมจำกัดระยะ: ขอบสิ่งกีดขวางต้องไม่หลุดถนน (ถนนกว้าง ±ROAD_HALF_W)
        """
        if width_range:
            self.width = round(rng.uniform(*width_range) / 10) * 10
        limit = C.ROAD_HALF_W - self.width / 2       # จุดกลางไปได้ไกลสุดเท่านี้
        _, lo, hi = rng.choices(PATTERNS, weights)[0]
        self.swing_speed = rng.uniform(lo, hi)
        self.amplitude = rng.uniform(0.4, 1.0) * limit if self.swing_speed else 0
        self.start_x = rng.uniform(-(limit - self.amplitude), limit - self.amplitude)
        self.start_time = self.time_accumulator = rng.uniform(0, 6.28)
        self.x = self.position()

    def x_at(self, t):
        """ตำแหน่ง x เมื่อผ่านไป t วินาทีหลังเริ่มด่าน (ใช้เช็กล่วงหน้าว่าหลบทันไหม)"""
        return self.start_x + math.sin((self.start_time + t) * self.swing_speed) * self.amplitude

    def position(self):
        return self.start_x + math.sin(self.time_accumulator * self.swing_speed) * self.amplitude

    def update(self, dt):
        self.time_accumulator += dt
        self.x = self.position()

    def hits(self, crowd_x):
        return abs(crowd_x - self.x) <= self.width / 2

    def on_reach(self, crowd):
        # คนที่ตำแหน่งจริงอยู่ในช่วงความกว้างของสิ่งกีดขวาง = โดนชนจริง
        k = crowd.spread()
        victims = [p for p in crowd.people
                   if abs(crowd.x + p.dx * k - self.x) <= self.width / 2]
        crowd.remove(victims)

    def draw(self, screen, camera, font):
        if not camera.visible(self.z):
            return
        x1, y, scale = camera.project(self.x - self.width / 2, self.z)
        x2, _, _ = camera.project(self.x + self.width / 2, self.z)
        h = 25 * scale
        pygame.draw.rect(screen, C.OBSTACLE_COLOR, (x1, y - h, x2 - x1, h))
