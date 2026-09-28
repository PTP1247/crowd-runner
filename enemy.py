"""กองศัตรู / บอส: ปะทะแล้วจำนวนหักลบกัน   [เจ้าของ: B, ทำสัปดาห์ 5]"""
import math
import pygame
import config as C


class EnemyGroup:
    def __init__(self, z, count, x=0):
        self.x, self.z = x, z
        self.count = count
        self.used = False

    def update(self, dt):
        pass

    def on_reach(self, crowd):
        # เวอร์ชันง่าย: หักลบทันที
        # TODO(B): ทำให้ค่อยๆ หักทีละคนต่อเฟรม (ดูสนุกกว่า เหมือนในวิดีโอ)
        fight = min(crowd.count, self.count)
        crowd.count -= fight
        self.count -= fight
        self.used = True

    def draw(self, screen, camera, font):
        if self.used or not camera.visible(self.z):
            return
        n = min(self.count, C.MAX_DRAWN_PEOPLE)
        for i in range(n):
            # วางเป็นวงก้นหอย (golden angle) ให้ดูเป็นก้อนกลม
            r = C.PERSON_SPACING * math.sqrt(i)
            a = i * 2.39996
            sx, sy, scale = camera.project(self.x + r * math.cos(a), self.z + r * math.sin(a))
            pygame.draw.circle(screen, C.ENEMY_COLOR, (sx, sy), max(1, 5 * scale))
        sx, sy, scale = camera.project(self.x, self.z)
        text = font.render(str(self.count), True, C.WHITE)
        screen.blit(text, text.get_rect(center=(sx, sy - 40 * scale)))


# TODO(B): class Boss(EnemyGroup) ที่เส้นชัย มีหลอดเลือด (HP) และภาพต่างจากศัตรูธรรมดา
