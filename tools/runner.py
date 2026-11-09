from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
TIMEOUT = 300

PYTEST_INI = """\
[pytest]
addopts = -p no:cacheprovider
markers =
    category(name): категория тест-кейса (typical, naive, edge, format, fuzz)
"""

CATEGORY_PLUGIN = '''\
def pytest_collection_modifyitems(items):
    for item in items:
        mark = item.get_closest_marker("category")
        item.user_properties.append(("category", mark.args[0] if mark and mark.args else "other"))
'''

CATEGORIES = {
    "typical": "Типичные",
    "naive": "Наивные",
    "edge": "Краевые",
    "format": "Формат",
    "fuzz": "Фаззинг",
}
COVERAGE_RC = """\
[run]
branch = true
omit =
    */tests/*
    */conftest.py

[report]
exclude_also =
    if __name__ == .__main__.:
"""


@dataclass
class TestRun:
    total: int = 0
    passed: int = 0
    failed: list = field(default_factory=list)
    timeout: bool = False
    crashed: str = ""
    coverage: float | None = None
    output: str = ""
    by_category: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.total > 0 and self.passed == self.total and not self.timeout and not self.crashed

    def to_dict(self) -> dict:
        return {"total": self.total, "passed": self.passed, "failed": self.failed,
                "timeout": self.timeout, "crashed": self.crashed, "coverage": self.coverage,
                "by_category": self.by_category}

    def category_report(self, title: str) -> str:
        lines = [f"{title}:"]
        keys = list(CATEGORIES) + sorted(set(self.by_category) - set(CATEGORIES))
        for key in keys:
            if key not in self.by_category:
                continue
            passed, total = self.by_category[key]
            lines.append(f"- {CATEGORIES.get(key, key)}: {passed}/{total} {'✓' if passed == total else '✗'}")
        lines.append(f"Итого: {self.passed}/{self.total}")
        return "\n".join(lines)


def task_dirs(base: Path = TASKS_DIR) -> list[Path]:
    return sorted(p for p in base.glob("t[0-9][0-9]_*") if p.is_dir())


def task_number(path: Path) -> int:
    return int(path.name[1:3])


def find_task(selector: str, base: Path = TASKS_DIR) -> Path:
    for path in task_dirs(base):
        if selector in (path.name, str(task_number(path)), f"{task_number(path):02d}"):
            return path
    raise SystemExit(f"Нет задачи {selector!r}. Есть: "
                     + ", ".join(str(task_number(p)) for p in task_dirs(base)))


def module_files(task_dir: Path) -> list[Path]:
    return sorted(p for p in task_dir.glob("*.py") if not p.name.startswith("test_"))


def _parse_junit(path: Path, result: TestRun):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    for suite in suites:
        for case in suite.iter("testcase"):
            result.total += 1
            bad = case.find("failure") is not None or case.find("error") is not None
            skipped = case.find("skipped") is not None
            category = next((p.get("value") for p in case.iter("property") if p.get("name") == "category"),
                            "other")
            counts = result.by_category.setdefault(category, [0, 0])
            counts[1] += 1
            if bad or skipped:
                name = case.get("name", "?")
                result.failed.append(name + (" (пропущен)" if skipped and not bad else ""))
            else:
                result.passed += 1
                counts[0] += 1


def run_tests(test_files, code_dir: Path, *, coverage: bool = False, timeout: int = TIMEOUT,
              verbose: bool = False, extra_env: dict | None = None, import_code: bool = False) -> TestRun:
    result = TestRun()
    test_files = [Path(f) for f in test_files]
    if not test_files:
        return result
    with tempfile.TemporaryDirectory(prefix="course-") as tmp:
        tmp = Path(tmp)
        tests = tmp / "tests"
        tests.mkdir()
        for f in test_files:
            shutil.copy2(f, tests / f.name)
        for folder in {f.parent for f in test_files}:
            for helper in [*folder.glob("*.py"), *folder.glob("golden.json.gz")]:
                if not helper.name.startswith("test_") and helper.name != "conftest.py":
                    shutil.copy2(helper, tests / helper.name)
        (tmp / "pytest.ini").write_text(PYTEST_INI, encoding="utf-8")
        (tmp / "conftest.py").write_text(CATEGORY_PLUGIN, encoding="utf-8")
        junit = tmp / "junit.xml"
        cmd = [sys.executable, "-m", "pytest", str(tests), "-c", str(tmp / "pytest.ini"),
               "--rootdir", str(tmp), "--import-mode=importlib", f"--junitxml={junit}",
               "-q", "--tb=short" if verbose else "--tb=line", "-p", "no:cacheprovider"]
        if coverage:
            (tmp / ".coveragerc").write_text(COVERAGE_RC, encoding="utf-8")
            cmd += [f"--cov={code_dir}", f"--cov-config={tmp / '.coveragerc'}",
                    f"--cov-report=json:{tmp / 'coverage.json'}", "--cov-report=term-missing"]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tests), str(Path(__file__).resolve().parent)] + ([str(code_dir)] if import_code else [])),
                   COURSE_CODE_DIR=str(Path(code_dir).resolve()), PYTHONDONTWRITEBYTECODE="1",
                   PYTHONIOENCODING="utf-8", **(extra_env or {}))
        try:
            proc = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=timeout)
            result.output = proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as error:
            result.timeout = True
            result.output = (error.stdout or b"").decode("utf-8", "replace") \
                if isinstance(error.stdout, bytes) else (error.stdout or "")
            return result
        if junit.exists():
            _parse_junit(junit, result)
        if result.total == 0:
            last = [line for line in result.output.splitlines() if line.strip()]
            result.crashed = last[-1] if last else "pytest не запустился"
        cov_file = tmp / "coverage.json"
        if coverage and cov_file.exists():
            data = json.loads(cov_file.read_text(encoding="utf-8"))
            result.coverage = round(data["totals"]["percent_covered"], 1)
    return result


def coverage_table(output: str) -> str:
    match = re.search(r"(Name\s+Stmts.*?TOTAL[^\n]*)", output, re.S)
    return match.group(1) if match else ""
