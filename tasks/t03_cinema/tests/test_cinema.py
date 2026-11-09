# Открытые тесты для самопроверки. Сгенерировано из контрольных тестов —
# не редактируйте: контрольные тесты преподавателя проверяют больше случаев.
"""Задача 3. Кинозал: запуск программы, схема зала, команды и их ответы.

Программа: python cinema.py ЗАЛ.txt. Команды из stdin: time, session, book, pay, cancel, show, free, history.
"""
import pytest

from course_program import assert_error, assert_output, run

PROGRAM = "cinema.py"
HALL = "oooooooooo\n" * 4 + "VVVVVVVVVV\n"


def session(commands, hall=HALL):
    return run(PROGRAM, "hall.txt", stdin="".join(c + "\n" for c in commands), files={"hall.txt": hall})


@pytest.mark.category("typical")
def test_example_from_task():
    result = session(["time 14:20", "session S1 19:00", "book S1 3:5 Иванов", "book S1 3:5 Петров",
                      "time 14:22", "cancel 1 Иванов", "book S1 3:5 Петров", "show S1", "history S1"])
    assert_output(result, """
        Время: 14:20
        Сеанс S1 добавлен (начало в 19:00)
        Бронь 1: Иванов, сеанс S1, ряд 3, место 5, 300 руб. — УСПЕШНО
        ОШИБКА: …
        Время: 14:22
        Бронь 1 отменена
        Бронь 2: Петров, сеанс S1, ряд 3, место 5, 300 руб. — УСПЕШНО
               1  2  3  4  5  6  7  8  9  10
        Ряд 1: o  o  o  o  o  o  o  o  o  o
        Ряд 2: o  o  o  o  o  o  o  o  o  o
        Ряд 3: o  o  o  o  x  o  o  o  o  o
        Ряд 4: o  o  o  o  o  o  o  o  o  o
        Ряд 5: V  V  V  V  V  V  V  V  V  V
          14:20 Иванов → ряд 3, место 5 (отменено в 14:22)
          14:22 Петров → ряд 3, место 5 (активно)
    """)


@pytest.mark.category("typical")
def test_group_booking_gets_separate_numbers_and_prices():
    hall = "DooD\nVVVV\n"
    result = session(["session Премьера", "book Премьера 1:1,2:2,1:3 Семья Ивановых", "free Премьера",
                      "cancel 2 Семья Ивановых", "free Премьера"], hall)
    assert_output(result, """
        Сеанс Премьера добавлен
        Бронь 1: Семья Ивановых, сеанс Премьера, ряд 1, место 1, 300 руб. — УСПЕШНО
        Бронь 2: Семья Ивановых, сеанс Премьера, ряд 2, место 2, 600 руб. — УСПЕШНО
        Бронь 3: Семья Ивановых, сеанс Премьера, ряд 1, место 3, 300 руб. — УСПЕШНО
        Свободно мест: 5 из 8
        Бронь 2 отменена
        Свободно мест: 6 из 8
    """)


@pytest.mark.category("typical")
def test_sessions_are_independent_and_numbers_are_global():
    result = session(["session A", "session B", "book A 1:1 Иванов", "book B 1:1 Петров", "free A", "free B",
                      "cancel 2 Петров", "history A", "history B"])
    assert_output(result, """
        Сеанс A добавлен
        Сеанс B добавлен
        Бронь 1: Иванов, сеанс A, ряд 1, место 1, 300 руб. — УСПЕШНО
        Бронь 2: Петров, сеанс B, ряд 1, место 1, 300 руб. — УСПЕШНО
        Свободно мест: 49 из 50
        Свободно мест: 49 из 50
        Бронь 2 отменена
          00:00 Иванов → ряд 1, место 1 (активно)
          00:00 Петров → ряд 1, место 1 (отменено в 00:00)
    """)


@pytest.mark.category("edge")
def test_render_irregular_hall_with_gaps():
    hall = "  ..ooo..  \n.oooooo.\nVV..VV\nDoooooooooooD\n"
    result = session(["session S", "book S 1:3 А", "book S 4:13 Б", "show S"], hall)
    assert_output(result, """
        Сеанс S добавлен
        Бронь 1: А, сеанс S, ряд 1, место 3, 300 руб. — УСПЕШНО
        Бронь 2: Б, сеанс S, ряд 4, место 13, 300 руб. — УСПЕШНО
               1  2  3  4  5  6  7  8  9  10 11 12 13
        Ряд 1:       x  o  o
        Ряд 2:    o  o  o  o  o  o
        Ряд 3: V  V        V  V
        Ряд 4: D  o  o  o  o  o  o  o  o  o  o  o  x
    """)


