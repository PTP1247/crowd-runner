"""กลุ่มคนของผู้เล่น   [เจ้าของ: B]"""
import math
import random
import pygame
import config as C


class Person:
    def __init__(self, dx=0.0, dz=0.0):
        self.dx = dx              # ตำแหน่งซ้าย-ขวา เทียบกับศูนย์กลางก้อน
        self.dz = dz              # ตำแหน่งหน้า-หลัง เทียบกับศูนย์กลางก้อน
        self.vx = 0.0
        self.vz = 0.0
        self.speed = random.uniform(0.85, 1.15)
        self.anim_t = random.random() * 6.28
        self.wander_t = random.random() * 6.28


class Crowd:
    def __init__(self, count):
        self.x = 0.0              # ตำแหน่งซ้าย-ขวาในโลก
        self.z = 0.0              # main.py อัปเดตให้ = camera.z + CROWD_OFFSET ทุกเฟรม
        self.target_x = None      # ถ้าคุมด้วยเมาส์ จะเลื่อนเข้าหาจุดนี้
        self.people = []
        self.set_count(count)

    @property
    def count(self):              # จำนวนจริง (ใช้คำนวณ)
        return len(self.people)

    @count.setter
    def count(self, n):
        self.set_count(n)

    def set_count(self, n):
        n = max(0, int(n))
        while len(self.people) < n:
            self.people.append(Person(random.uniform(-5, 5), random.uniform(-5, 5)))
        del self.people[n:]

    def add(self, n):
        self.set_count(self.count + n)

    def remove(self, people):
        gone = set(map(id, people))
        self.people = [p for p in self.people if id(p) not in gone]

    def radius(self):
        """รัศมีของก้อนคน โดยประมาณ (ใช้กันไม่ให้ตกขอบถนน / คำนวณการชน)"""
        return C.PERSON_SPACING * math.sqrt(min(self.count, C.MAX_DRAWN_PEOPLE))

    def move(self, direction, dt):
        """direction: -1 = ซ้าย, +1 = ขวา, 0 = อยู่นิ่ง  (คีย์บอร์ด)"""
        if direction:
            self.target_x = None
            self.x += direction * C.CROWD_SIDE_SPEED * dt

    def update(self, dt):
        if self.target_x is not None:
            self.x += (self.target_x - self.x) * min(1.0, 10 * dt)
        limit = max(0.0, C.ROAD_HALF_W - self.radius())
        self.x = max(-limit, min(limit, self.x))  # ห้ามหลุดถนน

        target_r = C.PERSON_SPACING * math.sqrt(self.count) * 0.8
        for p in self.people:
            fx = fz = 0.0
            # ดึงเข้าหาศูนย์กลาง
            d = math.hypot(p.dx, p.dz) or 0.001
            if d > target_r * 0.3:
                pull = (d - target_r * 0.3) * C.CROWD_COHESION
                fx -= p.dx / d * pull
                fz -= p.dz / d * pull
            # ผลักคนใกล้เคียง
            for q in random.sample(self.people, min(self.count, 8)):
                if q is p:
                    continue
                ddx, ddz = p.dx - q.dx, p.dz - q.dz
                dist = math.hypot(ddx, ddz) or 0.001
                if dist < C.PERSON_SPACING:
                    push = (C.PERSON_SPACING - dist) * C.CROWD_SEPARATION
                    fx += ddx / dist * push
                    fz += ddz / dist * push
            # สุ่มส่าย
            p.wander_t += dt * random.uniform(1.0, 3.0)
            fx += math.cos(p.wander_t) * C.CROWD_WANDER
            fz += math.sin(p.wander_t * 1.3) * C.CROWD_WANDER

            damp = 1 - min(1.0, 3 * dt)
            p.vx = (p.vx + fx * dt) * damp
            p.vz = (p.vz + fz * dt) * damp
            p.dx += p.vx * p.speed * dt
            p.dz += p.vz * p.speed * dt
            p.anim_t += dt * 10 * p.speed

    def draw(self, screen, camera, font):
        # วาดจากคนที่อยู่ไกล (dz มาก) ก่อน ให้คนหน้าบังคนหลัง
        for p in sorted(self.people[:C.MAX_DRAWN_PEOPLE], key=lambda p: -p.dz):
            sx, sy, scale = camera.project(self.x + p.dx, self.z + p.dz)
            bob = math.sin(p.anim_t) * 2 * scale
            # TODO(B): เปลี่ยนวงกลมเป็นรูปคน (sprite) + animation วิ่ง
            pygame.draw.circle(screen, C.PLAYER_COLOR, (sx, sy - 6 * scale + bob), max(1, 5 * scale))
        sx, sy, scale = camera.project(self.x, self.z)
        text = font.render(str(self.count), True, C.WHITE)
        bg = text.get_rect(center=(sx, sy - 70 * scale)).inflate(10, 4)
        pygame.draw.rect(screen, C.PLAYER_COLOR, bg, border_radius=6)
        screen.blit(text, text.get_rect(center=bg.center))