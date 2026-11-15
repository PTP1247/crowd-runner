"""จุดเริ่มเกม: game loop + state machine   [เจ้าของ: A]

รัน:  python main.py

State machine:  MENU --(เลือกด่าน: space/enter/คลิก)--> PLAYING --(ถึงเส้นชัย)--> WIN
                                                         +--(คนเหลือ 0)--> LOSE
                PLAYING --(P / Esc)--> PAUSED --(Esc / P)--> PLAYING,  --(M)--> MENU
                MENU --(ปุ่ม Music & Sound)--> SETTINGS --(Esc / คลิกนอกแผ่น)--> MENU
                MENU --(ปุ่ม Reset scores)--> CONFIRM --(Reset: ลบคะแนน / Cancel / Esc)--> MENU
                WIN --(R)--> PLAYING ด่านเดิม,  --(Enter)--> ด่านถัดไป (ชนะ) / เล่นใหม่ (แพ้),  --(M)--> MENU
"""
import sys
import math
import random
import bisect
import pygame

from game.core import config as C
from game import ui
from game.core import scores
from game.core.camera import Camera
from game.world.crowd import Crowd
from game.core import sound
from game.world.gate import GatePair
from game.world.level import load_level, list_levels, best_count, difficulty
from game.world.obstacle import Obstacle
from game.world.effects import Effects
from game.world.enemy import EnemyGroup, pull_crowd
from game.world import trees

MENU, PLAYING, PAUSED, WIN, LOSE = "menu", "playing", "paused", "win", "lose"
SETTINGS = "settings"     # หน้าปรับเสียงที่เปิดจากเมนู
CONFIRM = "confirm"       # ถามยืนยันก่อนลบคะแนนทั้งหมด (ปุ่ม Reset scores)
MENU_KEYS_SIDE = (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d)   # เมนู/แผ่นยืนยัน: สลับปุ่มซ้าย-ขวา
PAUSE_LEFT = (pygame.K_LEFT, pygame.K_a)       # หน้าหยุดเกม/หน้าปรับเสียง: ลดความดัง
PAUSE_RIGHT = (pygame.K_RIGHT, pygame.K_d)     # เพิ่มความดัง
PAUSE_STEP = 0.1          # กดหนึ่งครั้ง = 10%
PAUSE_HOLD = 0.35         # กดค้างเกินกี่วินาทีถึงเลื่อนต่อเนื่อง
PAUSE_SLIDE = 0.8         # เลื่อนต่อเนื่องกี่ส่วนต่อวินาที (0.8 = 80%/วินาที)
ROAD_STRIP_PX = 2      # ลายอิฐบนถนน: แถบไกลๆ สูงบนจอประมาณกี่พิกเซล (น้อย = เนียนแต่ช้า)
ROAD_TILE = 200        # ลายอิฐ 1 รอบยาวกี่ unit ตามแกน z
TIP_TIME = 5.0         # คำแนะนำด่านแรกโชว์กี่วินาที
HIT_RATE = 14          # ระหว่างปะทะ: ประกายหมัดอย่างน้อยกี่ครั้งต่อวินาที (บวกเพิ่มตามจำนวนคนที่หายไป)
RUSH_DUST_RATE = 30    # ศัตรูวิ่งเข้ามา: ฝุ่นฟุ้งกี่ก้อนต่อวินาที
TIPS = ["Steer: Left/Right or A/D", "Take the gate that gives MORE people",
        "Dodge red blocks, beat the red army"]

