from __future__ import annotations

import difflib
import functools
import gzip
import hashlib
import io
import json
import os
import re
import runpy
import subprocess
import sys
import tempfile
import textwrap
import time
import traceback
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

WILDCARD = "…"


@dataclass
class Result:
    code: int
    out: str
    err: str
    seconds: float
    peak_memory: int | None = None

    @property
    def lines(self) -> list[str]:
        return self.out.splitlines()

    @property
    def crashed(self) -> bool:
        return "Traceback (most recent call last)" in self.err


MAIN_GUARD = re.compile(r"""^if\s+__name__\s*==\s*['"]__main__['"]\s*:""", re.M)


def locate_program(folder, name: str) -> Path | None:
    folder = Path(folder)
    if (folder / name).is_file():
        return folder / name
    candidates = sorted(p for p in folder.glob("*.py")
                        if p.is_file() and not p.name.startswith("test_") and p.name != "conftest.py")
    if len(candidates) == 1:
        return candidates[0]
    mains = [p for p in candidates if MAIN_GUARD.search(p.read_text(encoding="utf-8-sig", errors="replace"))]
    return mains[0] if len(mains) == 1 else None


def _caller_task_dir() -> Path | None:
    here = Path(__file__).resolve()
    frame = sys._getframe(1)
    while frame is not None:
        file = Path(frame.f_code.co_filename)
        if file.name.startswith("test_") and file.resolve() != here and file.parent.name == "tests":
            return file.resolve().parent.parent
        frame = frame.f_back
    return None


def find_program(name: str) -> Path:
    code_dir = os.environ.get("COURSE_CODE_DIR") or _caller_task_dir()
    if code_dir:
        found = locate_program(code_dir, name)
        if found:
            return found
        others = [p.name for p in Path(code_dir).glob("*.py") if not p.name.startswith("test_")]
        if len(others) > 1:
            raise AssertionError(f"Не найдена программа {name}: в папке задачи несколько файлов "
                                 f"({', '.join(sorted(others))}) - назовите программу {name} или оставьте "
                                 "`if __name__ == \"__main__\":` только в ней")
    else:
        for place in sys.path:
            if place and (Path(place) / name).is_file():
                return Path(place) / name
    raise AssertionError(f"Не найден файл программы {name} - создайте его в папке задачи")


