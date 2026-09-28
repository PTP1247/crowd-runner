"""กลุ่มคนของผู้เล่น   [เจ้าของ: B]"""
import math
import pygame
import config as C


class Crowd:
    def __init__(self, count):
        self.count = count        # จำนวนจริง (ใช้คำนวณ)
        self.x = 0.0              # ตำแหน่งซ้าย-ขวาในโลก
        self.z = 0.0              # main.py อัปเดตให้ = camera.z + CROWD_OFFSET ทุกเฟรม
        self.target_x = None      # ถ้าคุมด้วยเมาส์ จะเลื่อนเข้าหาจุดนี้

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
            # เลื่อนเข้าหาเมาส์แบบนุ่มๆ (ขยับ 10 เท่าของระยะที่เหลือต่อวินาที)
            self.x += (self.target_x - self.x) * min(1.0, 10 * dt)
        limit = C.ROAD_HALF_W - self.radius()
        self.x = max(-limit, min(limit, self.x))  # ห้ามหลุดถนน

    def draw(self, screen, camera, font):
        n = min(self.count, C.MAX_DRAWN_PEOPLE)
        # วาดจากคนที่อยู่ไกล (dz มาก) ก่อน ให้คนหน้าบังคนหลัง
        people = []
        for i in range(n):
            r = C.PERSON_SPACING * math.sqrt(i)
            a = i * 2.39996  # golden angle (เรเดียน) ทำให้เรียงเป็นวงสวย ไม่ซ้อนกัน
            people.append((r * math.sin(a) * 0.5, r * math.cos(a)))  # บีบแกน z ให้ก้อนไม่ยืดยาว
        people.sort(key=lambda p: -p[0])
        for dz, dx in people:
            sx, sy, scale = camera.project(self.x + dx, self.z + dz)
            # TODO(B): เปลี่ยนวงกลมเป็นรูปคน (sprite) + animation วิ่ง
            pygame.draw.circle(screen, C.PLAYER_COLOR, (sx, sy - 6 * scale), max(1, 5 * scale))
        sx, sy, scale = camera.project(self.x, self.z)
        text = font.render(str(self.count), True, C.WHITE)
        bg = text.get_rect(center=(sx, sy - 70 * scale)).inflate(10, 4)
        pygame.draw.rect(screen, C.PLAYER_COLOR, bg, border_radius=6)
        screen.blit(text, text.get_rect(center=bg.center))
