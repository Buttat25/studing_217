import argparse
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

LINE_RE = re.compile(
    r"^[ \t]*(?P<dt>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?)"
    r"[ \t]*(?P<sep>[|;\t])[ \t]*"
    r"(?P<etype>[A-Za-z][A-Za-z0-9_]*)"
    r"(?:[ \t]*(?P=sep)[ \t]*(?P<desc>.*))?[ \t]*$"
)

KV_RE = re.compile(r'([A-Za-z0-9_]+)\s*=\s*(?:"([^"]*)"|([^,\s]*))')


class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        sys.stderr.write(f"Ошибка: {message}\n")
        sys.exit(2)


def format_int(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def format_float(val: float) -> str:
    int_part, frac_part = f"{val:.1f}".split(".")
    return f"{format_int(int(int_part))}.{frac_part}"


def pluralize(n: int, form1: str, form2: str, form5: str) -> str:
    n_abs = abs(n) % 100
    if 11 <= n_abs <= 19:
        return form5
    n_rem = n_abs % 10
    if n_rem == 1:
        return form1
    if 2 <= n_rem <= 4:
        return form2
    return form5


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    kb = size_bytes / 1024
    if kb < 1024:
        return f"{kb:.1f} КБ"
    mb = kb / 1024
    return f"{mb:.1f} МБ"


def parse_timestamp(dt_str: str) -> datetime | None:
    date_part = dt_str[:10]
    rest = dt_str[11:]
    time_part = rest[:8]
    tz_part = rest[8:]

    try:
        year, month, day = map(int, date_part.split("-"))
        hour, minute, second = map(int, time_part.split(":"))
        dt = datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None

    if not tz_part or tz_part == "Z":
        return dt.replace(tzinfo=timezone.utc)

    sign = 1 if tz_part[0] == "+" else -1
    tz_digits = tz_part[1:].replace(":", "")
    if len(tz_digits) != 4:
        return None

    tz_h = int(tz_digits[:2])
    tz_m = int(tz_digits[2:])
    if tz_h > 14 or tz_m > 59:
        return None

    offset = timezone(timedelta(hours=sign * tz_h, minutes=sign * tz_m))
    return dt.replace(tzinfo=offset).astimezone(timezone.utc)


def extract_codes(desc: str | None) -> set[str]:
    if not desc:
        return set()
    codes = set()
    for match in KV_RE.finditer(desc):
        key = match.group(1)
        val = match.group(2) if match.group(2) is not None else match.group(3)
        if key == "code" and val:
            codes.add(val)
    return codes


def format_dt(dt: datetime, multi_day: bool) -> str:
    if multi_day:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt.strftime("%H:%M:%S")


def format_bucket(bucket_start: datetime, bucket_min: int, multi_day: bool) -> str:
    bucket_end = bucket_start + timedelta(minutes=bucket_min)
    start_str = bucket_start.strftime("%H:%M")
    end_str = bucket_end.strftime("%H:%M")
    if multi_day:
        return f"{bucket_start.strftime('%Y-%m-%d')} {start_str}–{end_str}"
    return f"{start_str}–{end_str}"


def main() -> None:
    parser = CustomArgumentParser(description="Анализатор дневника событий")
    parser.add_argument("file", help="Путь к файлу журнала")
    parser.add_argument("--bucket", type=int, default=60, help="Интервал в минутах")
    parser.add_argument("--gap", type=int, default=30, help="Порог промежутка в минутах")
    args = parser.parse_args()

    if args.bucket <= 0 or 1440 % args.bucket != 0:
        parser.error("сутки (1440 минут) должны делиться на --bucket без остатка")
    if args.gap <= 0:
        parser.error("параметр --gap должен быть положительным числом")
    if not os.path.isfile(args.file):
        sys.stderr.write(f"Ошибка: файл '{args.file}' не найден\n")
        sys.exit(1)

    file_size = os.path.getsize(args.file)
    file_name = os.path.basename(args.file)

    non_empty_lines = 0
    broken_count = 0
    broken_examples: list[tuple[int, str]] = []
    parsed_count = 0
    out_of_order_count = 0

    type_counts: dict[str, int] = {}
    bucket_counts: Counter[datetime] = Counter()

    min_dt: datetime | None = None
    max_dt: datetime | None = None

    gaps: list[tuple[datetime, datetime, int]] = []
    gap_threshold = timedelta(minutes=args.gap)

    err_streak_count = 0
    err_streak_start: datetime | None = None
    err_streak_end: datetime | None = None
    err_streak_codes: set[str] = set()
    error_streaks: list[tuple[int, datetime, datetime, list[str]]] = []

    def flush_error_streak() -> None:
        nonlocal err_streak_count, err_streak_start, err_streak_end, err_streak_codes
        if err_streak_count >= 3 and err_streak_start and err_streak_end:
            error_streaks.append(
                (
                    err_streak_count,
                    err_streak_start,
                    err_streak_end,
                    sorted(err_streak_codes),
                )
            )
        err_streak_count = 0
        err_streak_start = None
        err_streak_end = None
        err_streak_codes = set()

    with open(args.file, "r", encoding="utf-8", errors="replace") as f:
        for line_num, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip("\r\n")
            if line_num == 1 and line.startswith("\ufeff"):
                line = line.lstrip("\ufeff")

            if not line.strip():
                continue

            non_empty_lines += 1
            match = LINE_RE.match(line)
            if not match:
                broken_count += 1
                if len(broken_examples) < 10:
                    broken_examples.append((line_num, line))
                continue

            dt = parse_timestamp(match.group("dt"))
            if dt is None:
                broken_count += 1
                if len(broken_examples) < 10:
                    broken_examples.append((line_num, line))
                continue

            etype = match.group("etype").upper()
            desc = match.group("desc")

            parsed_count += 1
            type_counts[etype] = type_counts.get(etype, 0) + 1

            minutes_from_midnight = dt.hour * 60 + dt.minute
            bucket_start_min = (minutes_from_midnight // args.bucket) * args.bucket
            bucket_dt = dt.replace(
                hour=bucket_start_min // 60,
                minute=bucket_start_min % 60,
                second=0,
                microsecond=0,
            )
            bucket_counts[bucket_dt] += 1

            if min_dt is None or dt < min_dt:
                min_dt = dt

            if max_dt is None:
                max_dt = dt
            else:
                if dt < max_dt:
                    out_of_order_count += 1
                else:
                    diff = dt - max_dt
                    if diff > gap_threshold:
                        gap_minutes = int(diff.total_seconds() // 60)
                        gaps.append((max_dt, dt, gap_minutes))
                    max_dt = dt

            if etype == "ERROR":
                if err_streak_count == 0:
                    err_streak_start = dt
                err_streak_end = dt
                err_streak_count += 1
                err_streak_codes.update(extract_codes(desc))
            else:
                flush_error_streak()

    flush_error_streak()

    multi_day = bool(min_dt and max_dt and min_dt.date() != max_dt.date())

    print(f"Отчёт по файлу {file_name}:")
    print(f"  Размер файла: {format_size(file_size)}")
    print(f"  Всего строк: {format_int(non_empty_lines)}")
    print(f"  Успешно разобрано: {format_int(parsed_count)}")

    if broken_count == 0:
        print("  Битых строк: 0")
    else:
        print(f"  Битых строк: {format_int(broken_count)} (пропущены)")

    if out_of_order_count > 0:
        print(f"  Записано не по порядку времени: {format_int(out_of_order_count)}")

    if broken_examples:
        print("\nПримеры битых строк:")
        for b_num, b_text in broken_examples:
            print(f"  строка {b_num}: {b_text}")

    print("\nСтатистика по типам событий:")
    if not type_counts:
        print("  нет событий")
    else:
        max_name_len = max(len(k) for k in type_counts)
        max_cnt_len = max(len(format_int(v)) for v in type_counts.values())
        for etype, count in type_counts.items():
            pct = (count / parsed_count) * 100
            name_padded = etype.ljust(max_name_len + 2)
            cnt_padded = format_int(count).rjust(max_cnt_len)
            print(f"  {name_padded}: {cnt_padded} ({pct:.1f}%)")

    print("\nПики активности:")
    if parsed_count == 0 or min_dt is None or max_dt is None:
        print("  нет данных")
    else:
        first_b_min = ((min_dt.hour * 60 + min_dt.minute) // args.bucket) * args.bucket
        first_bucket = min_dt.replace(
            hour=first_b_min // 60, minute=first_b_min % 60, second=0, microsecond=0
        )
        last_b_min = ((max_dt.hour * 60 + max_dt.minute) // args.bucket) * args.bucket
        last_bucket = max_dt.replace(
            hour=last_b_min // 60, minute=last_b_min % 60, second=0, microsecond=0
        )

        total_buckets = (
            int((last_bucket - first_bucket).total_seconds() // 60) // args.bucket
        ) + 1
        avg_events = parsed_count / total_buckets

        all_buckets = [
            first_bucket + timedelta(minutes=i * args.bucket)
            for i in range(total_buckets)
        ]

        peak_bucket = min(all_buckets, key=lambda b: (-bucket_counts[b], b))
        peak_count = bucket_counts[peak_bucket]
        peak_word = pluralize(peak_count, "событие", "события", "событий")

        min_bucket = min(all_buckets, key=lambda b: (bucket_counts[b], b))
        min_count = bucket_counts[min_bucket]
        min_word = pluralize(min_count, "событие", "события", "событий")

        print(
            f"  Максимальная нагрузка: {format_bucket(peak_bucket, args.bucket, multi_day)} "
            f"({format_int(peak_count)} {peak_word})"
        )
        print(
            f"  Минимальная нагрузка: {format_bucket(min_bucket, args.bucket, multi_day)} "
            f"({format_int(min_count)} {min_word})"
        )
        print(f"  Среднее за {args.bucket} мин: {format_float(avg_events)}")

    print(f"\nПодозрительные промежутки (более {args.gap} мин без событий):")
    if not gaps:
        print("  не обнаружено")
    else:
        for g_start, g_end, g_mins in gaps:
            print(
                f"  {format_dt(g_start, multi_day)} – {format_dt(g_end, multi_day)} "
                f"({format_int(g_mins)} мин)"
            )

    print("\nСерии ошибок:")
    if not error_streaks:
        print("  не обнаружено")
    else:
        for count, s_start, s_end, codes in error_streaks:
            err_word = pluralize(count, "ошибка", "ошибки", "ошибок")
            codes_str = f" (code={', '.join(codes)})" if codes else ""
            print(
                f"  {format_dt(s_start, multi_day)}–{format_dt(s_end, multi_day)}: "
                f"{format_int(count)} {err_word} подряд{codes_str} - ВОЗМОЖНЫЙ СБОЙ"
            )


if __name__ == "__main__":
    main()

