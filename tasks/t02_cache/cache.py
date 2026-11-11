import sys
import os
import time


class Node:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None
        self.hash_next = None


class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.size = 0
        self.buckets_count = max(16, capacity * 2)
        self.buckets = [None] * self.buckets_count
        self.head = Node(None, None)
        self.tail = Node(None, None)
        self.head.next = self.tail
        self.tail.prev = self.head

    def _hash(self, key):
        h = 5381
        for ch in key:
            h = ((h << 5) + h) + ord(ch)
        return h % self.buckets_count

    def _find_node(self, key):
        idx = self._hash(key)
        curr = self.buckets[idx]
        while curr is not None:
            if curr.key == key:
                return curr
            curr = curr.hash_next
        return None

    def _add_to_front(self, node):
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def _remove_from_list(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _remove_from_bucket(self, node):
        idx = self._hash(node.key)
        curr = self.buckets[idx]
        prev = None
        while curr is not None:
            if curr is node:
                if prev is None:
                    self.buckets[idx] = curr.hash_next
                else:
                    prev.hash_next = curr.hash_next
                return
            prev = curr
            curr = curr.hash_next

    def get(self, key):
        node = self._find_node(key)
        if node is None:
            return None
        self._remove_from_list(node)
        self._add_to_front(node)
        return node.value

    def put(self, key, value):
        node = self._find_node(key)
        if node is not None:
            node.value = value
            self._remove_from_list(node)
            self._add_to_front(node)
            return

        if self.size >= self.capacity:
            oldest = self.tail.prev
            self._remove_from_list(oldest)
            self._remove_from_bucket(oldest)
            self.size -= 1

        new_node = Node(key, value)
        idx = self._hash(key)
        new_node.hash_next = self.buckets[idx]
        self.buckets[idx] = new_node
        self._add_to_front(new_node)
        self.size += 1

    def delete(self, key):
        node = self._find_node(key)
        if node is None:
            return False
        self._remove_from_list(node)
        self._remove_from_bucket(node)
        self.size -= 1
        return True

    def get_keys_fresh_to_old(self):
        keys = []
        curr = self.head.next
        while curr is not self.tail:
            keys.append(curr.key)
            curr = curr.next
        return keys


def format_number(num):
    return f"{num:,}".replace(",", " ")


def parse_args():
    if len(sys.argv) < 2:
        print("Ошибка: не указаны аргументы", file=sys.stderr)
        sys.exit(2)

    catalog_file = None
    cache_size = 1000
    delay = 0.0

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--size':
            if i + 1 >= len(args):
                print("Ошибка: не указано значение --size", file=sys.stderr)
                sys.exit(2)
            val = args[i + 1]
            try:
                s_val = int(val)
                if s_val <= 0:
                    raise ValueError
            except ValueError:
                print(f"Ошибка: некорректное значение --size '{val}'", file=sys.stderr)
                sys.exit(2)
            cache_size = s_val
            i += 2
        elif args[i] == '--delay':
            if i + 1 >= len(args):
                print("Ошибка: не указано значение --delay", file=sys.stderr)
                sys.exit(2)
            val = args[i + 1]
            try:
                d_val = float(val)
                if d_val < 0:
                    raise ValueError
            except ValueError:
                print(f"Ошибка: некорректное значение --delay '{val}'", file=sys.stderr)
                sys.exit(2)
            delay = d_val
            i += 2
        else:
            if args[i].startswith('-'):
                print(f"Ошибка: неизвестный параметр '{args[i]}'", file=sys.stderr)
                sys.exit(2)
            if catalog_file is not None:
                print("Ошибка: избыточные аргументы командной строки", file=sys.stderr)
                sys.exit(2)
            catalog_file = args[i]
            i += 1

    if catalog_file is None:
        print("Ошибка: не указан файл каталога", file=sys.stderr)
        sys.exit(2)

    return catalog_file, cache_size, delay


def load_catalog(catalog_file):
    entries = []
    with open(catalog_file, 'r', encoding='utf-8-sig') as f:
        for cat_line in f:
            if ';' in cat_line:
                c_art, c_prod = cat_line.split(';', 1)
                c_art = c_art.strip()
                if c_art:
                    entries.append((c_art, c_prod.strip()))
    entries.sort(key=lambda item: item[0])
    unique_entries = []
    for item in entries:
        if not unique_entries or unique_entries[-1][0] != item[0]:
            unique_entries.append(item)
    return unique_entries


def find_in_catalog(catalog_entries, key):
    left = 0
    right = len(catalog_entries) - 1
    while left <= right:
        mid = (left + right) // 2
        mid_key = catalog_entries[mid][0]
        if mid_key == key:
            return catalog_entries[mid][1]
        elif mid_key < key:
            left = mid + 1
        else:
            right = mid - 1
    return None


def main():
    catalog_file, cache_size, delay = parse_args()

    if not os.path.exists(catalog_file):
        print(f"Ошибка: файл '{catalog_file}' не найден", file=sys.stderr)
        sys.exit(1)

    catalog_entries = load_catalog(catalog_file)
    cache = LRUCache(cache_size)

    for line in sys.stdin:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        parts = line_stripped.split(None, 1)
        cmd = parts[0]
        args_str = parts[1].strip() if len(parts) > 1 else ""

        if cmd == 'get':
            artikul = args_str
            if not artikul:
                print("ОШИБКА: пустой артикул")
                continue

            cached_val = cache.get(artikul)
            if cached_val is not None:
                print(f"{artikul}: \"{cached_val}\"")
            else:
                if delay > 0:
                    time.sleep(delay)

                found_product = find_in_catalog(catalog_entries, artikul)
                if found_product is not None:
                    print(f"{artikul}: \"{found_product}\"")
                    cache.put(artikul, found_product)
                else:
                    print(f"{artikul}: [товар не найден]")

        elif cmd == 'put':
            if ';' not in args_str:
                print("ОШИБКА: неверный формат put")
                continue
            artikul, product = args_str.split(';', 1)
            artikul = artikul.strip()
            product = product.strip()

            if not artikul or not product:
                print("ОШИБКА: пустой артикул или название товара")
                continue

            cache.put(artikul, product)
            print(f"{artikul}: сохранено")

        elif cmd == 'del':
            artikul = args_str
            if not artikul:
                print("ОШИБКА: пустой артикул")
                continue
            if cache.delete(artikul):
                print(f"{artikul}: удалено")
            else:
                print(f"{artikul}: не найдено в кэше")

        elif cmd == 'list':
            if args_str:
                print("ОШИБКА: команда list не принимает аргументы")
                continue
            size_fmt = format_number(cache.size)
            limit_fmt = format_number(cache_size)
            if cache.size == 0:
                print(f"Список ({size_fmt} из {limit_fmt}): пусто")
            else:
                keys = cache.get_keys_fresh_to_old()
                print(f"Список ({size_fmt} из {limit_fmt}): {', '.join(keys)}")
        else:
            print(f"ОШИБКА: неизвестная команда '{cmd}'")


if __name__ == "__main__":
    main()
