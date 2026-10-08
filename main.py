"""จุดเริ่มเกม: game loop + state machine   [เจ้าของ: A]

รัน:  python main.py

State machine:  MENU --(เลือกด่าน: space/click)--> PLAYING --(ถึงเส้นชัย)--> WIN
                                                         +--(คนเหลือ 0)--> LOSE
                WIN/LOSE --(R)--> PLAYING ด่านเดิม,  --(M)--> MENU
"""
import sys
import random
import bisect
import pygame

import config as C
import ui
import scores
from camera import Camera
from crowd import Crowd
from level import load_level, list_levels, best_count

MENU, PLAYING, WIN, LOSE = "menu", "playing", "win", "lose"
ROAD_STRIP_PX = 2      # ลายอิฐบนถนน: แต่ละแถบสูงบนจอประมาณกี่พิกเซล (น้อย = เนียนแต่ช้า)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 64)
        self.camera = Camera()
        self.road_rows = self.make_road_rows()   # ลายถนนอิฐ (หั่นเป็นแถวไว้ล่วงหน้า)
        self.tuft_sprites = self.make_tuft_sprites()
        self.tuft_cache = {}                     # (แบบ, กว้าง) -> กอหญ้าที่ย่อแล้ว
        self.clouds = self.make_clouds()
        self.level_files = list_levels()
        self.level_names = [(f, load_level(f).name) for f in self.level_files]
        self.selected = 0                       # index ด่านที่เลือกในเมนู
        self.scores = scores.load_scores()
        self.unlock_all = False                 # ปุ่ม U ในเมนู: ปลดล็อกทุกด่านชั่วคราว (ไว้ทดสอบ/โชว์ ไม่บันทึกลงไฟล์)
        self.state = MENU
        self.reset()

    def reset(self):
        self.level = load_level(self.level_files[self.selected], random)   # สุ่มประตู+สิ่งกีดขวางใหม่ทุกรอบ
        self.result = None   # (ดาว, high score เดิม, สถิติใหม่ไหม) ตั้งค่าตอนจบด่าน
        self.best = best_count(self.level)   # คิดก่อนเล่น เพราะตอนปะทะ enemy.count จะลดลง
        self.crowd = Crowd(self.level.start_count)
        self.camera.z = 0.0
        self.next_index = 0  # object ถัดไปใน level.objects ที่กลุ่มคนยังไม่ถึง
        self.make_tufts()

    # ---------------- สร้างลายพิกเซล ----------------
    def make_road_rows(self, w=96, h=128):
        """สร้างลายอิฐปูทางแบบพิกเซล ต่อเนื่องทุกด้าน แล้วหั่นเป็นแถวไว้ใช้วาด"""
        rng = random.Random(7)                       # seed คงที่ ลายเดิมทุกครั้ง
        bw, bh = 16, 8                               # ขนาดอิฐ (w หาร bw ลงตัว, h หาร bh ลงตัว)
        mortar = (70, 62, 62)                        # สีร่องระหว่างอิฐ
        bricks = [(150, 98, 82), (160, 106, 88),     # โทนอิฐแดงน้ำตาล
                  (140, 90, 76), (168, 114, 94),
                  (132, 88, 78)]
        tex = pygame.Surface((w, h))
        tex.fill(mortar)
        for row in range(h // bh):
            shift = (bw // 2) if row % 2 else 0      # แถวคี่เยื้องครึ่งก้อน
            for col in range(w // bw):
                color = rng.choice(bricks)
                light = tuple(min(255, c + 14) for c in color)
                x0 = col * bw + shift
                y0 = row * bh
                for dy in range(bh - 1):             # เว้น 1 พิกเซลล่างเป็นร่อง
                    for dx in range(bw - 1):         # เว้น 1 พิกเซลขวาเป็นร่อง
                        c = light if dy == 0 else color   # ขอบบนสว่างนิดให้ดูนูน
                        tex.set_at(((x0 + dx) % w, y0 + dy), c)
        return [tex.subsurface((0, i, w, 1)).copy() for i in range(h)]

    def make_tuft_sprites(self):
        """กอหญ้าพิกเซลเล็กๆ 3 แบบ"""
        rng = random.Random(3)
        dark, light = (60, 120, 64), (130, 200, 105)
        sprites = []
        for _ in range(3):
            surf = pygame.Surface((9, 6), pygame.SRCALPHA)
            for bx in (1, 4, 7):
                hgt = rng.randint(2, 5)
                for y in range(hgt):
                    surf.set_at((bx, 5 - y), light if y == hgt - 1 else dark)
            sprites.append(surf)
        return sprites

    def make_tufts(self):
        """สุ่มตำแหน่งกอหญ้าตลอดด่าน (ซ้าย-ขวานอกถนน) เรียงตาม z ไว้ล่วงหน้า"""
        rng = random.Random(11)
        self.tufts = []
        for z in range(0, int(self.level.finish_z) + 400, 40):
            for _ in range(2):
                side = rng.choice((-1, 1))
                x = side * rng.uniform(C.ROAD_HALF_W + 30, C.ROAD_HALF_W + 700)
                self.tufts.append((z, x, rng.randrange(len(self.tuft_sprites))))
        self.tuft_zs = [t[0] for t in self.tufts]

    def make_clouds(self):
        """เมฆก้อนเหลี่ยมแบบพิกเซล"""
        white, shade = (245, 248, 255), (214, 226, 245)
        shapes = [
            [(2, 3, 10, 3), (0, 4, 14, 3), (4, 1, 6, 3)],
            [(1, 2, 8, 3), (0, 3, 11, 2), (3, 0, 4, 3)],
        ]
        clouds = []
        for rects in shapes:
            surf = pygame.Surface((15, 8), pygame.SRCALPHA)
            for x, y, w, h in rects:
                pygame.draw.rect(surf, white, (x, y, w, h))
            pygame.draw.rect(surf, shade, (0, 6, 14, 1))
            clouds.append(pygame.transform.scale(surf, (15 * 8, 8 * 8)))
        return clouds

    def draw_sky(self):
        # ไล่สีเป็นขั้นๆ ให้ดูเป็นพิกเซล
        top, bottom, bands = (70, 140, 230), (170, 215, 250), 8
        h = C.HORIZON_Y
        for i in range(bands):
            t = i / (bands - 1)
            color = tuple(int(top[k] + (bottom[k] - top[k]) * t) for k in range(3))
            self.screen.fill(color, (0, i * h // bands, C.SCREEN_W, h // bands + 1))
        # เมฆลอยช้าๆ วนกลับมาเมื่อหลุดจอ
        t = pygame.time.get_ticks() / 1000
        for cloud, y, speed, x0 in ((self.clouds[0], 50, 12, 80),
                                    (self.clouds[1], 110, 8, 300),
                                    (self.clouds[0], 170, 5, 520)):
            x = (x0 + t * speed) % (C.SCREEN_W + 240) - 120
            self.screen.blit(cloud, (x, min(y, h - cloud.get_height())))

    # ---------------- input ----------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_v:
                    self.camera.toggle_mode()
                if self.state == MENU:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        self.move_selection(-1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.move_selection(1)
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.start_level()
                    elif event.key == pygame.K_u:
                        self.unlock_all = not self.unlock_all
                        if not self.unlocked(self.selected):   # ปิดแล้วด่านที่เลือกอยู่ล็อก กลับไปด่านแรก
                            self.selected = 0
                elif self.state in (WIN, LOSE):
                    if event.key == pygame.K_r:
                        self.start_level()
                    elif event.key == pygame.K_m:
                        # ชนะแล้วเลื่อนไปด่านถัดไปที่เพิ่งปลดล็อกให้เลย
                        if self.state == WIN and self.unlocked(self.selected + 1):
                            self.selected += 1
                        self.reset()
                        self.state = MENU
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.state == MENU:
                for i in range(len(self.level_files)):
                    if ui.menu_row_rect(i).collidepoint(event.pos) and self.unlocked(i):
                        self.selected = i
                        self.start_level()
                        break

        if self.state == PLAYING:
            keys = pygame.key.get_pressed()
            direction = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            self.crowd.move(direction, self.dt, self.level.speed)
            if pygame.mouse.get_pressed()[0]:  # กดเมาส์ค้างแล้วลาก
                mx, _ = pygame.mouse.get_pos()
                self.crowd.target_x = self.camera.unproject_x(mx, self.crowd.z)

    def unlocked(self, i):
        if i >= len(self.level_files):
            return False
        return self.unlock_all or scores.is_unlocked(self.level_files, i, self.scores)

    def move_selection(self, step):
        """เลื่อนไปด่านที่ปลดล็อกแล้วถัดไป (ข้ามด่านที่ล็อก วนรอบได้)"""
        n = len(self.level_files)
        i = self.selected
        for _ in range(n):
            i = (i + step) % n
            if self.unlocked(i):
                self.selected = i
                return

    def start_level(self):
        self.reset()
        self.state = PLAYING

    def finish_level(self, won):
        """เรียกครั้งเดียวตอนจบด่าน: คิดดาว + บันทึก high score"""
        filename = self.level_files[self.selected]
        count = self.crowd.count if won else 0
        star_count = scores.stars(won, count, self.best)
        old = self.scores.get(filename)
        new_record = won and scores.record(filename, count, star_count)
        self.scores = scores.load_scores()
        self.result = (star_count, old, new_record)
        self.state = WIN if won else LOSE

    # ---------------- update ----------------
    def update(self):
        if self.state != PLAYING:
            return
        # คูณ dt เสมอ: ความเร็วจะเท่ากันไม่ว่าเครื่องจะได้ 30 หรือ 144 FPS
        self.camera.z += self.level.speed * self.dt
        self.crowd.z = self.camera.z + C.CROWD_OFFSET
        self.crowd.update(self.dt)

        # ตรวจว่ากลุ่มคนวิ่ง "ถึง/เลย" object ไหนบ้างในเฟรมนี้
        # ใช้ >= แทน == เพราะ z เพิ่มทีละหลาย unit ต่อเฟรม อาจกระโดดข้ามค่าพอดีไป
        objects = self.level.objects
        while self.next_index < len(objects) and self.crowd.z >= objects[self.next_index].z:
            objects[self.next_index].on_reach(self.crowd)
            self.next_index += 1

        for obj in objects:
            obj.update(self.dt)

        if self.crowd.count <= 0:
            self.finish_level(False)
        elif self.crowd.z >= self.level.finish_z:
            self.finish_level(True)

    # ---------------- draw ----------------
    def draw_world(self):
        cam = self.camera
        near, far = cam.z + C.Z_NEAR, cam.z + C.Z_FAR

        # ท้องฟ้า + พื้น
        if cam.mode == "depth":
            self.draw_sky()
            pygame.draw.rect(self.screen, C.GROUND_A, (0, C.HORIZON_Y, C.SCREEN_W, C.SCREEN_H))
        else:
            self.screen.fill(C.GROUND_A)

        # พื้นหญ้าแถบสลับสี (perspective)
        band, gw = 120, 3000
        z = (int(near) // band) * band
        while z < far:
            if (z // band) % 2:
                a, b = max(z, near), min(z + band, far)
                pts = [cam.project(x, zz)[:2] for x, zz in ((-gw, a), (gw, a), (gw, b), (-gw, b))]
                pygame.draw.polygon(self.screen, C.GROUND_B, pts)
            z += band

        # กอหญ้า: วาดไกล -> ใกล้
        lo = bisect.bisect_left(self.tuft_zs, near)
        hi = bisect.bisect_right(self.tuft_zs, far)
        for z, x, k in reversed(self.tufts[lo:hi]):
            sx, sy, s = cam.project(x, z)
            w = int(9 * 3 * s)
            if w >= 2:
                sprite = self.tuft_cache.get((k, w))
                if sprite is None:
                    sprite = self.tuft_cache[(k, w)] = pygame.transform.scale(
                        self.tuft_sprites[k], (w, max(1, int(w * 6 / 9))))
                self.screen.blit(sprite, (sx - w // 2, sy - sprite.get_height()))

        # ถนน = สี่เหลี่ยมคางหมูจากใกล้ไปไกล (ในโหมด flat จะกลายเป็นสี่เหลี่ยมผืนผ้าเอง)
        corners = [cam.project(x, z)[:2] for x, z in
                   ((-C.ROAD_HALF_W, near), (C.ROAD_HALF_W, near), (C.ROAD_HALF_W, far), (-C.ROAD_HALF_W, far))]
        pygame.draw.polygon(self.screen, C.ROAD, corners)   # พื้นรองกันช่องโหว่

        # ลายอิฐบนถนน: หั่นเป็นแถบบางๆ ตามแกน z ความกว้างแต่ละแถบตาม perspective
        # ความหนาแถบปรับตามระยะ: ให้แต่ละแถบสูงบนจอ ~ROAD_STRIP_PX พิกเซล (ไกลๆ แถบเดียวคลุมหลายร้อย unit)
        # ทำไม: เดิมหั่นทีละ 4 unit เสมอ = ~500 แถบ/เฟรม ส่วนใหญ่สูงไม่ถึง 1 พิกเซล เปลืองเวลาเปล่าๆ
        min_step, tile = 4, 200        # min_step = แถบบางสุด (world unit) / tile = ความยาวลายต่อรอบ
        n = len(self.road_rows)
        z = near
        while z < far:
            dy = abs(cam.project(0, z + 1)[1] - cam.project(0, z)[1]) or 1e-6   # พิกเซลต่อ 1 unit ตรงนี้
            z1 = min(z + max(min_step, ROAD_STRIP_PX / dy), far)
            xl, y0, _ = cam.project(-C.ROAD_HALF_W, z)
            xr, _, _ = cam.project(C.ROAD_HALF_W, z)
            _, y1, _ = cam.project(0, z1)
            w, h = int(xr - xl), int(abs(y0 - y1)) + 1       # +1 กันรอยแตก
            if w > 0 and h > 0:
                v = (z % tile) / tile                         # ลายต่อเนื่องเอง ไม่ต้องสะท้อน
                row = self.road_rows[min(n - 1, int(v * n))]
                self.screen.blit(pygame.transform.scale(row, (w, h)), (xl, min(y0, y1)))
            z = z1

        # เส้นประกลางถนน ทำให้รู้สึกว่ากำลังวิ่ง (ถ้าไม่อยากได้บนลายอิฐ ลบบล็อกนี้ทิ้งได้)
        step = 200
        z = (int(near) // step + 1) * step
        while z < far:
            x1, y1, _ = cam.project(0, z)
            x2, y2, _ = cam.project(0, z + step / 2)
            pygame.draw.line(self.screen, C.ROAD_EDGE, (x1, y1), (x2, y2), 3)
            z += step

        # เส้นชัย
        if cam.visible(self.level.finish_z):
            x1, y, s = cam.project(-C.ROAD_HALF_W, self.level.finish_z)
            x2, _, _ = cam.project(C.ROAD_HALF_W, self.level.finish_z)
            pygame.draw.line(self.screen, C.FINISH_COLOR, (x1, y), (x2, y), max(2, int(12 * s)))

        # painter's algorithm: วาดของไกล (z มาก) ก่อน ของใกล้ทับทีหลัง
        # กลุ่มคนอยู่ใกล้กล้องที่สุดเสมอ จึงวาดท้ายสุด
        for obj in sorted(self.level.objects, key=lambda o: -o.z):
            obj.draw(self.screen, cam, self.font)
        self.crowd.draw(self.screen, cam, self.font)

    def draw(self):
        if self.state == MENU:
            unlocked = [self.unlocked(i) for i in range(len(self.level_files))]
            ui.draw_menu(self.screen, self.big_font, self.font, self.level_names, self.selected, self.scores,
                         unlocked, self.unlock_all)
        else:
            self.draw_world()
            progress = self.crowd.z / self.level.finish_z
            ui.draw_hud(self.screen, self.font, self.level, progress)
            if self.state in (WIN, LOSE):
                ui.draw_end(self.screen, self.big_font, self.font, self.state == WIN, self.crowd.count,
                            *self.result)
        pygame.display.flip()

    def run(self):
        while True:
            # tick() คืนเวลาที่ผ่านไปเป็นมิลลิวินาที -> แปลงเป็นวินาที
            # min(..., 0.05) กันเฟรมกระตุกนานๆ (เช่น ลากหน้าต่าง) ทำให้วิ่งทะลุประตู
            self.dt = min(self.clock.tick(C.FPS) / 1000, 0.05)
            self.handle_events()
            self.update()
            self.draw()


if __name__ == "__main__":
    Game().run()