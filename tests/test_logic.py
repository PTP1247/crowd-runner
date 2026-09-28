"""ทดสอบ logic ที่ไม่ต้องเปิดหน้าต่าง   [เจ้าของ: C]

รัน:  python -m pytest      (หรือ  python tests/test_logic.py  ถ้าไม่มี pytest)
ทำไมต้องมี: ก่อน merge เข้า main รันไฟล์นี้ ถ้าใครแก้สูตรพัง จะรู้ทันที
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gate import Gate
from crowd import Crowd
from obstacle import Obstacle
from enemy import EnemyGroup
from level import load_level


def test_gate_ops():
    assert Gate(0, 1, "+", 20).apply(10) == 30
    assert Gate(0, 1, "x", 3).apply(10) == 30
    assert Gate(0, 1, "/", 3).apply(10) == 3      # ปัดลง
    assert Gate(0, 1, "-", 10).apply(4) == 0      # ไม่ติดลบ


def test_obstacle_hit_and_miss():
    crowd = Crowd(20)
    crowd.x = -75
    Obstacle(-75, 100, 150, 5).on_reach(crowd)
    assert crowd.count == 15
    crowd.x = 75
    Obstacle(-75, 100, 150, 5).on_reach(crowd)    # อยู่คนละฝั่ง ไม่โดน
    assert crowd.count == 15


def test_enemy_fight():
    crowd = Crowd(50)
    EnemyGroup(100, 40).on_reach(crowd)
    assert crowd.count == 10


def test_level1_loads_sorted():
    level = load_level("level1.json")
    zs = [o.z for o in level.objects]
    assert zs == sorted(zs)
    assert level.finish_z > zs[-1]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
