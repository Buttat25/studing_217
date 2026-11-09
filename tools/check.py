from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from code_rules import check_code
from course_program import locate_program
from runner import ROOT, TASKS_DIR, find_task, module_files, run_tests, task_dirs


DETAIL_LINES = 120


def required_programs(task_dir: Path) -> list[str]:
    names = set()
    for test in (task_dir / "tests").glob("test_*.py"):
        names |= set(re.findall(r'^PROGRAM\s*=\s*"([^"]+)"', test.read_text(encoding="utf-8"), re.M))
    return sorted(names)


def check_task(task_dir: Path, verbose: bool) -> dict:
    missing = [name for name in required_programs(task_dir) if locate_program(task_dir, name) is None]
    public = run_tests(sorted((task_dir / "tests").glob("test_*.py")), task_dir, verbose=verbose)
    code = None if missing else check_code(task_dir)
    return {"task": task_dir.name, "public": public, "missing": missing, "code": code}


def task_title(task_name: str) -> str:
    return f"Задача {int(task_name[1:3])}"


def text_report(results: list[dict]) -> str:
    blocks = []
    for result in results:
        public = result["public"]
        if result["missing"]:
            blocks.append(f"{task_title(result['task'])}:\n- нет файла: {', '.join(result['missing'])}")
        elif public.timeout or public.crashed:
            blocks.append(f"{task_title(result['task'])}:\n- тесты не выполнены "
                          f"({'превышено время' if public.timeout else public.crashed})")
        else:
            blocks.append(public.category_report(task_title(result["task"])))
    return "\n\n".join(blocks)


def describe(result: dict, verbose: bool) -> list[str]:
    public = result["public"]
    lines = [f"== {result['task']} =="]
    files = sorted(p.name for p in module_files(ROOT / "tasks" / result["task"]))
    if result["missing"] and len(files) > 1:
        lines.append(f"  Не найдена программа {', '.join(result['missing'])}: в папке несколько файлов "
                     f"({', '.join(files)}) - назовите программу как в README или оставьте "
                     "`if __name__ == \"__main__\":` только в ней")
        return lines
    if result["missing"]:
        many = len(result["missing"]) > 1
        lines.append(f"  {'Нет файлов' if many else 'Нет файла'}: {', '.join(result['missing'])} - "
                     f"{'создайте их' if many else 'создайте его'} в папке tasks/{result['task']} "
                     "по разделу «Программа» в README задачи")
        return lines
    if public.timeout:
        lines.append("  Тесты: превышено время - где-то бесконечный цикл или очень медленный алгоритм")
    elif public.crashed:
        lines.append(f"  Тесты: не запустились - {public.crashed}")
    else:
        lines += ["  " + row for row in public.category_report(task_title(result["task"])).splitlines()]
        for name in public.failed[: None if verbose else 5]:
            lines.append(f"    ✗ {name}")
        if len(public.failed) > 5 and not verbose:
            lines.append(f"    … и ещё {len(public.failed) - 5}; подробно: -v")
    if result["code"] is not None:
        lines.append("  Требования к коду (см. README): " + ("✓" if not result["code"] else "✗"))
        lines += [f"    ✗ {problem}" for problem in result["code"][:10]]
        if len(result["code"]) > 10:
            lines.append(f"    … и ещё {len(result['code']) - 10}")
    if verbose and (public.failed or public.crashed):
        output = public.output.splitlines()
        start = next((i for i, row in enumerate(output) if "FAILURES" in row and row.startswith("=")), None)
        if start is None:
            lines += ["", "  --- вывод pytest ---"] + ["  " + row for row in output[-60:]]
        else:
            details = [row for row in output[start + 1:] if not row.startswith("FAILED ")][:DETAIL_LINES]
            lines += ["", "  --- первые упавшие тесты: что ожидалось и что напечатала программа ---"]
            lines += ["  " + row for row in details]
            if len(output) - start > DETAIL_LINES:
                lines.append(f"  … (показаны первые {DETAIL_LINES} строк; исправьте эти тесты и запустите снова)")
    return lines


def summary_row(result: dict) -> str:
    public = result["public"]
    if result["missing"]:
        return f"| {result['task']:<16} | {'нет файла':>9} | ✗ |"
    text = "время!" if public.timeout else ("ошибка" if public.crashed else f"{public.passed}/{public.total}")
    mark = "✓" if public.ok else "✗"
    return f"| {result['task']:<16} | {text:>9} | {mark} |"


def cmd_check(selector: str, verbose: bool) -> int:
    dirs = task_dirs() if selector == "all" else [find_task(selector)]
    results = []
    for task_dir in dirs:
        result = check_task(task_dir, verbose)
        results.append(result)
        print("\n".join(describe(result, verbose)))
        print()
    if len(results) > 1:
        print("| Задача           | Тесты     |   |")
        print("|------------------|-----------|---|")
        for result in results:
            print(summary_row(result))
    return 0 if all(r["public"].ok for r in results) else 1


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE).strip("_")
    return cleaned or "student"


def cmd_submit(name: str, out_dir: Path) -> int:
    if not name.strip():
        raise SystemExit("Укажите имя: --name \"Фамилия Имя\"")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    archive = out_dir / f"submission_{safe_name(name)}_{stamp}.zip"
    report = {"name": name.strip(), "created": datetime.now().isoformat(timespec="seconds"),
              "python": platform.python_version(), "tasks": {}}
    print(f"Проверяю решения перед отправкой ({name.strip()})…")
    results = []
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for task_dir in task_dirs():
            result = check_task(task_dir, verbose=False)
            results.append(result)
            report["tasks"][task_dir.name] = {"public": result["public"].to_dict(), "code": result["code"]}
            print("  " + summary_row(result))
            for path in module_files(task_dir):
                zf.write(path, f"{task_dir.name}/{path.name}")
        text = f"Отчёт о прохождении открытых тестов - {name.strip()}\n\n{text_report(results)}\n"
        zf.writestr("report.json", json.dumps(report, ensure_ascii=False, indent=2))
        zf.writestr("report.txt", text)
    report_path = archive.with_suffix(".txt")
    report_path.write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"Готово: {archive}")
    print(f"Отчёт: {report_path}")
    print("Отправьте этот файл преподавателю - он проверит решения контрольными тестами.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Самопроверка задач курса")
    parser.add_argument("target", help="номер задачи, all или submit")
    parser.add_argument("-v", "--verbose", action="store_true", help="подробный вывод")
    parser.add_argument("--name", default="", help="ваше имя (для submit)")
    parser.add_argument("--out", default=str(ROOT / "submissions"), help="куда сохранить архив")
    args = parser.parse_args(argv)
    if not TASKS_DIR.exists():
        raise SystemExit("Не найдена папка tasks/")
    if args.target == "submit":
        return cmd_submit(args.name, Path(args.out))
    return cmd_check(args.target, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
