"""กลุ่มคนของผู้เล่น   [เจ้าของ: B + ระบบแอนิเมชันวิ่ง]"""

import math
import random

import pygame
from game.core import config as C
from game.core import sprites

RUN_STRAIGHT_ROW = 4 # ชีต Run แถวล่างสุด: วิ่งตรงขึ้นไป หันหลังให้กล้อง
RUN_RIGHT_ROW = 3    # ชีต Run แถวรองล่างสุด: วิ่งเฉียงขึ้นขวา
ATTACK_ROW = 4      # แถวล่างสุดของ Attack-Sheet: ต่อยแบบหันหลังให้กล้อง (หันเข้าหาศัตรู/บอส)
ATTACK_SPEED = 1.2   # anim_t เดินราว 10/วินาที -> ท่าต่อย ~12 เฟรม/วินาที

# รัศมีที่ 90% ของคนในก้อนอยู่ข้างใน ตามจำนวน "คนจำลอง" (ไม่เกิน SIM_PEOPLE)
# วัดจากฟิสิกส์ใน Crowd.update() ตอน PERSON_SPACING = 9 (ก้อนอัดแน่นขึ้นเรื่อยๆ จึงไม่โตตาม sqrt ตรงๆ)
# ใช้ให้กองศัตรูมีขนาดเท่ากลุ่มคนจำนวนเท่ากัน  ถ้าแก้ฟิสิกส์ test_enemy_group_same_size_as_crowd จะบอกให้วัดใหม่
_RADIUS_TABLE = [(1, 1.1), (2, 4.3), (5, 9.1), (10, 12.4), (20, 18.0),
                 (40, 21.2), (70, 22.8), (100, 23.3), (150, 23.7)]


def blob_radius(count):
    """รัศมีของก้อนคน count คน (90% ของคนอยู่ในวงนี้) สูตรเดียวกับที่ Crowd วาดจริง:
    รัศมีของคนจำลอง x ตัวคูณ spread() (= (คนจริง / คนจำลอง) ** C.CROWD_GROWTH)"""
    if count <= 0:
        return 0.0
    sim = min(count, C.SIM_PEOPLE)
    r = _RADIUS_TABLE[-1][1]
    for (n0, r0), (n1, r1) in zip(_RADIUS_TABLE, _RADIUS_TABLE[1:]):
        if sim <= n1:
            r = r0 + (r1 - r0) * (sim - n0) / (n1 - n0) if sim > n0 else r0
            break
    return r * (C.PERSON_SPACING / 9) * (count / sim) ** C.CROWD_GROWTH


