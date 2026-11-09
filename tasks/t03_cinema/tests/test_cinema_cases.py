import random
import string

import pytest

from cinema_model import expected
from course_program import assert_output, run

PROGRAM = "cinema.py"
HALL = "oooooooooo\n" * 4 + "VVVVVVVVVV\n"
HEADER = "       1  2  3  4  5  6  7  8  9  10"


def session(commands, hall=HALL):
    if isinstance(commands, (list, tuple)):
        commands = "".join(c + "\n" for c in commands)
    return run(PROGRAM, "hall.txt", stdin=commands, files={"hall.txt": hall})


def booked(n, user, row, seat, price=300, name="S1"):
    return f"Бронь {n}: {user}, сеанс {name}, ряд {row}, место {seat}, {price} руб. - УСПЕШНО"


@pytest.mark.category("typical")
@pytest.mark.parametrize("row, seat, price", [(3, 5, 300), (1, 1, 300), (5, 10, 600), (4, 10, 300)])
def test_3_1_book_seat(row, seat, price):
    assert_output(session(["session S1", f"book S1 {row}:{seat} Иванов", "free S1"]), f"""
        Сеанс S1 добавлен
        {booked(1, "Иванов", row, seat, price)}
        Свободно мест: 49 из 50
    """)


@pytest.mark.category("typical")
@pytest.mark.parametrize("paid", [False, True])
def test_3_2_cancel_booking(paid):
    commands = ["session S1", "book S1 3:5 Иванов"] + (["pay 1 Иванов"] if paid else []) + \
               ["time 00:02", "cancel 1 Иванов", "free S1", "book S1 3:5 Петров"]
    expected = ["Сеанс S1 добавлен", booked(1, "Иванов", 3, 5)] + (["Бронь 1 оплачена"] if paid else []) + \
               ["Время: 00:02", "Бронь 1 отменена", "Свободно мест: 50 из 50", booked(2, "Петров", 3, 5)]
    assert_output(session(commands), expected)


@pytest.mark.category("naive")
@pytest.mark.parametrize("second", ["Петров", "Иванов"])
def test_3_4_second_user_gets_seat_taken_error(second):
    assert_output(session(["session S1", "book S1 3:5 Иванов", f"book S1 3:5 {second}", "history S1"]), f"""
        Сеанс S1 добавлен
        {booked(1, "Иванов", 3, 5)}
        ОШИБКА: …
          00:00 Иванов → ряд 3, место 5 (активно)
    """)


@pytest.mark.category("naive")
@pytest.mark.parametrize("times", [1, 3, 10])
def test_3_5_book_cancel_book_again(times):
    commands, expected = ["session S1"], ["Сеанс S1 добавлен"]
    for i in range(times):
        commands += ["book S1 2:7 Иванов", f"cancel {i + 1} Иванов"]
        expected += [booked(i + 1, "Иванов", 2, 7), f"Бронь {i + 1} отменена"]
    commands += ["book S1 2:7 Иванов", "free S1"]
    expected += [booked(times + 1, "Иванов", 2, 7), "Свободно мест: 49 из 50"]
    assert_output(session(commands), expected)


@pytest.mark.category("edge")
@pytest.mark.parametrize("wait, expired", [("14:29", False), ("14:30", True), ("15:00", True)])
def test_3_7_unpaid_booking_is_released(wait, expired):
    result = session(["time 14:20", "session S1", "book S1 3:5 Иванов", f"time {wait}", "free S1",
                      "pay 1 Иванов", "history S1"])
    assert_output(result, [
        "Время: 14:20", "Сеанс S1 добавлен", booked(1, "Иванов", 3, 5), f"Время: {wait}",
        f"Свободно мест: {50 if expired else 49} из 50",
        "ОШИБКА: …" if expired else "Бронь 1 оплачена",
        f"  14:20 Иванов → ряд 3, место 5 ({'истекло в 14:30' if expired else 'оплачено'})",
    ])


@pytest.mark.category("edge")
def test_3_7_bookings_expire_independently():
    result = session(["session S1", "time 10:00", "book S1 1:1 А", "time 10:05", "book S1 1:2 Б",
                      "pay 1 А", "time 10:12", "free S1", "time 10:15", "free S1", "history S1"])
    assert_output(result, [
        "Сеанс S1 добавлен", "Время: 10:00", booked(1, "А", 1, 1), "Время: 10:05", booked(2, "Б", 1, 2),
        "Бронь 1 оплачена", "Время: 10:12", "Свободно мест: 48 из 50", "Время: 10:15",
        "Свободно мест: 49 из 50",
        "  10:00 А → ряд 1, место 1 (оплачено)",
        "  10:05 Б → ряд 1, место 2 (истекло в 10:15)",
    ])


