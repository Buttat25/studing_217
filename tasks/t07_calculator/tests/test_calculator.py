import pytest

from course_program import assert_output, run

PROGRAM = "calculator.py"


def session(*lines):
    result = run(PROGRAM, stdin="".join(line + "\n" for line in lines))
    assert result.code == 0 and not result.crashed, result.err[-2000:]
    return result


def answer(*lines):
    before = len(session(*lines[:-1]).lines) if len(lines) > 1 else 0
    return "\n".join(session(*lines).lines[before:])


def is_error(text):
    return text.startswith("ОШИБКА: ") and "\n" not in text


@pytest.mark.category("typical")
def test_example_from_task():
    result = session("2 + 2 * 2", "10 / 0", "log(-5)", "sqrt(16) + 3^2", "convert 5 km to miles",
                     "convert 100 kg to lbs", "matrix [[1, 2], [3, 4]] + [[5, 6], [7, 8]]",
                     "matrix [[1, 2, 3]] * [[1], [2]]", "true AND (false OR true)",
                     "NOT (x > 5) AND (y < 10), где x=7, y=3", "precision 5", "1 / 3", "history")
    assert_output(result, """
        = 6
        ОШИБКА: …
        ОШИБКА: …
        = 13.0
        = 3.10686 miles
        = 220.462 lbs
        = [[6, 8],
           [10, 12]]
        ОШИБКА: …1×3…2×1…
        = true
        = false
        Точность установлена: 5 знаков после запятой
        = 0.33333
          1. 2 + 2 * 2 = 6
          2. 10 / 0 → ОШИБКА
          3. log(-5) → ОШИБКА
          4. sqrt(16) + 3^2 = 13.0
          5. convert 5 km to miles = 3.10686 miles
          6. convert 100 kg to lbs = 220.462 lbs
          7. matrix [[1, 2], [3, 4]] + [[5, 6], [7, 8]] = [[6, 8], [10, 12]]
          8. matrix [[1, 2, 3]] * [[1], [2]] → ОШИБКА
          9. true AND (false OR true) = true
          10. NOT (x > 5) AND (y < 10), где x=7, y=3 = false
          11. 1 / 3 = 0.33333
    """)


@pytest.mark.category("typical")
@pytest.mark.parametrize("expr, result", [
    ("10 - 4 - 3", "= 3"), ("100 / 10 / 5", "= 2.0"), ("2 ^ 3 ^ 2", "= 512"), ("2^-1", "= 0.5"),
    ("(-2)^2", "= 4"), ("--3", "= 3"), ("+5", "= 5"), ("2 ** 10", "= 1024"), ("  7  ", "= 7"),
    ("1.5 * 2", "= 3.0"), (".5 + 5.", "= 5.5"), ("1e3 + 2.5E-1", "= 1000.25"), ("2 * -3", "= -6"),
    ("2^3^0", "= 2"), ("10 / 2", "= 5.0"), ("2^64 + 1", "= 18446744073709551617"), ("(-2) ^ 2.0", "= 4.0"),
])
def test_arithmetic(expr, result):
    assert answer(expr) == result


@pytest.mark.category("typical")
@pytest.mark.parametrize("expr, result", [
    ("sqrt(16) + 3^2", "= 13.0"), ("log(1000)", "= 3.0"), ("log(8, 2)", "= 3.0"), ("ln(e)", "= 1.0"),
    ("abs(-7)", "= 7"), ("abs(-2.5)", "= 2.5"), ("sin(0)", "= 0.0"), ("cos(0)", "= 1.0"), ("exp(0)", "= 1.0"),
    ("2 * pi", "= 6.2831853072"), ("sin(pi)", "= 0.0"), ("cos(pi / 2)", "= 0.0"), ("tan(pi / 4)", "= 1.0"),
    ("e", "= 2.7182818285"), ("sqrt(2)", "= 1.4142135624"), ("pi * r ^ 2, где r=2", "= 12.5663706144"),
    ("pi + 1, где pi=3", "= 4"), ("log( 100 )", "= 2.0"),
])
def test_functions_and_constants(expr, result):
    assert answer(expr) == result


