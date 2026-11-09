# Открытые тесты для самопроверки. Сгенерировано из контрольных тестов —
# не редактируйте: контрольные тесты преподавателя проверяют больше случаев.
"""Задача 7. Тест-кейсы 7.1–7.22: калькулятор получает строки из stdin и печатает ответы.

Программа: python calculator.py (диалог) или python calculator.py "выражение".
"""
import random
import re
from fractions import Fraction

import pytest

from course_program import run

PROGRAM = "calculator.py"


def session(*lines):
    result = run(PROGRAM, stdin="".join(line + "\n" for line in lines))
    assert result.code == 0 and not result.crashed, result.err[-2000:]
    return result


def answer(*lines):
    """Ответ программы на последнюю строку (после выполнения предыдущих)."""
    before = len(session(*lines[:-1]).lines) if len(lines) > 1 else 0
    return "\n".join(session(*lines).lines[before:])


def is_error(text):
    return text.startswith("ОШИБКА: ") and "\n" not in text


# ============================================================ 🟢 Типичные
@pytest.mark.category("typical")
@pytest.mark.parametrize("expr, result", [
    ("2 + 2 * 2", "= 6"), ("3 + 4 * 5", "= 23"), ("10 - 2 * 3", "= 4"),
    ("2 * 3 + 4 * 5", "= 26"), ("1 + 6 / 3", "= 3.0"), ("2 ^ 3 * 2", "= 16"),
])
def test_7_1_operator_priority(expr, result):
    """7.1 Приоритет операций."""
    assert answer(expr) == result


@pytest.mark.category("typical")
@pytest.mark.parametrize("expr, result", [
    ("(2 + 2) * 2", "= 8"), ("(1 + 2) * (3 + 4)", "= 21"), ("2 * (3 + 4) * 5", "= 70"),
    ("(10 - 4) / 3", "= 2.0"), ("(2 + 3) ^ 2", "= 25"),
])
def test_7_2_parentheses(expr, result):
    """7.2 Скобки меняют порядок вычислений."""
    assert answer(expr) == result


@pytest.mark.category("typical")
@pytest.mark.parametrize("command, result", [
    ("matrix [[1, 2], [3, 4]] + [[5, 6], [7, 8]]", "= [[6, 8],\n   [10, 12]]"),
    ("matrix [[1, 2, 3]] + [[3, 2, 1]]", "= [[4, 4, 4]]"),
    ("matrix [[1], [2]] + [[10], [20]]", "= [[11],\n   [22]]"),
    ("matrix [[0.5, 1], [2, 3]] + [[0.5, 0], [0, -3]]", "= [[1.0, 1],\n   [2, 0]]"),
])
def test_7_4_matrix_addition(command, result):
    """7.4 Сложение матриц."""
    assert answer(command) == result


@pytest.mark.category("typical")
@pytest.mark.parametrize("expr, result", [
    ("true AND (false OR true)", "= true"), ("false OR false", "= false"),
    ("NOT false AND true", "= true"), ("(true OR false) AND NOT true", "= false"),
    ("TRUE and not FALSE", "= true"),
])
def test_7_5_logic(expr, result):
    """7.5 Логические выражения."""
    assert answer(expr) == result


# ============================================================ 🟡 Наивные
@pytest.mark.category("naive")
@pytest.mark.parametrize("expr", ["10 / 0", "1 / (3 - 3)", "0 / 0", "5 / 0.0", "x / y, где x=1, y=0", "2 ^ -1 / 0"])
def test_7_6_division_by_zero(expr):
    """7.6 Деление на ноль — ошибка, а не inf и не падение."""
    assert is_error(answer(expr))


@pytest.mark.category("naive")
@pytest.mark.parametrize("expr", ["log(-5)", "log(0)", "ln(-1)", "log(-0.001)", "ln(0)", "log(-8, 2)"])
def test_7_7_log_of_non_positive(expr):
    """7.7 Логарифм от неположительного числа — ошибка."""
    assert is_error(answer(expr))


@pytest.mark.category("naive")
@pytest.mark.parametrize("command, sizes", [
    ("matrix [[1, 2, 3]] * [[1], [2]]", ("1×3", "2×1")),
    ("matrix [[1, 2]] * [[1, 2]]", ("1×2", "1×2")),
    ("matrix [[1], [2], [3]] * [[1], [2], [3]]", ("3×1", "3×1")),
    ("matrix [[1, 2], [3, 4]] + [[1, 2, 3]]", ("2×2", "1×3")),
    ("matrix [[1]] * [[1, 2], [3, 4]]", ("1×1", "2×2")),
])
def test_7_9_incompatible_matrix_sizes(command, sizes):
    """7.9 Несовместимые размеры матриц — ошибка с размерами (знак ×)."""
    output = answer(command)
    assert is_error(output) and re.search(f"{sizes[0]}.*{sizes[1]}", output), output


