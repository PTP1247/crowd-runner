"""กลุ่มคนของผู้เล่น   [เจ้าของ: B + ระบบแอนิเมชันวิ่ง]"""

import math
import random
from pathlib import Path

import pygame
import config as C

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "16x32"

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
        self.people = []          # คนที่จำลองฟิสิกส์จริง (ไม่เกิน C.SIM_PEOPLE) ใช้วาด + เช็กชน
        self._count = 0           # จำนวนคนจริง อาจมากกว่า len(people) มาก
        self.sprite_cache = {}    # (เฟรม, กว้าง, สูง) -> ภาพที่ย่อแล้ว

        # ==========================================
        # 1. ส่วนค้นหาและโหลดไฟล์ภาพ (ของคุณ Setthawut เดิม)
        # ==========================================
        # สร้างภาพสำรอง (สีเขียว) กรณีหาไฟล์ไม่เจอ (ปรับขนาดให้ตรงกับ 6 เฟรม 5 แถว)
        dummy = pygame.Surface((16 * 6, 32 * 5), pygame.SRCALPHA)
        pygame.draw.rect(dummy, (0, 255, 0), (0, 0, 16 * 6, 32 * 5))
        self.sheet_straight = dummy

        candidates = [
            ASSET_DIR / "Run-Sheet.png",
            ASSET_DIR / "Run.png",
            ASSET_DIR / "16x32 Run-Sheet.png",
            ASSET_DIR / "16x32 Run.png",
            Path("assets/16x32/Run-Sheet.png"),
            Path("assets/16x32/Run.png"),
        ]
        
        for candidate in candidates:
            try:
                if candidate.exists():
                    loaded = pygame.image.load(str(candidate)).convert_alpha()
                    self.sheet_straight = loaded
                    break
            except (pygame.error, FileNotFoundError, OSError):
                continue

        # ==========================================
        # 2. ส่วนหั่นภาพ 5 แถวและกลับด้านภาพ (โค้ดใหม่ที่เพิ่งเพิ่มเข้ามา)
        # ==========================================
        self.total_columns = 6  # จำนวนเฟรมแนวนอน (6 เฟรม)
        self.total_rows = 5     # จำนวนทิศทางแนวตั้ง (5 แถว)
        
        orig_w, orig_h = self.sheet_straight.get_size()
        self.frame_width = orig_w // self.total_columns
        self.frame_height = orig_h // self.total_rows
        
        # ระบุว่าทิศทางไหนอยู่แถวอะไร (เริ่มนับจาก 0)
        ROW_STRAIGHT = 4  # แถวล่างสุด: ท่าวิ่งตรง (วิ่งขึ้น หันหลังให้กล้อง)
        ROW_RIGHT = 3     # แถวรองล่างสุด: ท่าวิ่งขวา (ท่าเฉียงขึ้นขวา)

        self.frames_straight = []
        self.frames_left = []
        self.frames_right = []
        self.total_frames = self.total_columns
        
        # เริ่มหั่นภาพและพลิกภาพ!
        for i in range(self.total_frames):
            x_pos = i * self.frame_width
            
            # หั่นภาพ: ท่าวิ่งตรง
            rect_s = pygame.Rect(x_pos, ROW_STRAIGHT * self.frame_height, self.frame_width, self.frame_height)
            self.frames_straight.append(self.sheet_straight.subsurface(rect_s))
            
            # หั่นภาพ: ท่าวิ่งขวา
            rect_r = pygame.Rect(x_pos, ROW_RIGHT * self.frame_height, self.frame_width, self.frame_height)
            frame_right = self.sheet_straight.subsurface(rect_r)
            self.frames_right.append(frame_right)
            
            # สร้างภาพ: ท่าวิ่งซ้าย (เอาภาพวิ่งขวามาพลิกด้าน)
            frame_left = pygame.transform.flip(frame_right, True, False)
            self.frames_left.append(frame_left)
            
        # ==========================================
        # 3. สร้างจำนวนคนเริ่มต้น
        # ==========================================
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
        ยกกำลัง 0.4 (ไม่ใช่ 0.5): วัดแล้วตอนจำลองทุกคน ก้อนใหญ่อัดแน่นกว่าสูตรพื้นที่ล้วน
        ค่านี้ทำให้ความกว้างก้อนใกล้ของเดิม (1000 คน แผ่ข้างละ ~60)"""
        return (self._count / len(self.people)) ** 0.4 if self.people else 1.0

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


    def radius(self):
        """รัศมีของก้อนคน โดยประมาณ (ใช้กันไม่ให้ตกขอบถนน / คำนวณการชน)"""
        return C.PERSON_SPACING * math.sqrt(min(self.count, C.MAX_DRAWN_PEOPLE))

    def move(self, direction, dt, forward_speed=0):
        """direction: -1 = ซ้าย, +1 = ขวา, 0 = อยู่นิ่ง  (คีย์บอร์ด)
        forward_speed: ความเร็ววิ่งของด่าน  ยิ่งวิ่งเร็ว ยิ่งเลี้ยวเร็ว ไม่งั้นด่านเร็วๆ หลบไม่ทัน"""
        if direction:
            self.target_x = None
            side = max(C.CROWD_SIDE_SPEED, forward_speed * C.CROWD_SIDE_RATIO)
            self.x += direction * side * dt

    def update(self, dt):
        # 1. เลี้ยวตามเมาส์ (ถ้ามี)
        if self.target_x is not None:
            self.x += (self.target_x - self.x) * min(1.0, 10 * dt)
            
        # 2. ห้ามหลุดถนน
        limit = max(0.0, C.ROAD_HALF_W - self.radius())
        self.x = max(-limit, min(limit, self.x))
        
        # 📌 3. คำนวณความเร็วเลี้ยวที่แท้จริง (เทียบกับตำแหน่งของเฟรมที่แล้ว!)
        if hasattr(self, 'last_x') and dt > 0:
            self.crowd_vx = (self.x - self.last_x) / dt 
        else:
            self.crowd_vx = 0.0
            
        self.last_x = self.x  # เซฟตำแหน่งปัจจุบันไว้ใช้ในเฟรมถัดไป

        # --- โค้ดฟิสิกส์ด้านล่าง ปล่อยให้มันทำงานตามเดิมเลยครับ ---
        target_r = C.PERSON_SPACING * math.sqrt(len(self.people)) * 0.8
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
            
            # 📌 1. เลือก "กลุ่มลิ้นชักภาพที่หั่นไว้แล้ว" ตามทิศทางการวิ่ง
             # ในฟังก์ชัน draw
            # ใช้ความเร็วเลี้ยวรวมของกลุ่ม (crowd_vx) เป็นตัวตัดสินใจ
            if getattr(self, 'crowd_vx', 0) < -50:
                current_frames = self.frames_left
            elif getattr(self, 'crowd_vx', 0) > 50:
                current_frames = self.frames_right
            else:
                current_frames = self.frames_straight

            # 📌 2. คำนวณเฟรมภาพที่ต้องดึงมาแสดงผล (วนลูป 0 ถึง 5)
            frame_index = int(p.anim_t) % self.total_frames
            
            # 📌 3. หยิบภาพที่ตัดไว้แล้วออกมาจากลิ้นชักได้เลย (ไม่ต้องตัดใหม่แล้ว!)
            frame_surface = current_frames[frame_index]
            
            # 📌 4. ย่อ/ขยายรูปภาพตัวละครตามระยะลึก (3D Scale)
            new_w = max(1, int(self.frame_width * scale))
            new_h = max(1, int(self.frame_height * scale))
            # ย่อภาพครั้งเดียวต่อขนาด แล้วเก็บไว้ใช้ซ้ำ (scale ทุกคนทุกเฟรมกินเวลามาก)
            key = (id(frame_surface), new_w, new_h)
            scaled_sprite = self.sprite_cache.get(key)
            if scaled_sprite is None:
                if len(self.sprite_cache) > 2000:
                    self.sprite_cache.clear()
                scaled_sprite = self.sprite_cache[key] = pygame.transform.scale(frame_surface, (new_w, new_h))
            
            # 📌 5. คำนวณจังหวะตัวเด้ง (Bobbing) ขึ้นลง
            bob = math.sin(p.anim_t) * 1.5 * scale
            
            # 📌 6. แปะภาพตัวละครลงหน้าจอ
            screen.blit(scaled_sprite, (sx - new_w // 2, sy - new_h + bob))

        # --- วาดกล่องตัวเลขแสดงจำนวนคนด้านบน ---
        sx, sy, scale = camera.project(self.x, self.z)
        text = font.render(str(self.count), True, C.WHITE)
        bg = text.get_rect(center=(sx, sy - 70 * scale)).inflate(10, 4)
        pygame.draw.rect(screen, C.PLAYER_COLOR, bg, border_radius=6)
        screen.blit(text, text.get_rect(center=bg.center))

