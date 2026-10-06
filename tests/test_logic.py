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
import config as C
import scores
import endless
from itertools import product
from gate import GatePair
from level import load_level, list_levels, best_count, build_object


def test_gate_ops():
    assert Gate(0, 1, "+", 20).apply(10) == 30
    assert Gate(0, 1, "x", 3).apply(10) == 30
    assert Gate(0, 1, "/", 3).apply(10) == 3      # ปัดลง
    assert Gate(0, 1, "-", 10).apply(4) == 0      # ไม่ติดลบ


def test_obstacle_hit_and_miss():
    # กติกาของ B (branch dew): คนที่อยู่ในความกว้างของสิ่งกีดขวางหายหมด, damage ไม่ถูกใช้แล้ว
    crowd = Crowd(20)
    crowd.x = 75
    Obstacle(-75, 100, 150, 5).on_reach(crowd)    # อยู่คนละฝั่ง ไม่โดน
    assert crowd.count == 20
    crowd.x = -75
    Obstacle(-75, 100, 150, 5).on_reach(crowd)    # ทั้งก้อนอยู่ในช่วงพอดี โดนหมด
    assert crowd.count == 0


def test_enemy_fight():
    crowd = Crowd(50)
    EnemyGroup(100, 40).on_reach(crowd)
    assert crowd.count == 10


def test_level1_loads_sorted():
    level = load_level("level1.json")
    zs = [o.z for o in level.objects]
    assert zs == sorted(zs)
    assert level.finish_z > zs[-1]


# ---------- ประตู: กรณีขอบ ----------

def test_gate_invalid():
    for bad in (("?", 1), ("/", 0)):
        try:
            Gate(0, 1, *bad)
        except ValueError:
            continue
        raise AssertionError(f"Gate{bad} ควร raise ValueError")


def test_gate_good_and_label():
    assert Gate(0, 1, "+", 5).is_good() and Gate(0, 1, "x", 2).is_good()
    assert not Gate(0, 1, "-", 5).is_good() and not Gate(0, 1, "/", 2).is_good()
    assert Gate(0, 1, "x", 3).label() == "×3"
    assert Gate(0, 1, "/", 2).label() == "÷2"


def test_gate_pair_picks_side():
    crowd = Crowd(10)
    crowd.x = -50                              # ฝั่งซ้าย
    GatePair(100, ("+", 5), ("x", 10)).on_reach(crowd)
    assert crowd.count == 15
    crowd.x = 50                               # ฝั่งขวา
    pair = GatePair(100, ("+", 5), ("x", 10))
    pair.on_reach(crowd)
    assert crowd.count == 150 and pair.used
    crowd.x = 0                                # ตรงกลางพอดี นับเป็นฝั่งขวา (x_min <= x)
    GatePair(100, ("-", 100), ("+", 1)).on_reach(crowd)
    assert crowd.count == 151


# ---------- ศัตรู ----------

def test_enemy_bigger_than_crowd():
    crowd = Crowd(10)
    enemy = EnemyGroup(100, 25)
    enemy.on_reach(crowd)
    assert crowd.count == 0 and enemy.count == 15 and enemy.used


# ---------- ไฟล์ด่าน ----------

def test_list_levels_numeric_order():
    files = list_levels()
    assert files[0] == "level1.json"
    nums = [int("".join(ch for ch in f if ch.isdigit())) for f in files]
    assert nums == sorted(nums)


def test_build_object_unknown_type():
    try:
        build_object({"type": "dragon", "z": 1})
    except ValueError:
        return
    raise AssertionError("type ที่ไม่รู้จักควร raise ValueError")


def test_all_levels_valid():
    """ทุกด่าน: โหลดได้, เรียงตาม z, ของอยู่บนถนนก่อนเส้นชัย, หลบสิ่งกีดขวางได้, ชนะได้จริง"""
    for filename in list_levels():
        level = load_level(filename)
        zs = [o.z for o in level.objects]
        assert zs == sorted(zs), filename
        assert level.start_count > 0 and level.speed > 0, filename
        assert zs and 0 < zs[0] and zs[-1] < level.finish_z, filename
        for obj in level.objects:
            if isinstance(obj, Obstacle):
                # กว้างไม่เกินครึ่งถนน = มีช่องให้หลบเสมอ (สิ่งกีดขวางลบทุกคนที่โดน)
                assert obj.width <= C.ROAD_HALF_W, f"{filename}: obstacle z={obj.z} กว้างเกิน"
                assert abs(obj.x) <= C.ROAD_HALF_W, filename
        assert best_count(level) > 0, f"{filename}: เลือกประตูดีที่สุดแล้วยังแพ้"


def test_levels_get_harder():
    """ด่านหลังๆ วิ่งเร็วขึ้น (หรือเท่าเดิม) และยาวขึ้น (หรือเท่าเดิม)"""
    levels = [load_level(f) for f in list_levels()]
    for a, b in zip(levels, levels[1:]):
        assert b.speed >= a.speed or b.finish_z > a.finish_z, f"{b.name} ง่ายกว่า {a.name}"


def test_best_count_level1():
    # 10 -> +20=30 -> x3=90 -> +35=125 -> x2=250 -> สู้ศัตรู 40 = 210
    assert best_count(load_level("level1.json")) == 210


# ---------- ดาว + high score ----------

def test_stars():
    assert scores.stars(False, 100, 200) == 0
    assert scores.stars(True, 0, 200) == 0
    assert scores.stars(True, 10, 200) == 1
    assert scores.stars(True, 50, 200) == 2
    assert scores.stars(True, 100, 200) == 3
    assert scores.stars(True, 5, 0) == 1        # กันหารศูนย์


