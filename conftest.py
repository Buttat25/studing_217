import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
for task_dir in sorted((ROOT / "tasks").glob("t[0-9][0-9]_*")):
    sys.path.insert(0, str(task_dir))
    sys.path.insert(0, str(task_dir / "tests"))
