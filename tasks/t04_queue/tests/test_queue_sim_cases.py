import random

import pytest

from course_program import assert_error, assert_output, run
from queue_model import customers_text, parse_report, report, simulate

PROGRAM = "queue_sim.py"


def check(people, cashiers, max_queue=10, closing=None):
    args = ["--cashiers", str(cashiers), "--max-queue", "none" if max_queue is None else str(max_queue)]
    if closing is not None:
        args += ["--close", str(closing)]
    stats = simulate(people, cashiers, max_queue, closing)
    assert_output(run(PROGRAM, *args, stdin=customers_text(people)), report(stats))
    return stats


def random_mode(*args):
    result = run(PROGRAM, *args)
    assert result.code == 0 and not result.crashed, result.err
    return result


def consistent(result, cashiers):
    numbers = parse_report(result.lines)
    assert numbers["served"] + numbers["balked"] == numbers["arrived"]
    assert len(numbers["cashiers"]) == cashiers
    assert sum(s for s, _ in numbers["cashiers"]) == numbers["served"]
    assert all(0 <= load <= 100 for _, load in numbers["cashiers"])
    assert 0 <= numbers["min_wait"] <= numbers["max_wait"]
    return numbers


@pytest.mark.category("typical")
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_4_1_low_intensity_everyone_served(seed):
    rng = random.Random(seed)
    people = [(i * 10 + rng.randint(0, 3), rng.randint(2, 5)) for i in range(10)]
    stats = check(people, 3, closing=120)
    assert stats["served"] == 10 and stats["max_wait"] == 0


@pytest.mark.category("typical")
@pytest.mark.parametrize("seed", [5, 6])
def test_4_1_low_intensity_generated(seed):
    result = random_mode("--cashiers", "3", "--seed", str(seed), "--minutes", "300", "--interval", "20")
    numbers = consistent(result, 3)
    assert numbers["balked"] == 0 and numbers["arrived"] == numbers["served"] > 0


@pytest.mark.category("typical")
@pytest.mark.parametrize("seed", [0, 42, 2026])
def test_4_3_same_seed_same_result(seed):
    args = ("--cashiers", "3", "--seed", str(seed))
    first, second = random_mode(*args), random_mode(*args)
    assert first.out == second.out
    assert first.lines[0] == f"Результаты симуляции (семя: {seed}):"
    consistent(first, 3)


@pytest.mark.category("typical")
def test_4_3_different_seeds_differ():
    outputs = {"\n".join(random_mode("--cashiers", "2", "--seed", str(s)).lines[1:]) for s in range(5)}
    assert len(outputs) > 1, "при разных зёрнах результаты всегда одинаковые"


@pytest.mark.category("naive")
@pytest.mark.parametrize("people", [[(0, 1), (1, 2), (5, 3)], [(i, 2) for i in range(50)]])
def test_4_4_zero_cashiers(people):
    stats = check(people, 0)
    assert stats["balked"] == len(people)


@pytest.mark.category("naive")
@pytest.mark.parametrize("cashiers, text", [(3, ""), (1, "\n\n"), (2, "# никого\n")])
def test_4_5_zero_customers(cashiers, text):
    assert_output(run(PROGRAM, "--cashiers", str(cashiers), stdin=text), report(simulate([], cashiers)))


@pytest.mark.category("edge")
@pytest.mark.parametrize("last, admitted", [(59.9, True), (59, True), (60, False), (75, False)])
def test_4_7_last_minute_customer(last, admitted):
    stats = check([(10, 30), (50, 20), (last, 30)], 1, closing=60)
    assert stats["arrived"] == (3 if admitted else 2)


@pytest.mark.category("edge")
@pytest.mark.parametrize("cashiers", [1, 2])
def test_4_9_max_queue_zero_nobody_waits(cashiers):
    people = [(i, 3) for i in range(30)]
    stats = check(people, cashiers, max_queue=0)
    assert stats["max_wait"] == 0 and stats["balked"] > 0


@pytest.mark.category("edge")
def test_4_10_shop_open_zero_minutes_random():
    result = random_mode("--cashiers", "2", "--seed", "1", "--minutes", "0")
    assert_output(result, report(simulate([], 2), seed=1))


@pytest.mark.category("edge")
def test_4_10_shop_open_zero_minutes_from_input():
    check([(0, 1), (1, 1)], 2, closing=0)


@pytest.mark.category("format")
@pytest.mark.parametrize("value", ["-1", "-5", "1.5", "три", ""])
def test_4_11_negative_cashiers(value):
    assert_error(run(PROGRAM, "--cashiers", value, stdin="1 2\n"), code=2)


@pytest.mark.category("format")
@pytest.mark.parametrize("line", ["5 0", "5 -1", "0 0.0"])
def test_4_12_zero_service_time_in_input(line):
    assert_error(run(PROGRAM, stdin=f"1 2\n{line}\n"), "строка 2")


@pytest.mark.category("format")
@pytest.mark.parametrize("service", ["0-5", "0-0", "-1-5"])
def test_4_12_zero_service_time_random(service):
    assert_error(run(PROGRAM, "--seed", "1", "--service", service), code=2)


@pytest.mark.category("format")
@pytest.mark.parametrize("value", ["-1", "-10", "2.5", "много"])
def test_4_14_negative_max_queue(value):
    assert_error(run(PROGRAM, "--max-queue", value, stdin="1 2\n"), code=2)


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_4_15_random_parameter_sets(seed):
    rng = random.Random(seed)
    for _ in range(15):
        people = [(rng.randint(0, 120), rng.randint(1, 8)) for _ in range(rng.randint(0, 80))]
        check(people, rng.randint(0, 4), rng.choice([None, 0, 1, 5, 20]), rng.choice([None, 60, 120]))


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [7, 8])
def test_4_15_random_mode_is_consistent(seed):
    rng = random.Random(seed)
    for _ in range(10):
        cashiers = rng.randint(0, 5)
        result = random_mode("--cashiers", str(cashiers), "--seed", str(rng.randint(0, 10 ** 6)),
                             "--minutes", str(rng.randint(0, 600)), "--interval", str(rng.choice([0.2, 1, 5])),
                             "--service", rng.choice(["1-2", "2-5", "0.5-10"]),
                             "--max-queue", rng.choice(["none", "0", "3", "10"]))
        consistent(result, cashiers)


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [11, 12])
def test_4_17_reproducibility_on_random_sets(seed):
    rng = random.Random(seed)
    for _ in range(10):
        args = ["--cashiers", str(rng.randint(1, 4)), "--seed", str(rng.randint(0, 999)),
                "--minutes", str(rng.randint(10, 300)), "--interval", str(rng.choice([0.3, 1, 2]))]
        assert random_mode(*args).out == random_mode(*args).out