@pytest.mark.category("edge")
@pytest.mark.parametrize("commands", [
    ["book S1 3:5,3:5 Иванов"],
    ["book S1 3:5 Иванов", "book S1 3:4,3:5,3:6 Петров"],
])
def test_3_8_same_seat_twice_only_one_wins(commands):
    result = session(["session S1"] + commands + ["free S1"])
    expected = ["Сеанс S1 добавлен"] + (["ОШИБКА: …"] if len(commands) == 1 else
                                         [booked(1, "Иванов", 3, 5), "ОШИБКА: …"])
    taken = 0 if len(commands) == 1 else 1
    assert_output(result, expected + [f"Свободно мест: {50 - taken} из 50"])


@pytest.mark.category("edge")
def test_3_9_full_hall_refuses_new_bookings():
    hall = "ooo\n.V.\n"
    result = session(["session S1", "book S1 1:1,1:2,1:3 А", "book S1 2:2 Б", "free S1", "book S1 1:2 В",
                      "show S1"], hall)
    assert_output(result, [
        "Сеанс S1 добавлен", booked(1, "А", 1, 1), booked(2, "А", 1, 2), booked(3, "А", 1, 3),
        booked(4, "Б", 2, 2, 600), "Свободно мест: 0 из 4", "ОШИБКА: …",
        "       1  2  3", "Ряд 1: x  x  x", "Ряд 2:    x",
    ])


@pytest.mark.category("format")
@pytest.mark.parametrize("seat", ["6:1", "1:11", "100:100", "2:1", "2:3", "2:4"])
def test_3_12_seat_does_not_exist(seat):
    hall = "oooooooooo\n.o.\n" + "oooooooooo\n" * 3
    assert_output(session(["session S1", f"book S1 {seat} Иванов"], hall), """
        Сеанс S1 добавлен
        ОШИБКА: …
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("start", ["25:00", "19:60", "7pm", "19.00", "1900", "-1:00", "19:0"])
def test_3_13_bad_session_time(start):
    assert_output(session([f"session S1 {start}", "book S1 1:1 Иванов", "session S1"]), """
        ОШИБКА: …
        ОШИБКА: …
        Сеанс S1 добавлен
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["time 24:00", "time 9", "time завтра", "time 12:3"])
def test_3_13_bad_clock_time(command):
    assert_output(session([command, "time 12:00"]), """
        ОШИБКА: …
        Время: 12:00
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["book S1 3:5", "book S1 3:5 ", "book S1 3:5     "])
def test_3_14_empty_user_name(command):
    assert_output(session(["session S1", command, "free S1"]), """
        Сеанс S1 добавлен
        ОШИБКА: …
        Свободно мест: 50 из 50
    """)


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [11, 12])
def test_3_16_random_seat_numbers(seed):
    rng = random.Random(seed)
    commands, expected, taken = ["session S1"], ["Сеанс S1 добавлен"], set()
    for _ in range(300):
        token = rng.choice([f"{rng.randint(-3, 7)}:{rng.randint(-3, 12)}", f"{rng.randint(1, 5)}",
                            f"{rng.choice('abc')}:{rng.randint(1, 9)}", f"{rng.randint(1, 5)}:{rng.randint(1, 10)}",
                            f"{rng.randint(1, 5)}:{rng.randint(1, 10)}.5", "", ":"])
        commands.append(f"book S1 {token} Гость" if token else "book S1 Гость")
        row_seat = token.split(":")
        valid = (len(row_seat) == 2 and all(p.lstrip("-").isdigit() for p in row_seat)
                 and 1 <= int(row_seat[0]) <= 5 and 1 <= int(row_seat[1]) <= 10
                 and (int(row_seat[0]), int(row_seat[1])) not in taken)
        if valid:
            taken.add((int(row_seat[0]), int(row_seat[1])))
            expected.append(booked(len(taken), "Гость", *map(int, row_seat), 600 if row_seat[0] == "5" else 300))
        else:
            expected.append("ОШИБКА: …")
    commands.append("free S1")
    expected.append(f"Свободно мест: {50 - len(taken)} из 50")
    assert_output(session(commands), expected)


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [21, 22])
def test_3_17_random_user_names(seed):
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}<>?/|\\'\"~ абвгдёжЯ😀"
    commands, expected, history = ["session S1"], ["Сеанс S1 добавлен"], []
    for n in range(1, 31):
        name = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 20))).strip() or "x"
        row, seat = (n - 1) // 10 + 1, (n - 1) % 10 + 1
        commands += [f"book S1 {row}:{seat} {name}", f"pay {n} {name}"]
        expected += [booked(n, name, row, seat), f"Бронь {n} оплачена"]
        history.append(f"  00:00 {name} → ряд {row}, место {seat} (оплачено)")
    assert_output(session(commands + ["history S1"]), expected + history)
