"""ดาว + high score ที่บันทึกลงไฟล์   [เจ้าของ: C]

ทำไมแยกจาก ui.py: ส่วนนี้เป็น logic ล้วนๆ ไม่ต้องเปิดหน้าต่าง จึงเขียน test ได้ง่าย
"""
import json
import math
from pathlib import Path

SCORE_FILE = Path(__file__).parent / "highscores.json"   # อยู่ใน .gitignore (คะแนนของแต่ละเครื่อง)

# สัดส่วนของ "จำนวนคนมากที่สุดที่เป็นไปได้" (level.best_count) ที่ต้องได้เพื่อรับดาว 2 และ 3
TWO_STAR = 0.25
THREE_STAR = 0.5


def stars(won, count, best):
    """0 = แพ้, 1 = ชนะ, 2 = เหลือคน >= 25% ของค่าสูงสุด, 3 = >= 50%"""
    if not won or count <= 0:
        return 0
    if best <= 0:
        return 1
    ratio = count / best
    if ratio >= THREE_STAR:
        return 3
    if ratio >= TWO_STAR:
        return 2
    return 1


def thresholds(best):
    """จำนวนคนที่ต้องเหลืออย่างน้อยเพื่อได้ 2 ดาวและ 3 ดาว (ปัดขึ้น ให้ตรงกับ stars())"""
    return math.ceil(best * TWO_STAR), math.ceil(best * THREE_STAR)


def load_scores(path=None):
    """คืน dict {ชื่อไฟล์ด่าน: {"count": .., "stars": ..}}  ไฟล์หาย/เสีย = เริ่มใหม่ ไม่ให้เกมพัง"""
    try:
        with open(path or SCORE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def record(level_file, count, star_count, path=None):
    """บันทึกจำนวนคนและดาว แยกกัน เก็บค่าที่ดีที่สุดของแต่ละอย่าง  คืน True ถ้าจำนวนคนเป็นสถิติใหม่
    ทำไมแยก: เลขประตูสุ่มทุกรอบ จำนวนคนสูงสุดที่เป็นไปได้เลยต่างกันมาก รอบที่ได้ 3 ดาว
    อาจเหลือคนน้อยกว่าสถิติเดิม ถ้าบันทึกเฉพาะตอนคนเยอะกว่า ดาวที่ได้จะหายไป"""
    scores = load_scores(path)
    old = scores.get(level_file, {"count": 0, "stars": 0})
    old_count, old_stars = old.get("count", 0), old.get("stars", 0)
    new_record = count > old_count
    if not new_record and star_count <= old_stars:
        return False
    scores[level_file] = {"count": max(count, old_count), "stars": max(star_count, old_stars)}
    try:
        with open(path or SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass  # เขียนไฟล์ไม่ได้ (เช่น โฟลเดอร์อ่านอย่างเดียว) ก็เล่นต่อได้ แค่ไม่จำคะแนน
    return new_record


def is_unlocked(level_files, i, scores):
    """ด่านแรกเล่นได้เสมอ ด่านอื่นต้องชนะด่านก่อนหน้าก่อน (มีคะแนนบันทึกไว้ = เคยชนะ)"""
    return i == 0 or level_files[i - 1] in scores
