import sys

def time_to_minutes(time_str):
    """Преобразует строку 'ЧЧ:ММ' в количество минут с начала суток"""
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 60 + minutes

def main():
    # 1. Чтение входных данных (из файла или стандартного ввода)
    if len(sys.argv) == 2:
        # Если передано имя файла, читаем его
        f = open(sys.argv[1], 'r', encoding='utf-8-sig')
        lines = f.readlines()
        f.close()
    else:
        # Иначе читаем из стандартного ввода (sys.stdin)
        lines = sys.stdin.readlines()

    # Списки для хранения чистых данных
    names = []
    arrivals = []
    departures = []
    arrival_ints = []
    departure_ints = []
    indices = []

    # 2. Построчный парсинг и строгая валидация
    line_number = 0
    for line in lines:
        line_number += 1
        line_stripped = line.strip()
        
        # Пропускаем пустые строки и комментарии
        if not line_stripped or line_stripped.startswith('#'):
            continue

        # Проверяем обязательное наличие двоеточия и запятой
        if ':' not in line_stripped or ',' not in line_stripped:
            print("Ошибка: строка " + str(line_number) + " не соответствует формату", file=sys.stderr)
            sys.exit(1)

        # Выделяем имя поезда (всё, что до первого двоеточия)
        parts_name = line_stripped.split(':', 1)
        name = parts_name[0].strip()
        
        if name in names:
            print("Ошибка: дублирование имени поезда '" + name + "'", file=sys.stderr)
            sys.exit(1)

        # Выделяем блок с прибытием и отправлением
        times_block = parts_name[1]
        
        # Приводим к нижнему регистру для обработки любого написания (ПРИБЫТИЕ/прибытие)
        times_block_lower = times_block.lower()
        
        if 'прибытие' not in times_block_lower or 'отправление' not in times_block_lower:
            print("Ошибка: строка " + str(line_number) + " не соответствует формату", file=sys.stderr)
            sys.exit(1)

        # Режем блок по запятой на две части
        time_parts = times_block.split(',')
        part_arr = time_parts[0].strip()
        part_dep = time_parts[1].strip()

        # Извлекаем непосредственно временные строки "ЧЧ:ММ"
        arr_str = part_arr.lower().replace('прибытие', '').strip()
        dep_str = part_dep.lower().replace('отправление', '').strip()

        # Переводим в минуты
        arr_m = time_to_minutes(arr_str)
        dep_m = time_to_minutes(dep_str)

        # Если отправление численно меньше прибытия — значит, это следующие сутки
        if dep_m < arr_m:
            dep_m += 1440

        # Проверка длительности стоянки (не более 2 часов = 120 минут)
        stay = dep_m - arr_m
        if stay <= 0 or stay > 120:
            print("Ошибка: поезд '" + name + "' стоит больше 2 часов (" + str(stay) + " мин)", file=sys.stderr)
            sys.exit(1)

        # Запоминаем валидные данные в параллельные списки
        names.append(name)
        arrivals.append(arr_str)
        departures.append(dep_str)
        arrival_ints.append(arr_m)
        departure_ints.append(dep_m)
        indices.append(len(names) - 1)

    if not names:
        print("Минимальное количество платформ: 0")
        return

    # 3. Сортировка поездов по времени прибытия (сохраняя стабильность порядка ввода)
    # Используем простой метод пузырька, понятный любому студенту
    n = len(names)
    for i in range(n):
        for j in range(0, n - i - 1):
            # Сортируем по времени прибытия, а при равенстве — по исходному индексу
            if (arrival_ints[j] > arrival_ints[j + 1]) or (arrival_ints[j] == arrival_ints[j + 1] and indices[j] > indices[j + 1]):
                # Меняем элементы местами во всех списках одновременно
                arrival_ints[j], arrival_ints[j + 1] = arrival_ints[j + 1], arrival_ints[j]
                departure_ints[j], departure_ints[j + 1] = departure_ints[j + 1], departure_ints[j]
                names[j], names[j + 1] = names[j + 1], names[j]
                arrivals[j], arrivals[j + 1] = arrivals[j + 1], arrivals[j]
                departures[j], departures[j + 1] = departures[j + 1], departures[j]
                indices[j], indices[j + 1] = indices[j + 1], indices[j]

    # 4. Распределение по платформам (Жадный алгоритм)
    # Каждая платформа — это список индексов назначенных на неё поездов
    platforms = []

    for k in range(n):
        curr_arrival = arrival_ints[k]
        assigned = False
        
        # Проверяем существующие платформы по порядку
        for p in range(len(platforms)):
            last_train_idx = platforms[p][-1]
            last_departure = departure_ints[last_train_idx]
            
            # По условию интервал полуоткрытый [прибытие, отправление)
            # Если новый поезд прибывает в момент или после отправления старого — платформа свободна
            if curr_arrival >= last_departure:
                platforms[p].append(k)
                assigned = True
                break
                
        # Если ни одна платформа не подошла, открываем новую
        if not assigned:
            platforms.append([k])

    # 5. Вывод результатов
    print("Минимальное количество платформ: " + str(len(platforms)))
    print("\nРаспределение по платформам:")
    for p in range(len(platforms)):
        platform_trains = []
        for idx in platforms[p]:
            train_info = names[idx] + " (" + arrivals[idx] + "–" + departures[idx] + ")"
            platform_trains.append(train_info)
        
        print("  Платформа " + str(p + 1) + ": " + ", ".join(platform_trains))

if __name__ == "__main__":
    main()
