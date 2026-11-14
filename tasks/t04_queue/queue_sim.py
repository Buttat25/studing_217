import sys
import heapq
import random
from collections import deque


def format_num(n):
    return f"{n:,}".replace(",", " ")


def plural_people(n):
    n_abs = abs(n)
    if 11 <= (n_abs % 100) <= 19:
        return "человек"
    rem = n_abs % 10
    if rem == 1:
        return "человек"
    if 2 <= rem <= 4:
        return "человека"
    return "человек"


def plural_customers(n):
    n_abs = abs(n)
    if 11 <= (n_abs % 100) <= 19:
        return "покупателей"
    rem = n_abs % 10
    if rem == 1:
        return "покупателя"
    return "покупателей"


def cli_error(msg):
    print(f"Ошибка: {msg}", file=sys.stderr)
    sys.exit(2)


def input_error(line_no, msg):
    print(f"Ошибка: строка {line_no} - {msg}", file=sys.stderr)
    sys.exit(1)


def parse_args(argv):
    cashiers = 3
    max_queue = 10
    close_time = None
    seed = None
    minutes = 720.0
    interval = 0.5
    service_min = 2.0
    service_max = 5.0

    has_close = False
    has_minutes = False
    has_interval = False
    has_service = False

    seen_flags = set()

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in seen_flags:
            cli_error(f"повторяющийся параметр '{arg}'")
        seen_flags.add(arg)

        if arg == '--cashiers':
            if i + 1 >= len(argv):
                cli_error("не указано значение для --cashiers")
            try:
                val = int(argv[i + 1])
            except ValueError:
                cli_error("некорректное число кассиров")
            if val < 0:
                cli_error("число кассиров не может быть отрицательным")
            cashiers = val
            i += 2
        elif arg == '--max-queue':
            if i + 1 >= len(argv):
                cli_error("не указано значение для --max-queue")
            val_str = argv[i + 1]
            if val_str.lower() == 'none':
                max_queue = None
            else:
                try:
                    val = int(val_str)
                except ValueError:
                    cli_error("некорректная максимальная длина очереди")
                if val < 0:
                    cli_error("максимальная длина очереди не может быть отрицательной")
                max_queue = val
            i += 2
        elif arg == '--close':
            if i + 1 >= len(argv):
                cli_error("не указано значение для --close")
            try:
                val = float(argv[i + 1])
            except ValueError:
                cli_error("некорректное время закрытия")
            if val < 0 or val != val or val == float('inf'):
                cli_error("недопустимое время закрытия")
            close_time = val
            has_close = True
            i += 2
        elif arg == '--seed':
            if i + 1 >= len(argv):
                cli_error("не указано значение для --seed")
            try:
                seed = int(argv[i + 1])
            except ValueError:
                cli_error("некорректное зерно генератора")
            i += 2
        elif arg == '--minutes':
            if i + 1 >= len(argv):
                cli_error("не указано значение для --minutes")
            try:
                val = float(argv[i + 1])
            except ValueError:
                cli_error("некорректная длительность работы")
            if val < 0 or val != val or val == float('inf'):
                cli_error("длительность работы не может быть отрицательной")
            minutes = val
            has_minutes = True
            i += 2
        elif arg == '--interval':
            if i + 1 >= len(argv):
                cli_error("не указано значение для --interval")
            try:
                val = float(argv[i + 1])
            except ValueError:
                cli_error("некорректный средний интервал")
            if val <= 0 or val != val or val == float('inf'):
                cli_error("средний интервал должен быть положительным")
            interval = val
            has_interval = True
            i += 2
        elif arg == '--service':
            if i + 1 >= len(argv):
                cli_error("не указано значение для --service")
            parts = argv[i + 1].split('-')
            if len(parts) != 2:
                cli_error("неверный формат интервала обслуживания")
            try:
                s_min = float(parts[0])
                s_max = float(parts[1])
            except ValueError:
                cli_error("некорректные числа в интервале обслуживания")
            if s_min <= 0 or s_max < s_min or s_min != s_min or s_max != s_max or s_max == float('inf'):
                cli_error("время обслуживания должно быть положительным")
            service_min = s_min
            service_max = s_max
            has_service = True
            i += 2
        else:
            cli_error(f"неизвестный параметр '{arg}'")

    if seed is None:
        if has_minutes or has_interval or has_service:
            cli_error("параметры генерации доступны только с --seed")
    else:
        if has_close:
            cli_error("параметр --close несовместим с режимом --seed")

    return {
        'cashiers': cashiers,
        'max_queue': max_queue,
        'close_time': close_time,
        'seed': seed,
        'minutes': minutes,
        'interval': interval,
        'service_min': service_min,
        'service_max': service_max,
    }


def read_customers_stdin():
    customers = []
    idx = 0
    for line_no, raw_line in enumerate(sys.stdin, start=1):
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) != 2:
            input_error(line_no, "ожидаются два числа (время прихода и обслуживания)")
        try:
            arr = float(parts[0])
            srv = float(parts[1])
        except ValueError:
            input_error(line_no, "некорректное числовое значение")
        if arr < 0 or srv <= 0 or arr != arr or srv != srv or arr == float('inf') or srv == float('inf'):
            input_error(line_no, "время прихода должно быть >= 0, время обслуживания > 0")
        customers.append((arr, idx, srv))
        idx += 1
    customers.sort(key=lambda x: (x[0], x[1]))
    return customers


