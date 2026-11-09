import pytest

from course_program import assert_error, assert_output, run
from scheduler_model import plan

PROGRAM = "scheduler.py"

EXAMPLE = """\
Задача A: "Написать код"           - зависит от: -
Задача B: "Написать тесты"         - зависит от: A
Задача C: "Собрать проект"         - зависит от: A, B
Задача D: "Прогнать тесты"         - зависит от: C
Задача E: "Выкатить на продакшн"   - зависит от: C, D
Задача F: "Обновить документацию"  - зависит от: E
"""


def dialog(commands):
    return run(PROGRAM, stdin="".join(c + "\n" for c in commands))


@pytest.mark.category("typical")
def test_example_from_task():
    assert_output(run(PROGRAM, "tasks.txt", files={"tasks.txt": EXAMPLE}), """
        Проверка зависимостей: циклов не обнаружено.

        Задачи, готовые к выполнению прямо сейчас:
          ✓ A: "Написать код"

        Порядок выполнения всех задач (топологическая сортировка):
          1. A: "Написать код"
          2. B: "Написать тесты"
          3. C: "Собрать проект"
          4. D: "Прогнать тесты"
          5. E: "Выкатить на продакшн"
          6. F: "Обновить документацию"

        Параллельные потоки (что можно делать одновременно):
          Этап 1: [A]
          Этап 2: [B]
          Этап 3: [C]
          Этап 4: [D]
          Этап 5: [E]
          Этап 6: [F]
    """)


@pytest.mark.category("typical")
def test_example_cycle_message():
    text = 'Задача X: "Икс" - зависит от: Y\nЗадача Y: "Игрек" - зависит от: Z\nЗадача Z: "Зет" - зависит от: X\n'
    result = run(PROGRAM, "tasks.txt", files={"tasks.txt": text})
    assert_output(result, """
        ОШИБКА: обнаружена циклическая зависимость!
        Цепочка: X → Y → Z → X
        Невозможно определить порядок выполнения.
    """, code=1)


@pytest.mark.category("typical")
def test_parallel_stages_and_alphabetical_order():
    text = ('Задача deploy: "Выкатить" - зависит от: test, docs\nЗадача code: "Код" - зависит от: -\n'
            'Задача test: "Тесты" - зависит от: code\nЗадача docs: "Документация" - зависит от: -\n'
            'Задача api: "API" - зависит от: code\n')
    deps = {"deploy": ["test", "docs"], "code": [], "test": ["code"], "docs": [], "api": ["code"]}
    titles = {"deploy": "Выкатить", "code": "Код", "test": "Тесты", "docs": "Документация", "api": "API"}
    assert_output(run(PROGRAM, "tasks.txt", files={"tasks.txt": text}), plan(deps, titles))


@pytest.mark.category("edge")
def test_file_format_details():
    text = ('﻿# список задач\n\n  задача   A :  "Код"  -  ЗАВИСИТ ОТ:   \n'
            'Задача B: "" - зависит от:  A ,A\n')
    assert_output(run(PROGRAM, "tasks.txt", files={"tasks.txt": text.encode("utf-8")}), """
        Проверка зависимостей: циклов не обнаружено.

        Задачи, готовые к выполнению прямо сейчас:
          ✓ A: "Код"

        Порядок выполнения всех задач (топологическая сортировка):
          1. A: "Код"
          2. B

        Параллельные потоки (что можно делать одновременно):
          Этап 1: [A]
          Этап 2: [B]
    """)


@pytest.mark.category("edge")
def test_empty_task_list():
    assert_output(run(PROGRAM, "tasks.txt", files={"tasks.txt": "\n# пусто\n"}), """
        Проверка зависимостей: циклов не обнаружено.

        Задачи, готовые к выполнению прямо сейчас:
          нет

        Порядок выполнения всех задач (топологическая сортировка):
          нет задач

        Параллельные потоки (что можно делать одновременно):
          нет задач
    """)


@pytest.mark.category("edge")
def test_stage_is_one_plus_max_of_dependencies():
    deps = {"A": [], "B": ["A"], "C": ["B"], "D": ["A", "C"], "E": []}
    assert_output(dialog(["add A", "add B A", "add C B", "add D A C", "add E", "stages", "plan"]),
                  [f"Задача {t} добавлена" for t in deps] + ["Этап 1: [A, E]", "Этап 2: [B]", "Этап 3: [C]",
                                                             "Этап 4: [D]"] + plan(deps))


