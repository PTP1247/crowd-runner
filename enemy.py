"""กองศัตรู: ปะทะแล้วจำนวนหักลบกันทีละคน   [เจ้าของ: B]"""
import math
import pygame
import config as C
import sprites

ENEMY_TINT = (255, 120, 110)    # ย้อม sprite คนให้เป็นสีแดง แยกจากฝั่งเรา


class EnemyGroup:
    def __init__(self, z, count, x=0):
        self.x, self.z = x, z
        self.count = count
        self.used = False
        self.fighting = False     # True ระหว่างปะทะ: main.py หยุดวิ่งรอจนจบ
        self.lost = 0             # ฝั่งเราเสียไปกี่คนในการปะทะครั้งนี้
        self.crowd = None
        self.rate = 0.0           # หักกันกี่คนต่อวินาที
        self.carry = 0.0          # เศษคนที่ยังหักไม่ครบ 1 (สะสมข้ามเฟรม)
        self.anim_t = 0.0

    def on_reach(self, crowd):
        """เริ่มปะทะ: หักทีละนิดใน update() แทนหักทีเดียว ดูสนุกกว่า เหมือนในวิดีโอ"""
        self.crowd = crowd
        self.fighting = True
        self.rate = max(C.FIGHT_MIN_RATE, min(self.count, crowd.count) / C.FIGHT_TIME)
        self.update(0)

    def update(self, dt):
        self.anim_t += dt
        if not self.fighting:
            return
        self.carry += self.rate * dt
        k = min(int(self.carry), self.count, self.crowd.count)
        self.carry -= int(self.carry)
        self.crowd.count -= k
        self.count -= k
        self.lost += k
        if self.count <= 0 or self.crowd.count <= 0:
            self.fighting = False
            self.used = True

    def finish(self):
        """ปะทะให้จบทันที (ใช้ใน test และตอนกดข้าม)"""
        while self.fighting:
            self.carry = self.count + self.crowd.count
            self.update(0)

    def draw(self, screen, camera, font):
        if self.used or not camera.visible(self.z):
            return
        sheet = "Attack" if self.fighting else "Idle"
        cut = sprites.frames(sheet, tint=ENEMY_TINT)
        n = min(self.count, C.MAX_DRAWN_PEOPLE)
        k = max(1.0, (self.count / max(1, n)) ** 0.4)       # กองใหญ่แผ่กว้างตามจำนวนจริง (แบบเดียวกับ Crowd)
        # วาดเลื่อนไปข้างหน้าเท่ารัศมีกอง: ขอบหน้ากองอยู่ที่ z พอดี กลุ่มคนเราหยุดชนตรงนั้น ไม่ทับกัน
        cz = self.z + C.PERSON_SPACING * math.sqrt(max(0, n - 1)) * k
        spots = []
        for i in range(n):
            # วางเป็นวงก้นหอย (golden angle) ให้ดูเป็นก้อนกลม
            r = C.PERSON_SPACING * math.sqrt(i) * k
            a = i * 2.39996
            spots.append((self.x + r * math.cos(a), cz + r * math.sin(a), i))
        for x, z, i in sorted(spots, key=lambda s: -s[1]):   # ไกลก่อน ใกล้ทับทีหลัง
            sx, sy, scale = camera.project(x, z)
            frame = cut[int(self.anim_t * 10 + i) % len(cut)]
            w, h = int(frame.get_width() * scale), int(frame.get_height() * scale)
            screen.blit(sprites.scaled(frame, w, h), (sx - w // 2, sy - h))
        sx, sy, scale = camera.project(self.x, cz)
        text = font.render(str(self.count), True, C.WHITE)
        bg = text.get_rect(center=(sx, sy - 70 * scale)).inflate(10, 4)
        pygame.draw.rect(screen, C.ENEMY_COLOR, bg, border_radius=6)
        screen.blit(text, text.get_rect(center=bg.center))

