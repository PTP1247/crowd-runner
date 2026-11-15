"""ทุกอย่างที่เป็น "หน้าจอ" ที่ไม่ใช่โลกของเกม: เมนู, HUD, หน้าจบ   [เจ้าของ: C]"""
import math

import pygame
from game.core import config as C


def draw_text_center(screen, font, text, y, color=C.WHITE):
    surf = font.render(text, True, color)
    screen.blit(surf, surf.get_rect(center=(C.SCREEN_W // 2, y)))


MENU_TOP = 190      # y ของแถวแรกในรายการด่าน
MENU_ROW_H = 44
NAME_W = 220        # ชื่อด่านกว้างเกินนี้ย่อให้พอดีแถว
STAR_ON = (255, 205, 40)
STAR_OFF = (90, 100, 130)


MENU_BG_FILE = C.ASSET_DIR / "menu_bg.png"   # สร้างด้วย tools/make_menu_bg.py
_menu_bg = []


def menu_background():
    """ภาพพื้นหลังเมนู (โหลดครั้งแรกที่ใช้) ไม่มีไฟล์ = None ใช้สีพื้นแทน"""
    if not _menu_bg:
        try:
            image = pygame.image.load(str(MENU_BG_FILE)).convert()
            _menu_bg.append(pygame.transform.smoothscale(image, (C.SCREEN_W, C.SCREEN_H)))
        except (pygame.error, FileNotFoundError, OSError):
            _menu_bg.append(None)
    return _menu_bg[0]


def draw_text_shadow(screen, font, text, y, color=C.WHITE):
    """ตัวหนังสือกลางจอมีเงาดำ อ่านออกบนภาพพื้นหลังที่สีหลากหลาย"""
    for dx, dy in ((2, 2), (-1, 2), (2, -1), (0, 3)):
        surf = font.render(text, True, (12, 16, 30))
        screen.blit(surf, surf.get_rect(center=(C.SCREEN_W // 2 + dx, y + dy)))
    draw_text_center(screen, font, text, y, color)


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


# ปุ่มสองปุ่มใต้รายการด่าน วางคู่กัน กว้างรวมเท่าแถวด่าน
BUTTON_W = (C.SCREEN_W - 60 - 8) // 2
SOUND_BUTTON = pygame.Rect(30, 716, BUTTON_W, 44)                    # "Music & Sound" -> หน้าปรับเสียง
RESET_BUTTON = pygame.Rect(C.SCREEN_W - 30 - BUTTON_W, 716, BUTTON_W, 44)   # "Reset scores" -> ถามยืนยัน
MENU_BUTTONS = {"sound": SOUND_BUTTON, "reset": RESET_BUTTON}         # main.py ใช้เช็กเมาส์


def draw_reset_icon(screen, center, color=C.WHITE):
    """ไอคอนลูกศรวนกลับ (เริ่มใหม่): วงเกือบรอบ + หัวลูกศร"""
    cx, cy = center
    pygame.draw.arc(screen, color, (cx - 9, cy - 9, 18, 18), 0.6, 5.6, 3)
    pygame.draw.polygon(screen, color, [(cx + 4, cy - 11), (cx + 12, cy - 6), (cx + 4, cy - 1)])


def draw_speaker(screen, center, on, color=C.WHITE):
    """ไอคอนลำโพง: มีคลื่นเสียง = เปิด, มีกากบาท = ปิดเสียงหมด"""
    cx, cy = center
    pygame.draw.rect(screen, color, (cx - 11, cy - 4, 6, 8))
    pygame.draw.polygon(screen, color, [(cx - 6, cy - 4), (cx + 1, cy - 10), (cx + 1, cy + 10), (cx - 6, cy + 4)])
    if on:
        for r in (6, 11):
            pygame.draw.arc(screen, color, (cx + 1 - r, cy - r, 2 * r, 2 * r), -0.9, 0.9, 2)
    else:
        pygame.draw.line(screen, color, (cx + 5, cy - 5), (cx + 13, cy + 5), 2)
        pygame.draw.line(screen, color, (cx + 5, cy + 5), (cx + 13, cy - 5), 2)


def draw_menu(screen, big, small, levels, selected, scores, unlocked, tiers=None,
              button=None, sound_on=True):
    """levels: [(ชื่อไฟล์, ชื่อด่าน), ...]   selected: index ที่เลือกอยู่   scores: จาก scores.load_scores()
    unlocked: [True/False ต่อด่าน]  ด่านที่ล็อกวาดเป็นสีเทา + แม่กุญแจ
    tiers: ระดับความยากต่อด่าน 0-3 (จาก difficulty_tier) โชว์เป็นขีดหน้าชื่อ
    button: ไฮไลต์อยู่ที่ปุ่มไหนแทนแถวด่าน ("sound" / "reset" / None = แถวด่าน)
    sound_on: มีเสียงอย่างน้อยหนึ่งช่องเปิดอยู่ไหม (ไอคอนลำโพง)"""
    bg = menu_background()
    if bg:
        screen.blit(bg, (0, 0))
        dim(screen, 60)                 # ภาพหม่นลงนิด ตัวหนังสือ/แถวด่านเด่นกว่า
        shade = pygame.Surface((C.SCREEN_W, 175), pygame.SRCALPHA)
        for y in range(175):            # หัวจอเข้มขึ้นไล่ลงมา ให้ชื่อเกมอ่านง่าย
            shade.fill((14, 20, 40, int(150 * (1 - y / 175))), (0, y, C.SCREEN_W, 1))
        screen.blit(shade, (0, 0))
    else:
        screen.fill((30, 40, 70))
    draw_text_shadow(screen, big, C.TITLE, 90)
    draw_text_shadow(screen, small, "Choose a level", 150, (220, 228, 245))
    for i, (filename, name) in enumerate(levels):
        rect = menu_row_rect(i)
        if not unlocked[i]:
            row_fill(screen, rect, (34, 40, 58), 240)
            if tiers:
                draw_meter(screen, (rect.x + 10, rect.centery), tiers[i], (60, 66, 88))
            label = small.render(name, True, (122, 130, 154))
            if label.get_width() > NAME_W:
                label = pygame.transform.smoothscale(
                    label, (NAME_W, max(1, label.get_height() * NAME_W // label.get_width())))
            screen.blit(label, label.get_rect(midleft=(rect.x + 42, rect.centery)))
            draw_lock(screen, (rect.right - 25, rect.centery), (122, 130, 154))
            continue
        active = i == selected and button is None
        row_fill(screen, rect, (70, 95, 160) if active else (45, 58, 95))
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
    draw_text_shadow(screen, small, "Click a level or Up/Down + SPACE", hint_y + 34, (225, 230, 245))
    draw_button(screen, small, SOUND_BUTTON, "Music & Sound", button == "sound",
                lambda c: draw_speaker(screen, c, sound_on))
    draw_button(screen, small, RESET_BUTTON, "Reset scores", button == "reset",
                lambda c: draw_reset_icon(screen, c))


def draw_button(screen, small, rect, text, active, icon, fill=(70, 95, 160)):
    """ปุ่มหน้าตาแบบแถวด่าน (ไฮไลต์ + กรอบขาวเมื่อเลือกด้วยคีย์บอร์ด/เมาส์ชี้)
    icon(center): ฟังก์ชันวาดไอคอนหน้าตัวหนังสือ (None = ไม่มี)  ไอคอน + ตัวหนังสืออยู่กลางปุ่ม"""
    row_fill(screen, rect, fill if active else (45, 58, 95))
    if active:
        pygame.draw.rect(screen, C.WHITE, rect, 2, border_radius=8)
    label = small.render(text, True, C.WHITE)
    icon_w = 30 if icon else 0
    left = rect.centerx - (label.get_width() + icon_w) // 2
    if icon:
        icon((left + 11, rect.centery))
    screen.blit(label, label.get_rect(midleft=(left + icon_w, rect.centery)))


CONFIRM_PANEL = pygame.Rect(0, 0, 400, 270)       # ถามยืนยันก่อนลบคะแนน
CONFIRM_PANEL.center = (C.SCREEN_W // 2, C.SCREEN_H // 2)
DANGER = (190, 60, 60)                             # ปุ่ม "Reset" ตอนเลือก: แดง (ลบแล้วกู้คืนไม่ได้)


def confirm_buttons():
    """[ปุ่ม Cancel, ปุ่ม Reset] ในแผ่นยืนยัน (main.py ใช้เช็กเมาส์ ui ใช้วาด)"""
    w = (CONFIRM_PANEL.w - 36 - 12) // 2
    y = CONFIRM_PANEL.bottom - 74
    return [pygame.Rect(CONFIRM_PANEL.x + 18, y, w, 50), pygame.Rect(CONFIRM_PANEL.right - 18 - w, y, w, 50)]


def draw_confirm_reset(screen, big, small, focus):
    """แผ่นถาม "ลบคะแนนทั้งหมด?"  focus: 0 = Cancel (ค่าเริ่มต้น กันกดพลาด), 1 = Reset"""
    dim(screen, 120)
    rect = CONFIRM_PANEL
    panel(screen, rect)
    pygame.draw.rect(screen, C.WHITE, rect, 3, border_radius=14)
    draw_text_center(screen, big, "RESET?", rect.y + 50)
    for k, line in enumerate(("Delete all stars and high scores.", "Levels 2-10 will be locked again.")):
        surf = fit_text(small, line, MUTED, rect.w - 40)
        screen.blit(surf, surf.get_rect(center=(rect.centerx, rect.y + 102 + k * 30)))
    cancel, reset = confirm_buttons()
    draw_button(screen, small, cancel, "Cancel", focus == 0, None)
    draw_button(screen, small, reset, "Reset", focus == 1, None, fill=DANGER)


def row_fill(screen, rect, color, alpha=215):
    """แถวด่านโปร่งแสงนิดๆ เห็นภาพพื้นหลังลางๆ ข้างหลัง"""
    surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(surf, (*color, alpha), surf.get_rect(), border_radius=8)
    screen.blit(surf, rect.topleft)


def draw_hud(screen, font, level, progress):
    """progress: 0.0 - 1.0 ระยะทางที่วิ่งมาแล้ว"""
    screen.blit(font.render(level.name, True, C.BLACK), (12, 10))
    bar = pygame.Rect(12, 40, C.SCREEN_W - 24, 10)
    pygame.draw.rect(screen, C.WHITE, bar, border_radius=5)
    fill = bar.copy()
    fill.width = int(bar.width * max(0.0, min(1.0, progress)))
    pygame.draw.rect(screen, C.PLAYER_COLOR, fill, border_radius=5)


END_W = C.SCREEN_W - 60          # หน้าจบด่าน: กว้างเท่านี้ สูงตามจำนวนบรรทัด
END_PAD = 22                      # ขอบในของกล่อง (ตัวหนังสือห้ามเลยเข้าไป)


def fit_text(font, text, color, max_w):
    """ตัวหนังสือที่ย่อลงถ้ากว้างเกิน max_w (เช่น ชื่อบอสยาวๆ) จะได้ไม่ล้นกล่อง"""
    surf = font.render(text, True, color)
    if surf.get_width() > max_w:
        h = max(1, surf.get_height() * max_w // surf.get_width())
        surf = pygame.transform.smoothscale(surf, (max_w, h))
    return surf


def draw_end(screen, big, small, won, count, star_count=0, best=None, new_record=False,
             cause=None, thresholds=None, has_next=False):
    """best: high score เดิมของด่านนี้ (dict จาก scores หรือ None)
    cause: แพ้เพราะอะไร (ข้อความ)   thresholds: (คนที่ต้องเหลือเพื่อ 2 ดาว, 3 ดาว)
    has_next: ชนะแล้วมีด่านถัดไปให้กด Enter ไปต่อไหม
    กล่องสูงตามจำนวนบรรทัด (จัดกลางจอ) และบรรทัดที่กว้างเกินถูกย่อ: ตัวหนังสือไม่ล้นกล่องทุกกรณี"""
    dim(screen, 120)
    max_w = END_W - 2 * END_PAD
    rows = [(fit_text(big, "YOU WIN!" if won else "GAME OVER", C.WHITE, max_w), 12), ("stars", 26)]
    if won:
        rows.append((fit_text(small, f"People left: {count}", C.WHITE, max_w), 6))
        if thresholds and star_count < 3:
            need = thresholds[0] if star_count < 2 else thresholds[1]
            rows.append((fit_text(small, f"{need}+ people for the next star", MUTED, max_w), 6))
    elif cause:
        rows.append((fit_text(small, f"Wiped out by {cause}", MUTED, max_w), 6))
    if new_record:
        rows.append((fit_text(small, "NEW HIGH SCORE!", STAR_ON, max_w), 6))
    elif best:
        rows.append((fit_text(small, f"High score: {best['count']}", MUTED, max_w), 6))
    rows[-1] = (rows[-1][0], 30)                           # เว้นช่องก่อนบรรทัดปุ่ม
    if won and has_next:
        rows.append((fit_text(small, "ENTER: next level", C.WHITE, max_w), 6))
    elif not won:
        rows.append((fit_text(small, "ENTER: try again", C.WHITE, max_w), 6))
    keys = "R: play again    M: level menu" if won else "M: level menu"   # แพ้: ไม่มี R (Enter เล่นใหม่อยู่แล้ว)
    rows.append((fit_text(small, keys, MUTED, max_w), 0))
    star_h = 44
    height = 2 * END_PAD + sum((star_h if r == "stars" else r.get_height()) + gap for r, gap in rows)
    rect = pygame.Rect(0, 0, END_W, height)
    rect.center = (C.SCREEN_W // 2, C.SCREEN_H // 2)
    panel(screen, rect)
    y = rect.y + END_PAD
    for r, gap in rows:
        if r == "stars":
            draw_stars(screen, (rect.centerx, y + star_h // 2), star_count, r=22)
            y += star_h + gap
        else:
            screen.blit(r, r.get_rect(midtop=(rect.centerx, y)))
            y += r.get_height() + gap


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


PAUSE_PANEL = pygame.Rect(0, 0, 400, 440)
PAUSE_PANEL.center = (C.SCREEN_W // 2, C.SCREEN_H // 2)
SOUND_PANEL = pygame.Rect(0, 0, 400, 330)     # หน้าปรับเสียงจากเมนู: ไม่มีบรรทัด R/M จึงเตี้ยกว่า
SOUND_PANEL.center = (C.SCREEN_W // 2, C.SCREEN_H // 2)
PAUSE_ROWS = (("music", "Music"), ("effect", "Effect"))
TRACK_FILL = (205, 207, 214)        # ในรางสไลเดอร์: เทาอ่อน
TRACK_OFF = (110, 116, 136)         # ปิดกล่องอยู่: รางจางลง
KNOB = (22, 24, 34)


def pause_layout(panel=PAUSE_PANEL):
    """ตำแหน่งปุ่มในแผ่นปรับเสียง (main.py ใช้เช็กเมาส์ ui ใช้วาด ให้ตรงกันเสมอ)
    panel: PAUSE_PANEL (หน้าหยุดเกม) หรือ SOUND_PANEL (หน้าปรับเสียงจากเมนู)
    คืน [{"row": แถว (กรอบไฮไลต์), "track": รางสไลเดอร์, "box": กล่องเปิด/ปิด}, ...] ตามลำดับ PAUSE_ROWS"""
    out = []
    for i in range(len(PAUSE_ROWS)):
        row = pygame.Rect(panel.x + 18, panel.y + 112 + i * 68, panel.w - 36, 58)
        track = pygame.Rect(row.x + 112, row.centery - 8, row.w - 170, 16)
        box = pygame.Rect(0, 0, 24, 24)
        box.center = (row.right - 26, row.centery)
        out.append({"row": row, "track": track, "box": box})
    return out


def draw_pause(screen, big, small, settings, focus):
    """หน้าหยุดเกม: แผ่นปรับเสียง + ปุ่ม R/M + "Press ESC to continue" กระพริบ"""
    rect = PAUSE_PANEL
    draw_sound_panel(screen, big, small, settings, focus, rect, "PAUSE")
    y = pause_layout(rect)[-1]["row"].bottom + 40
    for text in ("R : restart", "M : main menu"):          # ไม่กระพริบ
        surf = small.render(text, True, MUTED)
        screen.blit(surf, surf.get_rect(midleft=(rect.x + 32, y)))
        y += 36
    blink(screen, small, "Press ESC to continue", rect.bottom - 40)


def draw_sound_settings(screen, big, small, settings, focus):
    """หน้าปรับเสียงจากเมนู (ปุ่ม "Music & Sound"): แผ่นเดียวกับหน้าหยุดเกม แต่ไม่มี R/M"""
    draw_sound_panel(screen, big, small, settings, focus, SOUND_PANEL, "SOUND")
    blink(screen, small, "Press ESC to go back", SOUND_PANEL.bottom - 40)


def blink(screen, small, text, y):
    """กระพริบ: โชว์ครึ่งจังหวะ หายครึ่งจังหวะ"""
    if pygame.time.get_ticks() // BLINK_MS % 2 == 0:
        draw_text_center(screen, small, text, y)


def draw_sound_panel(screen, big, small, settings, focus, rect, title_text):
    """แผ่นปรับเสียง: หัวข้อ + สไลเดอร์ความดัง 0-100% + กล่องเปิด/ปิด (มีกากบาท = เปิด) ของเพลงและเสียงประกอบ
    settings: sound.settings   focus: แถวที่เลือกอยู่ (คีย์บอร์ด / เมาส์ชี้) วาดกรอบไฮไลต์แบบเมนูเลือกด่าน"""
    dim(screen, 120)
    panel(screen, rect)
    pygame.draw.rect(screen, C.WHITE, rect, 3, border_radius=14)
    # หัวข้อ  == PAUSE ==  (เส้นคู่สองข้าง)
    title = big.render(title_text, True, C.WHITE)
    tr = title.get_rect(center=(rect.centerx, rect.y + 62))
    screen.blit(title, tr)
    for x0, x1 in ((rect.x + 28, tr.left - 16), (tr.right + 16, rect.right - 28)):
        for dy in (-6, 4):
            pygame.draw.line(screen, C.WHITE, (x0, tr.centery + dy), (x1, tr.centery + dy), 4)
    for i, (layout, (channel, name)) in enumerate(zip(pause_layout(rect), PAUSE_ROWS)):
        row, track, box = layout["row"], layout["track"], layout["box"]
        c = settings[channel]
        active = i == focus
        pygame.draw.rect(screen, (70, 95, 160) if active else (45, 58, 95), row, border_radius=8)
        if active:
            pygame.draw.rect(screen, C.WHITE, row, 2, border_radius=8)
        label = small.render(name, True, C.WHITE)
        screen.blit(label, label.get_rect(midleft=(row.x + 14, row.centery)))
        # สไลเดอร์: รางมนขอบเข้ม ข้างในเทาอ่อน + ปุ่มกลมสีเข้ม  % อยู่ใต้ปุ่มตอนเลือกแถวนี้
        pygame.draw.rect(screen, TRACK_FILL if c["on"] else TRACK_OFF, track, border_radius=8)
        pygame.draw.rect(screen, KNOB, track, 2, border_radius=8)
        kx = track.x + 8 + round((track.w - 16) * c["volume"])
        pygame.draw.circle(screen, C.WHITE, (kx, track.centery), 11)
        pygame.draw.circle(screen, KNOB, (kx, track.centery), 9)
        if active:
            pct = TINY_FONT().render(f"{round(c['volume'] * 100)}%", True, C.WHITE)
            screen.blit(pct, pct.get_rect(midbottom=(kx, track.y - 2)))
        # กล่อง: มีกากบาท = เปิด, ว่าง = ปิด
        pygame.draw.rect(screen, (30, 36, 60), box)
        pygame.draw.rect(screen, C.WHITE, box, 2)
        if c["on"]:
            inner = box.inflate(-8, -8)
            pygame.draw.line(screen, C.WHITE, inner.topleft, inner.bottomright, 3)
            pygame.draw.line(screen, C.WHITE, inner.topright, inner.bottomleft, 3)


_tiny = []


def TINY_FONT():
    """ฟอนต์เล็กสำหรับตัวเลข % และคำแนะนำปุ่ม (สร้างครั้งแรกที่ใช้ หลัง pygame.init)"""
    if not _tiny:
        _tiny.append(pygame.font.Font(None, 22))
    return _tiny[0]


BLINK_MS = 700      # ข้อความ "Press ESC" กระพริบสลับทุกกี่มิลลิวินาที


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
