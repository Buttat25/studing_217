# Открытые тесты для самопроверки. Сгенерировано из контрольных тестов —
# не редактируйте: контрольные тесты преподавателя проверяют больше случаев.
"""Задача 6. Тест-кейсы 6.1–6.17: план по списку задач (файл) и операции в диалоге (stdin).

Программа: python scheduler.py ФАЙЛ   — план выполнения или сообщение о цикле;
           python scheduler.py < команды — диалог.
"""
import random
import string

import pytest

from course_program import assert_error, assert_output, run
from scheduler_model import is_cycle, order, plan, reaches, stages, task_file

PROGRAM = "scheduler.py"


def from_file(deps, titles=None):
    return run(PROGRAM, "tasks.txt", files={"tasks.txt": task_file(deps, titles)})


def dialog(commands):
    return run(PROGRAM, stdin="".join(c + "\n" for c in commands))


def check_plan(deps, titles=None):
    assert_output(from_file(deps, titles), plan(deps, titles))


def cycle_chain(result):
    assert result.code == 1 and not result.crashed, result.err
    assert result.lines[0] == "ОШИБКА: обнаружена циклическая зависимость!", result.out
    assert result.lines[2] == "Невозможно определить порядок выполнения."
    assert result.lines[1].startswith("Цепочка: ")
    return result.lines[1][len("Цепочка: "):].split(" → ")


# ============================================================ 🟢 Типичные
@pytest.mark.category("typical")
@pytest.mark.parametrize("names", [["A", "B", "C", "D"], ["z", "y", "x"], ["deploy", "build", "code", "plan", "idea"]])
def test_6_1_linear_chain(names):
    """6.1 Линейная цепочка — порядок по цепочке (даже если имена не по алфавиту)."""
    deps = {names[0]: []}
    for prev, name in zip(names, names[1:]):
        deps[name] = [prev]
    check_plan(deps, {n: f"Шаг {n}" for n in names})


@pytest.mark.category("typical")
@pytest.mark.parametrize("task", ["A", "Задача-1", "deploy_prod"])
def test_6_3_single_task(task):
    """6.3 Одна задача без зависимостей."""
    assert_output(from_file({task: []}, {task: "Единственная"}), f"""
        Проверка зависимостей: циклов не обнаружено.

        Задачи, готовые к выполнению прямо сейчас:
          ✓ {task}: "Единственная"

        Порядок выполнения всех задач (топологическая сортировка):
          1. {task}: "Единственная"

        Параллельные потоки (что можно делать одновременно):
          Этап 1: [{task}]
    """)


# ============================================================ 🟡 Наивные
@pytest.mark.category("naive")
def test_6_4_two_task_cycle_in_file():
    """6.4 Цикл A → B → A — ошибка с цепочкой."""
    deps = {"A": ["B"], "B": ["A"]}
    assert is_cycle(deps, cycle_chain(from_file(deps)))


@pytest.mark.category("naive")
def test_6_4_two_task_cycle_in_dialog_graph_unchanged():
    assert_output(dialog(["add A", "add B A", "dep A B", "order", "status A"]), """
        Задача A добавлена
        Задача B добавлена
        ОШИБКА: …A → B → A…
        Порядок: A, B
        A: ожидает
    """)


@pytest.mark.category("naive")
@pytest.mark.parametrize("task", ["X", "build"])
def test_6_5_task_depends_on_itself(task):
    """6.5 Задача зависит сама от себя — ошибка с цепочкой [X, X]."""
    assert_output(dialog([f"add {task}", f"dep {task} {task}", f"add Y {task} Y", "order"]), f"""
        Задача {task} добавлена
        ОШИБКА: …{task} → {task}…
        ОШИБКА: …Y → Y…
        Порядок: {task}
    """)


# ============================================================ 🔴 Краевые
@pytest.mark.category("edge")
@pytest.mark.parametrize("missing", ["Z", "задача-призрак"])
def test_6_7_dependency_on_missing_task(missing):
    """6.7 Зависимость от несуществующей задачи — ошибка с её именем."""
    assert_error(run(PROGRAM, "tasks.txt", files={"tasks.txt": task_file({"A": [], "B": ["A", missing]})}), missing)
    assert_output(dialog(["add A", f"add B A {missing}", f"dep A {missing}", "order"]), """
        Задача A добавлена
        ОШИБКА: …
        ОШИБКА: …
        Порядок: A
    """)


@pytest.mark.category("edge")
@pytest.mark.parametrize("count", [1000, 5000])
def test_6_8_many_tasks_depend_on_one(count):
    """6.8 Тысячи задач зависят от одной — быстро, порядок корректен."""
    deps = {"root": []}
    deps.update({f"t{i:05d}": ["root"] for i in range(count)})
    result = from_file(deps)
    assert_output(result, plan(deps))
    assert result.seconds < 2, f"{result.seconds:.1f} с"


@pytest.mark.category("edge")
def test_6_9_very_long_chain_without_recursion():
    deps = {"c0": []}
    deps.update({f"c{i}": [f"c{i - 1}"] for i in range(1, 20_000)})
    result = from_file(deps)
    assert result.code == 0 and not result.crashed, result.err[-500:]
    assert result.lines[-1] == "  Этап 20000: [c19999]"