# ============================================================ 🔴 Краевые
@pytest.mark.category("edge")
@pytest.mark.parametrize("expr, result", [
    ("((2 + 3) * (4 - 1)) / 2", "= 7.5"), ("(((1 + 1)))", "= 2"),
    ("((1 + 2) * (3 + (4 - 1)))", "= 18"), ("2 * ((3))", "= 6"), ("((((((7))))))", "= 7"),
])
def test_7_10_nested_parentheses(expr, result):
    """7.10 Вложенные скобки."""
    assert answer(expr) == result


@pytest.mark.category("edge")
@pytest.mark.parametrize("expr, result", [
    ("-5 + (-3) * 2", "= -11"), ("-(-3)", "= 3"), ("-2 * -2", "= 4"),
    ("3 - -3", "= 6"), ("-(2 + 3)", "= -5"), ("-2 ^ 2", "= -4"),
])
def test_7_11_negative_numbers(expr, result):
    """7.11 Отрицательные числа и унарный минус."""
    assert answer(expr) == result


@pytest.mark.category("edge")
@pytest.mark.parametrize("expr, result", [
    ("10^100", "= 1" + "0" * 100),
    ("2^200", f"= {2 ** 200}"),
    ("10^100 + 1", "= 1" + "0" * 99 + "1"),
    ("10^999", "= 1" + "0" * 999),
])
def test_7_12_big_numbers_are_exact(expr, result):
    """7.12 Большие числа считаются точно."""
    assert answer(expr) == result


@pytest.mark.category("edge")
@pytest.mark.parametrize("expr", ["10^1000", "9^9^9", "10.0^400"])
def test_7_12_too_big_numbers(expr):
    result = session(expr)
    assert is_error(result.out) and result.seconds < 2, result.out[:200]


@pytest.mark.category("edge")
@pytest.mark.parametrize("expr, result", [
    ("1 / 3", "= 0.33333"), ("2 / 3", "= 0.66667"), ("1 / 7", "= 0.14286"), ("10 / 3", "= 3.33333"),
    ("0.1 + 0.2", "= 0.3"),
])
def test_7_13_precision_5(expr, result):
    """7.13 Точность 5 знаков."""
    assert session("precision 5", expr).lines == ["Точность установлена: 5 знаков после запятой", result]


# ============================================================ ❌ Формат
@pytest.mark.category("format")
@pytest.mark.parametrize("expr", ["2 + * 3", "* 2", "2 +", "2 3", "2 ** * 2", "+", "2 + + * 3"])
def test_7_15_bad_syntax(expr):
    """7.15 Некорректный синтаксис — ошибка."""
    assert is_error(answer(expr))


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["convert 5 km", "convert 5", "convert km to m", "convert 5 km to",
                                     "convert 5 km miles", "convert"])
def test_7_17_incomplete_convert(command):
    """7.17 Неполная команда convert — ошибка."""
    assert is_error(answer(command))


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["matrix [[1, 2], [3]]", "matrix [[1], [2, 3]] + [[1]]", "matrix [[]]",
                                     "matrix [1, 2]", "matrix [[1, 2], [3, 'x']]", "matrix [[1, 2]", "matrix"])
def test_7_18_bad_matrix(command):
    """7.18 Некорректная матрица — ошибка."""
    assert is_error(answer(command))


# ============================================================ 🎲 Фаззинг
def random_expr(rng, depth, allow_division=True):
    """(текст, точное значение Fraction или "zero", если где-то деление на ноль, атом ли это)."""
    if depth == 0 or rng.random() < 0.25:
        n = rng.randint(0, 20)
        return str(n), Fraction(n), True
    op = rng.choice("+-*/" if allow_division else "+-*")
    lt, lv, la = random_expr(rng, depth - 1, allow_division)
    rt, rv, ra = random_expr(rng, depth - 1, allow_division and op != "/")   # делитель — без деления
    left = lt if la else f"({lt})"
    right = rt if ra else f"({rt})"
    if "zero" in (lv, rv) or (op == "/" and rv == 0):
        value = "zero"
    else:
        value = {"+": lv + rv, "-": lv - rv, "*": lv * rv, "/": lv / rv if op == "/" else None}[op]
    text = f"{left} {op} {right}"
    if value != "zero" and rng.random() < 0.15:
        text, value = f"-({text})", -value
    return text, value, False


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [1, 2])
def test_7_19_random_math_expressions(seed):
    """7.19 1000 случайных выражений: верный результат или ошибка «деление на ноль»."""
    rng = random.Random(seed)
    cases = [random_expr(rng, rng.randint(1, 4))[:2] for _ in range(1000)]
    outputs = session(*[text for text, _ in cases]).lines
    assert len(outputs) == len(cases)
    for (text, value), output in zip(cases, outputs):
        if value == "zero":
            assert is_error(output), f"{text} → {output}"
        elif "/" not in text:
            assert output == f"= {value}", f"{text} → {output}"
        else:
            assert output.startswith("= "), f"{text} → {output}"
            assert float(output[2:]) == pytest.approx(float(value), rel=1e-9, abs=1e-9), text