def _normalize(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _forget_modules(folder: Path):
    target = os.path.normcase(str(folder))
    for name, module in list(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if file and os.path.normcase(os.path.dirname(os.path.abspath(file))) == target:
            del sys.modules[name]


def run(program: str, *args, stdin: str | bytes = "", files: dict | None = None,
        trace_memory: bool = False, cwd=None) -> Result:
    path = find_program(program).resolve()
    data = stdin.encode("utf-8") if isinstance(stdin, str) else stdin
    if cwd is not None:
        Path(cwd).mkdir(parents=True, exist_ok=True)
        return _start(path, [str(a) for a in args], data, str(cwd), files, trace_memory)
    with tempfile.TemporaryDirectory(prefix="course-run-") as workdir:
        return _start(path, [str(a) for a in args], data, workdir, files, trace_memory)


def _start(path: Path, args: list[str], data: bytes, workdir: str, files, trace_memory: bool) -> Result:
    for name, content in (files or {}).items():
        target = Path(workdir) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    if os.environ.get("COURSE_ISOLATED") == "1":
        return _run_isolated(path, args, data, workdir, trace_memory)
    return _run_here(path, args, data, workdir, trace_memory)


_LAUNCHER = """
import os, runpy, sys, tracemalloc
path = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path[0] = os.path.dirname(path)
trace = os.environ.pop("COURSE_TRACE_FILE", "")
if trace:
    tracemalloc.start()
try:
    runpy.run_path(path, run_name="__main__")
finally:
    if trace:
        with open(trace, "w") as file:
            file.write(str(tracemalloc.get_traced_memory()[1]))
"""


def _run_isolated(path: Path, args: list[str], data: bytes, workdir: str, trace_memory: bool) -> Result:
    timeout = float(os.environ.get("COURSE_RUN_TIMEOUT", "30"))
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COURSE_", "PYTHON"))}
    env.update(PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    trace_file = Path(tempfile.gettempdir()) / f"course-memory-{os.getpid()}-{time.time_ns()}"
    if trace_memory:
        env["COURSE_TRACE_FILE"] = str(trace_file)
    start = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, "-c", _LAUNCHER, str(path), *args], input=data,
                              capture_output=True, cwd=workdir, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise AssertionError(f"Программа работала дольше {timeout:g} с - зависла или слишком медленная") from None
    seconds = time.perf_counter() - start
    peak = None
    if trace_memory and trace_file.exists():
        peak = int(trace_file.read_text())
        trace_file.unlink()
    return Result(proc.returncode, _normalize(proc.stdout.decode("utf-8", "replace")),
                  _normalize(proc.stderr.decode("utf-8", "replace")), seconds, peak)


def _run_here(path: Path, args: list[str], data: bytes, workdir: str, trace_memory: bool) -> Result:
    saved = (sys.argv, sys.stdin, sys.stdout, sys.stderr, list(sys.path), os.getcwd())
    out_buffer, err_buffer = io.BytesIO(), io.BytesIO()
    code, peak = 0, None
    streams = (io.TextIOWrapper(io.BytesIO(data), encoding="utf-8"),
               io.TextIOWrapper(out_buffer, encoding="utf-8", newline="\n", write_through=True),
               io.TextIOWrapper(err_buffer, encoding="utf-8", newline="\n", write_through=True))
    sys.argv = [str(path), *args]
    sys.stdin, sys.stdout, sys.stderr = streams
    sys.path.insert(0, str(path.parent))
    _forget_modules(path.parent)
    os.chdir(workdir)
    start = time.perf_counter()
    if trace_memory:
        tracemalloc.start()
    try:
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exit_:
        if exit_.code is None:
            code = 0
        elif isinstance(exit_.code, int):
            code = exit_.code
        else:
            print(exit_.code, file=sys.stderr)
            code = 1
    except BaseException:
        traceback.print_exc()
        code = 1
    finally:
        seconds = time.perf_counter() - start
        if trace_memory:
            peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
        sys.argv, sys.stdin, sys.stdout, sys.stderr, sys.path[:], cwd = saved
        for stream in streams:
            try:
                stream.flush()
                stream.detach()
            except ValueError:
                pass
        os.chdir(cwd)
        _forget_modules(path.parent)
    return Result(code, _normalize(out_buffer.getvalue().decode("utf-8", "replace")),
                  _normalize(err_buffer.getvalue().decode("utf-8", "replace")), seconds, peak)


GOLDEN_FILE = "golden.json.gz"


def _golden_key(name: str, args, kwargs) -> str:
    def plain(value):
        if isinstance(value, (bytes, bytearray)):
            return {"bytes": bytes(value).hex()}
        raise TypeError(f"нельзя записать {type(value).__name__}")

    data = json.dumps([name, args, kwargs], sort_keys=True, ensure_ascii=False, default=plain)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def golden(func):
    name = f"{func.__module__}.{func.__name__}"

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = json.loads(json.dumps(func(*args, **kwargs)))
        record = os.environ.get("COURSE_GOLDEN_RECORD")
        if record:
            with open(record, "a", encoding="utf-8") as file:
                file.write(_golden_key(name, args, kwargs) + "\t" + json.dumps(result, ensure_ascii=False) + "\n")
        return result

    return wrapper


_GOLDEN_CACHE: dict = {}


def golden_lookup(module_file: str, name: str):
    path = Path(module_file).with_name(GOLDEN_FILE)

    def lookup(*args, **kwargs):
        if path not in _GOLDEN_CACHE:
            with gzip.open(path, "rt", encoding="utf-8") as file:
                _GOLDEN_CACHE[path] = json.load(file)
        try:
            return json.loads(json.dumps(_GOLDEN_CACHE[path][_golden_key(name, args, kwargs)]))
        except KeyError:
            raise AssertionError(f"Нет записанного ожидаемого ответа ({name}) - не меняйте тесты; "
                                 "если тесты обновлялись, возьмите свежую версию папки tests/") from None

    lookup.__name__ = name.rsplit(".", 1)[-1]
    return lookup


def line_matches(expected: str, actual: str) -> bool:
    if WILDCARD not in expected:
        return expected == actual
    pattern = ".*".join(re.escape(part) for part in expected.split(WILDCARD))
    return re.fullmatch(pattern, actual, re.S) is not None


def expected_lines(expected) -> list[str]:
    if isinstance(expected, str):
        expected = textwrap.dedent(expected).strip("\n").splitlines()
    return [line.rstrip() for line in expected]


def _show(result: Result) -> str:
    text = f"код возврата {result.code}"
    if result.err:
        text += "\nstderr:\n" + textwrap.indent(result.err[-2000:], "  ")
    return text


def assert_output(result: Result, expected, code: int = 0):
    want = expected_lines(expected)
    got = result.lines
    same = len(want) == len(got) and all(line_matches(w, g) for w, g in zip(want, got))
    if not same:
        diff = "\n".join(difflib.unified_diff(want, got, "ожидается", "вывод программы", lineterm="", n=2))
        raise AssertionError(f"Вывод не совпадает (- ожидается, + ваш вывод):\n{diff}\n{_show(result)}")
    if result.crashed or result.code != code:
        raise AssertionError(f"Ожидался код возврата {code}\n{_show(result)}")


def assert_lines(result: Result, *expected: str):
    position = 0
    for want in (line.rstrip() for line in expected):
        for index in range(position, len(result.lines)):
            if line_matches(want, result.lines[index]):
                position = index + 1
                break
        else:
            raise AssertionError(f"В выводе нет строки {want!r} (после уже найденных)\n"
                                 f"Вывод:\n{textwrap.indent(result.out[-3000:], '  ')}\n{_show(result)}")
    if result.crashed:
        raise AssertionError(f"Программа упала\n{_show(result)}")


def assert_error(result: Result, *fragments: str, code: int = 1):
    problem = ""
    if result.crashed:
        problem = "программа упала с исключением вместо понятного сообщения об ошибке"
    elif result.code != code:
        problem = f"ожидался код возврата {code}"
    elif not any(line.startswith("Ошибка:") for line in result.err.splitlines()):
        problem = "в stderr нет строки, начинающейся с «Ошибка:»"
    else:
        missing = [f for f in fragments if f not in result.err]
        if missing:
            problem = f"в сообщении об ошибке нет: {', '.join(map(repr, missing))}"
    if problem:
        raise AssertionError(f"{problem}\n{_show(result)}\nstdout:\n{textwrap.indent(result.out[-1000:], '  ')}")
