# Открытые тесты для самопроверки. Сгенерировано из контрольных тестов —
# не редактируйте: контрольные тесты преподавателя проверяют больше случаев.
"""Задача 5. Журнал событий: запуск программы, формат строк, оформление отчёта, ошибки запуска.

Дословные отчёты здесь закрепляют правила; модель eventlog_model сверяется с ними же.
"""
from datetime import datetime, timedelta

import pytest

from course_program import assert_error, assert_lines, assert_output, run
from eventlog_model import report

PROGRAM = "eventlog.py"

EXAMPLE = """\
2026-11-05 08:15:22 | LOGIN   | user=ivanov, ip=192.168.1.10
2026-11-05 08:16:01 | VIEW    | item=SKU-1001
2026-11-05 08:16:45 | VIEW    | item=SKU-2045
2026-11-05 08:17:30 | CART    | item=SKU-1001
2026-11-05 08:20:10 | PURCHASE| order=10050, sum=54990
2026-11-05 08:45:00 | LOGIN   | user=petrov, ip=10.0.0.5
[битая строка без разделителей]
2026-11-05 09:30:15 | ERROR   | code=503, msg="service unavailable"
2026-11-05 09:30:16 | ERROR   | code=503, msg="service unavailable"
2026-11-05 09:30:17 | ERROR   | code=503, msg="service unavailable"
2026-11-05 12:00:00 | LOGIN   | user=admin
"""

EXAMPLE_REPORT = """
    Отчёт по файлу events.log:
      Размер файла: 616 Б
      Всего строк: 11
      Успешно разобрано: 10
      Битых строк: 1 (пропущены)

    Примеры битых строк:
      строка 7: [битая строка без разделителей]

    Статистика по типам событий:
      LOGIN     : 3 (30.0%)
      VIEW      : 2 (20.0%)
      CART      : 1 (10.0%)
      PURCHASE  : 1 (10.0%)
      ERROR     : 3 (30.0%)

    Пики активности:
      Максимальная нагрузка: 08:00–09:00 (6 событий)
      Минимальная нагрузка: 10:00–11:00 (0 событий)
      Среднее за 60 мин: 2.0

    Подозрительные промежутки (более 30 мин без событий):
      08:45:00 – 09:30:15 (45 мин)
      09:30:17 – 12:00:00 (149 мин)

    Серии ошибок:
      09:30:15–09:30:17: 3 ошибки подряд (code=503) — ВОЗМОЖНЫЙ СБОЙ
"""


def analyze(data, *options, name="events.log"):
    return run(PROGRAM, name, *options, files={name: data})


@pytest.mark.category("typical")
def test_example_from_task():
    assert_output(analyze(EXAMPLE), EXAMPLE_REPORT)


@pytest.mark.category("typical")
def test_model_matches_example():
    """Модель, по которой строятся остальные проверки, совпадает с дословным отчётом."""
    from course_program import expected_lines
    assert report(EXAMPLE) == expected_lines(EXAMPLE_REPORT)


@pytest.mark.category("typical")
def test_file_name_without_folder_and_bom_crlf():
    data = ("﻿" + EXAMPLE.replace("\n", "\r\n")).encode("utf-8")
    result = analyze(data, name="logs/day1.log")
    assert result.lines[0] == "Отчёт по файлу day1.log:"
    assert result.lines[1] == "  Размер файла: 630 Б"
    assert result.lines[2:] == report(EXAMPLE)[2:]


@pytest.mark.category("typical")
def test_bucket_15_minutes_literal():
    data = ("2026-11-05 10:01:00 | A\n2026-11-05 10:14:59 | A\n2026-11-05 10:16:00 | B\n"
            "2026-11-05 10:50:00 | A\n")
    assert_output(analyze(data, "--bucket", "15", "--gap", "20"), """
        Отчёт по файлу events.log:
          Размер файла: 96 Б
          Всего строк: 4
          Успешно разобрано: 4
          Битых строк: 0

        Статистика по типам событий:
          A  : 3 (75.0%)
          B  : 1 (25.0%)

        Пики активности:
          Максимальная нагрузка: 10:00–10:15 (2 события)
          Минимальная нагрузка: 10:30–10:45 (0 событий)
          Среднее за 15 мин: 1.0

        Подозрительные промежутки (более 20 мин без событий):
          10:16:00 – 10:50:00 (34 мин)

        Серии ошибок:
          не обнаружено
    """)


@pytest.mark.category("edge")
def test_multi_day_log_shows_dates_literal():
    data = ("2026-11-05 23:50:00 | ERROR | code=500\n2026-11-05 23:55:00 | ERROR | code=\"502\"\n"
            "2026-11-06 00:10:00 | ERROR\n2026-11-06 02:00:00 | VIEW | item=1\n")
    assert_output(analyze(data, "--bucket", "120"), """
        Отчёт по файлу events.log:
          Размер файла: 144 Б
          Всего строк: 4
          Успешно разобрано: 4
          Битых строк: 0

        Статистика по типам событий:
          ERROR  : 3 (75.0%)
          VIEW   : 1 (25.0%)

        Пики активности:
          Максимальная нагрузка: 2026-11-05 22:00–00:00 (2 события)
          Минимальная нагрузка: 2026-11-06 00:00–02:00 (1 событие)
          Среднее за 120 мин: 1.3

        Подозрительные промежутки (более 30 мин без событий):
          2026-11-06 00:10:00 – 2026-11-06 02:00:00 (110 мин)

        Серии ошибок:
          2026-11-05 23:50:00–2026-11-06 00:10:00: 3 ошибки подряд (code=500, 502) — ВОЗМОЖНЫЙ СБОЙ
    """)


