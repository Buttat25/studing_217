# Открытые тесты для самопроверки. Сгенерировано из контрольных тестов —
# не редактируйте: контрольные тесты преподавателя проверяют больше случаев.
"""Задача 2. Кэш: запуск программы, каталог, команды и их ответы.

Программа: python cache.py КАТАЛОГ [--size N] [--delay СЕК]. Каталог — строки «ключ; описание».
Команды из stdin: get КЛЮЧ, put КЛЮЧ; ЗНАЧЕНИЕ, del КЛЮЧ, list, stats.
"""
import pytest

from course_program import assert_error, assert_output, run

PROGRAM = "cache.py"

CATALOG = """\
SKU-1001; Смартфон X-Pro, 128 ГБ, чёрный
SKU-2045; Наушники беспроводные SoundMax
SKU-3300; Чехол для смартфона силиконовый
"""


def session(commands: str, *options, catalog: str = CATALOG):
    return run(PROGRAM, "catalog.txt", *options, stdin=commands, files={"catalog.txt": catalog})


@pytest.mark.category("typical")
def test_example_from_task():
    commands = "get SKU-1001\nget SKU-2045\nget SKU-1001\nget SKU-3300\nget SKU-9999\nget SKU-2045\nstats\n"
    assert_output(session(commands), """
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из внешнего источника]
        SKU-2045: "Наушники беспроводные SoundMax" [из внешнего источника]
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из кэша]
        SKU-3300: "Чехол для смартфона силиконовый" [из внешнего источника]
        SKU-9999: [товар не найден]
        SKU-2045: "Наушники беспроводные SoundMax" [из кэша]
        Статистика работы кэша:
          Всего запросов: 6
          Попаданий в кэш: 2 (33.3%)
          Промахов (обращений к внешнему источнику): 4
          Из них не найдено: 1
          Размер кэша: 3 из 1 000
          Вытеснено записей по стратегии LRU: 0
    """)


@pytest.mark.category("typical")
def test_list_shows_most_recent_first():
    commands = "list\nget SKU-1001\nget SKU-2045\nget SKU-3300\nget SKU-1001\nlist\n"
    assert_output(session(commands), """
        Кэш (0 из 1 000): пусто
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из внешнего источника]
        SKU-2045: "Наушники беспроводные SoundMax" [из внешнего источника]
        SKU-3300: "Чехол для смартфона силиконовый" [из внешнего источника]
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из кэша]
        Кэш (3 из 1 000): SKU-1001, SKU-3300, SKU-2045
    """)


@pytest.mark.category("typical")
def test_put_new_key_is_cached_without_source():
    commands = "put NEW-1; Новинка\nget NEW-1\ndel NEW-1\nget NEW-1\nstats\n"
    assert_output(session(commands), """
        NEW-1: сохранено
        NEW-1: "Новинка" [из кэша]
        NEW-1: удалено из кэша
        NEW-1: [товар не найден]
        Статистика работы кэша:
          Всего запросов: 2
          Попаданий в кэш: 1 (50.0%)
          Промахов (обращений к внешнему источнику): 1
          Из них не найдено: 1
          Размер кэша: 0 из 1 000
          Вытеснено записей по стратегии LRU: 0
    """)


@pytest.mark.category("naive")
def test_put_spaces_around_semicolon_are_ignored():
    assert_output(session("put   K 1  ;   значение с пробелами  \nget K 1\n"), """
        K 1: сохранено
        K 1: "значение с пробелами" [из кэша]
    """)


@pytest.mark.category("naive")
def test_put_evicts_oldest_when_full():
    commands = "get SKU-1001\nget SKU-2045\nput X; икс\nlist\nstats\n"
    assert_output(session(commands, "--size", "2"), """
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из внешнего источника]
        SKU-2045: "Наушники беспроводные SoundMax" [из внешнего источника]
        X: сохранено
        Кэш (2 из 2): X, SKU-2045
        Статистика работы кэша:
          Всего запросов: 2
          Попаданий в кэш: 0 (0.0%)
          Промахов (обращений к внешнему источнику): 2
          Из них не найдено: 0
          Размер кэша: 2 из 2
          Вытеснено записей по стратегии LRU: 1
    """)


@pytest.mark.category("edge")
def test_blank_lines_in_commands_are_skipped():
    assert_output(session("\n\nget SKU-3300\n   \n\nlist\n"), """
        SKU-3300: "Чехол для смартфона силиконовый" [из внешнего источника]
        Кэш (1 из 1 000): SKU-3300
    """)


@pytest.mark.category("edge")
def test_no_commands_no_output():
    assert_output(session(""), "")


@pytest.mark.category("edge")
def test_big_numbers_in_stats_use_space_separator():
    commands = "get SKU-1001\n" * 12_345 + "stats\n"
    assert_output(session(commands, "--size", "25000"), """
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из внешнего источника]
    """.strip().splitlines() + ['SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из кэша]'] * 12_344 + [
        "Статистика работы кэша:",
        "  Всего запросов: 12 345",
        "  Попаданий в кэш: 12 344 (100.0%)",
        "  Промахов (обращений к внешнему источнику): 1",
        "  Из них не найдено: 0",
        "  Размер кэша: 1 из 25 000",
        "  Вытеснено записей по стратегии LRU: 0",
    ])


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["fetch SKU-1001", "GET SKU-1001", "list all", "stats now", "?"])
def test_unknown_command(command):
    assert_output(session(command + "\nget SKU-2045\n"), """
        ОШИБКА: …
        SKU-2045: "Наушники беспроводные SoundMax" [из внешнего источника]
    """)


# ============================================================ каталог и запуск
@pytest.mark.category("edge")
def test_catalog_comments_blank_lines_and_bom():
    catalog = "﻿# каталог магазина\n\nA1;  Товар А  \n  # ещё\nB2 ;Товар;Б\n"
    assert_output(session("get A1\nget B2\n", catalog=catalog), """
        A1: "Товар А" [из внешнего источника]
        B2: "Товар;Б" [из внешнего источника]
    """)


@pytest.mark.category("format")
@pytest.mark.parametrize("catalog, fragment", [
    ("A; один\nстрока без точки с запятой\n", "строка 2"),
    ("A; один\n; без ключа\n", "строка 2"),
    ("A; один\n\nB;\n", "строка 3"),
    ("A; один\nA; другой\n", "строка 2"),
])
def test_bad_catalog(catalog, fragment):
    assert_error(session("get A\n", catalog=catalog), fragment)


@pytest.mark.category("format")
def test_missing_catalog_file():
    assert_error(run(PROGRAM, "нет.txt", stdin="get A\n"), "нет.txt")


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
        SKU-1001: "Смартфон X-Pro, 128 ГБ, чёрный" [из внешнего источника]
        SKU-2045: "Наушники беспроводные SoundMax" [из внешнего источника]
        Кэш (1 из 1): SKU-2045
    """)
