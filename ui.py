"""ทุกอย่างที่เป็น "หน้าจอ" ที่ไม่ใช่โลกของเกม: เมนู, HUD, หน้าจบ   [เจ้าของ: C]"""
import math
import pygame
import config as C


def draw_text_center(screen, font, text, y, color=C.WHITE):
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(C.SCREEN_W // 2, y)))


MENU_TOP = 190      # y ของแถวแรกในรายการด่าน
MENU_ROW_H = 44
NAME_W = 220        # ชื่อด่านกว้างเกินนี้ย่อให้พอดีแถว
STAR_ON = (255, 205, 40)
STAR_OFF = (90, 100, 130)


def menu_row_rect(i):
    """สี่เหลี่ยมของแถวด่านที่ i (ใช้วาดเมนู)"""
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


def draw_lock(screen, center, color):
    """แม่กุญแจเล็กๆ: ห่วงด้านบน + ตัวกุญแจสี่เหลี่ยม"""
    cx, cy = center
    pygame.draw.rect(screen, color, (cx - 6, cy - 12, 12, 12), 3, border_radius=6)
    pygame.draw.rect(screen, color, (cx - 9, cy - 4, 18, 14), border_radius=3)


DIFFICULTY_TIERS = (30, 45, 55)      # คะแนน level.difficulty ที่ขึ้นขีดถัดไป (1-4 ขีด)
TIER_COLORS = [(90, 200, 120), (230, 200, 70), (240, 140, 60), (235, 70, 70)]


def difficulty_tier(score):
    """0 = ง่าย ... 3 = ยากสุด"""
    return sum(score >= t for t in DIFFICULTY_TIERS)


def draw_meter(screen, midleft, tier, dim_color=None):
    """ขีดความยาก 4 ขีดสูงขึ้นเรื่อยๆ ขีดที่ถึงแล้วมีสีตามระดับ"""
    x, cy = midleft
    for k in range(4):
        h = 6 + k * 4
        color = dim_color or (TIER_COLORS[tier] if k <= tier else (70, 80, 110))
        pygame.draw.rect(screen, color, (x + k * 6, cy + 9 - h, 4, h))


def draw_menu(screen, big, small, levels, selected, scores, unlocked, unlock_all=False, tiers=None):
    """levels: [(ชื่อไฟล์, ชื่อด่าน), ...]   selected: index ที่เลือกอยู่   scores: จาก scores.load_scores()
    unlocked: [True/False ต่อด่าน]  ด่านที่ล็อกวาดเป็นสีเทา + แม่กุญแจ
    tiers: ระดับความยากต่อด่าน 0-3 (จาก difficulty_tier) โชว์เป็นขีดหน้าชื่อ"""
    screen.fill((30, 40, 70))
    draw_text_center(screen, big, C.TITLE, 90)
    draw_text_center(screen, small, "Choose a level", 150, (190, 200, 230))
    for i, (filename, name) in enumerate(levels):
        rect = menu_row_rect(i)
        if not unlocked[i]:
            pygame.draw.rect(screen, (38, 44, 62), rect, border_radius=8)
            if tiers:
                draw_meter(screen, (rect.x + 10, rect.centery), tiers[i], (60, 66, 88))
            label = small.render(name, True, (95, 105, 130))
            if label.get_width() > NAME_W:
                label = pygame.transform.smoothscale(
                    label, (NAME_W, max(1, label.get_height() * NAME_W // label.get_width())))
            screen.blit(label, label.get_rect(midleft=(rect.x + 42, rect.centery)))
            draw_lock(screen, (rect.right - 25, rect.centery), (95, 105, 130))
            continue
        active = i == selected
        pygame.draw.rect(screen, (70, 95, 160) if active else (45, 58, 95), rect, border_radius=8)
        if active:
            pygame.draw.rect(screen, C.WHITE, rect, 2, border_radius=8)
        if tiers:
            draw_meter(screen, (rect.x + 10, rect.centery), tiers[i])
        label = small.render(name, True, C.WHITE)
        if label.get_width() > NAME_W:        # ชื่อยาวเกิน ย่อให้พอดีแถว
            label = pygame.transform.smoothscale(
                label, (NAME_W, max(1, label.get_height() * NAME_W // label.get_width())))
        screen.blit(label, label.get_rect(midleft=(rect.x + 42, rect.centery)))
        best = scores.get(filename)
        draw_stars(screen, (rect.right - 95, rect.centery), best["stars"] if best else 0, r=8)
        if best:
            text = small.render(str(best["count"]), True, (190, 200, 230))
            screen.blit(text, text.get_rect(midright=(rect.right - 10, rect.centery)))
    hint_y = MENU_TOP + len(levels) * MENU_ROW_H + 20
    # draw_text_center(screen, small, "Win a level to unlock the next one", hint_y, (190, 200, 230))
    draw_text_center(screen, small, "Up/Down + SPACE to choose a level", hint_y + 34, (190, 200, 230))
    draw_text_center(screen, small, "In game: P pause  R restart  N sound", hint_y + 68, (190, 200, 230))
    if unlock_all:
        draw_text_center(screen, small, "U: unlock all (testing)  [ON]", hint_y + 102, STAR_ON)
    else:
        draw_text_center(screen, small, "U: unlock all (testing)", hint_y + 102, (120, 130, 160))


def draw_hud(screen, font, level, progress):
    """progress: 0.0 - 1.0 ระยะทางที่วิ่งมาแล้ว"""
    screen.blit(font.render(level.name, True, C.BLACK), (12, 10))
    bar = pygame.Rect(12, 40, C.SCREEN_W - 24, 10)
    pygame.draw.rect(screen, C.WHITE, bar, border_radius=5)
    fill = bar.copy()
    fill.width = int(bar.width * max(0.0, min(1.0, progress)))
    pygame.draw.rect(screen, C.PLAYER_COLOR, fill, border_radius=5)


def draw_end(screen, big, small, won, count, star_count=0, best=None, new_record=False,
             cause=None, thresholds=None, has_next=False):
    """best: high score เดิมของด่านนี้ (dict จาก scores หรือ None)
    cause: แพ้เพราะอะไร (ข้อความ)   thresholds: (คนที่ต้องเหลือเพื่อ 2 ดาว, 3 ดาว)
    has_next: ชนะแล้วมีด่านถัดไปให้กด Enter ไปต่อไหม"""
    dim(screen, 120)
    panel(screen, pygame.Rect(30, 215, C.SCREEN_W - 60, 360))
    draw_text_center(screen, big, "YOU WIN!" if won else "GAME OVER", 270)
    draw_stars(screen, (C.SCREEN_W // 2, 340), star_count, r=22)
    y = 400
    if won:
        draw_text_center(screen, small, f"People left: {count}", y)
        y += 34
        if thresholds and star_count < 3:
            need = thresholds[0] if star_count < 2 else thresholds[1]
            draw_text_center(screen, small, f"{need}+ people for the next star", y, MUTED)
            y += 34
    elif cause:
        draw_text_center(screen, small, f"Wiped out by {cause}", y, MUTED)
        y += 34
    if new_record:
        draw_text_center(screen, small, "NEW HIGH SCORE!", y, STAR_ON)
    elif best:
        draw_text_center(screen, small, f"High score: {best['count']}", y, MUTED)
    y += 70
    if won and has_next:
        draw_text_center(screen, small, "ENTER: next level", y)
    elif not won:
        draw_text_center(screen, small, "ENTER: try again", y)
    draw_text_center(screen, small, "R: play again    M: level menu", y + 34, MUTED)


MUTED = (190, 200, 230)


def dim(screen, alpha):
    overlay = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    screen.blit(overlay, (0, 0))


def panel(screen, rect):
    """แผ่นทึบหลังข้อความ กันตัวเลข/คนในฉากโผล่มาทับตัวหนังสือ"""
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (18, 24, 46, 240), surf.get_rect(), border_radius=14)
    screen.blit(surf, rect.topleft)


def draw_pause(screen, big, small, muted):
    dim(screen, 120)
    rect = pygame.Rect(0, 0, C.SCREEN_W - 100, 400)
    rect.center = (C.SCREEN_W // 2, C.SCREEN_H // 2)
    panel(screen, rect)
    # panel(screen, pygame.Rect(50, C.SCREEN_H/2 , C.SCREEN_W - 100, 400))
    draw_text_center(screen, big, "== PAUSED ==", 280)
    draw_text_center(screen, small, "R: restart    M: level menu", 390, MUTED)
    draw_text_center(screen, small, f"N: sound {'off' if muted else 'on'}", 424, MUTED)
    # กระพริบ: โชว์ครึ่งวินาที หายครึ่งวินาที  วางชิดขอบล่างของแผ่น
    if pygame.time.get_ticks() // BLINK_MS % 2 == 0:
        draw_text_center(screen, small, "Press any key to continue", rect.bottom - 40)


BLINK_MS = 700      # ข้อความ "Press any key" กระพริบสลับทุกกี่มิลลิวินาที


def draw_popups(screen, font, popups, anchor):
    """ตัวเลขลอยขึ้นจากก้อนคนแล้วจางหาย  popups: [ข้อความ, สี, อายุ]  anchor: จุดบนจอเหนือก้อนคน"""
    x, y = anchor
    for i, (text, color, age) in enumerate(popups):
        t = age / C.POPUP_TIME
        image = font.render(text, True, color)
        outline = font.render(text, True, C.BLACK)
        alpha = int(255 * (1 - t ** 2))
        image.set_alpha(alpha)
        outline.set_alpha(alpha)
        cy = y - 30 - t * 70 - i * 6
        rect = image.get_rect(center=(x, cy))
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            screen.blit(outline, rect.move(dx, dy))
        screen.blit(image, rect)


def draw_tips(screen, font, lines, alpha):
    """คำแนะนำช่วงแรกของด่านแรก วางกลางจอ ค่อยๆ จางหาย"""
    box = pygame.Surface((C.SCREEN_W - 40, 34 * len(lines) + 16), pygame.SRCALPHA)
    box.fill((20, 30, 60, int(190 * alpha / 255)))
    rect = box.get_rect(midtop=(C.SCREEN_W // 2, 62))     # บนท้องฟ้า ไม่บังประตูที่โผล่จากขอบฟ้า
    screen.blit(box, rect)
    for i, line in enumerate(lines):
        text = font.render(line, True, C.WHITE)
        text.set_alpha(alpha)
        screen.blit(text, text.get_rect(center=(C.SCREEN_W // 2, rect.y + 25 + i * 34)))
