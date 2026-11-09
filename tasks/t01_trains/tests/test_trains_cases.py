import random
import string

import pytest

from course_program import assert_error, assert_output, run
from trains_model import report as model_report

PROGRAM = "trains.py"


def schedule(*spans) -> str:
    return "".join(f"Поезд {i}: прибытие {a}, отправление {d}\n" for i, (a, d) in enumerate(spans, 1))


def hhmm(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def report(*spans) -> list[str]:
    return model_report([list(span) for span in spans])


def check(*spans):
    assert_output(run(PROGRAM, stdin=schedule(*spans)), report(*spans))


@pytest.mark.category("typical")
@pytest.mark.parametrize("spans", [
    [("09:00", "10:00"), ("11:00", "12:00")],
    [("06:00", "06:30"), ("07:00", "07:45"), ("08:00", "09:00")],
    [("00:00", "01:00"), ("12:00", "13:00"), ("23:00", "23:59")],
    [("10:00", "10:05"), ("10:10", "10:15"), ("10:20", "10:25"), ("10:30", "10:35")],
])
def test_1_1_trains_do_not_overlap(spans):
    assert report(*spans)[0] == "Минимальное количество платформ: 1"
    check(*spans)


@pytest.mark.category("typical")
@pytest.mark.parametrize("spans", [
    [("09:00", "10:00"), ("09:30", "10:30")],
    [("12:00", "14:00"), ("13:59", "15:00")],
    [("08:00", "09:00"), ("08:30", "09:30"), ("09:00", "10:00")],
    [("18:00", "19:00"), ("18:10", "18:20"), ("18:30", "18:40")],
])
def test_1_2_two_trains_overlap(spans):
    assert report(*spans)[0] == "Минимальное количество платформ: 2"
    check(*spans)


@pytest.mark.category("naive")
@pytest.mark.parametrize("spans", [
    [("09:00", "09:30"), ("09:30", "10:00")],
    [("08:00", "08:20"), ("08:20", "08:40"), ("08:40", "09:00"), ("09:00", "09:20")],
    [("23:00", "23:30"), ("23:30", "24:00")],
    [("09:30", "10:00"), ("09:00", "09:30")],
])
def test_1_4_arrival_at_departure_moment(spans):
    assert report(*spans)[0] == "Минимальное количество платформ: 1"
    check(*spans)


@pytest.mark.category("naive")
@pytest.mark.parametrize("span", [("09:00", "09:30"), ("22:00", "24:00"), ("23:50", "00:10"), ("12:00", "12:01")])
def test_1_5_single_train(span):
    assert_output(run(PROGRAM, stdin=schedule(span)), f"""
        Минимальное количество платформ: 1

        Распределение по платформам:
          Платформа 1: Поезд 1 ({span[0]}–{span[1]})
    """)


@pytest.mark.category("edge")
@pytest.mark.parametrize("text", ["", "\n\n", "# пустое расписание\n", "   \n# комментарий\n\n"])
def test_1_7_empty_schedule(text):
    assert_output(run(PROGRAM, stdin=text), "Минимальное количество платформ: 0")


@pytest.mark.category("edge")
def test_1_7_empty_schedule_file():
    assert_output(run(PROGRAM, "empty.txt", files={"empty.txt": ""}), "Минимальное количество платформ: 0")


@pytest.mark.category("edge")
@pytest.mark.parametrize("time_", ["09:00", "00:00", "23:59", "12:30"])
def test_1_9_zero_stay_is_an_error(time_):
    assert_error(run(PROGRAM, stdin=schedule(("08:00", "08:30"), (time_, time_))))


@pytest.mark.category("edge")
@pytest.mark.parametrize("seed, max_stay", [(1, 30), (2, 120)])
def test_1_10_ten_thousand_trains_fast(seed, max_stay):
    rng = random.Random(seed)
    spans = []
    for _ in range(10_000):
        a = rng.randrange(1440)
        spans.append((hhmm(a), hhmm((a + rng.randint(1, max_stay)) % 1440)))
    result = run(PROGRAM, stdin=schedule(*spans))
    assert_output(result, report(*spans))
    assert result.seconds < 1, f"{result.seconds:.2f} с"


@pytest.mark.category("format")
@pytest.mark.parametrize("spans", [
    [("10:00", "09:00")],
    [("18:00", "06:00")],
    [("23:00", "01:01")],
    [("12:00", "11:59")],
    [("08:00", "08:30"), ("12:00", "13:00"), ("15:00", "14:00")],
])
def test_1_12_departure_before_arrival_is_an_error(spans):
    assert_error(run(PROGRAM, stdin=schedule(*spans)))


@pytest.mark.category("format")
@pytest.mark.parametrize("arrival, departure", [
    ("25:00", "26:00"), ("24:30", "01:00"), ("99:99", "10:00"), ("12:60", "13:00"),
    ("09:00", "25:00"), ("09:00", "24:01"),
])
def test_1_13_time_out_of_range(arrival, departure):
    assert_error(run(PROGRAM, stdin=schedule((arrival, departure))))


@pytest.mark.category("format")
@pytest.mark.parametrize("line", [
    "Поезд 1: прибытие 09:00",
    "Поезд 1: прибытие 09:00, отправление",
    "Поезд 1: прибытие 09:00, отправление   ",
    "Поезд 1: прибытие 09:00,",
])
def test_1_14_missing_departure(line):
    assert_error(run(PROGRAM, stdin=line + "\n"))


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [11, 12, 13])
def test_1_15_thousand_random_trains(seed):
    rng = random.Random(seed)
    spans = []
    for _ in range(1000):
        a = rng.randrange(1440)
        spans.append((hhmm(a), hhmm((a + rng.randint(1, 120)) % 1440)))
    check(*spans)


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [31, 32])
def test_1_17_random_strings_instead_of_time(seed):
    rng = random.Random(seed)
    alphabet = string.ascii_letters + string.digits + string.punctuation.replace(":", "").replace(",", "") + "абвгдё"
    for _ in range(300):
        bad = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 12)))
        if rng.random() < 0.3:
            bad = f"{rng.choice('ab9')}{rng.randint(0, 9)}:{rng.choice(['x1', '5', '123', 'zz'])}"
        assert_error(run(PROGRAM, stdin=f"Поезд 1: прибытие {bad}, отправление 10:00\n"))
