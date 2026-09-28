"""จุดเริ่มเกม: game loop + state machine   [เจ้าของ: A]

รัน:  python main.py

State machine:  MENU --(space/click)--> PLAYING --(ถึงเส้นชัย)--> WIN
                                               \--(คนเหลือ 0)--> LOSE
                WIN/LOSE --(R)--> MENU
"""
import sys
import pygame

import config as C
import ui
from camera import Camera
from crowd import Crowd
from level import load_level

MENU, PLAYING, WIN, LOSE = "menu", "playing", "win", "lose"


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 64)
        self.camera = Camera()
        self.state = MENU
        self.reset()

    def reset(self):
        self.level = load_level("level1.json")
        self.crowd = Crowd(self.level.start_count)
        self.camera.z = 0.0
        self.next_index = 0  # object ถัดไปใน level.objects ที่กลุ่มคนยังไม่ถึง

    # ---------------- input ----------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_v:
                    self.camera.toggle_mode()
                if self.state == MENU and event.key == pygame.K_SPACE:
                    self.state = PLAYING
                if self.state in (WIN, LOSE) and event.key == pygame.K_r:
                    self.reset()
                    self.state = MENU
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == MENU:
                self.state = PLAYING

        if self.state == PLAYING:
            keys = pygame.key.get_pressed()
            direction = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            self.crowd.move(direction, self.dt)
            if pygame.mouse.get_pressed()[0]:  # กดเมาส์ค้างแล้วลาก
                mx, _ = pygame.mouse.get_pos()
                self.crowd.target_x = self.camera.unproject_x(mx, self.crowd.z)

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
            self.state = LOSE
        elif self.crowd.z >= self.level.finish_z:
            self.state = WIN

    # ---------------- draw ----------------
    def draw_world(self):
        cam = self.camera
        self.screen.fill(C.SKY if cam.mode == "depth" else C.GROUND)
        if cam.mode == "depth":
            pygame.draw.rect(self.screen, C.GROUND, (0, C.HORIZON_Y, C.SCREEN_W, C.SCREEN_H))

        # ถนน = สี่เหลี่ยมคางหมูจากใกล้ไปไกล (ในโหมด flat จะกลายเป็นสี่เหลี่ยมผืนผ้าเอง)
        near, far = cam.z + C.Z_NEAR, cam.z + C.Z_FAR
        corners = [cam.project(x, z)[:2] for x, z in
                   ((-C.ROAD_HALF_W, near), (C.ROAD_HALF_W, near), (C.ROAD_HALF_W, far), (-C.ROAD_HALF_W, far))]
        pygame.draw.polygon(self.screen, C.ROAD, corners)

        # เส้นประกลางถนน ทำให้รู้สึกว่ากำลังวิ่ง
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
            ui.draw_menu(self.screen, self.big_font, self.font)
        else:
            self.draw_world()
            progress = self.crowd.z / self.level.finish_z
            ui.draw_hud(self.screen, self.font, self.level, progress)
            if self.state in (WIN, LOSE):
                ui.draw_end(self.screen, self.big_font, self.font, self.state == WIN, self.crowd.count)
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
