"""โหลดด่านจากไฟล์ JSON   [เจ้าของ: C]

ทำไมใช้ JSON: แยก "ข้อมูลด่าน" ออกจาก "โค้ด" เพิ่มด่านใหม่ได้โดยไม่ต้องแก้ Python
"""
import json
from pathlib import Path

from gate import GatePair
from obstacle import Obstacle
from enemy import EnemyGroup

LEVEL_DIR = Path(__file__).parent / "levels"


class Level:
    def __init__(self, name, start_count, speed, finish_z, objects):
        self.name = name
        self.start_count = start_count
        self.speed = speed          # ความเร็ววิ่งไปข้างหน้า (units/วินาที)
        self.finish_z = finish_z
        self.objects = objects      # เรียงตาม z น้อยไปมาก


def build_object(data):
    """แปลง dict หนึ่งก้อนจาก JSON -> object ในเกม"""
    kind = data["type"]
    if kind == "gate_pair":
        return GatePair(data["z"], tuple(data["left"]), tuple(data["right"]))
    if kind == "obstacle":
        return Obstacle(data["x"], data["z"], data["width"], data["damage"])
    if kind == "enemy":
        return EnemyGroup(data["z"], data["count"], data.get("x", 0))
    raise ValueError(f"unknown object type: {kind!r}")


def load_level(filename):
    with open(LEVEL_DIR / filename, encoding="utf-8") as f:
        data = json.load(f)
    objects = sorted((build_object(o) for o in data["objects"]), key=lambda o: o.z)
    return Level(data["name"], data["start_count"], data["speed"], data["finish_z"], objects)


# TODO(C): list_levels() คืนชื่อไฟล์ด่านทั้งหมดใน levels/ เพื่อทำเมนูเลือกด่าน
