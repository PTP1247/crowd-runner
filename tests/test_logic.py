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
from gate import GatePair
from level import (load_level, list_levels, best_count, build_object,
                   run_count, fatal_gates, max_wrong_picks, difficulty,
                   dodge_spans, obstacle_style)


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


def test_big_crowd_simulates_sample():
    """คนเยอะจำลองแค่ตัวแทน SIM_PEOPLE คน แต่นับจำนวนจริงครบ และโดนชนแล้วเสียตามสัดส่วน"""
    crowd = Crowd(1000)
    assert crowd.count == 1000 and len(crowd.people) == C.SIM_PEOPLE
    lost = crowd.remove(crowd.people[: C.SIM_PEOPLE // 2])      # ตัวแทนโดนครึ่งหนึ่ง
    assert lost == 500 and crowd.count == 500
    assert len(crowd.people) == C.SIM_PEOPLE                     # เติมตัวแทนกลับให้ครบ
    crowd.count = 40                                             # คนน้อย: ตัวแทน = คนจริง 1 ต่อ 1
    assert len(crowd.people) == 40 and crowd.spread() == 1
    assert crowd.remove(crowd.people[:3]) == 3 and crowd.count == 37
    assert crowd.remove(list(crowd.people)) == 37 and crowd.count == 0


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


def test_obstacles_random_but_on_road():
    """ลายสิ่งกีดขวางสุ่มใหม่ทุกครั้งที่โหลด แต่ขอบต้องไม่หลุดถนนตลอดการแกว่ง"""
    import random
    for filename in list_levels():
        for seed in range(20):
            for obj in load_level(filename, random.Random(seed)).objects:
                if isinstance(obj, Obstacle):
                    reach = abs(obj.start_x) + obj.amplitude + obj.width / 2
                    assert reach <= C.ROAD_HALF_W + 1e-9, f"{filename}: obstacle z={obj.z} หลุดถนน"
    layouts = {tuple(round(o.x) for o in load_level("level8.json", random.Random(s)).objects
                     if isinstance(o, Obstacle)) for s in range(5)}
    assert len(layouts) > 1, "เล่นแต่ละรอบควรได้ลายสิ่งกีดขวางต่างกัน"


def test_obstacles_passable_and_scale_with_difficulty():
    """สุ่มสิ่งกีดขวางแล้วต้องหลบพ้นได้เสมอ (บนเส้นทางเลือกประตูดีที่สุด) และด่านยากได้สิ่งกีดขวางโหดกว่า"""
    import random
    for filename in list_levels():
        for seed in range(10):
            level = load_level(filename, random.Random(seed))
            assert dodge_spans(level), f"{filename} seed {seed}: มีสิ่งกีดขวางที่หลบไม่ทัน"
    easy, hard = obstacle_style(load_level("level1.json")), obstacle_style(load_level("level10.json"))
    assert easy[0][1] < hard[0][1]          # กว้างได้มากกว่า
    assert easy[1][2] < hard[1][2]          # โอกาสได้ลายแกว่งเร็วมากกว่า
    assert easy[3] > hard[3]                # ช่องหลบแคบกว่า


def test_dodge_spans_detects_blocked_road():
    level = load_level("level1.json")
    for obj in level.objects:
        if isinstance(obj, Obstacle):       # ขวางกลางถนนทั้งเส้น หลบไม่ได้แน่นอน
            obj.width, obj.start_x, obj.amplitude = 2 * C.ROAD_HALF_W, 0, 0
    assert dodge_spans(level) == []


def test_random_gates_keep_difficulty():
    """สุ่มเลขประตู + สลับซ้าย/ขวาแล้ว ความยากต้องเท่ากับด่านตามไฟล์ และเลขต้องเปลี่ยนจริง"""
    import random

    def labels(level):
        return [(o.left.label(), o.right.label()) for o in level.objects if isinstance(o, GatePair)]

    for filename in list_levels():
        original = load_level(filename)
        variants = [load_level(filename, random.Random(seed)) for seed in range(10)]
        for level in variants:
            assert difficulty(level) == difficulty(original), filename
            assert best_count(level) > 0, filename
        assert any(labels(v) != labels(original) for v in variants), f"{filename}: เลขประตูไม่เคยเปลี่ยน"


def test_levels_get_harder():
    """ด่านหลังๆ วิ่งเร็วขึ้น (หรือเท่าเดิม) และยาวขึ้น (หรือเท่าเดิม)"""
    levels = [load_level(f) for f in list_levels()]
    for a, b in zip(levels, levels[1:]):
        assert b.speed >= a.speed or b.finish_z > a.finish_z, f"{b.name} ง่ายกว่า {a.name}"


# ด่านถัดไปง่ายกว่าด่านที่ยากที่สุดก่อนหน้าได้ไม่เกินเท่านี้ (เผื่อด่าน "พักหายใจ" หลังด่านยาก)
DIFFICULTY_DIP = 5


def test_difficulty_increases():
    """คะแนนความยาก (level.difficulty) ต้องไม่ต่ำกว่าด่านที่ยากที่สุดก่อนหน้าเกิน DIFFICULTY_DIP

    ทำไมเทียบกับด่านที่ยากที่สุด ไม่ใช่แค่ด่านก่อนหน้า: กันความยากค่อยๆ ไหลลงทีละนิดหลายด่านติดกัน
    """
    hardest, bad = None, []
    for filename in list_levels():
        level = load_level(filename)
        score = difficulty(level)
        if hardest and score < hardest[1] - DIFFICULTY_DIP:
            bad.append(f"{level.name} ({score}) ง่ายกว่า {hardest[0]} ({hardest[1]})")
        if not hardest or score > hardest[1]:
            hardest = (level.name, score)
    assert not bad, "\n".join(bad)


def test_difficulty_level1():
    level = load_level("level1.json")
    assert run_count(level) == best_count(level) == 155
    assert run_count(level, {0}) == 95            # เลือก x2 แทน +20 ยังรอด
    assert run_count(level, {2}) == 0             # เลือก /3 แทน +35 แพ้
    assert fatal_gates(level) == [2]
    assert max_wrong_picks(level) == 2
    assert difficulty(level) == 24.3              # 40*(1/4) + 25*(1/3) + 15*0 + 20*(3/10)


def test_best_count_level1():
    # 10 -> +20=30 -> x3=90 -> +35=125 -> x2=250 -> สู้ศัตรู 95 = 155
    assert best_count(load_level("level1.json")) == 155


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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
