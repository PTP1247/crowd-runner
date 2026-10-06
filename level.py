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


def list_levels():
    """คืนชื่อไฟล์ด่านทั้งหมดใน levels/ เรียงตามเลข (level2 มาก่อน level10)

    ทำไมไม่ใช้ sorted() ธรรมดา: เรียงแบบตัวอักษรจะได้ level1, level10, level2, ...
    """
    def number(path):
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return int(digits) if digits else 0
    return [p.name for p in sorted(LEVEL_DIR.glob("*.json"), key=lambda p: (number(p), p.name))]


def best_count(level):
    """จำนวนคนมากที่สุดที่เป็นไปได้ตอนถึงเส้นชัย (เลือกประตูดีที่สุดทุกบาน, หลบสิ่งกีดขวางได้หมด)

    ทำไมเลือกบานที่ได้มากสุดทีละบานแล้วได้คำตอบที่ดีที่สุด: ทุกตัวดำเนินการ (+ - x /)
    และการปะทะศัตรู ยิ่งเริ่มด้วยคนมาก ผลก็ยิ่งมาก (ไม่มีทางที่คนน้อยกว่าตอนนี้แล้วจะได้มากกว่าทีหลัง)
    ใช้เป็นฐานคิดดาว และใช้ใน test ตรวจว่าทุกด่านชนะได้จริง
    """
    count = level.start_count
    for obj in level.objects:
        if isinstance(obj, GatePair):
            count = max(obj.left.apply(count), obj.right.apply(count))
        elif isinstance(obj, EnemyGroup):
            count = max(0, count - obj.count)
    return count
