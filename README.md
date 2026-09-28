# Crowd Runner (Python midterm)

เกมคนวิ่งผ่านประตู `+ - × ÷` เลียนแบบเกมโฆษณา ทำด้วย Pygame

## รันเกม

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## ปุ่ม

| ปุ่ม | ทำอะไร |
|---|---|
| Space / คลิก | เริ่มเกม |
| A, D หรือ ลูกศรซ้าย/ขวา | เลื่อนกลุ่มคน |
| กดเมาส์ค้างแล้วลาก | เลื่อนกลุ่มคนตามเมาส์ |
| V | สลับมุมมอง flat (มองจากบน) / depth (แนวลึก) |
| R | เล่นใหม่ (หน้าจบ) |

## ทดสอบ

```bash
python -m pytest        # หรือ python tests/test_logic.py
```

## โครงสร้าง

| ไฟล์ | หน้าที่ | เจ้าของ |
|---|---|---|
| `main.py` | game loop, state machine | A |
| `camera.py` | แปลง (x, z) -> จอ | A |
| `config.py` | ค่าคงที่ทั้งหมด | ทุกคน (แก้ระวัง) |
| `crowd.py` `gate.py` `obstacle.py` `enemy.py` | gameplay | B |
| `level.py` `levels/*.json` `ui.py` `tests/` `assets/` | ด่าน, UI, ทดสอบ | C |

คู่มือทำงานร่วมกันอยู่ใน `GUIDE_TH.md`
