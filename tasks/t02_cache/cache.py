import sys
import os
import time

def format_number(num):
    return f"{num:,}".replace(",", " ")

def parse_args():
    if len(sys.argv) < 2:
        print("Ошибка: не указан файл каталога", file=sys.stderr)
        sys.exit(1)
    catalog_file, cache_size, delay = None, 1000, 0.0
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--size':
            cache_size = int(args[i+1]); i += 2
        elif args[i] == '--delay':
            delay = float(args[i+1]); i += 2
        else:
            catalog_file = args[i]; i += 1
    if catalog_file is None:
        print("Ошибка: не указан файл каталога", file=sys.stderr)
        sys.exit(1)
    return catalog_file, cache_size, delay

def main():
    catalog_file, cache_size, delay = parse_args()
    if not os.path.exists(catalog_file):
        print(f"Ошибка: файл '{catalog_file}' не найден", file=sys.stderr)
        sys.exit(1)

    TABLE_SIZE = cache_size * 3
    hash_keys = [None] * TABLE_SIZE
    hash_vals = [None] * TABLE_SIZE
    
    lru_order = []
    current_size = 0

    def get_hash(key_str):
        h = 0
        for char in key_str:
            h = (h * 31 + ord(char)) % TABLE_SIZE
        return h

    def hash_store(key, value):
        nonlocal current_size
        idx = get_hash(key)
        start_idx = idx
        while hash_keys[idx] is not None and hash_keys[idx] != key:
            idx = (idx + 1) % TABLE_SIZE
            if idx == start_idx:
                return False
        if hash_keys[idx] is None:
            current_size += 1
        hash_keys[idx] = key
        hash_vals[idx] = value
        return True

    def hash_get(key):
        idx = get_hash(key)
        start_idx = idx
        while hash_keys[idx] is not None:
            if hash_keys[idx] == key:
                return hash_vals[idx]
            idx = (idx + 1) % TABLE_SIZE
            if idx == start_idx:
                break
        return None

    def hash_delete(key):
        nonlocal current_size
        idx = get_hash(key)
        start_idx = idx
        while hash_keys[idx] is not None:
            if hash_keys[idx] == key:
                hash_keys[idx] = None
                hash_vals[idx] = None
                current_size -= 1
                next_idx = (idx + 1) % TABLE_SIZE
                while hash_keys[next_idx] is not None:
                    k_re, v_re = hash_keys[next_idx], hash_vals[next_idx]
                    hash_keys[next_idx] = None
                    hash_vals[next_idx] = None
                    current_size -= 1
                    hash_store(k_re, v_re)
                    next_idx = (next_idx + 1) % TABLE_SIZE
                return True
            idx = (idx + 1) % TABLE_SIZE
            if idx == start_idx:
                break
        return False

    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
        except Exception: break
        line_stripped = line.strip()
        if not line_stripped: continue
        
        if ' ' in line_stripped:
            cmd, args_str = line_stripped.split(' ', 1)
            cmd = cmd.strip().lower()
            args_str = args_str.strip()
        else:
            cmd = line_stripped.lower(); args_str = ""

        if cmd == 'get':
            artikul = args_str
            if not artikul: continue
            cached_val = hash_get(artikul)
            if cached_val is not None:
                print(f"{artikul}: \"{cached_val}\"")
                lru_order.remove(artikul); lru_order.append(artikul)
            else:
                if delay > 0: time.sleep(delay)
                found_product = None
                with open(catalog_file, 'r', encoding='utf-8-sig') as f:
                    for cat_line in f:
                        if ';' in cat_line:
                            c_art, c_prod = cat_line.split(';', 1)
                            if c_art.strip() == artikul:
                                found_product = c_prod.strip(); break
                if found_product is not None:
                    print(f"{artikul}: \"{found_product}\"")
                    if current_size >= cache_size:
                        oldest = lru_order.pop(0)
                        hash_delete(oldest)
                    hash_store(artikul, found_product)
                    lru_order.append(artikul)
                else:
                    print(f"{artikul}: [товар не найден]")

        elif cmd == 'put':
            if ';' not in args_str: continue
            artikul, product = args_str.split(';', 1)
            artikul, product = artikul.strip(), product.strip()
            if not artikul: continue
            
            if hash_get(artikul) is not None:
                lru_order.remove(artikul)
            elif current_size >= cache_size:
                oldest = lru_order.pop(0)
                hash_delete(oldest)
            hash_store(artikul, product)
            lru_order.append(artikul)
            print(f"{artikul}: сохранено")

        elif cmd == 'del':
            artikul = args_str
            if not artikul: continue
            if hash_get(artikul) is not None:
                hash_delete(artikul)
                lru_order.remove(artikul)
                print(f"{artikul}: удалено")
            else:
                print(f"{artikul}: не найдено в кэше")

        elif cmd == 'list':
            size_fmt = format_number(current_size)
            limit_fmt = format_number(cache_size)
            if current_size == 0:
                print(f"Список ({size_fmt} из {limit_fmt}): пусто")
            else:
                print(f"Список ({size_fmt} из {limit_fmt}): {', '.join(list(reversed(lru_order)))}")

if __name__ == "__main__":
    main()