@pytest.mark.category("edge")
def test_6_10_removing_referenced_task():
    """6.10 Удаление задачи, на которую ссылаются: отказ, а с --force — удаление вместе со ссылками."""
    assert_output(dialog(["add A", "add B A", "add C B", "remove A", "order", "remove A --force", "ready",
                          "order", "remove C", "order"]), """
        Задача A добавлена
        Задача B добавлена
        Задача C добавлена
        ОШИБКА: …B…
        Порядок: A, B, C
        Задача A удалена
        Готовы к выполнению: B
        Порядок: B, C
        Задача C удалена
        Порядок: B
    """)


# ============================================================ ❌ Формат
@pytest.mark.category("format")
@pytest.mark.parametrize("text", ['Задача : "Пусто" — зависит от: —\n', 'Задача   :"x" — зависит от: —\n'])
def test_6_11_empty_task_name(text):
    """6.11 Пустое имя задачи — ошибка."""
    assert_error(run(PROGRAM, "tasks.txt", files={"tasks.txt": text}))
    assert_output(dialog(["add", "add   ", "order"]), """
        ОШИБКА: …
        ОШИБКА: …
        Порядок: нет задач
    """)


@pytest.mark.category("format")
def test_6_12_duplicate_names():
    """6.12 Повтор имени — «задача уже существует», и в диалоге, и в файле."""
    text = 'Задача A: "Первая" — зависит от: —\nЗадача A: "Вторая" — зависит от: —\n'
    assert_error(run(PROGRAM, "tasks.txt", files={"tasks.txt": text}), "A")
    assert_output(dialog(["add A", "add A", "add B", "add B A", "order"]), """
        Задача A добавлена
        ОШИБКА: …
        Задача B добавлена
        ОШИБКА: …
        Порядок: A, B
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("text, fragment", [
    ('Задача A "Код" — зависит от: —\n', "строка 1"),
    ('Задача A: "Код" — зависит от: —\nЗадача B: Тесты — зависит от: A\n', "строка 2"),
    ('Задача A: "Код" — зависит от: —\nЗадача B: "Тесты" зависит от A\n', "строка 2"),
    ('Задача A: "Код" — зависит от: —\n\nЗадача B: "Тесты" — зависит от: A,, \n', "строка 3"),
    ('Задача A: "Код" — зависит от: —\nTask B: "Tests" — depends on: A\n', "строка 2"),
])
def test_6_14_bad_syntax(text, fragment):
    """6.14 Некорректный синтаксис списка задач — ошибка разбора с номером строки."""
    assert_error(run(PROGRAM, "tasks.txt", files={"tasks.txt": text}), fragment)


# ============================================================ 🎲 Фаззинг


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [21, 22])
def test_6_16_random_names_with_special_characters(seed):
    """6.16 Случайные имена со спецсимволами (без пробелов и запятых): всё работает."""
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}<>?/|~№абвгдёЯ😀"
    names = sorted({"".join(rng.choice(alphabet) for _ in range(rng.randint(1, 10))) for _ in range(30)})
    deps = {}
    for i, name in enumerate(names):
        deps[name] = rng.sample(names[:i], min(i, rng.randint(0, 2)))
    check_plan(deps, {n: f"«{n}»" for n in names})


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [31, 32, 33])
def test_6_17_random_add_and_remove(seed):
    """6.17 Случайные добавления и удаления: граф всегда согласован с моделью."""
    rng = random.Random(seed)
    deps, commands, expected = {}, [], []
    for step in range(400):
        roll = rng.random()
        existing = sorted(deps)
        if roll < 0.4 or not existing:
            name = f"T{rng.randint(0, 40)}"
            chosen = rng.sample(existing, min(len(existing), rng.randint(0, 2)))
            commands.append(" ".join(["add", name] + chosen))
            if name in deps:
                expected.append("ОШИБКА: …")
            else:
                deps[name] = chosen
                expected.append(f"Задача {name} добавлена")
        elif roll < 0.6:
            name, force = rng.choice(existing), rng.random() < 0.5
            commands.append(f"remove {name}" + (" --force" if force else ""))
            users = [t for t in deps if name in deps[t]]
            if users and not force:
                expected.append("ОШИБКА: …")
            else:
                del deps[name]
                for t in deps:
                    deps[t] = [d for d in deps[t] if d != name]
                expected.append(f"Задача {name} удалена")
        elif roll < 0.8:
            a, b = rng.choice(existing), rng.choice(existing)
            commands.append(f"dep {a} {b}")
            if b in deps[a]:
                expected.append(f"{a} зависит от {b}")
            elif reaches(deps, b, a):
                expected.append("ОШИБКА: …")
            else:
                deps[a].append(b)
                expected.append(f"{a} зависит от {b}")
        else:
            commands.append("order")
            expected.append("Порядок: " + (", ".join(order(deps)) or "нет задач"))
    commands.append("ready")
    expected.append("Готовы к выполнению: " + (", ".join(sorted(t for t in deps if not deps[t])) or "нет"))
    assert_output(dialog(commands), expected)
