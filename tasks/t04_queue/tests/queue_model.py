import math

from course_program import golden_lookup


simulate = golden_lookup(__file__, "queue_model.simulate")


report = golden_lookup(__file__, "queue_model.report")


def customers_text(people):
    return "".join(f"{a!r} {s!r}\n" for a, s in people)


def parse_report(lines):
    def value(prefix):
        line = next(l for l in lines if l.startswith(prefix))
        return line[len(prefix):]

    def integer(text):
        return int(text.split(" (")[0].replace(" ", "").split("мин")[0].split("человек")[0])

    cashiers = []
    for line in lines:
        if line.startswith("  Кассир "):
            served = int(line.split("обслужил ")[1].split(" покупател")[0].replace(" ", ""))
            load = int(line.split("загрузка ")[1].rstrip("%"))
            cashiers.append((served, load))
    return {
        "arrived": integer(value("  Всего пришло покупателей: ")),
        "served": integer(value("  Обслужено покупателей: ")),
        "balked": integer(value("  Ушло из-за длинной очереди: ")),
        "max_wait": float(value("  Максимальное время ожидания: ").split()[0]),
        "min_wait": float(value("  Минимальное время ожидания: ").split()[0]),
        "cashiers": cashiers,
    }