def generate_customers(seed, minutes, interval, service_min, service_max):
    rng = random.Random(seed)
    customers = []
    t = 0.0
    idx = 0
    while True:
        dt = rng.expovariate(1.0 / interval)
        t += dt
        if t >= minutes:
            break
        srv = rng.uniform(service_min, service_max)
        customers.append((t, idx, srv))
        idx += 1
    return customers


def simulate(customers, cashiers, max_queue, close_time):
    total_arrived = 0
    served_count = 0
    left_count = 0

    wait_sum = 0.0
    max_wait = 0.0
    min_wait = None

    max_q_len = 0
    total_service_time = 0.0

    cashier_served = [0] * cashiers
    cashier_busy_time = [0.0] * cashiers
    last_service_end = 0.0

    free_cashiers = list(range(cashiers))
    heapq.heapify(free_cashiers)

    departures = []
    queue = deque()

    def process_departures_until(limit_time):
        nonlocal served_count, wait_sum, max_wait, min_wait, total_service_time, last_service_end
        while departures and departures[0][0] <= limit_time:
            t_end, c_id = heapq.heappop(departures)
            if queue:
                arr_t, srv_t = queue.popleft()
                w = t_end - arr_t
                if w < 0.0:
                    w = 0.0
                wait_sum += w
                if w > max_wait:
                    max_wait = w
                if min_wait is None or w < min_wait:
                    min_wait = w

                served_count += 1
                total_service_time += srv_t
                cashier_served[c_id] += 1
                cashier_busy_time[c_id] += srv_t

                finish_t = t_end + srv_t
                if finish_t > last_service_end:
                    last_service_end = finish_t
                heapq.heappush(departures, (finish_t, c_id))
            else:
                heapq.heappush(free_cashiers, c_id)

    for arr_t, _, srv_t in customers:
        if close_time is not None and arr_t >= close_time:
            continue

        process_departures_until(arr_t)
        total_arrived += 1

        if free_cashiers:
            c_id = heapq.heappop(free_cashiers)
            if min_wait is None or 0.0 < min_wait:
                min_wait = 0.0
            served_count += 1
            total_service_time += srv_t
            cashier_served[c_id] += 1
            cashier_busy_time[c_id] += srv_t

            finish_t = arr_t + srv_t
            if finish_t > last_service_end:
                last_service_end = finish_t
            heapq.heappush(departures, (finish_t, c_id))
        else:
            if cashiers == 0 or (max_queue is not None and len(queue) >= max_queue):
                left_count += 1
            else:
                queue.append((arr_t, srv_t))
                if len(queue) > max_q_len:
                    max_q_len = len(queue)

    process_departures_until(float('inf'))

    if served_count > 0:
        avg_wait = wait_sum / served_count
        avg_service = total_service_time / served_count
        min_w_val = min_wait if min_wait is not None else 0.0
        max_w_val = max_wait
    else:
        avg_wait = 0.0
        avg_service = 0.0
        min_w_val = 0.0
        max_w_val = 0.0

    if close_time is not None:
        work_duration = max(close_time, last_service_end)
    else:
        work_duration = last_service_end

    cashier_stats = []
    for c_id in range(cashiers):
        if work_duration > 0.0:
            load_pct = (cashier_busy_time[c_id] / work_duration) * 100.0
        else:
            load_pct = 0.0
        cashier_stats.append((c_id + 1, cashier_served[c_id], load_pct))

    return {
        'total_arrived': total_arrived,
        'served_count': served_count,
        'left_count': left_count,
        'avg_wait': avg_wait,
        'max_wait': max_w_val,
        'min_wait': min_w_val,
        'max_q_len': max_q_len,
        'avg_service': avg_service,
        'cashier_stats': cashier_stats,
    }


def main():
    cfg = parse_args(sys.argv[1:])

    if cfg['seed'] is not None:
        customers = generate_customers(
            cfg['seed'],
            cfg['minutes'],
            cfg['interval'],
            cfg['service_min'],
            cfg['service_max'],
        )
        eff_close = cfg['minutes']
    else:
        customers = read_customers_stdin()
        eff_close = cfg['close_time']

    res = simulate(customers, cfg['cashiers'], cfg['max_queue'], eff_close)

    if cfg['seed'] is not None:
        print(f"Результаты симуляции (семя: {cfg['seed']}):")
    else:
        print("Результаты симуляции:")

    print("")
    print("Общая статистика:")
    print(f"  Всего пришло покупателей: {format_num(res['total_arrived'])}")
    print(f"  Обслужено покупателей: {format_num(res['served_count'])}")
    print(f"  Ушло из-за длинной очереди: {format_num(res['left_count'])}")
    print("")
    print("Время ожидания:")
    print(f"  Среднее время ожидания: {res['avg_wait']:.1f} мин")
    print(f"  Максимальное время ожидания: {res['max_wait']:.1f} мин")
    print(f"  Минимальное время ожидания: {res['min_wait']:.1f} мин")
    print("")
    print("Очередь:")
    print(f"  Максимальная длина очереди: {format_num(res['max_q_len'])} {plural_people(res['max_q_len'])}")
    print(f"  Среднее время обслуживания: {res['avg_service']:.1f} мин на покупателя")
    print("")
    print("Загрузка кассиров:")
    if not res['cashier_stats']:
        print("  кассиров нет")
    else:
        for num, cnt, load_pct in res['cashier_stats']:
            print(f"  Кассир {num}: обслужил {format_num(cnt)} {plural_customers(cnt)}, загрузка {load_pct:.0f}%")


if __name__ == "__main__":
    main()