class Game:
    def __init__(self):
        pygame.init()
        sound.init()
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 64)
        self.camera = Camera()
        self.road_rows = self.make_road_rows()   # ลายถนนอิฐ (หั่นเป็นแถวไว้ล่วงหน้า)
        self.road_mips = self.make_road_mips(self.road_rows)
        self.tuft_sprites = self.make_tuft_sprites()
        self.tuft_cache = {}                     # (แบบ, กว้าง) -> กอหญ้าที่ย่อแล้ว
        tree_sprites = trees.make_tree_sprites()  # ต้นไม้ข้างถนน 3 แบบ + ดอกไม้ + แบบกลับซ้ายขวา
        self.tree_sprites = [tree_sprites, [pygame.transform.flip(t, True, False) for t in tree_sprites]]
        self.tree_cache = {}
        self.clouds = self.make_clouds()
        self.level_files = list_levels()
        plain = [load_level(f) for f in self.level_files]      # ด่านตามไฟล์ (ไม่สุ่ม) โหลดครั้งเดียว ใช้ชื่อ + ความยากในเมนู
        self.level_names = [(f, lv.name) for f, lv in zip(self.level_files, plain)]
        self.level_tiers = [ui.difficulty_tier(difficulty(lv)) for lv in plain]
        self.selected = 0                       # index ด่านที่เลือกในเมนู
        self.scores = scores.load_scores()
        self.menu_button = None                 # เมนู: ไฮไลต์อยู่ที่ปุ่มไหน "sound"/"reset" (None = แถวด่าน)
        self.confirm_focus = 0                  # แผ่นยืนยันลบคะแนน: 0 = Cancel, 1 = Reset
        self.pause_focus = 0                    # หน้าหยุดเกม/หน้าปรับเสียง: แถวที่เลือก (0 = Music, 1 = Effect)
        self.pause_drag = None                  # กำลังลากสไลเดอร์แถวไหนด้วยเมาส์
        self.pause_hold = 0.0                   # กดซ้าย/ขวาค้างมานานเท่าไร (ค้างนานแล้วเลื่อนต่อเนื่อง)
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
        self.fight = None    # ศัตรูที่กำลังปะทะอยู่ (ระหว่างนี้หยุดวิ่ง)
        self.boss_music = False   # บอสเริ่มตีกันแล้ว: เปิดเพลงบอสค้างไว้จนจบด่าน (ดู music_theme)
        self.popups = []     # [ข้อความ, สี, อายุวินาที] ตัวเลขลอยเหนือก้อนคน
        self.lose_cause = None
        self.elapsed = 0.0   # เล่นด่านนี้มากี่วินาทีแล้ว (ใช้โชว์คำแนะนำช่วงแรก)
        self.effects = Effects()   # ประกายหมัด / เศษกระเด็น ตอนปะทะ
        self.hit_timer = 0.0
        self.dust_timer = 0.0
        self.make_tufts()
        self.trees = trees.scatter(self.level.finish_z, random)   # ตำแหน่งต้นไม้สุ่มใหม่ทุกรอบ
        self.tree_zs = [t[0] for t in self.trees]

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

    @staticmethod
    def make_road_mips(rows):
        """ลายถนนหลายระดับความละเอียด: ระดับ 0 = แถวจริง, ระดับ L = เฉลี่ยสีทีละ 2^L แถว
        ใช้กับถนนไกลๆ ที่แถบบนจอ 1 แถบคลุมหลายแถวของลาย (จำนวนแถวต้องเป็นกำลังของ 2)"""
        mips = [rows]
        while len(mips[-1]) > 1:
            prev = mips[-1]
            mips.append([pygame.transform.average_surfaces(prev[i:i + 2]) for i in range(0, len(prev), 2)])
        return mips

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
                sound.save_settings()          # ปรับเสียงในหน้าหยุดแล้วปิดหน้าต่างเลย ก็ยังจำค่าไว้
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                self.handle_key(event.key)
            elif self.state in (PAUSED, SETTINGS) and event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN,
                                                                      pygame.MOUSEBUTTONUP):
                self.handle_pause_mouse(event)
            elif self.state == MENU and event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                self.handle_menu_mouse(event)
            elif self.state == CONFIRM and event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                self.handle_confirm_mouse(event)
        if self.state in (PAUSED, SETTINGS):
            self.hold_pause_keys()

        # คุมด้วยคีย์บอร์ดอย่างเดียว (ไม่รับเมาส์)  เจอศัตรูแล้ว (วิ่งเข้าหา + ปะทะ) เลี้ยวไม่ได้ ถูกดึงเข้าหาศัตรู
        if self.state == PLAYING and not self.crowd_locked():
            keys = pygame.key.get_pressed()
            direction = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            self.crowd.move(direction, self.dt, self.level.speed)

    def crowd_locked(self):
        """เจอศัตรูแล้ว: ตั้งแต่ศัตรูวิ่งพุ่งเข้าหาจนปะทะจบ ผู้เล่นคุมกลุ่มคนไม่ได้"""
        if self.fight is not None:
            return True
        objects = self.level.objects
        nxt = objects[self.next_index] if self.next_index < len(objects) else None
        return isinstance(nxt, EnemyGroup) and nxt.rushing

    def handle_key(self, key):
        if key == pygame.K_n:
            sound.toggle_mute()
        if self.state == MENU:
            if key in (pygame.K_UP, pygame.K_w):
                self.move_selection(-1)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.move_selection(1)
            elif key in MENU_KEYS_SIDE and self.menu_button:   # อยู่ที่ปุ่มล่าง: ซ้าย/ขวา สลับสองปุ่ม
                self.menu_button = "reset" if self.menu_button == "sound" else "sound"
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.menu_button == "sound":
                    self.open_settings()
                elif self.menu_button == "reset":
                    self.open_confirm()
                else:
                    self.start_level()
            elif key == pygame.K_u:                    # ปุ่มลับไว้ทดสอบ/โชว์ (ไม่มีคำแนะนำบนจอ)
                self.unlock_all = not self.unlock_all
                if not self.unlocked(self.selected):   # ปิดแล้วด่านที่เลือกอยู่ล็อก กลับไปด่านแรก
                    self.selected = 0
        elif self.state == PLAYING:
            if key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = PAUSED
            elif key == pygame.K_r:
                self.start_level()
        elif self.state == PAUSED:
            # ปุ่มที่มีหน้าที่ของตัวเอง: R เริ่มใหม่, M เมนู, N เปิด/ปิดเสียงทั้งหมด (สลับไปแล้วข้างบน)
            # Esc (หรือ P ปุ่มเดียวกับตอนกดหยุด) = เล่นต่อ ("Press ESC to continue")  ปุ่มอื่นไม่ทำอะไร
            if self.sound_key(key):
                pass
            elif key in (pygame.K_r, pygame.K_m):
                sound.save_settings()
                self.start_level() if key == pygame.K_r else self.go_to_menu()
            elif key in (pygame.K_ESCAPE, pygame.K_p):
                self.close_sound_panel(PLAYING)
        elif self.state == SETTINGS:
            # หน้าปรับเสียงจากเมนู: ปุ่มเหมือนหน้าหยุดเกม  Esc/Backspace = กลับเมนู ("Press ESC to go back")
            if not self.sound_key(key) and key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.close_sound_panel(MENU)
        elif self.state == CONFIRM:
            # ถามยืนยันลบคะแนน: ซ้าย/ขวา (A/D) เลือก, Enter/Space ยืนยันปุ่มที่เลือก, Esc/Backspace = ยกเลิก
            if key in MENU_KEYS_SIDE:
                self.confirm_focus = 1 - self.confirm_focus
            elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.close_confirm(self.confirm_focus == 1)
            elif key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.close_confirm(False)
        elif self.state in (WIN, LOSE):
            if key == pygame.K_r and self.state == WIN:   # แพ้: ไม่มี R (Enter = เล่นใหม่)
                self.start_level()
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                # ชนะ: ไปด่านถัดไปเลย (ถ้ามี)  แพ้: เล่นใหม่
                if self.state == WIN and self.unlocked(self.selected + 1):
                    self.selected += 1
                self.start_level()
            elif key == pygame.K_m:
                self.go_to_menu()

    def sound_key(self, key):
        """ปุ่มในแผ่นปรับเสียง (หน้าหยุดเกม + หน้าปรับเสียง): ขึ้น/ลง (W/S) เลือกแถว,
        ซ้าย/ขวา (A/D) ปรับความดังทีละ 10%, Enter/Space เปิด/ปิดกล่อง   คืน True ถ้าเป็นปุ่มของแผ่นนี้"""
        channel = ui.PAUSE_ROWS[self.pause_focus][0]
        if key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
            step = -1 if key in (pygame.K_UP, pygame.K_w) else 1
            self.pause_focus = (self.pause_focus + step) % len(ui.PAUSE_ROWS)
        elif key in PAUSE_LEFT + PAUSE_RIGHT:
            step = -PAUSE_STEP if key in PAUSE_LEFT else PAUSE_STEP
            sound.set_volume(channel, round((sound.settings[channel]["volume"] + step) / PAUSE_STEP) * PAUSE_STEP)
            self.pause_hold = 0.0
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            sound.toggle(channel)
        else:
            return False
        return True

    def open_settings(self):
        """ปุ่ม Music & Sound ในเมนู -> หน้าปรับเสียง"""
        self.pause_focus = 0
        self.pause_drag = None
        self.state = SETTINGS

    def open_confirm(self):
        """ปุ่ม Reset scores ในเมนู -> ถามยืนยันก่อน (เริ่มที่ Cancel กันกด Enter พลาด)"""
        self.confirm_focus = 0
        self.state = CONFIRM

    def close_confirm(self, do_reset):
        """ปิดแผ่นยืนยัน  do_reset: ลบคะแนนทั้งหมด -> ดาว/high score หาย ด่าน 2 ขึ้นไปล็อกใหม่ กลับไปเลือกด่านแรก"""
        if do_reset:
            self.scores = scores.reset_scores()
            self.selected = 0
        self.state = MENU

    def handle_confirm_mouse(self, event):
        """เมาส์ในแผ่นยืนยัน: ชี้ปุ่ม = ไฮไลต์, คลิกปุ่ม = เลือก, คลิกนอกแผ่น = ยกเลิก"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button != 1:
            return
        for i, rect in enumerate(ui.confirm_buttons()):
            if rect.collidepoint(event.pos):
                self.confirm_focus = i
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.close_confirm(i == 1)
                return
        if event.type == pygame.MOUSEBUTTONDOWN and not ui.CONFIRM_PANEL.collidepoint(event.pos):
            self.close_confirm(False)

    def close_sound_panel(self, state):
        """ออกจากหน้าหยุดเกม/หน้าปรับเสียง: บันทึกค่าเสียงลงไฟล์ แล้วไปหน้า state"""
        sound.save_settings()
        self.pause_drag = None
        self.state = state

    def hold_pause_keys(self):
        """กดซ้าย/ขวาค้าง: กดครั้งแรกเลื่อน 10% (handle_key) ค้างเกิน PAUSE_HOLD วินาทีแล้วเลื่อนต่อเนื่อง"""
        keys = pygame.key.get_pressed()
        direction = any(keys[k] for k in PAUSE_RIGHT) - any(keys[k] for k in PAUSE_LEFT)
        if not direction:
            self.pause_hold = 0.0
            return
        self.pause_hold += self.dt
        if self.pause_hold > PAUSE_HOLD:
            channel = ui.PAUSE_ROWS[self.pause_focus][0]
            sound.set_volume(channel, sound.settings[channel]["volume"] + direction * PAUSE_SLIDE * self.dt)

    def handle_menu_mouse(self, event):
        """เมาส์ในเมนูเลือกด่าน: ชี้แถว = เลือก (ไฮไลต์), คลิกซ้าย = เริ่มด่านนั้น  ด่านที่ล็อกอยู่ไม่ตอบสนอง
        ปุ่ม Music & Sound / Reset scores: ชี้ = ไฮไลต์, คลิก = เปิดหน้าปรับเสียง / ถามยืนยันลบคะแนน"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button != 1:
            return
        for name, rect in ui.MENU_BUTTONS.items():
            if rect.collidepoint(event.pos):
                self.menu_button = name
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.open_settings() if name == "sound" else self.open_confirm()
                return
        for i in range(len(self.level_files)):
            if ui.menu_row_rect(i).collidepoint(event.pos) and self.unlocked(i):
                self.selected = i
                self.menu_button = None
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.start_level()
                return

    def handle_pause_mouse(self, event):
        """เมาส์ในหน้าหยุดเกม/หน้าปรับเสียง: ชี้แถว = ไฮไลต์, คลิก/ลากราง = ปรับความดัง, คลิกกล่อง = เปิด/ปิด
        หน้าปรับเสียง: คลิกนอกแผ่น = กลับเมนู"""
        panel = ui.PAUSE_PANEL if self.state == PAUSED else ui.SOUND_PANEL
        layout = ui.pause_layout(panel)
        if event.type == pygame.MOUSEBUTTONUP:
            if self.pause_drag is not None:
                sound.save_settings()
            self.pause_drag = None
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button != 1:
            return
        if (event.type == pygame.MOUSEBUTTONDOWN and self.state == SETTINGS
                and not panel.collidepoint(event.pos)):
            self.close_sound_panel(MENU)
            return
        if self.pause_drag is None:
            for i, part in enumerate(layout):
                if part["row"].collidepoint(event.pos):
                    self.pause_focus = i
        if event.type == pygame.MOUSEBUTTONDOWN:
            part = layout[self.pause_focus]
            if part["box"].inflate(10, 10).collidepoint(event.pos):
                sound.toggle(ui.PAUSE_ROWS[self.pause_focus][0])
                sound.save_settings()
                return
            if part["track"].inflate(24, 24).collidepoint(event.pos):
                self.pause_drag = self.pause_focus
        if self.pause_drag is not None:
            track = layout[self.pause_drag]["track"]
            sound.set_volume(ui.PAUSE_ROWS[self.pause_drag][0], (event.pos[0] - track.x - 8) / (track.w - 16))

    def go_to_menu(self):
        # ชนะแล้วเลื่อนไปด่านถัดไปที่เพิ่งปลดล็อกให้เลย
        if self.state == WIN and self.unlocked(self.selected + 1):
            self.selected += 1
        self.reset()
        self.state = MENU

    def unlocked(self, i):
        if i >= len(self.level_files):
            return False
        return self.unlock_all or scores.is_unlocked(self.level_files, i, self.scores)

    def move_selection(self, step):
        """เลื่อนไปแถวถัดไปในเมนู: ด่านที่ปลดล็อกแล้ว (ข้ามด่านที่ล็อก) แล้วปุ่ม Music & Sound, Reset scores
        ท้ายสุด วนรอบได้"""
        items = [i for i in range(len(self.level_files)) if self.unlocked(i)] + list(ui.MENU_BUTTONS)
        now = self.menu_button or self.selected
        nxt = items[(items.index(now) + step) % len(items)]
        if isinstance(nxt, str):
            self.menu_button = nxt
        else:
            self.menu_button = None
            self.selected = nxt

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
        sound.play("win" if won else "lose")

    # ---------------- update ----------------
    def update(self):
        if self.state != PLAYING:
            return
        dt = self.dt
        self.camera.update(dt)
        self.elapsed += dt
        for popup in self.popups:
            popup[2] += dt
        self.popups = [p for p in self.popups if p[2] < C.POPUP_TIME]
        self.effects.update(dt)

        if self.fight:
            self.update_fight(dt)
            return

        # คูณ dt เสมอ: ความเร็วจะเท่ากันไม่ว่าเครื่องจะได้ 30 หรือ 144 FPS
        self.camera.z += self.level.speed * dt
        self.crowd.z = self.camera.z + C.CROWD_OFFSET
        self.crowd.update(dt)

        # ตรวจว่ากลุ่มคนวิ่ง "ถึง/เลย" object ไหนบ้างในเฟรมนี้
        # ใช้ >= แทน == เพราะ z เพิ่มทีละหลาย unit ต่อเฟรม อาจกระโดดข้ามค่าพอดีไป
        objects = self.level.objects
        # กองศัตรูข้างหน้า (ถ้าเป็นของชิ้นถัดไป) วิ่งพุ่งเข้าหาเมื่อเข้าใกล้ ดู EnemyGroup.rush
        nxt = objects[self.next_index] if self.next_index < len(objects) else None
        if isinstance(nxt, EnemyGroup):
            nxt.rush(self.crowd, dt)
            if nxt.rushing:
                self.spawn_rush_dust(nxt, dt)
        while self.next_index < len(objects) and self.reached(objects[self.next_index]):
            obj = objects[self.next_index]
            self.next_index += 1
            before = self.crowd.count
            obj.on_reach(self.crowd)
            if isinstance(obj, EnemyGroup) and obj.fighting:
                # ปะทะศัตรู: หยุดวิ่งจนกว่าจะจบ (ดู update_fight)
                self.fight = obj
                sound.play("fight")
                break
            self.react(obj, before)

        for obj in objects:
            obj.update(dt)

        if self.fight:          # เพิ่งเริ่มปะทะ (เช่นบอสหลังเส้นชัย): ห้ามนับว่าชนะจนกว่าจะปะทะจบ
            return
        if self.crowd.count <= 0:
            self.finish_level(False)
        elif self.crowd.back_z() >= self.level.finish_z + C.FINISH_DEPTH:
            # จบด่านเมื่อคนท้ายสุดผ่านแถบเส้นชัยแล้ว (ทุกคนข้ามเส้น) ด่านที่มีบอส: บอสถูกเรียกก่อนในลูปข้างบน
            self.finish_level(True)

    def reached(self, obj):
        """กลุ่มคนวิ่งถึง obj หรือยัง  ของบนถนน: ศูนย์กลางก้อนถึง  บอส: คนท้ายสุดข้ามเส้นชัยแล้ว"""
        if obj is self.level.boss:
            return self.crowd.back_z() >= obj.z
        return self.crowd.z >= obj.z

    def update_fight(self, dt):
        """ระหว่างปะทะ: ไม่วิ่ง ไม่อัปเดตสิ่งกีดขวาง
        ทำไมหยุดสิ่งกีดขวางด้วย: level.dodge_spans คิดจังหวะแกว่งจาก "ระยะทาง / ความเร็ว"
        ถ้าเวลาเดินระหว่างหยุดวิ่ง สิ่งกีดขวางข้างหน้าจะไม่อยู่ตรงที่เช็กไว้ว่าหลบทัน"""
        fight = self.fight
        before = self.crowd.count
        fight.update(dt)
        pull_crowd(self.crowd, fight.x, dt)       # ระหว่างปะทะ: ไหลเข้าหาศัตรู/บอสจนตรงกัน
        self.crowd.update(dt)
        if fight.engaged:                        # บอสที่ยังวิ่งเข้ามา: ยังไม่สั่น ยังไม่มีประกายหมัด
            if fight is self.level.boss:
                self.boss_music = True
            self.camera.shake(C.SHAKE_FIGHT, 0.1)
            self.spawn_hits(fight, before - self.crowd.count, dt)
        if fight.impact:                         # บอสโจมตีโดน
            strength = fight.impact_strength
            if strength >= 1:                    # ทุบ/กระทืบหนักครั้งเดียว: สั่นแรง + ฝุ่นระเบิดเป็นวง
                self.camera.shake(C.SHAKE_BOSS, 0.25)
                self.effects.slam(fight.x, fight.contact_z - 15, 70)
                sound.play("hit")
            else:                                # หมัดรัว: สั่นเบาๆ ถี่ๆ + ประกายใหญ่ตรงคนแถวหน้า
                self.camera.shake(C.SHAKE_BOSS * strength, 0.12)
                front = self.crowd.front_z()
                self.effects.hit(fight.x + random.uniform(-80, 80), front - random.uniform(5, 45),
                                 random.uniform(8, 20), (C.WHITE, fight.chip_color), big=random.random() < 0.5)
                if random.random() < 0.4:        # ไม่เล่นทุกหมัด ไม่งั้นเสียงรัวจนหนวกหู
                    sound.play("hit")
        if not fight.fighting:
            self.fight = None
            if fight.lost:
                self.add_popup(f"-{fight.lost}", C.GATE_BAD)
            if self.crowd.count <= 0:
                self.lose_cause = fight.name
            else:
                sound.play("win_fight")
        if self.crowd.count <= 0:
            self.finish_level(False)

    def spawn_rush_dust(self, enemy, dt):
        """ฝุ่นฟุ้งจากเท้ากองศัตรูที่กำลังวิ่งเข้ามา (ทั่วทั้งกอง)"""
        self.dust_timer += dt * RUSH_DUST_RATE
        r = enemy.radius()
        while self.dust_timer >= 1:
            self.dust_timer -= 1
            self.effects.puff(enemy.x + random.uniform(-r, r), enemy.z + random.uniform(0, 2 * r))

    def spawn_hits(self, fight, lost, dt):
        """ประกายหมัดตรงแนวที่สองฝั่งชนกัน ให้ดูเหมือนต่อยกันจริง
        ต่อเนื่องตามเวลา (HIT_RATE) + เพิ่มตามจำนวนคนที่หายไปในเฟรมนี้ กองใหญ่จึงดูวุ่นกว่า"""
        self.hit_timer += dt * HIT_RATE
        n = int(self.hit_timer) + min(lost, 3)
        self.hit_timer -= int(self.hit_timer)
        people, k = self.crowd.people, self.crowd.spread()
        contact = fight.contact_z                            # บอส: ปะทะตรงหน้าตัวบอส
        colors = (C.WHITE, fight.chip_color)
        for _ in range(n):
            x = self.crowd.x + (random.choice(people).dx * k if people else 0)   # ตรงตำแหน่งคนจริงในก้อน
            if contact is not None:
                # บอส: ประกายต่ำติดพื้น อยู่ใต้เท้าบอสบนจอ ไม่บังท่าโจมตี (ยกขา / ทุบหมัด)
                x, z = max(fight.x - 35, min(fight.x + 35, x)), contact + random.uniform(-10, 10)
                h = random.uniform(2, 9)
            else:
                z = fight.z + random.uniform(0, 25)           # ขอบหน้ากองศัตรูอยู่ที่ fight.z พอดี
                h = random.uniform(10, 22)
            self.effects.hit(x, z, h, colors, big=random.random() < 0.12)

    def react(self, obj, before):
        """เอฟเฟกต์หลังผ่าน object: ตัวเลขลอย, กล้องสั่น, เสียง และจำสาเหตุถ้าคนหมด"""
        change = self.crowd.count - before
        if isinstance(obj, GatePair):
            good = obj.chosen.is_good()
            # + กับ - บอกจำนวนเปลี่ยนอยู่แล้ว  × กับ ÷ ต้องบอกด้วยว่าได้/เสียกี่คน
            text = f"{change:+d}" if obj.chosen.op in "+-" else f"{obj.chosen.label()}  ({change:+d})"
            self.add_popup(text, C.GATE_GOOD if good else C.GATE_BAD)
            sound.play("gate_good" if good else "gate_bad")
            cause = f"the {obj.chosen.label()} gate"
        elif isinstance(obj, Obstacle):
            if change < 0:
                self.add_popup(f"-{-change}", C.GATE_BAD)
                self.camera.shake(C.SHAKE_HIT * min(1.0, 0.3 + 2 * -change / before), 0.3)
                sound.play("hit")
            cause = "an obstacle"
        else:
            cause = "a trap"
        if self.crowd.count <= 0:
            self.lose_cause = cause

    def add_popup(self, text, color):
        self.popups.append([text, color, 0.0])

    # ---------------- draw ----------------
    def draw_tree(self, tree):
        """ต้นไม้หนึ่งต้นบนหญ้าข้างถนน: ขนาดตามระยะ (ย่อแล้วเก็บไว้ใช้ซ้ำ ปัดขนาดของต้นใกล้ๆ ไม่ให้แคชบวม)"""
        z, x, kind, flip = tree
        sx, sy, s = self.camera.project(x, z)
        sprite = self.tree_sprites[flip][kind]
        w = int(sprite.get_width() * trees.SCALES[kind] * s)
        if w < 3:
            return
        if w > 120:
            w -= w % 8
        if sx + w < 0 or sx - w > C.SCREEN_W:
            return
        key = (flip, kind, w)
        image = self.tree_cache.get(key)
        if image is None:
            if len(self.tree_cache) > 300:
                self.tree_cache.clear()
            h = max(1, w * sprite.get_height() // sprite.get_width())
            image = self.tree_cache[key] = pygame.transform.scale(sprite, (w, h))
        self.screen.blit(image, (sx - w // 2, sy - image.get_height()))

    def draw_world(self):
        cam = self.camera
        near, far = cam.z + C.Z_NEAR, cam.z + C.Z_FAR

        # ท้องฟ้า + พื้น
        self.draw_sky()
        pygame.draw.rect(self.screen, C.GROUND_A, (0, C.HORIZON_Y, C.SCREEN_W, C.SCREEN_H))

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

        # ถนน = สี่เหลี่ยมคางหมูจากใกล้ไปไกล
        corners = [cam.project(x, z)[:2] for x, z in
                   ((-C.ROAD_HALF_W, near), (C.ROAD_HALF_W, near), (C.ROAD_HALF_W, far), (-C.ROAD_HALF_W, far))]
        pygame.draw.polygon(self.screen, C.ROAD, corners)   # พื้นรองกันช่องโหว่

        # ลายอิฐบนถนน: หั่นเป็นแถบตามแกน z ความกว้างแต่ละแถบตาม perspective
        # ทุกแถบตัดตรงขอบแถวของลาย (ไม่ตัดกลางแถว) และใช้แถวที่ "ละเอียดพอดี" กับระยะ:
        #   ใกล้กล้อง: แถบละ 1 แถวของลาย สูงเท่าของจริง
        #   ไกลออกไป: แถบเดียวคลุมหลายแถว -> ใช้แถวที่เฉลี่ยสีหลายแถวไว้แล้ว (road_mips ระดับ L = เฉลี่ย 2^L แถว)
        # ทำไม: เดิมแต่ละแถบหยิบลายมาแถวเดียวตรงจุดเริ่มแถบแล้วยืดเต็มแถบ ถ้าบังเอิญเป็นแถวร่องอิฐ (สีเข้ม)
        # จะได้แถบดำหนาพาดถนน ตอนวิ่งมันกระพริบจนไม่ค่อยเห็น แต่ตอนหยุด (ปะทะ) มันค้างเป็นรอยดำ
        tile = ROAD_TILE
        row_len = tile / len(self.road_rows)           # 1 แถวของลาย ยาวกี่ unit
        top = len(self.road_mips) - 1
        z = near
        while z < far:
            dy = abs(cam.project(0, z + 1)[1] - cam.project(0, z)[1]) or 1e-6   # พิกเซลต่อ 1 unit ตรงนี้
            rows_per_strip = ROAD_STRIP_PX / dy / row_len                       # แถบสูง ~ROAD_STRIP_PX คลุมกี่แถว
            level = min(top, int(math.log2(rows_per_strip))) if rows_per_strip >= 2 else 0
            block = row_len * (1 << level)
            index = int(z // block)
            z1 = min((index + 1) * block, far)                                  # จบตรงขอบแถวพอดี
            xl, y0, _ = cam.project(-C.ROAD_HALF_W, z)
            xr, _, _ = cam.project(C.ROAD_HALF_W, z)
            _, y1, _ = cam.project(0, z1)
            w, h = int(xr - xl), int(abs(y0 - y1)) + 1       # +1 กันรอยแตก
            if w > 0 and h > 0:
                rows = self.road_mips[level]
                row = rows[index % len(rows)]                 # ลายต่อเนื่องเอง (tile หาร block ลงตัว)
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

        # เส้นชัย: แถบตาหมากรุกขาว-ดำ 2 แถว (เส้นดำเส้นเดียวดูเหมือนรอยแตกบนถนน)
        fz = self.level.finish_z
        if cam.visible(fz) or cam.visible(fz + C.FINISH_DEPTH):
            cols, rows = 12, 2
            cw, rd = 2 * C.ROAD_HALF_W / cols, C.FINISH_DEPTH / rows
            for r in range(rows):
                for c in range(cols):
                    x0, z0 = -C.ROAD_HALF_W + c * cw, fz + r * rd
                    if z0 + rd < near or z0 > far:
                        continue
                    pts = [cam.project(x, z)[:2] for x, z in
                           ((x0, z0), (x0 + cw, z0), (x0 + cw, z0 + rd), (x0, z0 + rd))]
                    pygame.draw.polygon(self.screen, C.FINISH_COLOR if (r + c) % 2 else C.WHITE, pts)

        # painter's algorithm: วาดของไกล (z มาก) ก่อน ของใกล้ทับทีหลัง
        # ต้นไม้ข้างถนนเรียงรวมกับของบนถนน  ต้นที่ใกล้กล้องกว่ากลุ่มคนวาดหลังกลุ่มคน (บังกลุ่มคนได้ถูกต้อง)
        lo = bisect.bisect_left(self.tree_zs, near)
        hi = bisect.bisect_right(self.tree_zs, far)
        front_trees = []
        drawables = [(obj.z, obj) for obj in self.level.objects] + [(t[0], t) for t in self.trees[lo:hi]]
        for z, item in sorted(drawables, key=lambda d: -d[0]):
            if isinstance(item, tuple):
                if z < self.crowd.z:
                    front_trees.append(item)
                else:
                    self.draw_tree(item)
            else:
                item.draw(self.screen, cam, self.font)
        # ปะทะศัตรู/บอสอยู่: กลุ่มคนใช้ท่าต่อย (บอสที่ยังวิ่งเข้ามา: ยืนรอ ยังไม่ต่อย)
        self.crowd.attacking = self.fight is not None and self.fight.engaged
        self.crowd.waiting = self.fight is not None and not self.fight.engaged
        self.crowd.draw(self.screen, cam, self.font)
        for tree in front_trees:                         # เรียงไกล -> ใกล้อยู่แล้ว
            self.draw_tree(tree)
        if self.fight is not None:
            self.fight.draw_overlay(self.screen, cam)   # รอยหมัดบอสที่ลงถึงตัวคน ต้องทับกลุ่มคน
        self.effects.draw(self.screen, cam)             # ประกายหมัดวาดทับทุกอย่าง

    def draw(self):
        if self.state in (MENU, SETTINGS, CONFIRM):
            unlocked = [self.unlocked(i) for i in range(len(self.level_files))]
            sound_on = any(c["on"] for c in sound.settings.values())
            ui.draw_menu(self.screen, self.big_font, self.font, self.level_names, self.selected, self.scores,
                         unlocked, self.level_tiers, self.menu_button, sound_on)
            if self.state == SETTINGS:
                ui.draw_sound_settings(self.screen, self.big_font, self.font, sound.settings, self.pause_focus)
            elif self.state == CONFIRM:
                ui.draw_confirm_reset(self.screen, self.big_font, self.font, self.confirm_focus)
        else:
            self.draw_world()
            sx, sy, scale = self.camera.project(self.crowd.x, self.crowd.z)
            ui.draw_popups(self.screen, self.font, self.popups, (sx, sy - 70 * scale))
            progress = self.crowd.z / self.level.finish_z
            ui.draw_hud(self.screen, self.font, self.level, progress)
            if self.selected == 0 and self.elapsed < TIP_TIME and self.state == PLAYING:
                fade = min(1.0, (TIP_TIME - self.elapsed) / 0.6)
                ui.draw_tips(self.screen, self.font, TIPS, int(255 * fade))
            if self.state == PAUSED:
                ui.draw_pause(self.screen, self.big_font, self.font, sound.settings, self.pause_focus)
            elif self.state in (WIN, LOSE):
                ui.draw_end(self.screen, self.big_font, self.font, self.state == WIN, self.crowd.count,
                            *self.result, cause=self.lose_cause,
                            thresholds=scores.thresholds(self.best),
                            has_next=self.unlocked(self.selected + 1))
        pygame.display.flip()

    def run(self):
        while True:
            # tick() คืนเวลาที่ผ่านไปเป็นมิลลิวินาที -> แปลงเป็นวินาที
            # min(..., 0.05) กันเฟรมกระตุกนานๆ (เช่น ลากหน้าต่าง) ทำให้วิ่งทะลุประตู
            self.dt = min(self.clock.tick(C.FPS) / 1000, 0.05)
            self.handle_events()
            self.update()
            sound.play_music(self.music_theme())   # เพลงเดิม = เล่นต่อ เปลี่ยนหน้าจอ = เปลี่ยนเพลง
            self.draw()

    def music_theme(self):
        """เพลงของหน้าจอตอนนี้: เมนู -> "menu", วิ่ง/หยุดเกม -> "game",
        บอสกับกลุ่มคนตีกันแล้ว -> "boss" (ค้างไว้ถึงจบด่าน ไม่สลับกลับตอนบอสแพ้ก่อนขึ้นหน้าชนะ)
        จบด่าน -> None ค่อยๆ เงียบ ให้ได้ยินเสียงชนะ/แพ้ชัดๆ"""
        if self.state in (MENU, SETTINGS, CONFIRM):
            return "menu"
        if self.state in (WIN, LOSE):
            return None
        return "boss" if self.boss_music else "game"


if __name__ == "__main__":
    Game().run()