def matrix_text(rows):
    return "[" + ", ".join("[" + ", ".join(map(str, row)) + "]" for row in rows) + "]"


def matrix_answer(rows):
    return "= [" + ",\n   ".join("[" + ", ".join(map(str, row)) + "]" for row in rows) + "]"


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [3, 4])
def test_7_20_random_matrices(seed):
    """7.20 Случайные матрицы разных размеров: верный результат или ошибка с размерами."""
    rng = random.Random(seed)
    commands, expected = [], []
    for _ in range(300):
        ra, ca, rb, cb = (rng.randint(1, 3) for _ in range(4))
        a = [[rng.randint(-5, 5) for _ in range(ca)] for _ in range(ra)]
        b = [[rng.randint(-5, 5) for _ in range(cb)] for _ in range(rb)]
        op = rng.choice("+-*")
        commands.append(f"matrix {matrix_text(a)} {op} {matrix_text(b)}")
        ok = (ra, ca) == (rb, cb) if op in "+-" else ca == rb
        if not ok:
            expected.append(("error", f"{ra}×{ca}", f"{rb}×{cb}"))
        elif op == "*":
            expected.append(matrix_answer([[sum(a[i][k] * b[k][j] for k in range(rb)) for j in range(cb)]
                                           for i in range(ra)]))
        else:
            sign = 1 if op == "+" else -1
            expected.append(matrix_answer([[x + sign * y for x, y in zip(r1, r2)] for r1, r2 in zip(a, b)]))
    out = session(*commands).out
    blocks = re.split(r"\n(?=[=О])", out)
    assert len(blocks) == len(commands), out[:500]
    for command, want, got in zip(commands, expected, blocks):
        if isinstance(want, tuple):
            assert is_error(got) and re.search(f"{want[1]}.*{want[2]}", got), f"{command} → {got}"
        else:
            assert got == want, command


def random_logic(rng, depth, values):
    if depth == 0 or rng.random() < 0.3:
        choice = rng.random()
        if choice < 0.4:
            name = rng.choice("abc")
            return name, str(values[name])
        if choice < 0.6:
            word = rng.choice(["true", "false", "TRUE", "False"])
            return word, str(word.lower() == "true")
        x, y = rng.randint(-5, 5), rng.randint(-5, 5)
        op = rng.choice(["<", "<=", ">", ">=", "==", "!="])
        return f"({x} {op} {y})", f"({x} {op} {y})"
    kind = rng.choice(["AND", "OR", "NOT"])
    if kind == "NOT":
        text, py = random_logic(rng, depth - 1, values)
        return f"NOT {text}", f"not {py}"
    left, lp = random_logic(rng, depth - 1, values)
    right, rp = random_logic(rng, depth - 1, values)
    text, py = f"{left} {kind} {right}", f"{lp} {kind.lower()} {rp}"
    if rng.random() < 0.5:
        text, py = f"({text})", f"({py})"
    return text, py


LENGTH = {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001, "mi": 1609.344, "ft": 0.3048, "in": 0.0254, "yd": 0.9144}
MASS = {"kg": 1, "g": 0.001, "mg": 1e-6, "t": 1000, "lb": 0.45359237, "oz": 0.028349523125}
TIME = {"s": 1, "min": 60, "h": 3600, "day": 86400}


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [7, 8])
def test_7_22_random_convert_commands(seed):
    """7.22 Случайные convert: верный результат или ошибка (несовместимые или неизвестные единицы)."""
    rng = random.Random(seed)
    groups = [LENGTH, MASS, TIME]
    commands, expected = [], []
    for _ in range(300):
        group = rng.choice(groups)
        source = rng.choice(list(group))
        value = round(rng.uniform(-1000, 1000), rng.randint(0, 3))
        roll = rng.random()
        if roll < 0.7:
            target = rng.choice(list(group))
            commands.append(f"convert {value} {source} to {target}")
            expected.append((value * group[source] / group[target], target))
        elif roll < 0.85:
            other = rng.choice([g for g in groups if g is not group])
            commands.append(f"convert {value} {source} to {rng.choice(list(other))}")
            expected.append(None)
        else:
            unknown = "".join(rng.choice("qwxzj") for _ in range(rng.randint(2, 6)))
            commands.append(f"convert {value} {unknown} to {source}")
            expected.append(None)
    outputs = session(*commands).lines
    assert len(outputs) == len(commands)
    for command, want, got in zip(commands, expected, outputs):
        if want is None:
            assert is_error(got), f"{command} → {got}"
            continue
        match = re.fullmatch(rf"= (\S+) {re.escape(want[1])}", got)
        assert match, f"{command} → {got}"
        assert float(match.group(1)) == pytest.approx(want[0], rel=1e-5, abs=1e-12), command