@pytest.mark.category("naive")
@pytest.mark.parametrize("expr", [
    "0 ^ -1", "0^0", "0.0 ^ 0", "(2 - 2) ^ (3 - 3)", "0 ^ 0.0", "(-8) ^ (1/3)", "0.0 ^ -2", "exp(1000)",
    "1e308 * 10", "10^999 * 10^999", "10^400 + 0.5", "tan(pi / 2)", "log(8, 1)", "log(8, 0)", "log(8, -2)",
    "sqrt(1, 2)", "log()", "log(1, 2, 3)", "foo(2)", "x + 1", "2 $ 3", "2,5 + 1", "1e", "1.2.3", "()",
    "sqrt", "sin(", "x + 1, где x=abc", "x + 1, где x=true", "x + 1, где 5=x", "x + 1, где x=nan",
    "x + 1, где x=inf", "x, где x=1, x", "2 + 2 где", "٣ + 1", ", где x=1",
])
def test_math_errors(expr):
    assert is_error(answer(expr))


@pytest.mark.category("typical")
@pytest.mark.parametrize("line, result", [
    ("x * 2, где x=5", "= 10"), ("x * y + z, где x=2, y=3.5, z=-1", "= 6.0"), ("a+b, ГДЕ a=1,b=2", "= 3"),
    ("x ^ 2, где x=1e3", "= 1000000.0"),
])
def test_variables(line, result):
    assert answer(line) == result


@pytest.mark.category("edge")
@pytest.mark.parametrize("expr, result", [
    ("2.675 + 0", "= 2.675"), ("1 / 8", "= 0.125"), ("0.1 * 3", "= 0.3"), ("-0.0", "= 0.0"), ("0.0 * -1", "= 0.0"),
    ("10.0 ^ 20", "= 1e+20"), ("1.5 / 10^12", "= 1.5e-12"), ("123456789012345678.0", "= 1.2345678901e+17"),
    ("1 / 3 * 10^20", "= 3.3333333333e+19"), ("0.000001", "= 0.000001"), ("0.0000001", "= 1e-7"),
    ("999999999999999.0", "= 999999999999999.0"), ("2 / 3", "= 0.6666666667"), ("1e-11 / 1", "= 1e-11"),
    ("9.99999999999 + 0", "= 10.0"), ("-1 / 3", "= -0.3333333333"),
])
def test_number_format(expr, result):
    assert answer(expr) == result


@pytest.mark.category("edge")
@pytest.mark.parametrize("precision, expr, result", [
    (2, "2.675 + 0", "= 2.68"), (2, "0.125 + 0", "= 0.13"), (2, "-2.675 + 0", "= -2.68"), (3, "1 / 3", "= 0.333"),
    (2, "0.004 + 0", "= 0.0"), (2, "1.5e-12 * 1", "= 1.5e-12"), (2, "1 / 3 / 10^7", "= 3.33e-8"),
    (1, "9.96 + 0", "= 10.0"), (15, "1 / 3", "= 0.333333333333333"), (2, "9.996e20 * 1", "= 1e+21"),
    (0, "1.5e20 * 1", "= 2e+20"), (0, "2.5e-9 * 1", "= 3e-9"),
])
def test_rounding_half_up_by_decimal_notation(precision, expr, result):
    assert answer(f"precision {precision}", expr) == result


@pytest.mark.category("typical")
@pytest.mark.parametrize("command, result", [
    ("precision 1", "Точность установлена: 1 знак после запятой"),
    ("precision 2", "Точность установлена: 2 знака после запятой"),
    ("precision 11", "Точность установлена: 11 знаков после запятой"),
    ("precision 0", "Точность установлена: 0 знаков после запятой"),
    ("precision", "Текущая точность: 10 знаков после запятой"),
    ("PRECISION 3", "Точность установлена: 3 знака после запятой"),
])
def test_precision_command(command, result):
    assert answer(command) == result


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["precision 16", "precision -1", "precision 2.5", "precision пять",
                                     "precision 100", "precision 1 2"])
def test_bad_precision(command):
    result = session(command, "precision")
    assert is_error(result.lines[0]) and result.lines[1] == "Текущая точность: 10 знаков после запятой"


