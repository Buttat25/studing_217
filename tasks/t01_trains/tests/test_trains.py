import random

import pytest

from course_program import assert_error, assert_output, run

PROGRAM = "trains.py"

EXAMPLE = """\
Поезд 1: прибытие 09:00, отправление 09:30
Поезд 2: прибытие 09:10, отправление 10:00
Поезд 3: прибытие 09:30, отправление 10:30
Поезд 4: прибытие 10:30, отправление 11:00
Поезд 5: прибытие 10:40, отправление 11:30
"""

EXAMPLE_REPORT = """
    Минимальное количество платформ: 2

    Распределение по платформам:
      Платформа 1: Поезд 1 (09:00–09:30), Поезд 3 (09:30–10:30), Поезд 4 (10:30–11:00)
      Платформа 2: Поезд 2 (09:10–10:00), Поезд 5 (10:40–11:30)
"""


@pytest.mark.category("typical")
def test_example_from_stdin():
    assert_output(run(PROGRAM, stdin=EXAMPLE), EXAMPLE_REPORT)


@pytest.mark.category("typical")
def test_example_from_file():
    assert_output(run(PROGRAM, "schedule.txt", files={"schedule.txt": EXAMPLE}), EXAMPLE_REPORT)


@pytest.mark.category("typical")
def test_file_with_bom_and_windows_line_endings():
    data = ("﻿" + EXAMPLE.replace("\n", "\r\n")).encode("utf-8")


@pytest.mark.category("format")
def test_missing_file():
    assert_error(run(PROGRAM, "нет_такого.txt"), "нет_такого.txt")


@pytest.mark.category("format")
def test_too_many_arguments():
    assert_error(run(PROGRAM, "a.txt", "b.txt", files={"a.txt": EXAMPLE, "b.txt": EXAMPLE}), code=2)


@pytest.mark.category("typical")
def test_spaces_and_case_do_not_matter():
    text = "  Экспресс  :  ПРИБЫТИЕ   9:05 ,Отправление 9:40  \nскорый 7:прибытие 09:20,отправление 10:00\n"
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 2

        Распределение по платформам:
          Платформа 1: Экспресс (09:05–09:40)
          Платформа 2: скорый 7 (09:20–10:00)
    """)


@pytest.mark.category("edge")
def test_comments_and_blank_lines_are_skipped():
    text = "# утренние поезда\n\nПоезд 1: прибытие 09:00, отправление 09:30\n   # ещё комментарий\n\n"
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 1

        Распределение по платформам:
          Платформа 1: Поезд 1 (09:00–09:30)
    """)


@pytest.mark.category("typical")
def test_names_are_printed_as_given():
    text = "Ласточка №7 (Москва - Тверь): прибытие 8:00, отправление 8:15\n"
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 1

        Распределение по платформам:
          Платформа 1: Ласточка №7 (Москва - Тверь) (08:00–08:15)
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("text, fragment", [
    ("Поезд 1 прибытие 09:00 отправление 09:30\n", "строка 1"),
    ("Поезд 1: прибытие 09:00, отправление 09:30\nчепуха\n", "строка 2"),
    ("Поезд 1: прибытие 09:00, отправление 09:30\n\n# комментарий\nПоезд 2: 10:00 - 11:00\n", "строка 4"),
])
def test_unparsable_line_reports_line_number(text, fragment):
    assert_error(run(PROGRAM, stdin=text), fragment)


@pytest.mark.category("format")
@pytest.mark.parametrize("text", [
    "Поезд 1: прибытие 09:00, отправление 09:30\nПоезд 1: прибытие 10:00, отправление 10:30\n",
])
def test_duplicate_names(text):
    assert_error(run(PROGRAM, stdin=text), "Поезд 1")


@pytest.mark.category("format")
def test_empty_name():
    assert_error(run(PROGRAM, stdin="  : прибытие 09:00, отправление 09:30\n"))


@pytest.mark.category("format")
@pytest.mark.parametrize("bad", ["9:5", "09:5", "123:00", "09:000", "09:60", "24:00", "-1:00", ":30"])
def test_bad_arrival_time(bad):
    assert_error(run(PROGRAM, stdin=f"Поезд 1: прибытие {bad}, отправление 10:00\n"), bad)


@pytest.mark.category("format")
@pytest.mark.parametrize("bad", ["24:01", "24:30", "25:00", "10:5", "1000"])
def test_bad_departure_time(bad):
    assert_error(run(PROGRAM, stdin=f"Поезд 1: прибытие 09:00, отправление {bad}\n"), bad)


