import pytest

from grades import (
    GradesError, average, best_students, distribution, format_summary, main, median,
    parse_line, read_records,
)

CLASS = [
    "Иванов Иван: 5 4 4 3\n",
    "Петрова Анна: 5 5 4\n",
    "\n",
    "Сидоров Пётр:  3 3 4 2\n",
]


def test_parse_line():
    assert parse_line("Иванов Иван: 5 4 4 3") == ("Иванов Иван", [5, 4, 4, 3])


def test_parse_line_extra_spaces():
    assert parse_line("  Петрова   Анна :5  5 4 \n") == ("Петрова Анна", [5, 5, 4])


@pytest.mark.parametrize("line", ["Иванов Иван 5 4", ": 5 4", "Иванов: ", "Иванов: 5 6", "Иванов: 5 x"])
def test_parse_line_errors(line):
    with pytest.raises(GradesError):
        parse_line(line)


def test_read_records_skips_blank_lines():
    assert [name for name, _ in read_records(CLASS)] == ["Иванов Иван", "Петрова Анна", "Сидоров Пётр"]


def test_average():
    assert average([5, 4, 4, 3]) == 4.0
    assert average([5, 5, 4]) == 4.67


def test_median_odd():
    assert median([5, 3, 4]) == 4.0
    assert median([2]) == 2.0


def test_median_even():
    assert median([5, 4, 4, 3]) == 4.0
    assert median([5, 3, 4, 2]) == 3.5
    assert median([5, 4]) == 4.5


def test_distribution():
    assert distribution(read_records(CLASS)) == {2: 1, 3: 3, 4: 4, 5: 3}


def test_best_students():
    records = read_records(CLASS + ["Козлов Олег: 4 5 5\n"])
    assert best_students(records) == ["Козлов Олег", "Петрова Анна"]
    assert best_students([]) == []


def test_format_summary():
    text = format_summary(read_records(CLASS))
    assert "Иванов Иван: средний балл 4.00, медиана 4" in text
    assert "Сидоров Пётр: средний балл 3.00, медиана 3" in text
    assert "Распределение оценок: «2» - 1, «3» - 3, «4» - 4, «5» - 3" in text
    assert text.endswith("Лучшие ученики: Петрова Анна")


def test_format_summary_median_half():
    text = format_summary(read_records(["Орлова Ольга: 5 4\n"]))
    assert "медиана 4.5" in text


def test_main(tmp_path, capsys):
    path = tmp_path / "class.txt"
    path.write_text("".join(CLASS), encoding="utf-8")
    assert main([str(path)]) == 0
    assert "Лучшие ученики: Петрова Анна" in capsys.readouterr().out


def test_main_errors(tmp_path, capsys):
    assert main([]) == 2
    assert main([str(tmp_path / "нет.txt")]) == 1
    bad = tmp_path / "bad.txt"
    bad.write_text("Иванов: 7\n", encoding="utf-8")
    assert main([str(bad)]) == 1
    assert "неверная оценка" in capsys.readouterr().err