@pytest.mark.category("naive")
def test_broken_lines_do_not_break_error_series_but_other_types_do():
    data = ("2026-11-05 10:00:00 | ERROR | code=1\nмусор\n2026-11-05 10:00:01 | ERROR | code=2\n"
            "2026-11-05 10:00:02 | ERROR\n2026-11-05 10:00:03 | VIEW\n2026-11-05 10:00:04 | ERROR\n"
            "2026-11-05 10:00:05 | ERROR\n")
    assert_lines(analyze(data), "Серии ошибок:", "  10:00:00–10:00:02: 3 ошибки подряд (code=1, 2) — ВОЗМОЖНЫЙ СБОЙ")
    assert analyze(data).lines[-1].startswith("  10:00:00–10:00:02")


@pytest.mark.category("naive")
def test_gap_exactly_threshold_is_not_suspicious():
    data = "2026-11-05 10:00:00 | A\n2026-11-05 10:30:00 | A\n2026-11-05 11:00:59 | A\n"
    assert_lines(analyze(data), "Подозрительные промежутки (более 30 мин без событий):",
                 "  10:30:00 – 11:00:59 (30 мин)")
    assert "  10:00:00 – 10:30:00 (30 мин)" not in analyze(data).lines


@pytest.mark.category("naive")
def test_peak_and_quiet_ties_take_earliest():
    data = "2026-11-05 10:10:00 | A\n2026-11-05 11:10:00 | A\n2026-11-05 13:10:00 | A\n"
    assert_lines(analyze(data), "  Максимальная нагрузка: 10:00–11:00 (1 событие)",
                 "  Минимальная нагрузка: 12:00–13:00 (0 событий)", "  Среднее за 60 мин: 0.8")


@pytest.mark.category("edge")
def test_only_first_ten_broken_examples():
    data = "".join(f"плохо {i}\n" for i in range(1, 16))
    result = analyze(data)
    assert_lines(result, "  Битых строк: 15 (пропущены)", "Примеры битых строк:", "  строка 1: плохо 1",
                 "  строка 10: плохо 10", "Статистика по типам событий:")
    assert "  строка 11: плохо 11" not in result.lines


@pytest.mark.category("edge")
@pytest.mark.parametrize("size, text", [(1023, "1023 Б"), (1024, "1.0 КБ"), (1536, "1.5 КБ"),
                                        (1024 * 1024, "1.0 МБ"), (5 * 1024 * 1024 + 1, "5.0 МБ")])
def test_file_size_format(size, text):
    data = ("2026-11-05 10:00:00 | A |" + "x" * size)[:size]
    assert analyze(data).lines[1] == f"  Размер файла: {text}"


@pytest.mark.category("edge")
def test_thousands_and_alignment():
    data = "".join(f"2026-11-05 10:{i % 60:02d}:00 | {'VIEW' if i % 10 else 'BUY'}\n" for i in range(12_000))
    assert_lines(analyze(data), "  Всего строк: 12 000", "  BUY   :  1 200 (10.0%)", "  VIEW  : 10 800 (90.0%)",
                 "  Максимальная нагрузка: 10:00–11:00 (12 000 событий)")


@pytest.mark.category("typical")
@pytest.mark.parametrize("text", [
    "2026-11-05 08:00:00 | view\n", "2026-11-05T08:00:00;VIEW;a=1\n", "  2026-11-05 08:00:00\tVIEW\t\n",
    "2026-11-05 08:00:00 |VIEW|описание | с | палками\n", "2026-11-05 08:00:00 | Log_2 |\n",
])
def test_line_formats(text):
    assert_output(analyze(text), report(text))
    assert_lines(analyze(text), "  Успешно разобрано: 1")


@pytest.mark.category("format")
@pytest.mark.parametrize("text", [
    "2026-11-05 08:00:00 | VIEW ; a=1\n", "2026-11-05 08:00:00 VIEW\n", "2026-11-05  08:00:00 | VIEW\n",
    "2026/11/05 08:00:00 | VIEW\n", "2026-11-05 08:00 | VIEW\n", "2026-11-05 08:00:00 | VI-EW\n",
    "2026-11-05 08:00:00 || VIEW\n", "2026-11-05 08:00:00 | _VIEW\n",
])
def test_broken_line_formats(text):
    assert_output(analyze(text), report(text))
    assert_lines(analyze(text), "  Битых строк: 1 (пропущены)")


@pytest.mark.category("format")
def test_missing_file():
    assert_error(run(PROGRAM, "нет.log"), "нет.log")


@pytest.mark.category("format")
@pytest.mark.parametrize("args", [
    [], ["a.log", "b.log"], ["a.log", "--bucket"], ["a.log", "--bucket", "0"], ["a.log", "--bucket", "7"],
    ["a.log", "--bucket", "15.5"], ["a.log", "--gap", "-5"], ["a.log", "--gap", "x"], ["a.log", "--fast"],
    ["a.log", "--bucket", "2880"],
])
def test_bad_arguments(args):
    assert_error(run(PROGRAM, *args, files={"a.log": EXAMPLE, "b.log": EXAMPLE}), code=2)


@pytest.mark.category("typical")
@pytest.mark.parametrize("bucket", [1, 30, 90, 240, 1440])
def test_bucket_options(bucket):
    start = datetime(2026, 11, 5, 6, 0)
    data = "".join(f"{start + timedelta(minutes=7 * i):%Y-%m-%d %H:%M:%S} | T{i % 3}\n" for i in range(100))
    assert_output(analyze(data, "--bucket", str(bucket)), report(data, bucket=bucket))
