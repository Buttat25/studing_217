# Открытые тесты для самопроверки. Сгенерировано из контрольных тестов —
# не редактируйте: контрольные тесты преподавателя проверяют больше случаев.
"""Задача 2. Тест-кейсы 2.1–2.17: программа получает каталог и команды, печатает ответы.

Программа: python cache.py КАТАЛОГ [--size N] [--delay СЕК]; команды — из stdin.
"""
import random
import string

import pytest

from cache_model import expected
from course_program import assert_error, assert_output, run

PROGRAM = "cache.py"

CATALOG = {
    "SKU-1001": "Смартфон X-Pro, 128 ГБ, чёрный",
    "SKU-2045": "Наушники беспроводные SoundMax",
    "SKU-3300": "Чехол для смартфона силиконовый",
}


def catalog_text(catalog) -> str:
    return "".join(f"{k}; {v}\n" for k, v in catalog.items())


def session(commands, catalog=CATALOG, *options):
    return run(PROGRAM, "catalog.txt", *options, stdin="".join(c + "\n" for c in commands),
               files={"catalog.txt": catalog_text(catalog)})


def check(commands, catalog=CATALOG, size=None):
    options = ("--size", str(size)) if size else ()
    assert_output(session(commands, catalog, *options), expected(commands, catalog, size or 1000))


# ============================================================ 🟢 Типичные
@pytest.mark.category("typical")
@pytest.mark.parametrize("key", list(CATALOG))
def test_2_1_second_request_is_from_cache(key):
    """2.1 Первый запрос — из источника, второй — из кэша."""
    assert_output(session([f"get {key}", f"get {key}"]), f"""
        {key}: "{CATALOG[key]}" [из внешнего источника]
        {key}: "{CATALOG[key]}" [из кэша]
    """)


@pytest.mark.category("typical")
def test_2_1_source_is_slow_cache_is_fast():
    """2.1 С задержкой источника 0.2 с: один запрос — не быстрее 0.2 с, 20 одинаковых — почти столько же."""
    one = session(["get SKU-1001"], CATALOG, "--delay", "0.2")
    many = session(["get SKU-1001"] * 20, CATALOG, "--delay", "0.2")
    assert one.code == 0 and many.code == 0, one.err + many.err
    assert one.seconds >= 0.2, "источник должен «думать» --delay секунд"
    assert many.seconds < 0.6, f"20 запросов заняли {many.seconds:.2f} с — кэш не работает"


@pytest.mark.category("typical")
@pytest.mark.parametrize("key", ["SKU-9999", "нет-такого", "sku-1001"])
def test_2_3_missing_item_is_not_cached(key):
    """2.3 «Не найдено» — в кэш не сохраняется, каждый запрос идёт в источник."""
    check([f"get {key}", f"get {key}", f"get {key}", "list", "stats"])


# ============================================================ 🟡 Наивные
@pytest.mark.category("naive")
@pytest.mark.parametrize("count", [2, 10, 100])
def test_2_4_identical_requests(count):
    """2.4 N одинаковых запросов — все, кроме первого, из кэша."""
    check(["get SKU-2045"] * count + ["stats"])


@pytest.mark.category("naive")
@pytest.mark.parametrize("commands", [
    ["get SKU-1001", "get SKU-2045", "get SKU-1001", "list", "stats"],
    ["get SKU-1001", "get SKU-1001", "get SKU-3300", "get SKU-3300", "get SKU-1001", "list", "stats"],
])
def test_2_5_capacity_one(commands):
    """2.5 Лимит 1: каждая новая запись вытесняет предыдущую."""
    check(commands, size=1)


# ============================================================ 🔴 Краевые
@pytest.mark.category("edge")
@pytest.mark.parametrize("seed", [1, 2])
def test_2_7_many_keys_small_cache(seed):
    """2.7 100 000 разных ключей при лимите 100: кэш не растёт, работает быстро."""
    rng = random.Random(seed)
    catalog = {f"K{i}": f"товар {i}" for i in range(100_000)}
    order = list(catalog)
    rng.shuffle(order)
    commands = [f"get {k}" for k in order] + ["get " + order[-1], "list", "stats"]
    lines = [f'{k}: "{catalog[k]}" [из внешнего источника]' for k in order]
    lines += [f'{order[-1]}: "{catalog[order[-1]]}" [из кэша]',
              "Кэш (100 из 100): " + ", ".join(reversed(order[-100:])),
              "Статистика работы кэша:", "  Всего запросов: 100 001", "  Попаданий в кэш: 1 (0.0%)",
              "  Промахов (обращений к внешнему источнику): 100 000", "  Из них не найдено: 0",
              "  Размер кэша: 100 из 100", "  Вытеснено записей по стратегии LRU: 99 900"]
    result = session(commands, catalog, "--size", "100")
    assert_output(result, lines)
    assert result.seconds < 5, f"{result.seconds:.1f} с"