@pytest.mark.category("edge")
def test_render_wide_row_numbers():
    hall = "oo\n" * 10
    result = session(["session S", "book S 10:2 А", "show S"], hall)
    assert_output(result, ["Сеанс S добавлен", "Бронь 1: А, сеанс S, ряд 10, место 2, 300 руб. — УСПЕШНО",
                           "        1  2"] + [f"Ряд {r}:  o  o" for r in range(1, 10)] + ["Ряд 10: o  x"])


@pytest.mark.category("edge")
def test_history_empty_and_expired_after_paid_others():
    result = session(["session S", "history S", "time 08:00", "book S 1:1 А", "book S 1:2 Б", "pay 2 Б",
                      "time 08:30", "history S"])
    assert_output(result, """
        Сеанс S добавлен
        История пуста
        Время: 08:00
        Бронь 1: А, сеанс S, ряд 1, место 1, 300 руб. — УСПЕШНО
        Бронь 2: Б, сеанс S, ряд 1, место 2, 300 руб. — УСПЕШНО
        Бронь 2 оплачена
        Время: 08:30
          08:00 А → ряд 1, место 1 (истекло в 08:10)
          08:00 Б → ряд 1, место 2 (оплачено)
    """)


@pytest.mark.category("naive")
@pytest.mark.parametrize("commands", [
    ["pay 1 А", "pay 1 А"],
    ["cancel 1 А", "cancel 1 А"],
    ["cancel 1 А", "pay 1 А"],
    ["time 00:10", "cancel 1 А"],
])
def test_repeated_or_late_operations(commands):
    result = session(["session S", "book S 1:1 А"] + commands)
    assert result.lines[-1].startswith("ОШИБКА: ") and result.code == 0 and not result.crashed, result.out


@pytest.mark.category("format")
@pytest.mark.parametrize("command", [
    "book X 1:1 А", "show X", "free X", "history X", "pay 99 А", "cancel 0 А", "pay первый А", "pay 1",
    "cancel", "session", "session S 10:00 лишнее", "show", "free S лишнее", "time", "sell S 1:1 А",
    "book S 1-1 А", "book S 1:1;1:2 А", "BOOK S 1:1 А",
])
def test_bad_commands(command):
    assert_output(session(["session S", command, "free S"]), """
        Сеанс S добавлен
        ОШИБКА: …
        Свободно мест: 50 из 50
    """)


@pytest.mark.category("format")
def test_duplicate_session():
    assert_output(session(["session S", "session S 10:00", "free S"]), """
        Сеанс S добавлен
        ОШИБКА: …
        Свободно мест: 50 из 50
    """)


@pytest.mark.category("edge")
def test_time_cannot_go_back():
    assert_output(session(["time 12:00", "time 11:59", "time 12:00", "time 23:59"]), """
        Время: 12:00
        ОШИБКА: …
        Время: 12:00
        Время: 23:59
    """)


@pytest.mark.category("edge")
def test_blank_lines_and_no_commands():
    assert_output(run(PROGRAM, "hall.txt", stdin="\n\n   \nsession S\n\n", files={"hall.txt": HALL}),
                  "Сеанс S добавлен")
    assert_output(run(PROGRAM, "hall.txt", stdin="", files={"hall.txt": HALL}), "")


# ============================================================ файл зала и запуск
@pytest.mark.category("edge")
def test_hall_with_bom_and_blank_lines():
    result = run(PROGRAM, "hall.txt", stdin="session S\nfree S\n", files={"hall.txt": "﻿\nooo\n\n  VV\n\n"})
    assert_output(result, ["Сеанс S добавлен", "Свободно мест: 5 из 5"])


@pytest.mark.category("format")
@pytest.mark.parametrize("hall, fragment", [("ooo\noXo\n", "ряд 2"), ("...\n..\n", ""), ("", ""), ("oo o\n", "ряд 1")])
def test_bad_hall(hall, fragment):
    assert_error(run(PROGRAM, "hall.txt", stdin="", files={"hall.txt": hall}), fragment)


@pytest.mark.category("format")
def test_missing_hall_file():
    assert_error(run(PROGRAM, "нет.txt", stdin=""), "нет.txt")


@pytest.mark.category("format")
@pytest.mark.parametrize("args", [[], ["hall.txt", "лишний"]])
def test_bad_arguments(args):
    assert_error(run(PROGRAM, *args, stdin="", files={"hall.txt": HALL}), code=2)