def edge_gap(count):
    """ศูนย์กลางก้อน count คน เข้าใกล้ขอบถนนได้ไม่เกินระยะนี้ (ขอบนอกก้อนห่างขอบถนน ROAD_EDGE_MARGIN)"""
    return blob_radius(count) + C.ROAD_EDGE_MARGIN

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
        self.people = []          # คนที่จำลองฟิสิกส์จริง (ไม่เกิน C.SIM_PEOPLE) ใช้วาด + เช็กชน
        self._count = 0           # จำนวนคนจริง อาจมากกว่า len(people) มาก
        self.sprite_cache = {}    # (เฟรม, กว้าง, สูง) -> ภาพที่ย่อแล้ว
        self.attacking = False    # main.py ตั้งเป็น True ระหว่างปะทะศัตรู/บอส: วาดท่าต่อยแทนท่าวิ่ง
        self.waiting = False      # main.py ตั้งเป็น True ตอนบอสกำลังวิ่งเข้ามา: ยืนรอ (ยังไม่ต่อย)
        self.last_x = None        # x ของเฟรมที่แล้ว ใช้คิดความเร็วเลี้ยว
        self.crowd_vx = 0.0       # ความเร็วเลี้ยวจริง (เลือกท่าวิ่งตรง / เฉียงซ้าย / เฉียงขวา)

        # ท่าวิ่งจากชีต Run: แถว 4 = วิ่งตรง (หันหลังให้กล้อง), แถว 3 = วิ่งเฉียงขวา, เฉียงซ้าย = กลับด้านแถว 3
        self.frames_straight = sprites.frames("Run", RUN_STRAIGHT_ROW)
        self.frames_right = sprites.frames("Run", RUN_RIGHT_ROW)
        self.frames_left = [pygame.transform.flip(f, True, False) for f in self.frames_right]
        self.total_frames = len(self.frames_straight)
        self.set_count(count)


    # ทำไมไม่จำลองทุกคน: ฟิสิกส์คิดทีละคนทุกเฟรม คน 3000 คนใช้ ~25 ms/เฟรม (เกินงบ 16.7 ms ของ 60 FPS)
    # จึงจำลองแค่ไม่เกิน C.SIM_PEOPLE คนเป็น "ตัวแทน" แล้วขยายระยะห่างด้วย spread()
    # ให้ก้อนกว้างเท่ากับคนจริงทั้งหมด  คนตัวแทน 1 คนโดนชน = เสียคนจริงตามสัดส่วน

    @property
    def count(self):              # จำนวนจริง (ใช้คำนวณ)
        return self._count

    @count.setter
    def count(self, n):
        self.set_count(n)

    def set_count(self, n):
        self._count = max(0, int(n))
        sim = min(self._count, C.SIM_PEOPLE)
        while len(self.people) < sim:
            self.people.append(Person(random.uniform(-5, 5), random.uniform(-5, 5)))
        del self.people[sim:]

    def spread(self):
        """ตัวคูณระยะของคนตัวแทน -> ระยะจริง
        ยกกำลัง C.CROWD_GROWTH: ต่ำกว่า 0.5 (สูตรพื้นที่) เพราะวาดแค่ MAX_DRAWN_PEOPLE คน
        ถ้าก้อนขยายเต็มที่ คนที่วาดจะกระจายห่างกันจนดูโหรง"""
        return (self._count / len(self.people)) ** C.CROWD_GROWTH if self.people else 1.0

    def offset(self, p):
        """ตำแหน่ง (dx, dz) จริงของคนตัวแทน p เทียบกับศูนย์กลางก้อน"""
        k = self.spread()
        return p.dx * k, p.dz * k

    def add(self, n):
        self.set_count(self.count + n)

    def remove(self, people):
        """เอาคนตัวแทนใน people ออก แล้วหักคนจริงตามสัดส่วน คืนจำนวนคนจริงที่เสียไป"""
        gone = set(map(id, people))
        n_sim = len(self.people)
        hit = sum(1 for p in self.people if id(p) in gone)
        if not hit:
            return 0
        k = self.spread()
        lost = self._count if hit == n_sim else round(self._count * hit / n_sim)
        self.people = [p for p in self.people if id(p) not in gone]
        self.set_count(self._count - lost)     # ก้อนใหญ่: เติมคนตัวแทนกลับให้ครบ

        # 📌 เพิ่มระบบ "จัดสมดุลศูนย์ถ่วงใหม่ (Center of Mass)"
        if self.people:
            # 1. หาพิกัดเฉลี่ย (จุดกึ่งกลางที่แท้จริง) ของคนที่รอดชีวิต
            avg_dx = sum(p.dx for p in self.people) / len(self.people)
            avg_dz = sum(p.dz for p in self.people) / len(self.people)

            # 2. ขยับตำแหน่งกลุ่ม (self.x) ให้วิ่งตามไปหาคนที่รอดชีวิต
            self.x += avg_dx * k
            
            # 3. ปรับระยะของคนแต่ละคนให้สัมพันธ์กับศูนย์กลางใหม่
            # (ไม่ต้องห่วง ภาพจะไม่กระตุกเลย แต่มันจะทำให้แรงดึงดูดกลับมาสมดุลทันที!)
            for p in self.people:
                p.dx -= avg_dx
                p.dz -= avg_dz
        return lost


    def depth_range(self):
        """(คนหลังสุด, คนหน้าสุด) ตามแกน z เทียบกับศูนย์กลางก้อน  นับเฉพาะคนที่วาดจริง (ที่ผู้เล่นเห็น)"""
        drawn = self.people[:C.MAX_DRAWN_PEOPLE]
        if not drawn:
            return 0.0, 0.0
        k = self.spread()
        dz = [p.dz for p in drawn]
        return min(dz) * k, max(dz) * k

    def back_z(self):
        """z ของคนที่อยู่ท้ายสุด (main.py: ต้องผ่านเส้นชัยทุกคนก่อนจบด่าน/เริ่มสู้บอส)"""
        return self.z + self.depth_range()[0]

    def front_z(self):
        """z ของคนที่อยู่หน้าสุด (boss.py: บอสเดินมาหยุดตรงหน้าคนแถวแรก)"""
        return self.z + self.depth_range()[1]

    def radius(self):
        """ระยะที่ศูนย์กลางก้อนต้องห่างขอบถนน = ขนาดจริงของก้อน (blob_radius) + ROAD_EDGE_MARGIN
        ก้อนทุกขนาดจึงหยุดห่างขอบถนนเท่ากัน  level.crowd_limit ใช้สูตรเดียวกัน (ต้องแก้คู่กัน)"""
        return edge_gap(self.count)

    def move(self, direction, dt, forward_speed=0):
        """direction: -1 = ซ้าย, +1 = ขวา, 0 = อยู่นิ่ง  (คีย์บอร์ด)
        forward_speed: ความเร็ววิ่งของด่าน  ยิ่งวิ่งเร็ว ยิ่งเลี้ยวเร็ว ไม่งั้นด่านเร็วๆ หลบไม่ทัน"""
        if direction:
            side = max(C.CROWD_SIDE_SPEED, forward_speed * C.CROWD_SIDE_RATIO)
            self.x += direction * side * dt

    def update(self, dt):
        # 1. ห้ามหลุดถนน
        limit = max(0.0, C.ROAD_HALF_W - self.radius())
        self.x = max(-limit, min(limit, self.x))
        
        # 2. ความเร็วเลี้ยวจริง (เทียบกับตำแหน่งเฟรมที่แล้ว) ใช้เลือกท่าวิ่งตอนวาด
        self.crowd_vx = (self.x - self.last_x) / dt if self.last_x is not None and dt > 0 else 0.0
        self.last_x = self.x

        # 3. ฟิสิกส์คนตัวแทน: ดึงเข้าหาศูนย์กลาง + ผลักคนที่ชิดเกินไป + ส่ายเล็กน้อย
        target_r = C.PERSON_SPACING * 0.8
        for p in self.people:
            fx = fz = 0.0
            # ดึงเข้าหาศูนย์กลาง
            d = math.hypot(p.dx, p.dz) or 0.001
            if d > target_r * 0.3:
                pull = (d - target_r * 0.3) * C.CROWD_COHESION
                fx -= p.dx / d * pull
                fz -= p.dz / d * pull
            
            # ผลักคนใกล้เคียง
            for q in random.sample(self.people, min(len(self.people), 8)):
                if q is p:
                    continue
                ddx, ddz = p.dx - q.dx, p.dz - q.dz
                dist = math.hypot(ddx, ddz) or 0.001
                if dist < C.PERSON_SPACING:
                    push = (C.PERSON_SPACING - dist) * C.CROWD_SEPARATION
                    fx += ddx / dist * push
                    fz += ddz / dist * push
            
            # สุ่มส่าย (ฟิสิกส์เดิม)
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
        k = self.spread()
        for p in sorted(self.people[:C.MAX_DRAWN_PEOPLE], key=lambda p: -p.dz):
            sx, sy, scale = camera.project(self.x + p.dx * k, self.z + p.dz * k)
            
            # 1. เลือกชุดท่า: ยืนรอบอส / ต่อย / วิ่ง (ตรง หรือเฉียงตามความเร็วเลี้ยว crowd_vx)
            if self.waiting:
                # บอสกำลังวิ่งเข้ามา: ยืนรอ (หันหลังให้กล้องเหมือนตอนต่อย)
                current_frames = sprites.frames("Idle", ATTACK_ROW)
                frame_index = int(p.anim_t * ATTACK_SPEED) % len(current_frames)
            elif self.attacking:
                # ระหว่างปะทะ: ท่าต่อย  anim_t แต่ละคนเริ่มไม่เท่ากัน จึงต่อยสลับจังหวะกันเอง ไม่พร้อมกันทั้งก้อน
                current_frames = sprites.frames("Attack", ATTACK_ROW)
                frame_index = int(p.anim_t * ATTACK_SPEED) % len(current_frames)
            else:
                if self.crowd_vx < -50:
                    current_frames = self.frames_left
                elif self.crowd_vx > 50:
                    current_frames = self.frames_right
                else:
                    current_frames = self.frames_straight
                frame_index = int(p.anim_t) % self.total_frames
            frame_surface = current_frames[frame_index]

            # 2. ย่อ/ขยายตามระยะลึก (scale จาก camera.project)
            new_w = max(1, int(frame_surface.get_width() * scale))
            new_h = max(1, int(frame_surface.get_height() * scale))
            # ย่อภาพครั้งเดียวต่อขนาด แล้วเก็บไว้ใช้ซ้ำ (scale ทุกคนทุกเฟรมกินเวลามาก)
            key = (id(frame_surface), new_w, new_h)
            scaled_sprite = self.sprite_cache.get(key)
            if scaled_sprite is None:
                if len(self.sprite_cache) > 2000:
                    self.sprite_cache.clear()
                scaled_sprite = self.sprite_cache[key] = pygame.transform.scale(frame_surface, (new_w, new_h))
            
            # 3. ตัวเด้งขึ้นลงตามจังหวะวิ่ง แล้ววาด (เท้าอยู่ที่ sy)
            bob = math.sin(p.anim_t) * 1.5 * scale
            screen.blit(scaled_sprite, (sx - new_w // 2, sy - new_h + bob))

        # --- วาดกล่องตัวเลขแสดงจำนวนคนด้านบน ---
        sx, sy, scale = camera.project(self.x, self.z)
        text = font.render(str(self.count), True, C.WHITE)
        bg = text.get_rect(center=(sx, sy - 70 * scale)).inflate(10, 4)
        pygame.draw.rect(screen, C.PLAYER_COLOR, bg, border_radius=6)
        screen.blit(text, text.get_rect(center=bg.center))