@pytest.mark.category("edge")
@pytest.mark.parametrize("keys", [
    ["ab", "ba"],
    ["SKU-12", "SKU-21"],
    ["abc", "acb", "bac", "bca", "cab", "cba"],
    ["Aa", "BB"],                                           # у Java-хэша строк одинаковый hashCode
    ["AaAa", "AaBB", "BBAa", "BBBB"],
])
def test_2_8_collisions(keys):
    """2.8 Ключи, которые совпадают у простых хэш-функций (анаграммы и т. п.), хранятся раздельно."""
    catalog = {k: f"значение {k}" for k in keys}
    check([f"get {k}" for k in keys] + [f"get {k}" for k in reversed(keys)] + [f"del {keys[0]}"]
          + [f"get {k}" for k in keys] + ["list"], catalog)


@pytest.mark.category("edge")
def test_2_10_evicted_key_goes_to_source_again():
    """2.10 Вытесненный ключ снова запрашивается у источника."""
    check(["get SKU-1001", "get SKU-2045", "get SKU-3300", "get SKU-1001", "get SKU-1001", "stats"], size=2)


# ============================================================ ❌ Формат


@pytest.mark.category("format")
@pytest.mark.parametrize("length", [1000, 10_000])
def test_2_12_very_long_key(length):
    """2.12 Очень длинный ключ работает."""
    key = "K" * length
    check([f"get {key}", f"get {key}", f"put {key}x; другое", "list"], {key: "длинный"})


@pytest.mark.category("format")
@pytest.mark.parametrize("key", ["SKU/1001", "товар №5", "a b  c", "!@#$%^&*()", "ключ\tс табуляцией",
                                 "😀🎉", "SELECT * FROM t"])
def test_2_13_special_characters(key):
    """2.13 Ключи со спецсимволами и пробелами внутри — обычные ключи."""
    check([f"get {key}", f"get {key}", "list"], {key: "особый товар", "other": "другой"})


@pytest.mark.category("format")
@pytest.mark.parametrize("size", ["0", "-1", "-100", "abc", "2.5", ""])
def test_2_14_bad_capacity(size):
    """2.14 Лимит 0, отрицательный или не число — ошибка запуска (код 2)."""
    result = run(PROGRAM, "catalog.txt", "--size", size, stdin="get SKU-1001\n",
                 files={"catalog.txt": catalog_text(CATALOG)})
    assert_error(result, code=2)


# ============================================================ 🎲 Фаззинг
def random_commands(rng, keys, count):
    commands = []
    for _ in range(count):
        roll = rng.random()
        key = rng.choice(keys)
        if roll < 0.7:
            commands.append(f"get {key}")
        elif roll < 0.8:
            commands.append(f"put {key}; новое {rng.randint(1, 99)}")
        elif roll < 0.9:
            commands.append(f"del {key}")
        elif roll < 0.95:
            commands.append("list")
        else:
            commands.append("stats")
    return commands + ["list", "stats"]


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_2_15_random_requests(seed):
    """2.15 10 000 случайных запросов: лимит соблюдается, ответы и статистика сходятся с моделью."""
    rng = random.Random(seed)
    catalog = {f"SKU-{i}": f"товар {i}" for i in range(300)}
    keys = list(catalog) + [f"нет-{i}" for i in range(30)]
    commands = [f"get {rng.choice(keys)}" for _ in range(10_000)] + ["list", "stats"]
    check(commands, catalog, size=rng.choice([1, 10, 50, 200]))


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [21, 22, 23])
def test_2_17_mixed_operations_keep_cache_consistent(seed):
    """2.17 Случайные запросы, обновления и удаления: всё совпадает с простой моделью LRU."""
    rng = random.Random(seed)
    catalog = {f"K{i}": f"товар {i}" for i in range(40)}
    keys = list(catalog) + ["нет-1", "нет-2"]
    check(random_commands(rng, keys, 3000), catalog, size=rng.choice([1, 3, 10, 30]))