@pytest.mark.category("typical")
@pytest.mark.parametrize("command, result", [
    ("convert 1 km to m", "= 1000 m"), ("convert 1000 m in km", "= 1 km"), ("convert 1 ft to in", "= 12 in"),
    ("convert 3 feet to yards", "= 1 yards"), ("convert 1 mile to ft", "= 5280 ft"), ("convert 2.5 cm to mm", "= 25 mm"),
    ("convert 1 lb to oz", "= 16 oz"), ("convert 1 t to kg", "= 1000 kg"), ("convert 500 mg to g", "= 0.5 g"),
    ("convert 2 tonnes to pounds", "= 4409.25 pounds"), ("convert 90 min to h", "= 1.5 h"),
    ("convert 2 days to hours", "= 48 hours"), ("convert 1 day to sec", "= 86400 sec"),
    ("convert 1 hr to s", "= 3600 s"), ("convert 37 C to F", "= 98.6 F"), ("convert -40 F to C", "= -40 C"),
    ("convert 0 K to C", "= -273.15 C"), ("convert 300 kelvin to celsius", "= 26.85 celsius"),
    ("convert 32 °F to °C", "= 0 °C"), ("convert 100 Fahrenheit to K", "= 310.928 K"),
    ("convert 123456789 m to m", "= 123457000 m"), ("convert 1e-9 m to m", "= 1e-9 m"),
    ("convert 2.5e20 km to km", "= 2.5e+20 km"), ("convert 0 kg to lb", "= 0 lb"), ("CONVERT 1 KM TO M", "= 1000 M"),
    ("convert 1 inch to cm", "= 2.54 cm"), ("convert 1 ounce to g", "= 28.3495 g"),
])
def test_convert(command, result):
    assert answer(command) == result


@pytest.mark.category("format")
@pytest.mark.parametrize("command", [
    "convert 5 kg to m", "convert 5 C to kg", "convert 5 parsec to m", "convert 5 m to parsec",
    "convert -300 C to K", "convert -1 K to C", "convert -500 F to C", "convert abc m to km",
    "convert nan m to km", "convert inf m to km", "convert 5 km into m",
])
def test_convert_errors(command):
    assert is_error(answer(command))


@pytest.mark.category("typical")
@pytest.mark.parametrize("command, result", [
    ("matrix [[1, 2], [3, 4]] * [[5, 6], [7, 8]]", "= [[19, 22],\n   [43, 50]]"),
    ("matrix [[1, 2], [3, 4]] - [[1, 1], [1, 1]]", "= [[0, 1],\n   [2, 3]]"),
    ("matrix [[1, 2], [3, 4]] * 2", "= [[2, 4],\n   [6, 8]]"),
    ("matrix 0.5 * [[1, 2]]", "= [[0.5, 1.0]]"),
    ("matrix [[1, 2, 3]] * [[1], [2], [3]]", "= [[14]]"),
    ("matrix [[1], [2]] * [[3, 4]]", "= [[3, 4],\n   [6, 8]]"),
    ("matrix det [[1, 2], [3, 4]]", "= -2"),
    ("matrix det [[2]]", "= 2"),
    ("matrix det [[1, 2, 3], [4, 5, 6], [7, 8, 10]]", "= -3"),
    ("matrix det [[0, 1], [1, 0]]", "= -1"),
    ("matrix det [[0.5, 1], [1, 4]]", "= 1.0"),
    ("matrix det [[1, 2], [2, 4]]", "= 0"),
    ("matrix det [[0, 0], [0, 0]]", "= 0"),
    ("matrix transpose [[1, 2, 3], [4, 5, 6]]", "= [[1, 4],\n   [2, 5],\n   [3, 6]]"),
    ("matrix t [[1, 2]]", "= [[1],\n   [2]]"),
    ("matrix [[1, -2.5e1], [ 3 ,4 ]]", "= [[1, -25.0],\n   [3, 4]]"),
    ("matrix [[1.0, 2.25], [0.1, -0.0]]", "= [[1.0, 2.25],\n   [0.1, 0.0]]"),
    ("matrix [[-1, 2]] - [[1, 2]]", "= [[-2, 0]]"),
    ("matrix [[1]] * [[5]]", "= [[5]]"),
    ("matrix [[1, 2]] * -1", "= [[-1, -2]]"),
    ("MATRIX [[1]] + [[1]]", "= [[2]]"),
])
def test_matrix(command, result):
    assert answer(command) == result


@pytest.mark.category("edge")
def test_matrix_precision():
    assert answer("precision 2", "matrix [[1, 2], [3, 4]] * 0.333") == "= [[0.33, 0.67],\n   [1.0, 1.33]]"
    assert answer("precision 3", "matrix det [[0.5, 1], [1, 4.25]]") == "= 1.125"


@pytest.mark.category("format")
@pytest.mark.parametrize("command", [
    "matrix [[1, 2]] + 3", "matrix 3 - [[1]]", "matrix 2 * 3", "matrix [[1]] / [[1]]",
    "matrix [[1]] + [[1]] + [[1]]", "matrix det [[1, 2]]", "matrix det [[1, 2], [3, 4]] + [[1]]",
    "matrix transpose", "matrix [[1]] + ", "matrix [[1]] * x", "matrix [[true]]", "matrix [[1e999]]",
    "matrix [[1,, 2]]", "matrix [[1, 2]] [[3]]", "matrix []", "matrix 3 + [[1]]", "matrix [[1], 2]",
])
def test_matrix_errors(command):
    assert is_error(answer(command))


