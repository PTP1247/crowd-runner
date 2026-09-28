"""สิ่งกีดขวางระหว่างประตู ลดจำนวนคน (จำเป็นสำหรับระดับ 1)   [เจ้าของ: B]"""
import pygame
import config as C


class Obstacle:
    def __init__(self, x, z, width, damage):
        self.x, self.z = x, z
        self.width = width
        self.damage = damage
        self.used = False

    def update(self, dt):
        pass  # TODO(B): ทำให้ขยับซ้าย-ขวาได้ (เช่น ใบมีดแกว่ง) จะท้าทายขึ้นมาก

    def hits(self, crowd_x):
        return abs(crowd_x - self.x) <= self.width / 2

    def on_reach(self, crowd):
        # TODO(B): ให้ damage ขึ้นกับว่ากลุ่มคนทับสิ่งกีดขวางมากแค่ไหน (ใช้ crowd.radius())
        if self.hits(crowd.x):
            crowd.count = max(0, crowd.count - self.damage)
        self.used = True

    def draw(self, screen, camera, font):
        if not camera.visible(self.z):
            return
        x1, y, scale = camera.project(self.x - self.width / 2, self.z)
        x2, _, _ = camera.project(self.x + self.width / 2, self.z)
        h = 25 * scale
        pygame.draw.rect(screen, C.OBSTACLE_COLOR, (x1, y - h, x2 - x1, h))