@pytest.mark.category("format")
def test_missing_file_and_arguments():
    assert_error(run(PROGRAM, "нет.txt"), "нет.txt")
    assert_error(run(PROGRAM, "a.txt", "b.txt", files={"a.txt": EXAMPLE, "b.txt": EXAMPLE}), code=2)


@pytest.mark.category("typical")
def test_statuses_done_fail_reset():
    commands = ["add A", "add B A", "add C B", "add D", "ready", "done B", "done A", "ready", "status B",
                "fail B", "status C", "ready", "done C", "reset B", "status C", "done B", "done C",
                "status C", "ready"]
    assert_output(dialog(commands), """
        Задача A добавлена
        Задача B добавлена
        Задача C добавлена
        Задача D добавлена
        Готовы к выполнению: A, D
        ОШИБКА: …A…
        Задача A выполнена
        Готовы к выполнению: B, D
        B: ожидает
        Задача B провалена; заблокированы: C
        C: заблокирована
        Готовы к выполнению: D
        ОШИБКА: …
        Задача B снова ожидает; разблокированы: C
        C: ожидает
        Задача B выполнена
        Задача C выполнена
        C: выполнена
        Готовы к выполнению: D
    """)


@pytest.mark.category("naive")
def test_blocked_through_chain_and_shared_failures():
    commands = ["add A", "add B", "add C A", "add D C B", "fail A", "status D", "fail B", "status B",
                "reset A", "status D", "fail D", "reset B", "status D", "fail D", "status D", "reset D"]
    assert_output(dialog(commands), """
        Задача A добавлена
        Задача B добавлена
        Задача C добавлена
        Задача D добавлена
        Задача A провалена; заблокированы: C, D
        D: заблокирована
        Задача B провалена
        B: провалена
        Задача A снова ожидает; разблокированы: C
        D: заблокирована
        ОШИБКА: …
        Задача B снова ожидает; разблокированы: D
        D: ожидает
        Задача D провалена
        D: провалена
        Задача D снова ожидает
    """)


@pytest.mark.category("edge")
def test_diamond_dependencies():
    commands = ["add A", "add B A", "add C A", "add D B C", "status D", "fail A", "status D", "reset A",
                "ready", "order"]
    assert_output(dialog(commands), """
        Задача A добавлена
        Задача B добавлена
        Задача C добавлена
        Задача D добавлена
        D: ожидает
        Задача A провалена; заблокированы: B, C, D
        D: заблокирована
        Задача A снова ожидает; разблокированы: B, C, D
        Готовы к выполнению: A
        Порядок: A, B, C, D
    """)


@pytest.mark.category("naive")
@pytest.mark.parametrize("commands", [
    ["add A", "done A", "done A"], ["add A", "done A", "fail A"], ["add A", "reset A"],
    ["add A", "fail A", "done A"], ["add A", "fail A", "fail A"],
])
def test_invalid_status_changes(commands):
    result = dialog(commands)
    assert result.lines[-1].startswith("ОШИБКА: ") and result.code == 0 and not result.crashed, result.out


@pytest.mark.category("typical")
def test_dependency_commands():
    commands = ["add A", "add B", "dep B A", "dep B A", "order", "undep B A", "undep B A", "ready", "dep A B",
                "dep B A", "plan"]
    assert_output(dialog(commands), """
        Задача A добавлена
        Задача B добавлена
        B зависит от A
        B зависит от A
        Порядок: A, B
        B больше не зависит от A
        ОШИБКА: …
        Готовы к выполнению: A, B
        A зависит от B
        ОШИБКА: …B → A → B…
        Проверка зависимостей: циклов не обнаружено.

        Задачи, готовые к выполнению прямо сейчас:
          ✓ B

        Порядок выполнения всех задач (топологическая сортировка):
          1. B
          2. A

        Параллельные потоки (что можно делать одновременно):
          Этап 1: [B]
          Этап 2: [A]
    """)


@pytest.mark.category("edge")
def test_add_with_bad_dependency_adds_nothing():
    assert_output(dialog(["add A", "add B A Z", "add B A", "order"]), """
        Задача A добавлена
        ОШИБКА: …Z…
        Задача B добавлена
        Порядок: A, B
    """)