@pytest.mark.category("typical")
@pytest.mark.parametrize("line, result", [
    ("NOT (x > 5) AND (y < 10), где x=7, y=3", "= false"),
    ("NOT x > 5, где x=3", "= true"),
    ("x >= 3 AND x <= 5, где x=3", "= true"),
    ("x == 2.5, где x=2.5", "= true"),
    ("x != -1, где x=-1", "= false"),
    ("a OR b AND c, где a=true, b=true, c=false", "= true"),
    ("(a OR b) AND c, где a=true, b=true, c=false", "= false"),
    ("flag == true, где flag=false", "= false"),
    ("flag != false, где flag=TRUE", "= true"),
    ("-x < 0, где x=5", "= true"),
    ("1 < 2", "= true"),
    ("not not true", "= true"),
    ("x > 1 OR y, где x=5, y=true", "= true"),
])
def test_logic(line, result):
    assert answer(line) == result


@pytest.mark.category("format")
@pytest.mark.parametrize("line", [
    "x > 5", "x > 5 AND y, где x=7", "x AND true, где x=5", "true < false", "true == 1", "1 < 2 < 3",
    "NOT 5 > 3 AND", "(true", "true OR", "AND true", "x > 5, где x=abc", "true AND 5", "x == y, где x=1, y=true",
    "1 > 0 AND", "true @ false", "-x > 0, где x=true",
])
def test_logic_errors(line):
    assert is_error(answer(line))


@pytest.mark.category("typical")
def test_history_empty_and_only_calculations():
    assert_output(session("history", "precision 3", "help", "2 + 2", "history"), [
        "История пуста", "Точность установлена: 3 знака после запятой"] + session("help").lines + [
        "= 4", "  1. 2 + 2 = 4"])


@pytest.mark.category("typical")
def test_help_lists_commands():
    lines = session("help").lines
    assert lines[0] == "Команды:" and any("convert" in l for l in lines) and any("matrix" in l for l in lines)


@pytest.mark.category("typical")
def test_save_history_to_file():
    result = run(PROGRAM, stdin="2 + 2\n1 / 0\nmatrix [[1], [2]] * 3\nsave log.txt\ncat\n")
    assert "История сохранена: log.txt" in result.lines and is_error(result.lines[-1])


@pytest.mark.category("typical")
def test_saved_file_content(tmp_path):
    target = tmp_path / "история.txt"
    session("2 + 2", "1 / 0", "matrix [[1], [2]] * 3", f"save {target}")
    assert target.read_text(encoding="utf-8") == "1. 2 + 2 = 4\n2. 1 / 0 → ОШИБКА\n3. matrix [[1], [2]] * 3 = [[3], [6]]\n"
    empty = tmp_path / "пусто.txt"
    assert session(f"save {empty}").lines == [f"История сохранена: {empty}"]
    assert empty.read_text(encoding="utf-8") == ""


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["save", "save    ", "save нет_такой_папки/a/b.txt"])
def test_save_errors(command):
    assert is_error(answer("1 + 1", command))


@pytest.mark.category("typical")
def test_exit_and_quit_stop_reading():
    assert_output(run(PROGRAM, stdin="1 + 1\nexit\n2 + 2\n"), "= 2")
    assert_output(run(PROGRAM, stdin="1 + 1\n  QUIT  \n2 + 2\n"), "= 2")


@pytest.mark.category("edge")
def test_blank_lines_and_no_input():
    assert_output(run(PROGRAM, stdin=""), "")
    assert_output(run(PROGRAM, stdin="\n   \n1 + 1\n\n"), "= 2")
    assert_output(run(PROGRAM, stdin="1 + 1"), "= 2")


@pytest.mark.category("typical")
@pytest.mark.parametrize("args, out, code", [
    (["2 + 2"], "= 4", 0), (["2", "+", "2"], "= 4", 0), (["10 / 0"], "ОШИБКА: …", 1),
    (["convert", "1", "km", "to", "m"], "= 1000 m", 0), (["matrix [[1, 2]] * [[1, 2]]"], "ОШИБКА: …", 1),
])
def test_one_expression_from_arguments(args, out, code):
    assert_output(run(PROGRAM, *args, stdin="5 + 5\n"), out, code=code)
