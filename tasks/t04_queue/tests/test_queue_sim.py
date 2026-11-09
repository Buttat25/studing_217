# Открытые тесты для самопроверки. Сгенерировано из контрольных тестов —
# не редактируйте: контрольные тесты преподавателя проверяют больше случаев.
"""Задача 4. Очередь: запуск программы, формат ввода и отчёта, правила обслуживания, ошибки.

Программа: python queue_sim.py [--cashiers N] [--max-queue N|none] [--close T] < покупатели
           python queue_sim.py [--cashiers N] [--max-queue N|none] --seed S [--minutes M]
                               [--interval I] [--service МИН-МАКС]
"""
import pytest

from course_program import assert_error, assert_output, run
from queue_model import parse_report, report, simulate

PROGRAM = "queue_sim.py"


@pytest.mark.category("typical")
def test_example_report():
    text = "0 3\n1 4\n1.5 2\n2 5\n2.5 1\n3 2\n"
    assert_output(run(PROGRAM, "--cashiers", "2", "--max-queue", "2", "--close", "10", stdin=text), """
        Результаты симуляции:

        Общая статистика:
          Всего пришло покупателей: 6
          Обслужено покупателей: 5
          Ушло из-за длинной очереди: 1

        Время ожидания:
          Среднее время ожидания: 1.3 мин
          Максимальное время ожидания: 3.0 мин
          Минимальное время ожидания: 0.0 мин

        Очередь:
          Максимальная длина очереди: 2 человека
          Среднее время обслуживания: 3.2 мин на покупателя

        Загрузка кассиров:
          Кассир 1: обслужил 3 покупателей, загрузка 100%
          Кассир 2: обслужил 2 покупателей, загрузка 60%
    """)


@pytest.mark.category("typical")
def test_defaults_three_cashiers_queue_ten_no_closing():
    people = [(0, 100)] * 15
    assert_output(run(PROGRAM, stdin="0 100\n" * 15), report(simulate(people, 3, 10, None)))


@pytest.mark.category("naive")
def test_cashier_frees_before_arrival_at_same_moment():
    """В один момент сначала освобождается касса, потом приходит покупатель — он не ждёт."""
    result = run(PROGRAM, "--cashiers", "1", "--max-queue", "0", stdin="0 5\n5 5\n10 5\n")
    numbers = parse_report(result.lines)
    assert (numbers["served"], numbers["balked"], numbers["max_wait"]) == (3, 0, 0.0)


@pytest.mark.category("naive")
def test_free_cashier_with_smallest_number():
    text = "0 10\n1 1\n2 1\n5 1\n"
    assert_output(run(PROGRAM, "--cashiers", "3", stdin=text),
                  report(simulate([(0, 10), (1, 1), (2, 1), (5, 1)], 3)))
    assert run(PROGRAM, "--cashiers", "3", stdin=text).lines[-3:] == [
        "  Кассир 1: обслужил 1 покупателя, загрузка 100%",
        "  Кассир 2: обслужил 3 покупателей, загрузка 30%",
        "  Кассир 3: обслужил 0 покупателей, загрузка 0%",
    ]


@pytest.mark.category("naive")
def test_queue_is_fifo_and_released_cashiers_in_number_order():
    people = [(0, 4), (0, 4), (1, 1), (1, 7), (2, 2), (3, 1)]
    text = "".join(f"{a} {s}\n" for a, s in people)
    assert_output(run(PROGRAM, "--cashiers", "2", "--max-queue", "none", stdin=text),
                  report(simulate(people, 2, None)))


@pytest.mark.category("naive")
def test_input_order_does_not_matter_equal_arrivals_keep_order():
    text = "5 1\n0 3\n0 1\n2 2\n"
    assert_output(run(PROGRAM, "--cashiers", "1", stdin=text),
                  report(simulate([(5, 1), (0, 3), (0, 1), (2, 2)], 1)))


@pytest.mark.category("edge")
def test_comments_spaces_and_decimal_numbers():
    text = "# приход обслуживание\n\n  0.25   1.5  \n\t1e1 2\n  # ещё\n3.75 .5\n"
    assert_output(run(PROGRAM, "--cashiers", "1", stdin=text),
                  report(simulate([(0.25, 1.5), (10.0, 2.0), (3.75, 0.5)], 1)))


@pytest.mark.category("edge")
@pytest.mark.parametrize("count, word", [(1, "человек"), (2, "человека"), (4, "человека"), (5, "человек"),
                                         (11, "человек"), (21, "человек"), (22, "человека")])
def test_queue_length_plural(count, word):
    result = run(PROGRAM, "--cashiers", "1", "--max-queue", "none", stdin="0 1\n" * (count + 1))
    assert f"  Максимальная длина очереди: {count} {word}" in result.lines


@pytest.mark.category("edge")
def test_big_numbers_use_space_separator():
    people = [(i * 0.1, 0.05) for i in range(1442)]
    result = run(PROGRAM, "--cashiers", "1", stdin="".join(f"{a!r} {s!r}\n" for a, s in people))
    assert "  Всего пришло покупателей: 1 442" in result.lines
    assert "  Кассир 1: обслужил 1 442 покупателей, загрузка 50%" in result.lines


@pytest.mark.category("edge")
def test_large_random_simulation_is_fast():
    result = run(PROGRAM, "--cashiers", "5", "--seed", "1", "--minutes", "100000", "--interval", "0.5")
    assert result.code == 0, result.err
    assert parse_report(result.lines)["arrived"] > 150_000
    assert result.seconds < 5, f"{result.seconds:.1f} с"


@pytest.mark.category("typical")
def test_random_mode_uses_defaults_and_ignores_stdin():
    a = run(PROGRAM, "--seed", "42", stdin="0 1\n")
    b = run(PROGRAM, "--seed", "42", "--minutes", "720", "--interval", "0.5", "--service", "2-5",
            "--cashiers", "3", "--max-queue", "10")
    assert a.code == 0 and a.out == b.out
    assert a.lines[0] == "Результаты симуляции (семя: 42):"


@pytest.mark.category("format")
@pytest.mark.parametrize("line", ["1", "1 2 3", "a 2", "1 b", "-1 2", "nan 2", "1 inf", "1,5 2"])
def test_bad_customer_line(line):
    assert_error(run(PROGRAM, stdin=f"0 1\n\n{line}\n"), "строка 3")


@pytest.mark.category("format")
@pytest.mark.parametrize("args", [
    ["--speed", "2"], ["--cashiers"], ["--cashiers", "2", "--cashiers", "3"], ["--minutes", "60"],
    ["--interval", "1"], ["--service", "2-5"], ["--seed", "1", "--close", "60"], ["--seed", "x"],
    ["--seed", "1", "--service", "5"], ["--close", "-1"], ["--close", "abc"], ["лишний"],
])
def test_bad_arguments(args):
    assert_error(run(PROGRAM, *args, stdin="0 1\n"), code=2)