@pytest.mark.category("edge")
def test_empty_dialog_and_blank_lines():
    assert_output(run(PROGRAM, stdin=""), "")
    assert_output(dialog(["", "order", "   ", "stages", "ready", "plan"]), """
        Порядок: нет задач
        нет задач
        Готовы к выполнению: нет
        Проверка зависимостей: циклов не обнаружено.

        Задачи, готовые к выполнению прямо сейчас:
          нет

        Порядок выполнения всех задач (топологическая сортировка):
          нет задач

        Параллельные потоки (что можно делать одновременно):
          нет задач
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("command", [
    "remove", "remove A B", "remove A --hard", "dep A", "dep A B C", "undep A", "done", "status", "fail A B",
    "ready now", "order 1", "plan all", "ADD A", "delete A", "status Z", "done Z", "remove Z",
])
def test_bad_commands(command):
    assert_output(dialog(["add A", "add B", command, "order"]), """
        Задача A добавлена
        Задача B добавлена
        ОШИБКА: …
        Порядок: A, B
    """)


@pytest.mark.category("typical")
def test_deadlines_and_overdue():
    commands = ["add A", "add B A", "add C", "deadline A 2026-11-10", "deadline C 2026-11-20",
                "overdue 2026-11-10", "overdue 2026-11-11", "done A", "overdue 2026-12-01",
                "deadline B 2026-11-01", "deadline C 2026-11-25", "overdue 2026-11-21", "remove C", "overdue 2027-01-01"]
    assert_output(dialog(commands), """
        Задача A добавлена
        Задача B добавлена
        Задача C добавлена
        Задача A: дедлайн 2026-11-10
        Задача C: дедлайн 2026-11-20
        Просрочены: нет
        Просрочены: A
        Задача A выполнена
        Просрочены: C
        Задача B: дедлайн 2026-11-01
        Задача C: дедлайн 2026-11-25
        Просрочены: B
        Задача C удалена
        Просрочены: B
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("command", [
    "deadline A 2026-13-01", "deadline A 2026-02-30", "deadline A 10.11.2026", "deadline A 2026-1-5",
    "deadline Z 2026-11-10", "deadline A", "overdue вчера", "overdue", "save", "load", "load нет.json",
    "save нет_папки/план.json",
])
def test_deadline_and_file_command_errors(command):
    result = dialog(["add A", command, "overdue 2030-01-01"])
    assert result.lines[0] == "Задача A добавлена" and result.lines[1].startswith("ОШИБКА: "), result.out
    assert result.lines[2] == "Просрочены: нет" and not result.crashed


@pytest.mark.category("typical")
def test_save_and_load_restore_state():
    commands = ["add A", "add B A", "add C", "deadline B 2026-11-10", "fail A", "save plan.json",
                "remove B --force", "done C", "add D", "load plan.json", "status A", "status B", "status C",
                "order", "overdue 2026-12-01", "remove D"]
    assert_output(dialog(commands), """
        Задача A добавлена
        Задача B добавлена
        Задача C добавлена
        Задача B: дедлайн 2026-11-10
        Задача A провалена; заблокированы: B
        Сохранено в plan.json
        Задача B удалена
        Задача C выполнена
        Задача D добавлена
        Загружено задач: 3
        A: провалена
        B: заблокирована
        C: ожидает
        Порядок: A, B, C
        Просрочены: B
        ОШИБКА: …
    """)


@pytest.mark.category("edge")
def test_saved_file_is_json_and_loads_in_new_run(tmp_path):
    import json
    first = run(PROGRAM, stdin="add код\nadd тесты код\nadd выкатка тесты\ndone код\n"
                               "deadline выкатка 2026-12-31\nsave план.json\n", cwd=tmp_path)
    assert first.lines[-1] == "Сохранено в план.json", first.out
    json.loads((tmp_path / "план.json").read_text(encoding="utf-8"))
    second = run(PROGRAM, stdin="load план.json\nready\norder\nstatus код\noverdue 2027-01-01\n", cwd=tmp_path)
    assert_output(second, """
        Загружено задач: 3
        Готовы к выполнению: тесты
        Порядок: код, тесты, выкатка
        код: выполнена
        Просрочены: выкатка
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("content", [b"", b"\xff\xfe\x00 binary", "это не JSON".encode(), b'{"tasks": [',
                                     b"[[[[", b"null"])
def test_load_corrupted_file_keeps_state(content):
    result = run(PROGRAM, stdin="add A\nload bad.json\norder\n", files={"bad.json": content})
    assert_output(result, """
        Задача A добавлена
        ОШИБКА: …
        Порядок: A
    """)


@pytest.mark.category("format")
def test_load_truncated_own_file(tmp_path):
    run(PROGRAM, stdin="add A\nadd B A\nsave s.json\n", cwd=tmp_path)
    text = (tmp_path / "s.json").read_bytes()
    (tmp_path / "s.json").write_bytes(text[: len(text) // 2])
    assert_output(run(PROGRAM, stdin="add X\nload s.json\norder\n", cwd=tmp_path), """
        Задача X добавлена
        ОШИБКА: …
        Порядок: X
    """)
