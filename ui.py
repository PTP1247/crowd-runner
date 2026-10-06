"""ทุกอย่างที่เป็น "หน้าจอ" ที่ไม่ใช่โลกของเกม: เมนู, HUD, หน้าจบ   [เจ้าของ: C]"""
import math
import pygame
import config as C


def draw_text_center(screen, font, text, y, color=C.WHITE):
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(C.SCREEN_W // 2, y)))


MENU_TOP = 190      # y ของแถวแรกในรายการด่าน
MENU_ROW_H = 44
STAR_ON = (255, 205, 40)
STAR_OFF = (90, 100, 130)


def menu_row_rect(i):
    """สี่เหลี่ยมของแถวด่านที่ i  (main.py ใช้เช็กว่าคลิกโดนแถวไหน)"""
    return pygame.Rect(30, MENU_TOP + i * MENU_ROW_H, C.SCREEN_W - 60, MENU_ROW_H - 6)


def draw_star(screen, center, r, filled):
    """ดาว 5 แฉก วาดเองเพราะฟอนต์ default ไม่มีตัว ★"""
    cx, cy = center
    pts = []
    for k in range(10):
        rad = r if k % 2 == 0 else r * 0.45
        a = math.radians(-90 + k * 36)
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    pygame.draw.polygon(screen, STAR_ON if filled else STAR_OFF, pts)


def draw_stars(screen, center, n, r=10, total=3):
    cx, cy = center
    gap = r * 2.4
    for k in range(total):
        draw_star(screen, (cx + (k - (total - 1) / 2) * gap, cy), r, k < n)


def draw_menu(screen, big, small, levels, selected, scores):
    """levels: [(ชื่อไฟล์, ชื่อด่าน), ...]   selected: index ที่เลือกอยู่   scores: จาก scores.load_scores()"""
    screen.fill((30, 40, 70))
    draw_text_center(screen, big, C.TITLE, 90)
    draw_text_center(screen, small, "Choose a level", 150, (190, 200, 230))
    for i, (filename, name) in enumerate(levels):
        rect = menu_row_rect(i)
        active = i == selected
        pygame.draw.rect(screen, (70, 95, 160) if active else (45, 58, 95), rect, border_radius=8)
        if active:
            pygame.draw.rect(screen, C.WHITE, rect, 2, border_radius=8)
        label = small.render(name, True, C.WHITE)
        if label.get_width() > 250:           # ชื่อยาวเกิน ย่อให้พอดีแถว
            label = pygame.transform.smoothscale(
                label, (250, max(1, label.get_height() * 250 // label.get_width())))
        screen.blit(label, label.get_rect(midleft=(rect.x + 12, rect.centery)))
        best = scores.get(filename)
        draw_stars(screen, (rect.right - 95, rect.centery), best["stars"] if best else 0, r=8)
        if best:
            text = small.render(str(best["count"]), True, (190, 200, 230))
            screen.blit(text, text.get_rect(midright=(rect.right - 10, rect.centery)))
    hint_y = MENU_TOP + len(levels) * MENU_ROW_H + 20
    draw_text_center(screen, small, "Up/Down + SPACE, or click a level", hint_y, (190, 200, 230))
    draw_text_center(screen, small, "Move: mouse or A/D   V: switch view", hint_y + 34, (190, 200, 230))


def draw_hud(screen, font, level, progress):
    """progress: 0.0 - 1.0 ระยะทางที่วิ่งมาแล้ว"""
    screen.blit(font.render(level.name, True, C.BLACK), (12, 10))
    bar = pygame.Rect(12, 40, C.SCREEN_W - 24, 10)
    pygame.draw.rect(screen, C.WHITE, bar, border_radius=5)
    fill = bar.copy()
    fill.width = int(bar.width * max(0.0, min(1.0, progress)))
    pygame.draw.rect(screen, C.PLAYER_COLOR, fill, border_radius=5)


def draw_end(screen, big, small, won, count, star_count=0, best=None, new_record=False):
    """best: high score เดิมของด่านนี้ (dict จาก scores หรือ None)"""
    overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    draw_text_center(screen, big, "YOU WIN!" if won else "GAME OVER", 300)
    draw_stars(screen, (C.SCREEN_W // 2, 370), star_count, r=22)
    if won:
        draw_text_center(screen, small, f"People left: {count}", 430)
    if new_record:
        draw_text_center(screen, small, "NEW HIGH SCORE!", 470, STAR_ON)
    elif best:
        draw_text_center(screen, small, f"High score: {best['count']}", 470)
    draw_text_center(screen, small, "R: play again    M: level menu", 530)
