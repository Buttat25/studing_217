import random
from datetime import datetime, timedelta

import pytest

from course_program import assert_lines, assert_output, run
from eventlog_model import report

PROGRAM = "eventlog.py"
START = datetime(2026, 11, 5, 8, 0, 0)


def analyze(data, *options, name="events.log"):
    return run(PROGRAM, name, *options, files={name: data})


def check(data, bucket=60, gap=30):
    options = []
    if bucket != 60:
        options += ["--bucket", str(bucket)]
    if gap != 30:
        options += ["--gap", str(gap)]
    assert_output(analyze(data, *options), report(data, bucket=bucket, gap=gap))


def line(moment, kind, description="", sep=" | "):
    return f"{moment:%Y-%m-%d %H:%M:%S}{sep}{kind}" + (f"{sep}{description}" if description else "") + "\n"


@pytest.mark.category("typical")
@pytest.mark.parametrize("kind", ["VIEW", "login", "Error"])
def test_5_1_hundred_lines_of_one_type(kind):
    data = "".join(line(START + timedelta(minutes=i), kind, f"n={i}") for i in range(100))
    check(data)
    assert_lines(analyze(data), f"  {kind.upper()}  : 100 (100.0%)")


@pytest.mark.category("typical")
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_5_2_mixed_types(seed):
    rng = random.Random(seed)
    kinds = ["LOGIN", "VIEW", "CART", "PURCHASE", "ERROR", "LOGOUT"]
    data = "".join(line(START + timedelta(seconds=i * 37), rng.choice(kinds)) for i in range(rng.randint(5, 300)))
    check(data)


@pytest.mark.category("naive")
@pytest.mark.parametrize("data", ["", "\n\n\n", "   \n\t\n"])
def test_5_5_empty_input(data):
    check(data)


@pytest.mark.category("naive")
def test_5_5_empty_file_literal():
    assert_output(analyze(""), """
        Отчёт по файлу events.log:
          Размер файла: 0 Б
          Всего строк: 0
          Успешно разобрано: 0
          Битых строк: 0

        Статистика по типам событий:
          нет событий

        Пики активности:
          нет данных

        Подозрительные промежутки (более 30 мин без событий):
          не обнаружено

        Серии ошибок:
          не обнаружено
    """)


@pytest.mark.category("naive")
@pytest.mark.parametrize("text", [
    "2026-11-05 08:15:22 | LOGIN | user=ivanov\n",
    "2026-11-05 23:59:59;error;code=1",
    "2026-11-05T00:00:00\tVIEW\n",
])
def test_5_6_single_line(text):
    check(text)


@pytest.mark.category("edge")
def test_5_7_big_file_is_streamed():
    rng = random.Random(7)
    kinds = ["LOGIN", "VIEW", "CART", "ERROR"]
    parts = []
    moment = START
    for i in range(150_000):
        moment += timedelta(seconds=rng.randint(0, 3))
        parts.append(line(moment, rng.choice(kinds), f"user=u{i % 500}, item=SKU-{i % 9000}"))
    data = "".join(parts).encode("utf-8")
    result = run(PROGRAM, "events.log", files={"events.log": data}, trace_memory=True)
    assert_lines(result, "  Успешно разобрано: 150 000")
    peak = result.peak_memory
    assert peak < len(data) / 3, f"пик памяти {peak / 2 ** 20:.1f} МБ при файле {len(data) / 2 ** 20:.1f} МБ - " \
                                 "похоже, файл читается целиком или события складываются в список"


@pytest.mark.category("edge")
def test_5_9_events_out_of_order():
    data = (line(START, "LOGIN") + line(START + timedelta(minutes=50), "VIEW")
            + line(START + timedelta(minutes=10), "CART") + line(START + timedelta(minutes=70), "VIEW")
            + line(START + timedelta(minutes=5), "ERROR"))
    check(data)
    assert_lines(analyze(data), "  Записано не по порядку времени: 2",
                 "  08:00:00 – 08:50:00 (50 мин)")


@pytest.mark.category("edge")
@pytest.mark.parametrize("copies", [2, 3, 10])
def test_5_10_duplicates_are_counted_separately(copies):
    data = line(START, "ERROR", "code=500") * copies + line(START + timedelta(minutes=1), "VIEW")
    check(data)


@pytest.mark.category("format")
@pytest.mark.parametrize("bad", ["[битая строка без разделителей]", "2026-11-05 08:00:00 LOGIN",
                                 "2026-11-05 08:00:00 | ", "| LOGIN | user=1", "2026-11-05 08:00:00 | 123ABC"])
def test_5_11_line_without_separators(bad):
    data = line(START, "LOGIN") + "\n" + bad + "\n" + line(START + timedelta(minutes=5), "VIEW")
    check(data)
    assert_lines(analyze(data), f"  строка 3: {bad}")


@pytest.mark.category("format")
@pytest.mark.parametrize("stamp", ["2026-13-45 08:00:00", "2026-02-29 10:00:00", "2026-11-05 24:00:00",
                                   "2026-11-05 08:60:00", "2026-11-05 08:00:60", "2026-11-31 08:00:00",
                                   "26-11-05 08:00:00", "2026-11-05 8:00:00"])
def test_5_12_invalid_dates(stamp):
    check(line(START, "VIEW") + f"{stamp} | LOGIN\n")


@pytest.mark.category("format")
@pytest.mark.parametrize("junk", [b"\x00\x01\x02", b"\xff\xfe\xfd binary", b"\x89PNG\r\n\x1a\n", b"\xc3\x28"])
def test_5_13_binary_data_in_text_file(junk):
    data = line(START, "LOGIN").encode() + junk + b"\n" + line(START + timedelta(minutes=2), "VIEW").encode()
    check(data)


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_5_15_random_lines_some_broken(seed):
    rng = random.Random(seed)
    kinds = ["LOGIN", "VIEW", "ERROR", "CART"]
    moment, parts = START, []
    for i in range(10_000):
        moment += timedelta(seconds=rng.choice([0, 1, 5, 60, 600, 2400]))
        if rng.random() < 0.1:
            parts.append(rng.choice(["мусор", "2026-99-99 10:00:00 | X", "", "   ", "| | |"]) + "\n")
        else:
            parts.append(line(moment, rng.choice(kinds), f"code={rng.randint(500, 503)}"))
    check("".join(parts), bucket=rng.choice([15, 60, 120]), gap=rng.choice([10, 30]))


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [11, 12])
def test_5_16_random_separators_and_spacing(seed):
    rng = random.Random(seed)
    parts = []
    for i in range(500):
        first, second = rng.choice("|;\t"), rng.choice("|;\t")
        space = lambda: rng.choice(["", " ", "  ", "\t"])
        stamp = f"{START + timedelta(minutes=i):%Y-%m-%d}{rng.choice(' T')}{START + timedelta(minutes=i):%H:%M:%S}"
        description = f"{space()}{second}{space()}d={i}" if rng.random() < 0.8 else ""
        parts.append(f"{space()}{stamp}{space()}{first}{space()}{rng.choice(['VIEW', 'err', 'Log_1'])}"
                     f"{description}{space()}\n")
    check("".join(parts))