def test_highscore_save_and_keep_best(tmp_path=None):
    import tempfile
    folder = Path(tmp_path or tempfile.mkdtemp())
    path = folder / "scores.json"
    assert scores.load_scores(path) == {}                     # ยังไม่มีไฟล์
    assert scores.record("level1.json", 50, 2, path)
    assert not scores.record("level1.json", 30, 1, path)      # แย่กว่าเดิม ไม่ทับ
    assert scores.record("level1.json", 80, 1, path)          # ดีกว่า: คนเพิ่ม แต่ดาวเก็บค่าสูงสุดไว้
    assert scores.load_scores(path)["level1.json"] == {"count": 80, "stars": 2}
    path.write_text("not json{", encoding="utf-8")            # ไฟล์เสีย ต้องไม่ทำเกมพัง
    assert scores.load_scores(path) == {}


def test_unlock_needs_previous_win():
    files = ["level1.json", "level2.json", "level3.json"]
    assert scores.is_unlocked(files, 0, {})                    # ด่านแรกเปิดเสมอ
    assert not scores.is_unlocked(files, 1, {})
    won1 = {"level1.json": {"count": 10, "stars": 1}}
    assert scores.is_unlocked(files, 1, won1)
    assert not scores.is_unlocked(files, 2, won1)              # ข้ามด่านไม่ได้


# ---------- โหมดไม่รู้จบ ----------

def brute_force_routes(start, objects):
    """ลองทุกเส้นทางทีละเส้นแบบตรงไปตรงมา ใช้ตรวจ endless.winning_routes"""
    pairs = [o for o in objects if isinstance(o, GatePair)]
    wins = 0
    for choice in product((0, 1), repeat=len(pairs)):
        pick, count = iter(choice), start
        for o in objects:
            if isinstance(o, GatePair):
                count = (o.right if next(pick) else o.left).apply(count)
            elif isinstance(o, EnemyGroup):
                count = max(0, count - o.count)
        wins += count > 0
    return wins, 2 ** len(pairs)


def test_winning_routes_matches_brute_force():
    for filename in list_levels():
        level = load_level(filename)
        assert endless.winning_routes(level.start_count, level.objects) == \
            brute_force_routes(level.start_count, level.objects), filename


def play_endless(seed, chunks):
    """ผู้เล่นที่เลือกประตูดีที่สุดเสมอ (หลบสิ่งกีดขวางได้หมด) วิ่งไป chunks ช่วง  คืน (level, จำนวนคน, ทุกจำนวนระหว่างทาง)"""
    level = endless.EndlessLevel(seed=seed)
    count, idx, z, seen = endless.START_COUNT, 0, float(C.CROWD_OFFSET), []
    speeds = []
    while z < C.CROWD_OFFSET + chunks * endless.CHUNK_LEN:
        z += 25
        idx = level.advance(z, count, idx)
        speeds.append(level.speed)
        zs = [o.z for o in level.objects]
        assert zs == sorted(zs)
        while idx < len(level.objects) and z >= level.objects[idx].z:
            o = level.objects[idx]
            if isinstance(o, GatePair):
                count = max(o.left.apply(count), o.right.apply(count))
            elif isinstance(o, EnemyGroup):
                count = max(0, count - o.count)
            idx += 1
            seen.append(count)
        assert count > 0, f"seed {seed}: เลือกถูกทุกครั้งแล้วยังแพ้ที่ z={z}"
    assert speeds == sorted(speeds)                          # เร็วขึ้นเรื่อยๆ ไม่ช้าลง
    return level, count, seen


def test_endless_always_winnable_and_bounded():
    for seed in range(5):
        level, count, seen = play_endless(seed, 20)
        assert max(seen) <= endless.COUNT_CAP                  # คนไม่ล้นจนเกมช้า
        assert len(level.objects) < 40                         # ของที่ผ่านไปแล้วถูกทิ้ง
        for chunk in level.chunks:
            assert chunk["wins"] >= 1                          # ทุกช่วงมีทางชนะ


def test_endless_gets_harder():
    level, _, _ = play_endless(seed=7, chunks=20)
    ratios = [c["wins"] / c["total"] for c in level.chunks]
    assert sum(ratios[:3]) / 3 > 0.5                           # ช่วงแรก: ทางชนะเกินครึ่ง
    assert sum(ratios[12:18]) / 6 < 0.2                        # ช่วงหลัง: เหลือไม่ถึง 20%
    for c in level.chunks:                                     # ได้ใกล้เป้าแต่ละช่วง
        assert abs(c["wins"] / c["total"] - c["target"]) < 0.15, c
    assert endless.speed_for(10) > endless.speed_for(0)


def test_endless_obstacles_dodgeable():
    level = endless.EndlessLevel(seed=3)
    for k in range(30):
        level.make_chunk(50, len(level.objects))
    for o in level.objects:
        if isinstance(o, Obstacle):
            assert o.width <= C.ROAD_HALF_W and abs(o.x) + o.width / 2 <= C.ROAD_HALF_W


def test_endless_best_distance():
    import tempfile
    path = Path(tempfile.mkdtemp()) / "scores.json"
    assert scores.record_distance(1234.7, path)
    assert not scores.record_distance(900, path)
    assert scores.record_distance(5000, path)
    assert scores.load_scores(path)[scores.ENDLESS] == {"distance": 5000}


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
