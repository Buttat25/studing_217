"""Чтобы можно было запускать pytest напрямую: `pytest tasks/t01_trains`.

Добавляет в sys.path папку tools/ (помощник запуска программ course_program), папки задач
(там лежат ваши программы) и папки их тестов. Основной способ проверки — `python tools/check.py N`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
for task_dir in sorted((ROOT / "tasks").glob("t[0-9][0-9]_*")):
    sys.path.insert(0, str(task_dir))
    sys.path.insert(0, str(task_dir / "tests"))          # вспомогательные модули тестов
