"""ทุกอย่างที่เป็น "หน้าจอ" ที่ไม่ใช่โลกของเกม: เมนู, HUD, หน้าจบ   [เจ้าของ: C]"""
import pygame
import config as C


def draw_text_center(screen, font, text, y, color=C.WHITE):
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(C.SCREEN_W // 2, y)))


def draw_menu(screen, big, small):
    screen.fill((30, 40, 70))
    draw_text_center(screen, big, C.TITLE, 250)
    draw_text_center(screen, small, "SPACE / click to start", 400)
    draw_text_center(screen, small, "Move: mouse or A/D, left/right", 450)
    draw_text_center(screen, small, "V: switch view (flat / depth)", 490)
    # TODO(C): เมนูเลือกด่าน, แสดง high score


def draw_hud(screen, font, level, progress):
    """progress: 0.0 - 1.0 ระยะทางที่วิ่งมาแล้ว"""
    screen.blit(font.render(level.name, True, C.BLACK), (12, 10))
    bar = pygame.Rect(12, 40, C.SCREEN_W - 24, 10)
    pygame.draw.rect(screen, C.WHITE, bar, border_radius=5)
    fill = bar.copy()
    fill.width = int(bar.width * max(0.0, min(1.0, progress)))
    pygame.draw.rect(screen, C.PLAYER_COLOR, fill, border_radius=5)


def draw_end(screen, big, small, won, count):
    overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    draw_text_center(screen, big, "YOU WIN!" if won else "GAME OVER", 330)
    if won:
        draw_text_center(screen, small, f"People left: {count}", 400)
    draw_text_center(screen, small, "R to play again", 460)
    # TODO(C): คำนวณดาว/คะแนน, บันทึก high score ลงไฟล์
