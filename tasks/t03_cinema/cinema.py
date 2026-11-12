import sys
import os


def time_to_minutes(t_str):
    if ':' not in t_str:
        return None
    parts = t_str.split(':')
    if len(parts) != 2:
        return None
    h_str, m_str = parts[0], parts[1]
    if len(h_str) != 2 or len(m_str) != 2:
        return None
    if not (h_str.isdigit() and m_str.isdigit()):
        return None
    h, m = int(h_str), int(m_str)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h * 60 + m


def minutes_to_time(mins):
    h = (mins // 60) % 24
    m = mins % 60
    return f"{h:02d}:{m:02d}"


def load_hall(filename):
    if not os.path.exists(filename):
        print(f"Ошибка: файл '{filename}' не найден", file=sys.stderr)
        sys.exit(1)

    with open(filename, 'r', encoding='utf-8-sig') as f:
        raw_lines = f.read().splitlines()

    hall = []
    has_seats = False
    for line_num, line in enumerate(raw_lines, start=1):
        cleaned = line.strip()
        if not cleaned:
            continue
        row = []
        for ch in cleaned:
            if ch in ('o', 'V', 'D', '.'):
                row.append(ch)
                if ch != '.':
                    has_seats = True
            else:
                print(f"Ошибка: недопустимый символ '{ch}' (ряд {line_num}) в схеме зала", file=sys.stderr)
                sys.exit(1)
        hall.append(row)

    if not hall or not has_seats:
        print("Ошибка: пустой файл зала или отсутствуют места", file=sys.stderr)
        sys.exit(1)

    return hall


def update_expirations(bookings, current_time):
    for b in bookings:
        if b['status'] == 'active':
            exp_time = b['created_at'] + 10
            if current_time >= exp_time:
                b['status'] = 'expired'
                b['status_time'] = exp_time


def is_seat_occupied(bookings, session_name, row, seat):
    for b in bookings:
        if b['session'] == session_name and b['row'] == row and b['seat'] == seat:
            if b['status'] in ('active', 'paid'):
                return True
    return False


def main():
    if len(sys.argv) != 2:
        print("Ошибка: укажите один файл схемы зала", file=sys.stderr)
        sys.exit(2)

    hall = load_hall(sys.argv[1])
    num_rows = len(hall)
    max_cols = max(len(r) for r in hall)

    prices = {'o': 300, 'V': 600, 'D': 300}

    current_time = 0
    sessions = {}
    bookings = []

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(None, 1)
        cmd = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

        if cmd != cmd.lower():
            print(f"ОШИБКА: неизвестная команда '{cmd}'")
            continue

        if cmd == 'time':
            t_str = rest.strip()
            new_mins = time_to_minutes(t_str)
            if new_mins is None:
                print("ОШИБКА: некорректный формат времени")
                continue
            if new_mins < current_time:
                print("ОШИБКА: время не может идти назад")
                continue
            current_time = new_mins
            update_expirations(bookings, current_time)
            print(f"Время: {minutes_to_time(current_time)}")

        elif cmd == 'session':
            s_parts = rest.split()
            if len(s_parts) not in (1, 2):
                print("ОШИБКА: неверный формат команды session")
                continue
            s_name = s_parts[0]
            if s_name in sessions:
                print(f"ОШИБКА: сеанс {s_name} уже существует")
                continue

            if len(s_parts) == 2:
                start_mins = time_to_minutes(s_parts[1])
                if start_mins is None:
                    print("ОШИБКА: некорректное время начала сеанса")
                    continue
                sessions[s_name] = start_mins
                print(f"Сеанс {s_name} добавлен (начало в {minutes_to_time(start_mins)})")
            else:
                sessions[s_name] = None
                print(f"Сеанс {s_name} добавлен")

        elif cmd == 'book':
            b_parts = rest.split(None, 2)
            if len(b_parts) < 3:
                print("ОШИБКА: недостаточно аргументов для book")
                continue

            s_name, seats_token, raw_user = b_parts[0], b_parts[1], b_parts[2]
            user_name = raw_user.strip()
            if not user_name:
                print("ОШИБКА: пустое имя пользователя")
                continue

            if s_name not in sessions:
                print(f"ОШИБКА: сеанс {s_name} не найден")
                continue

            update_expirations(bookings, current_time)

            start_mins = sessions[s_name]
            if start_mins is not None and current_time >= start_mins:
                print("ОШИБКА: бронирование закрыто, сеанс уже начался")
                continue

            seat_specs = seats_token.split(',')
            parsed_seats = []
            seen_in_group = set()
            error_msg = None

            for spec in seat_specs:
                if ':' not in spec:
                    error_msg = "неверный формат места"
                    break
                r_str, c_str = spec.split(':', 1)
                if not (r_str.isdigit() and c_str.isdigit()):
                    error_msg = "ряд и место должны быть числами"
                    break
                r_idx, c_idx = int(r_str), int(c_str)

                if r_idx < 1 or r_idx > num_rows or c_idx < 1 or c_idx > len(hall[r_idx - 1]):
                    error_msg = f"ряд {r_idx}, место {c_idx} не существует"
                    break

                seat_type = hall[r_idx - 1][c_idx - 1]
                if seat_type == '.':
                    error_msg = f"ряд {r_idx}, место {c_idx} является проходом"
                    break

                if (r_idx, c_idx) in seen_in_group:
                    error_msg = f"дублирование места ряд {r_idx}, место {c_idx} в запросе"
                    break

                if is_seat_occupied(bookings, s_name, r_idx, c_idx):
                    error_msg = f"ряд {r_idx}, место {c_idx} уже забронировано"
                    break

                seen_in_group.add((r_idx, c_idx))
                parsed_seats.append((r_idx, c_idx, prices[seat_type]))

            if error_msg is not None:
                print(f"ОШИБКА: {error_msg}")
                continue

            for r_idx, c_idx, price in parsed_seats:
                booking_id = len(bookings) + 1
                bookings.append({
                    'id': booking_id,
                    'session': s_name,
                    'row': r_idx,
                    'seat': c_idx,
                    'user': user_name,
                    'price': price,
                    'created_at': current_time,
                    'status': 'active',
                    'status_time': current_time
                })
                print(f"Бронь {booking_id}: {user_name}, сеанс {s_name}, ряд {r_idx}, место {c_idx}, {price} руб. - УСПЕШНО")

        elif cmd == 'pay':
            p_parts = rest.split(None, 1)
            if len(p_parts) < 2 or not p_parts[0].isdigit():
                print("ОШИБКА: неверный формат команды pay")
                continue

            b_id = int(p_parts[0])
            user_name = p_parts[1].strip()
            if b_id < 1 or b_id > len(bookings):
                print(f"ОШИБКА: бронь {b_id} не найдена")
                continue

            update_expirations(bookings, current_time)
            b = bookings[b_id - 1]

            if b['user'] != user_name:
                print("ОШИБКА: неверное имя пользователя для брони")
                continue

            if b['status'] == 'paid':
                print(f"ОШИБКА: бронь {b_id} уже оплачена")
                continue
            if b['status'] == 'cancelled':
                print(f"ОШИБКА: бронь {b_id} уже отменена")
                continue
            if b['status'] == 'expired':
                print(f"ОШИБКА: время оплаты брони {b_id} истекло")
                continue

            b['status'] = 'paid'
            b['status_time'] = current_time
            print(f"Бронь {b_id} оплачена")

        elif cmd == 'cancel':
            c_parts = rest.split(None, 1)
            if len(c_parts) < 2 or not c_parts[0].isdigit():
                print("ОШИБКА: неверный формат команды cancel")
                continue

            b_id = int(c_parts[0])
            user_name = c_parts[1].strip()
            if b_id < 1 or b_id > len(bookings):
                print(f"ОШИБКА: бронь {b_id} не найдена")
                continue

            update_expirations(bookings, current_time)
            b = bookings[b_id - 1]

            if b['user'] != user_name:
                print("ОШИБКА: неверное имя пользователя для брони")
                continue

            if b['status'] == 'cancelled':
                print(f"ОШИБКА: бронь {b_id} уже отменена")
                continue
            if b['status'] == 'expired':
                print(f"ОШИБКА: бронь {b_id} уже истекла")
                continue

            b['status'] = 'cancelled'
            b['status_time'] = current_time
            print(f"Бронь {b_id} отменена")

        elif cmd == 'show':
            s_name = rest.strip()
            if not s_name or len(s_name.split()) != 1:
                print("ОШИБКА: неверный формат команды show")
                continue
            if s_name not in sessions:
                print(f"ОШИБКА: сеанс {s_name} не найден")
                continue

            update_expirations(bookings, current_time)

            label_width = len(f"Ряд {num_rows}:") + 1
            header_cells = "".join(f"{col:<3}" for col in range(1, max_cols + 1))
            print((" " * label_width + header_cells).rstrip())

            for r_idx in range(1, num_rows + 1):
                label = f"Ряд {r_idx}:".ljust(label_width)
                row_cells = []
                for c_idx in range(1, max_cols + 1):
                    if c_idx <= len(hall[r_idx - 1]):
                        cell = hall[r_idx - 1][c_idx - 1]
                        if cell == '.':
                            disp = ' '
                        elif is_seat_occupied(bookings, s_name, r_idx, c_idx):
                            disp = 'x'
                        else:
                            disp = cell
                    else:
                        disp = ' '
                    row_cells.append(f"{disp:<3}")
                print((label + "".join(row_cells)).rstrip())

        elif cmd == 'free':
            s_name = rest.strip()
            if not s_name or len(s_name.split()) != 1:
                print("ОШИБКА: неверный формат команды free")
                continue
            if s_name not in sessions:
                print(f"ОШИБКА: сеанс {s_name} не найден")
                continue

            update_expirations(bookings, current_time)

            total_seats = 0
            free_seats = 0
            for r_idx in range(1, num_rows + 1):
                for c_idx in range(1, len(hall[r_idx - 1]) + 1):
                    if hall[r_idx - 1][c_idx - 1] != '.':
                        total_seats += 1
                        if not is_seat_occupied(bookings, s_name, r_idx, c_idx):
                            free_seats += 1
            print(f"Свободно мест: {free_seats} из {total_seats}")

        elif cmd == 'history':
            s_name = rest.strip()
            if not s_name or len(s_name.split()) != 1:
                print("ОШИБКА: неверный формат команды history")
                continue
            if s_name not in sessions:
                print(f"ОШИБКА: сеанс {s_name} не найден")
                continue

            update_expirations(bookings, current_time)

            session_bookings = [b for b in bookings if b['session'] == s_name]
            if not session_bookings:
                print("История пуста")
            else:
                for b in session_bookings:
                    t_created = minutes_to_time(b['created_at'])
                    if b['status'] == 'active':
                        st_text = "(активно)"
                    elif b['status'] == 'paid':
                        st_text = "(оплачено)"
                    elif b['status'] == 'cancelled':
                        st_text = f"(отменено в {minutes_to_time(b['status_time'])})"
                    else:
                        st_text = f"(истекло в {minutes_to_time(b['status_time'])})"
                    print(f"  {t_created} {b['user']} → ряд {b['row']}, место {b['seat']} {st_text}")

        else:
            print(f"ОШИБКА: неизвестная команда '{cmd}'")


if __name__ == "__main__":
    main()

