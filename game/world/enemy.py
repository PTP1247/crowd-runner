"""กองศัตรู: ปะทะแล้วจำนวนหักลบกันทีละคน   [เจ้าของ: B]"""
import math
import pygame
from game.core import config as C
from game.core import sprites
from game.world.crowd import blob_radius

ENEMY_TINT = (255, 120, 110)    # ย้อม sprite คนให้เป็นสีแดง แยกจากฝั่งเรา
ENEMY_CHIP = (240, 110, 95)     # สีเศษที่กระเด็นจากฝั่งศัตรูตอนปะทะ (ตรงกับสีที่ย้อม sprite)


def pull_crowd(crowd, x, dt):
    """ดึงกลุ่มคนไปหาตำแหน่ง x (ซ้าย-ขวา) แบบนุ่มๆ: ใกล้แล้วช้าลงเอง"""
    crowd.x += (x - crowd.x) * min(1.0, C.ENEMY_PULL * dt)


class EnemyGroup:
    """กองศัตรูธรรมดา และคลาสแม่ของ Boss
    main.py คุยกับทั้งสองแบบผ่านชุดเดียวกัน (rush / on_reach / update / draw + ค่าด้านล่าง)
    บอส override ค่าเหล่านี้ (ชื่อ, สีเศษ, จังหวะโจมตี, จุดปะทะ, รอยหมัดทับกลุ่มคน)"""
    can_rush = True               # Boss ปิดไว้ (บอสมีวิธีเข้าหาของตัวเอง)
    name = "the enemy army"       # main.py: แพ้เพราะอะไร
    chip_color = ENEMY_CHIP       # main.py: สีเศษที่กระเด็นจากฝั่งนี้
    impact = False                # บอส: True เฉพาะเฟรมที่ท่าโจมตีลงถึงตัว (main.py สั่นกล้อง + เสียง)
    impact_strength = 1.0         # แรงของจังหวะนั้น (>= 1 = หนัก)
    contact_z = None              # บอส: จุดที่ปะทะ (ประกายหมัดเกิดตรงนั้น)  None = ขอบหน้ากองศัตรู

    @property
    def engaged(self):
        """ตีกันจริงแล้วหรือยัง  กองศัตรูธรรมดา: ใช่ทันทีที่ปะทะ (บอสอาจยังเดินเข้ามาอยู่)"""
        return True

    def draw_overlay(self, screen, camera):
        """วาดทับกลุ่มคนหลังวาดกลุ่มคน (กองธรรมดาไม่มี บอสใช้วาดหมัดรัว/ดาบแทง)"""

    def __init__(self, z, count, x=0):
        self.x, self.z = x, z
        self.count = count
        self.used = False
        self.fighting = False     # True ระหว่างปะทะ: main.py หยุดวิ่งรอจนจบ
        self.rushing = False      # True ตอนวิ่งพุ่งเข้าหากลุ่มคน
        self.lost = 0             # ฝั่งเราเสียไปกี่คนในการปะทะครั้งนี้
        self.crowd = None
        self.rate = 0.0           # หักกันกี่คนต่อวินาที
        self.carry = 0.0          # เศษคนที่ยังหักไม่ครบ 1 (สะสมข้ามเฟรม)
        self.anim_t = 0.0

    def rush(self, crowd, dt):
        """main.py เรียกทุกเฟรมตอนกองนี้เป็น object ถัดไปที่กลุ่มคนจะถึง
        พอเข้าใกล้ C.ENEMY_RUSH_DIST: วิ่งพุ่งเข้าหา (z ลดลง) และกลุ่มคนถูกดึงเข้าหาศัตรู (ซ้าย-ขวา) หลบไม่ได้
        (main.py ล็อกปุ่มเลี้ยวตั้งแต่ตอนนี้จนปะทะจบ ดู Game.crowd_locked)

        ทำไมเลื่อน z จริง (ไม่ใช่แค่วาด): จุดเริ่มปะทะ = crowd.z >= self.z  ถ้าเลื่อนแค่ภาพ
        ศัตรูจะทับกลุ่มคนก่อนเริ่มปะทะ   จังหวะสิ่งกีดขวางข้างหลังไม่เพี้ยน เพราะสิ่งกีดขวาง
        ขยับเฉพาะตอนวิ่ง (ตอนปะทะหยุด) ระยะวิ่งรวมถึงสิ่งกีดขวางถัดไปจึงเท่าเดิม"""
        if not self.can_rush or self.used or self.fighting:
            return
        if not self.rushing and self.z - crowd.z > C.ENEMY_RUSH_DIST:
            return
        self.rushing = True
        self.z = max(crowd.z, self.z - C.ENEMY_RUSH_SPEED * dt)
        pull_crowd(crowd, self.x, dt)

    def on_reach(self, crowd):
        """เริ่มปะทะ: หักทีละนิดใน update() แทนหักทีเดียว ดูสนุกกว่า เหมือนในวิดีโอ"""
        self.crowd = crowd
        self.rushing = False
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

    def radius(self):
        """รัศมีขอบนอกของกอง: ขนาดเท่ากลุ่มคนของเราที่มีจำนวนเท่ากัน (crowd.blob_radius)
        blob_radius คือวงที่มีคน 90%  ขอบนอกของวงที่คนกระจายเท่าๆ กัน = r90 / sqrt(0.9)"""
        return blob_radius(self.count) / math.sqrt(0.9)

    def finish(self):
        """ปะทะให้จบทันที (ใช้ใน test และตอนกดข้าม)"""
        while self.fighting:
            self.carry = self.count + self.crowd.count
            self.update(0)

    def draw(self, screen, camera, font):
        if self.used or not camera.visible(self.z):
            return
        if self.fighting:
            cut = sprites.frames("Attack", tint=ENEMY_TINT)
        elif self.rushing:
            cut = sprites.frames("Run", row=0, tint=ENEMY_TINT)    # แถว 0 = วิ่งเข้าหากล้อง
        else:
            cut = sprites.frames("Idle", tint=ENEMY_TINT)
        n = min(self.count, C.MAX_DRAWN_PEOPLE)
        big_r = self.radius()
        # วาดเลื่อนไปข้างหน้าเท่ารัศมีกอง: ขอบหน้ากองอยู่ที่ z พอดี กลุ่มคนเราหยุดชนตรงนั้น ไม่ทับกัน
        cz = self.z + big_r
        spots = []
        for i in range(n):
            # วางเป็นวงก้นหอย (golden angle) กระจายเต็มวงเท่าๆ กัน ให้ดูเป็นก้อนกลมขนาดเท่ากลุ่มคน
            r = big_r * math.sqrt((i + 0.5) / n)
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

