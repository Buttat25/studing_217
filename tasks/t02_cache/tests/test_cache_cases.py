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


@pytest.mark.category("typical")
@pytest.mark.parametrize("key", list(CATALOG))
def test_2_1_second_request_is_from_cache(key):
    assert_output(session([f"get {key}", f"get {key}", "list"]), f"""
        {key}: "{CATALOG[key]}"
        {key}: "{CATALOG[key]}"
        Список (1 из 1 000): {key}
    """)


@pytest.mark.category("typical")
def test_2_1_source_is_slow_cache_is_fast():
    one = session(["get SKU-1001"], CATALOG, "--delay", "0.2")
    many = session(["get SKU-1001"] * 20, CATALOG, "--delay", "0.2")
    assert one.code == 0 and many.code == 0, one.err + many.err
    assert one.seconds >= 0.2, "источник должен «думать» --delay секунд"
    assert many.seconds < 0.6, f"20 запросов заняли {many.seconds:.2f} с - кэш не работает"


@pytest.mark.category("typical")
def test_2_1_cached_value_is_returned_without_source():
    check(["get SKU-1001", "put SKU-1001; версия из кэша", "get SKU-1001", "del SKU-1001", "get SKU-1001",
           "list"])


@pytest.mark.category("typical")
@pytest.mark.parametrize("key", ["SKU-9999", "нет-такого", "sku-1001"])
def test_2_3_missing_item_is_not_cached(key):
    check([f"get {key}", f"get {key}", f"get {key}", "list"])


@pytest.mark.category("naive")
@pytest.mark.parametrize("count", [2, 10, 100])
def test_2_4_identical_requests(count):
    check(["get SKU-2045"] * count + ["list"])


@pytest.mark.category("naive")
@pytest.mark.parametrize("commands", [
    ["get SKU-1001", "get SKU-2045", "list", "get SKU-1001", "list"],
    ["get SKU-1001", "get SKU-1001", "get SKU-3300", "get SKU-3300", "list", "put X; икс", "get SKU-1001", "list"],
])
def test_2_5_capacity_one(commands):
    check(commands, size=1)


@pytest.mark.category("edge")
@pytest.mark.parametrize("seed", [1, 2])
def test_2_7_many_keys_small_cache(seed):
    rng = random.Random(seed)
    catalog = {f"K{i}": f"товар {i}" for i in range(100_000)}
    order = list(catalog)
    rng.shuffle(order)
    commands = [f"get {k}" for k in order] + ["get " + order[-1], "get " + order[0], "list"]
    lines = [f'{k}: "{catalog[k]}"' for k in order]
    lines += [f'{order[-1]}: "{catalog[order[-1]]}"', f'{order[0]}: "{catalog[order[0]]}"']
    lines.append("Список (100 из 100): " + ", ".join([order[0], order[-1]] + order[-99:-1][::-1]))
    result = session(commands, catalog, "--size", "100")
    assert_output(result, lines)
    assert result.seconds < 5, f"{result.seconds:.1f} с"


@pytest.mark.category("edge")
@pytest.mark.parametrize("keys", [
    ["ab", "ba"],
    ["SKU-12", "SKU-21"],
    ["abc", "acb", "bac", "bca", "cab", "cba"],
    ["Aa", "BB"],
    ["AaAa", "AaBB", "BBAa", "BBBB"],
])
def test_2_8_collisions(keys):
    catalog = {k: f"значение {k}" for k in keys}
    check([f"get {k}" for k in keys] + [f"get {k}" for k in reversed(keys)] + [f"del {keys[0]}"]
          + [f"get {k}" for k in keys] + ["list"], catalog)


@pytest.mark.category("edge")
def test_2_10_evicted_key_goes_to_source_again():
    check(["put SKU-1001; из кэша", "get SKU-2045", "get SKU-3300", "get SKU-1001", "get SKU-1001", "list"],
          size=2)


@pytest.mark.category("format")
@pytest.mark.parametrize("length", [1000, 10_000])
def test_2_12_very_long_key(length):
    key = "K" * length
    check([f"get {key}", f"get {key}", f"put {key}x; другое", "list"], {key: "длинный"})


@pytest.mark.category("format")
@pytest.mark.parametrize("key", ["SKU/1001", "товар №5", "a b  c", "!@#$%^&*()", "ключ\tс табуляцией",
                                 "😀🎉", "SELECT * FROM t"])
def test_2_13_special_characters(key):
    check([f"get {key}", f"get {key}", "list"], {key: "особый товар", "other": "другой"})


@pytest.mark.category("format")
@pytest.mark.parametrize("command", ["  get SKU-1001", "get SKU-1001   ", "get   SKU-1001", "list   "])
def test_2_13_spaces_around_command(command):
    result = session(["get SKU-1001", command])
    assert result.code == 0 and result.lines[1].startswith(("SKU-1001: ", "Список (1 из 1 000)")), result.out
    assert "ОШИБКА" not in result.out


@pytest.mark.category("format")
@pytest.mark.parametrize("size", ["0", "-1", "-100", "abc", "2.5", ""])
def test_2_14_bad_capacity(size):
    result = run(PROGRAM, "catalog.txt", "--size", size, stdin="get SKU-1001\n",
                 files={"catalog.txt": catalog_text(CATALOG)})
    assert_error(result, code=2)


def random_commands(rng, keys, count):
    commands = []
    for _ in range(count):
        roll = rng.random()
        key = rng.choice(keys)
        if roll < 0.7:
            commands.append(f"get {key}")
        elif roll < 0.8:
            commands.append(f"put {key}; новое {rng.randint(1, 99)}")
        elif roll < 0.95:
            commands.append(f"del {key}")
        else:
            commands.append("list")
    return commands + ["list"]


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_2_15_random_requests(seed):
    rng = random.Random(seed)
    catalog = {f"SKU-{i}": f"товар {i}" for i in range(300)}
    keys = list(catalog) + [f"нет-{i}" for i in range(30)]
    commands = [f"get {rng.choice(keys)}" for _ in range(10_000)] + ["list"]
    check(commands, catalog, size=rng.choice([1, 10, 50, 200]))


@pytest.mark.category("fuzz")
@pytest.mark.parametrize("seed", [21, 22, 23])
def test_2_17_mixed_operations_keep_cache_consistent(seed):
    rng = random.Random(seed)
    catalog = {f"K{i}": f"товар {i}" for i in range(40)}
    keys = list(catalog) + ["нет-1", "нет-2"]
    check(random_commands(rng, keys, 3000), catalog, size=rng.choice([1, 3, 10, 30]))
