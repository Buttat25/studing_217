import pytest

from course_program import assert_error, assert_lines, assert_output, run

PROGRAM = "cache.py"

CATALOG = """\
SKU-1001; Смартфон X-Pro, 128 ГБ, чёрный
SKU-2045; Наушники беспроводные SoundMax
SKU-3300; Чехол для смартфона силиконовый
"""


def session(commands: str, *options, catalog: str = CATALOG):
    return run(PROGRAM, "catalog.txt", *options, stdin=commands, files={"catalog.txt": catalog})


def fill(count: int) -> str:
    return "".join(f"put F{i}; заполнитель {i}\n" for i in range(count))


@pytest.mark.category("typical")
def test_example_from_task():
    commands = "get SKU-1001\nget SKU-2045\nget SKU-1001\nget SKU-3300\nget SKU-9999\nget SKU-2045\n"
    assert_output(session(commands), """
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        SKU-2045: "Наушники беспроводные SoundMax"
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        SKU-3300: "Чехол для смартфона силиконовый"
        SKU-9999: [товар не найден]
        SKU-2045: "Наушники беспроводные SoundMax"
    """)


@pytest.mark.category("typical")
def test_list_shows_most_recent_first():
    commands = "list\nget SKU-1001\nget SKU-2045\nget SKU-3300\nget SKU-1001\nlist\n"
    assert_output(session(commands), """
        Список (0 из 1 000): пусто
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        SKU-2045: "Наушники беспроводные SoundMax"
        SKU-3300: "Чехол для смартфона силиконовый"
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        Список (3 из 1 000): SKU-1001, SKU-3300, SKU-2045
    """)


@pytest.mark.category("typical")
def test_put_new_key_is_cached_without_source():
    commands = "put NEW-1; Новинка\nget NEW-1\ndel NEW-1\nget NEW-1\nlist\n"
    assert_output(session(commands), """
        NEW-1: сохранено
        NEW-1: "Новинка"
        NEW-1: удалено
        NEW-1: [товар не найден]
        Список (0 из 1 000): пусто
    """)


@pytest.mark.category("typical")
def test_put_overrides_catalog_value():
    commands = "get SKU-1001\nput SKU-1001; Смартфон X-Pro, 256 ГБ\nget SKU-1001\nlist\n"
    assert_output(session(commands), """
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        SKU-1001: сохранено
        SKU-1001: "Смартфон X-Pro, 256 ГБ"
        Список (1 из 1 000): SKU-1001
    """)


@pytest.mark.category("naive")
def test_put_spaces_around_semicolon_are_ignored():
    assert_output(session("put   K 1  ;   значение с пробелами  \nget K 1\n"), """
        K 1: сохранено
        K 1: "значение с пробелами"
    """)


@pytest.mark.category("naive")
def test_full_cache_evicts_least_recently_used():
    commands = fill(1000) + "list\nget F0\nput NEW; новинка\nget F1\nget F0\n"
    result = session(commands)
    assert_lines(result, "Список (1 000 из 1 000): F999, F998, …, F1, F0")
    assert result.lines[-4:] == ['F0: "заполнитель 0"', "NEW: сохранено",
                                 "F1: [товар не найден]", 'F0: "заполнитель 0"'], result.lines[-4:]


@pytest.mark.category("naive")
def test_put_evicts_oldest_when_full():
    commands = "get SKU-1001\nget SKU-2045\nput X; икс\nlist\nget SKU-1001\nlist\n"
    assert_output(session(commands, "--size", "2"), """
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        SKU-2045: "Наушники беспроводные SoundMax"
        X: сохранено
        Список (2 из 2): X, SKU-2045
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        Список (2 из 2): SKU-1001, X
    """)


@pytest.mark.category("edge")
def test_blank_lines_in_commands_are_skipped():
    assert_output(session("\n\nget SKU-3300\n   \n\nlist\n"), """
        SKU-3300: "Чехол для смартфона силиконовый"
        Список (1 из 1 000): SKU-3300
    """)


@pytest.mark.category("edge")
def test_no_commands_no_output():
    assert_output(session(""), "")


@pytest.mark.category("edge")
def test_big_numbers_use_space_separator():
    result = session(fill(1234) + "list\n")
    assert result.lines[-1].startswith("Список (1 000 из 1 000): F1233, F1232, "), result.lines[-1][:80]
    result = session(fill(12_345) + "list\n", "--size", "25000")
    assert result.lines[-1].startswith("Список (12 345 из 25 000): F12344, F12343, "), result.lines[-1][:80]


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["fetch SKU-1001", "GET SKU-1001", "stats", "help", "?"])
def test_unknown_command(command):
    assert_output(session(command + "\nget SKU-2045\n"), """
        ОШИБКА: …
        SKU-2045: "Наушники беспроводные SoundMax"
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("args", [
    [], ["--size", "5"], ["catalog.txt", "--size"], ["catalog.txt", "other.txt"], ["catalog.txt", "--fast"],
    ["catalog.txt", "--delay", "-1"], ["catalog.txt", "--delay", "abc"], ["catalog.txt", "--delay"],
])
def test_bad_arguments(args):
    assert_error(run(PROGRAM, *args, stdin="get A\n", files={"catalog.txt": CATALOG}), code=2)


@pytest.mark.category("typical")
def test_options_in_any_order():
    result = run(PROGRAM, "--delay", "0", "--size", "1", "catalog.txt", stdin="get SKU-1001\nget SKU-2045\nlist\n",
                 files={"catalog.txt": CATALOG})
    assert_output(result, """
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный"
        SKU-2045: "Наушники беспроводные SoundMax"
        Список (1 из 1): SKU-2045
    """)
