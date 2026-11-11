import sys
import os
import time

def format_number(num):
    """Форматирует числа от 1000 с пробелом между разрядами (например, 1 000)"""
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
            val = args[i+1]
            if not val.isdigit() or int(val) <= 0:
                print(f"Ошибка: некорректное значение --size '{val}'", file=sys.stderr)
                sys.exit(2)
            cache_size = int(val)
            i += 2
        elif args[i] == '--delay':
            if i + 1 >= len(args):
                print("Ошибка: не указано значение --delay", file=sys.stderr)
                sys.exit(2)
            val = args[i+1]
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
            if args[i].startswith('--'):
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

def main():
    catalog_file, cache_size, delay = parse_args()
    
    if not os.path.exists(catalog_file):
        print(f"Ошибка: файл '{catalog_file}' не найден", file=sys.stderr)
        sys.exit(1)

    cache = {} 
    lru_order = [] 

    # Классический построчный ввод через sys.stdin, который никогда не виснет в тестах
    for line in sys.stdin:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        if ' ' in line_stripped:
            cmd, args_str = line_stripped.split(' ', 1)
            cmd = cmd.strip().lower()
            args_str = args_str.strip()
        else:
            cmd = line_stripped.lower()
            args_str = ""

        if cmd == 'get':
            artikul = args_str
            if not artikul:
                print("ОШИБКА: пустой артикул", file=sys.stderr)
                continue
                
            if artikul in cache:
                print(f"{artikul}: \"{cache[artikul]}\"")
                lru_order.remove(artikul)
                lru_order.append(artikul)
            else:
                if delay > 0:
                    time.sleep(delay)
                    
                found_product = None
                with open(catalog_file, 'r', encoding='utf-8-sig') as f:
                    for cat_line in f:
                        if ';' in cat_line:
                            c_art, c_prod = cat_line.split(';', 1)
                            if c_art.strip() == artikul:
                                found_product = c_prod.strip()
                                break
                                
                if found_product is not None:
                    print(f"{artikul}: \"{found_product}\"")
                    if len(cache) >= cache_size:
                        oldest = lru_order.pop(0)
                        del cache[oldest]
                    cache[artikul] = found_product
                    lru_order.append(artikul)
                else:
                    print(f"{artikul}: [товар не найден]")

        elif cmd == 'put':
            if ';' not in args_str:
                print("ОШИБКА: неверный формат put", file=sys.stderr)
                continue
            artikul, product = args_str.split(';', 1)
            artikul = artikul.strip()
            product = product.strip()
            
            if not artikul:
                print("ОШИБКА: пустой артикул", file=sys.stderr)
                continue
                
            if artikul in cache:
                lru_order.remove(artikul)
            elif len(cache) >= cache_size:
                oldest = lru_order.pop(0)
                del cache[oldest]
                
            cache[artikul] = product
            lru_order.append(artikul)
            print(f"{artikul}: сохранено")

        elif cmd == 'del':
            artikul = args_str
            if not artikul:
                print("ОШИБКА: пустой артикул", file=sys.stderr)
                continue
            if artikul in cache:
                del cache[artikul]
                lru_order.remove(artikul)
                print(f"{artikul}: удалено")
            else:
                print(f"{artikul}: … не найдено")

        elif cmd == 'list':
            size_fmt = format_number(len(cache))
            limit_fmt = format_number(cache_size)
            if not cache:
                print(f"Список ({size_fmt} из {limit_fmt}): пусто")
            else:
                reversed_order = list(reversed(lru_order))
                print(f"Список ({size_fmt} из {limit_fmt}): {', '.join(reversed_order)}")
        else:
            print(f"ОШИБКА: неизвестная команда '{cmd}'", file=sys.stderr)

if __name__ == "__main__":
    main()
