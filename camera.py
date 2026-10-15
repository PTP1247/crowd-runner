"""กล้อง: แปลงพิกัดโลก (x, z) -> พิกัดจอ (sx, sy, scale)   [เจ้าของ: A]

แนวคิดสำคัญ: logic ทั้งเกม (ชน, นับคน) ทำในพิกัดโลกเท่านั้น
ฟังก์ชัน project() เป็นที่เดียวที่รู้ว่า "วาดยังไง"
ดังนั้นเปลี่ยนจาก top-down (flat) เป็นแนวลึก (depth) = แก้ไฟล์นี้ไฟล์เดียว
"""
import random

import config as C


class Camera:
    def __init__(self, mode=C.CAMERA_MODE):
        self.mode = mode
        self.z = 0.0  # กล้องอยู่ที่ z เท่าไรในโลก (เพิ่มขึ้นเรื่อยๆ = กำลังวิ่งไปข้างหน้า)
        self.shake_power = 0.0      # สั่นแรงสุดกี่พิกเซล
        self.shake_time = 0.0       # เหลือเวลาสั่นอีกกี่วินาที
        self.shake_total = 1.0
        self.offset = (0.0, 0.0)    # เลื่อนภาพทั้งจอเฟรมนี้ (ใช้ตอนสั่น)
        self.rng = random.Random()  # แยกจาก random หลัก ไม่ให้การสั่นไปเปลี่ยนผลสุ่มอื่น

    def shake(self, power, duration=0.25):
        """สั่นกล้อง: ภาพทั้งจอเลื่อนสุ่มไปมาแล้วค่อยๆ เบาลง  (logic ในโลกไม่เปลี่ยน แค่ภาพ)"""
        if power >= self.shake_power * self.shake_time / self.shake_total:
            self.shake_power, self.shake_time, self.shake_total = power, duration, duration

    def update(self, dt):
        self.shake_time = max(0.0, self.shake_time - dt)
        p = self.shake_power * self.shake_time / self.shake_total
        self.offset = (self.rng.uniform(-p, p), self.rng.uniform(-p, p)) if p > 0.3 else (0.0, 0.0)

    def toggle_mode(self):
        self.mode = "flat" if self.mode == "depth" else "depth"

    def visible(self, z):
        """วัตถุที่ z นี้ควรถูกวาดไหม"""
        rel = z - self.z
        return C.Z_NEAR <= rel <= C.Z_FAR

    def project(self, x, z):
        """คืน (screen_x, screen_y, scale) ของจุดบนพื้นที่ (x, z)

        depth: scale = F / rel   (สามเหลี่ยมคล้าย: ไกลขึ้น 2 เท่า -> เล็กลงครึ่งหนึ่ง)
        flat : scale = 1, y ลดลงตามระยะแบบเส้นตรง
        """
        rel = z - self.z  # ระยะจากกล้อง
        if self.mode == "depth":
            rel = max(rel, 1e-3)  # กันหารศูนย์ (ปกติ visible() กรองไว้แล้ว)
            scale = C.FOCAL / rel
            sx = C.CENTER_X + x * scale
            sy = C.HORIZON_Y + C.CAM_HEIGHT * scale
        else:
            scale = 1.0
            sx = C.CENTER_X + x
            sy = C.FLAT_CROWD_Y - (rel - C.CROWD_OFFSET) * C.FLAT_PIXELS_PER_Z
        return sx + self.offset[0], sy + self.offset[1], scale

    def unproject_x(self, sx, z):
        """ทางกลับ: จากตำแหน่งเมาส์บนจอ -> x ในโลก (ที่ระยะ z)  ใช้กับการคุมด้วยเมาส์"""
        cx, _, scale = self.project(0, z)
        return (sx - cx) / scale