@pytest.mark.category("format")
def test_error_in_last_line_gives_no_report():
    result = run(PROGRAM, stdin=EXAMPLE + "Поезд 6: прибытие 12:00, отправление 12:00\n")
    assert_error(result, "Поезд 6")
    assert "Минимальное количество" not in result.out


@pytest.mark.category("edge")
@pytest.mark.parametrize("arrival, departure", [
    ("09:00", "11:00"), ("23:00", "01:00"), ("22:00", "24:00"), ("23:59", "01:59"), ("22:00", "00:00"),
])
def test_max_stay_is_two_hours_inclusive(arrival, departure):
    assert_output(run(PROGRAM, stdin=f"Поезд 8: прибытие {arrival}, отправление {departure}\n"), f"""
        Минимальное количество платформ: 1

        Распределение по платформам:
          Платформа 1: Поезд 8 ({arrival}–{departure})
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("arrival, departure", [
    ("09:00", "11:01"), ("00:00", "24:00"), ("08:00", "12:00"), ("23:00", "01:01"), ("12:00", "11:59"),
])
def test_stay_longer_than_two_hours(arrival, departure):
    assert_error(run(PROGRAM, stdin=f"Поезд 8: прибытие {arrival}, отправление {departure}\n"), "Поезд 8")


@pytest.mark.category("edge")
def test_departure_at_midnight_and_overnight():
    text = ("Поезд 1: прибытие 23:00, отправление 24:00\nПоезд 2: прибытие 23:30, отправление 00:30\n"
            "Поезд 3: прибытие 00:10, отправление 00:40\n")
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 2

        Распределение по платформам:
          Платформа 1: Поезд 3 (00:10–00:40), Поезд 1 (23:00–24:00)
          Платформа 2: Поезд 2 (23:30–00:30)
    """)


@pytest.mark.category("naive")
def test_same_arrival_keeps_input_order():
    text = ("Б: прибытие 10:00, отправление 10:30\nА: прибытие 10:00, отправление 10:20\n"
            "В: прибытие 10:00, отправление 10:10\n")
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 3

        Распределение по платформам:
          Платформа 1: Б (10:00–10:30)
          Платформа 2: А (10:00–10:20)
          Платформа 3: В (10:00–10:10)
    """)


@pytest.mark.category("naive")
def test_takes_free_platform_with_smallest_number():
    text = ("П1: прибытие 08:00, отправление 09:00\nП2: прибытие 08:10, отправление 08:30\n"
            "П3: прибытие 08:20, отправление 08:50\nП4: прибытие 08:40, отправление 09:30\n"
            "П5: прибытие 09:00, отправление 09:10\n")
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 3

        Распределение по платформам:
          Платформа 1: П1 (08:00–09:00), П5 (09:00–09:10)
          Платформа 2: П2 (08:10–08:30), П4 (08:40–09:30)
          Платформа 3: П3 (08:20–08:50)
    """)


@pytest.mark.category("naive")
def test_one_minute_overlap_needs_two_platforms():
    text = "А: прибытие 09:00, отправление 09:31\nБ: прибытие 09:30, отправление 10:00\n"
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 2

        Распределение по платформам:
          Платформа 1: А (09:00–09:31)
          Платформа 2: Б (09:30–10:00)
    """)


@pytest.mark.category("typical")
def test_nested_intervals():
    text = ("A: прибытие 08:00, отправление 10:00\nB: прибытие 08:30, отправление 09:00\n"
            "C: прибытие 09:00, отправление 09:30\n")
    assert_output(run(PROGRAM, stdin=text), """
        Минимальное количество платформ: 2

        Распределение по платформам:
          Платформа 1: A (08:00–10:00)
          Платформа 2: B (08:30–09:00), C (09:00–09:30)
    """)


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_random_small_schedules_count(seed):
    rng = random.Random(seed)
    for _ in range(15):
        spans = []
        for _ in range(rng.randint(1, 12)):
            a = rng.randrange(1440)
            spans.append((a, a + rng.randint(1, 120)))
        load = [0] * 2881
        for a, d in spans:
            for m in range(a, d):
                load[m] += 1
        text = "".join(f"T{i}: прибытие {a // 60:02d}:{a % 60:02d}, отправление "
                       f"{(d % 1440) // 60:02d}:{d % 60:02d}\n" for i, (a, d) in enumerate(spans))
        result = run(PROGRAM, stdin=text)
        assert result.code == 0, result.err
        assert result.lines[0] == f"Минимальное количество платформ: {max(load)}"
