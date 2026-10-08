"""ประตูเปลี่ยนจำนวนคน   [เจ้าของ: B]"""
import pygame
import config as C

# ตัวดำเนินการที่รองรับ: ใช้ในไฟล์ด่าน JSON เป็น "+", "-", "x", "/"
SYMBOLS = {"+": "+", "-": "-", "x": "×", "/": "÷"}


_label_cache = {}


def label_image(font, label, scale):
    """ตัวเลขบนประตู ย่อตามระยะให้ดูไกล-ใกล้สมจริง
    เก็บภาพไว้ใช้ซ้ำ (ปัด scale ทีละ 0.05) เพราะ render + smoothscale ทุกเฟรมช้า"""
    step = max(1, round(scale * 20))
    key = (id(font), label, step)
    image = _label_cache.get(key)
    if image is None:
        if len(_label_cache) > 1000:
            _label_cache.clear()
        text = font.render(label, True, C.WHITE)
        k = step / 20
        image = _label_cache[key] = pygame.transform.smoothscale(
            text, (max(1, int(text.get_width() * k)), max(1, int(text.get_height() * k))))
    return image


class Gate:
    """ประตูบานเดียว ครอบคลุมถนนตั้งแต่ x_min ถึง x_max"""

    def __init__(self, x_min, x_max, op, value):
        if op not in SYMBOLS:
            raise ValueError(f"unknown gate op: {op!r}")
        if op == "/" and value == 0:
            raise ValueError("gate cannot divide by 0")
        self.x_min, self.x_max = x_min, x_max
        self.op, self.value = op, value

    def apply(self, count):
        """คืนจำนวนคนใหม่ (pure function: ไม่แก้ state อะไร ทดสอบง่าย)"""
        if self.op == "+":
            return count + self.value
        if self.op == "-":
            return max(0, count - self.value)   # จำนวนคนติดลบไม่ได้
        if self.op == "x":
            return count * self.value
        return count // self.value              # "/" ใช้ // เพราะคนต้องเป็นจำนวนเต็ม

    def is_good(self):
        return self.op in ("+", "x")

    def label(self):
        return f"{SYMBOLS[self.op]}{self.value}"

    def contains(self, x):
        return self.x_min <= x < self.x_max


class GatePair:
    """ประตูคู่ซ้าย/ขวาที่ระยะ z เดียวกัน ผ่านได้แค่บานเดียว"""

    def __init__(self, z, left, right):
        self.z = z
        self.left = Gate(-C.ROAD_HALF_W, 0, *left)
        self.right = Gate(0, C.ROAD_HALF_W, *right)
        self.used = False

    def update(self, dt):
        pass  # TODO(B): animation เช่น ประตูกระพริบตอนถูกผ่าน

    def on_reach(self, crowd):
        """เรียกครั้งเดียวเมื่อกลุ่มคนวิ่งถึง z ของประตู"""
        gate = self.left if self.left.contains(crowd.x) else self.right
        crowd.count = gate.apply(crowd.count)
        self.used = True

    def draw(self, screen, camera, font):
        if self.used or not camera.visible(self.z):
            return
        for gate in (self.left, self.right):
            x1, y, scale = camera.project(gate.x_min, self.z)
            x2, _, _ = camera.project(gate.x_max, self.z)
            h = C.GATE_HEIGHT * scale
            rect = pygame.Rect(x1 + 2, y - h, x2 - x1 - 4, h)
            color = C.GATE_GOOD if gate.is_good() else C.GATE_BAD
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            surf.fill((*color, 150))  # โปร่งแสงให้เห็นคนข้างหลัง
            screen.blit(surf, rect.topleft)
            text = label_image(font, gate.label(), min(scale, 1.5))
            screen.blit(text, text.get_rect(center=rect.center))
