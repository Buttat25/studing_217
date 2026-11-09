from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_NAMES = {"dict", "set", "frozenset", "OrderedDict", "defaultdict", "Counter", "ChainMap",
                   "lru_cache", "cache"}
CALC_MODULES = ("calc_math", "calc_convert", "calc_matrix", "calc_logic")


def _sources(task_dir: Path) -> dict[str, ast.AST]:
    result = {}
    for path in sorted(task_dir.glob("*.py")):
        try:
            result[path.name] = ast.parse(path.read_text(encoding="utf-8-sig"))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            result[path.name] = None
    return result


def no_builtin_maps(task_dir: Path) -> list[str]:
    problems = []
    for name, tree in _sources(task_dir).items():
        if tree is None:
            problems.append(f"{name}: не удалось разобрать файл")
            continue
        for node in ast.walk(tree):
            what = None
            if isinstance(node, (ast.Dict, ast.DictComp)):
                what = "словарь {…}"
            elif isinstance(node, (ast.Set, ast.SetComp)):
                what = "множество {…}"
            elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES - {"cache"}:
                what = node.id
            elif isinstance(node, ast.Attribute) and (node.attr in FORBIDDEN_NAMES - {"cache"} or (
                    node.attr == "cache" and isinstance(node.value, ast.Name) and node.value.id == "functools")):
                what = node.attr
            elif isinstance(node, ast.ImportFrom) and node.module in ("collections", "functools"):
                found = [a.name for a in node.names if a.name in FORBIDDEN_NAMES]
                what = ", ".join(found) or None
            if what:
                problems.append(f"{name}:{node.lineno}: {what} - нужны свои структуры данных")
    return sorted(set(problems), key=lambda p: (p.split(":")[0], int(p.split(":")[1]) if p.split(":")[1].isdigit() else 0))


def independent_modules(task_dir: Path) -> list[str]:
    sources = _sources(task_dir)
    problems = [f"нет файла {m}.py" for m in CALC_MODULES if f"{m}.py" not in sources]
    for name, tree in sources.items():
        for node in ast.walk(tree) if tree is not None else ():
            if isinstance(node, ast.Name) and node.id in ("eval", "exec"):
                problems.append(f"{name}:{node.lineno}: {node.id} запрещён - выражение приходит от пользователя")
    for module in CALC_MODULES:
        tree = sources.get(f"{module}.py")
        if tree is None:
            if f"{module}.py" in sources:
                problems.append(f"{module}.py: не удалось разобрать файл")
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module.split(".")[0]]
            for other in names:
                if other in CALC_MODULES and other != module:
                    problems.append(f"{module}.py:{node.lineno}: импортирует {other} - модули должны быть независимыми")
    return problems


RULES = {
    "t02_cache": no_builtin_maps,
    "t07_calculator": independent_modules,
}


def check_code(task_dir: Path) -> list[str] | None:
    rule = RULES.get(task_dir.name)
    return None if rule is None else rule(task_dir)
