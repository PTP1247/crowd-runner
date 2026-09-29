"""สิ่งกีดขวางระหว่างประตู ลดจำนวนคน (จำเป็นสำหรับระดับ 1)   [เจ้าของ: B]"""
import pygame
import config as C
import random
import math
class Obstacle:
    def __init__(self, x, z, width, damage):
        self.x, self.z = x, z
        self.width = width
        self.damage = damage
        self.used = False
        self.start_x = x 
        self.time_accumulator = random.uniform(0, 6.28) 
    def update(self, dt):
        self.time_accumulator += dt
        self.x = self.start_x + math.sin(self.time_accumulator * 2.0) * 120
        pass  # TODO(B): ทำให้ขยับซ้าย-ขวาได้ (เช่น ใบมีดแกว่ง) จะท้าทายขึ้นมาก

    def hits(self, crowd_x):
        return abs(crowd_x - self.x) <= self.width / 2

    def on_reach(self, crowd):
        # คนที่ตำแหน่งจริงอยู่ในช่วงความกว้างของสิ่งกีดขวาง = โดนชนจริง
        victims = [p for p in crowd.people
                   if abs(crowd.x + p.dx - self.x) <= self.width / 2]
        crowd.remove(victims)

    def draw(self, screen, camera, font):
        if not camera.visible(self.z):
            return
        x1, y, scale = camera.project(self.x - self.width / 2, self.z)
        x2, _, _ = camera.project(self.x + self.width / 2, self.z)
        h = 25 * scale
        pygame.draw.rect(screen, C.OBSTACLE_COLOR, (x1, y - h, x2 - x1, h))
