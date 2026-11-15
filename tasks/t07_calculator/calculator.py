import re
import sys
from calc_convert import ConvertError, convert_units
from calc_logic import LogicError, calculate_logic, is_logic_expression
from calc_math import MathError, calculate_math, eval_math_raw
from calc_matrix import MatrixError, calculate_matrix


class CalcError(Exception):
    pass


WHERE_SPLIT_RE = re.compile(r"(?:,\s*|\s+)(?:where|где)\s+(.+)$", re.IGNORECASE)


def _plural_signs(n: int) -> str:
    if 11 <= (n % 100) <= 14:
        return f"{n} знаков"
    last = n % 10
    if last == 1:
        return f"{n} знак"
    if 2 <= last <= 4:
        return f"{n} знака"
    return f"{n} знаков"


def _parse_where(line: str):
    m = WHERE_SPLIT_RE.search(line)
    if not m:
        return line.strip(), {}

    expr_part = line[:m.start()].strip()
    where_part = m.group(1).strip()
    if not where_part:
        raise CalcError("пустой блок переменных после where/где")

    env = {}
    assignments = [item.strip() for item in where_part.split(",")]
    for item in assignments:
        if "=" not in item:
            raise CalcError(f"ожидалось присваивание вида x=5, получено '{item}'")
        name, raw_val = item.split("=", 1)
        name = name.strip()
        raw_val = raw_val.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name, re.ASCII):
            raise CalcError(f"недопустимое имя переменной '{name}'")
        low = raw_val.lower()
        if low == "true":
            env[name] = True
        elif low == "false":
            env[name] = False
        else:
            try:
                env[name] = eval_math_raw(raw_val, env=env)
            except MathError as exc:
                raise CalcError(f"ошибка в значении переменной '{name}': {exc}")

    return expr_part, env


def _substitute_vars_in_text(text: str, env: dict) -> str:
    if not env:
        return text

    def repl(match):
        word = match.group(0)
        if word in env:
            val = env[word]
            if isinstance(val, bool):
                return "true" if val else "false"
            return str(val)
        return word

    return re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", repl, text)


class CalculatorApp:
    def __init__(self):
        self.precision = 10
        self.history = []

    def process_line(self, raw_line: str):
        line = raw_line.strip()
        if not line:
            return None

        low = line.lower()

        if low in ("exit", "quit"):
            return "EXIT"

        if low == "help":
            return (
                "Команды:\n"
                "  <выражение> [where|где x=1, y=2] — вычисление математического или логического выражения\n"
                "  convert <число> <из> to|in <в> — конвертер единиц измерения\n"
                "  matrix <операция> — операции с матрицами (+, -, *, det, transpose/t)\n"
                "  precision [0..15] — показать или установить точность дробной части\n"
                "  history — показать историю вычислений\n"
                "  save <файл> — сохранить историю в файл\n"
                "  help — показать эту справку\n"
                "  exit | quit — выход"
            )

        if low == "precision":
            return f"Текущая точность: {_plural_signs(self.precision)} после запятой"

        if low.startswith("precision ") or re.fullmatch(r"precision\s+\S+", low):
            parts = line.split()
            if len(parts) != 2 or not re.fullmatch(r"[+-]?[0-9]+", parts[1], re.ASCII):
                return "ОШИБКА: точность должна быть целым числом от 0 до 15"
            val = int(parts[1])
            if not (0 <= val <= 15):
                return "ОШИБКА: точность должна быть от 0 до 15"
            self.precision = val
            return f"Точность установлена: {_plural_signs(self.precision)} после запятой"

        if low == "history":
            if not self.history:
                return "История пуста"
            return "\n".join(f"  {item}" for item in self.history)

        if low.startswith("save ") or low == "save":
            parts = line.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                return "ОШИБКА: не указано имя файла для сохранения"
            filename = parts[1].strip()
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    for item in self.history:
                        f.write(item + "\n")
                return f"История сохранена: {filename}"
            except OSError as exc:
                return f"ОШИБКА: не удалось сохранить файл ({exc})"

        try:
            expr_part, env = _parse_where(line)
            expr_low = expr_part.lower()

            if expr_low.startswith("convert ") or expr_low == "convert":
                prepared = _substitute_vars_in_text(expr_part, env)
                res = convert_units(prepared)
                formatted_out = f"= {res}"
                self.history.append(f"{len(self.history) + 1}. {line} = {res}")
                return formatted_out

            if expr_low.startswith("matrix ") or expr_low == "matrix":
                prepared = _substitute_vars_in_text(expr_part, env)
                res = calculate_matrix(prepared, precision=self.precision)
                formatted_out = f"= {res}"
                single_line_res = res.replace("\n   ", " ")
                self.history.append(f"{len(self.history) + 1}. {line} = {single_line_res}")
                return formatted_out

            if is_logic_expression(expr_part):
                res = calculate_logic(expr_part, env=env)
                formatted_out = f"= {res}"
                self.history.append(f"{len(self.history) + 1}. {line} = {res}")
                return formatted_out

            res = calculate_math(expr_part, env=env, precision=self.precision)
            formatted_out = f"= {res}"
            self.history.append(f"{len(self.history) + 1}. {line} = {res}")
            return formatted_out

        except (CalcError, MathError, ConvertError, MatrixError, LogicError) as exc:
            self.history.append(f"{len(self.history) + 1}. {line} → ОШИБКА")
            return f"ОШИБКА: {exc}"
        except Exception as exc:
            self.history.append(f"{len(self.history) + 1}. {line} → ОШИБКА")
            return f"ОШИБКА: {exc}"


def main():
    app = CalculatorApp()

    if len(sys.argv) > 1:
        expr = " ".join(sys.argv[1:])
        out = app.process_line(expr)
        if out == "EXIT" or out is None:
            sys.exit(0)
        print(out)
        if out.startswith("ОШИБКА:"):
            sys.exit(1)
        sys.exit(0)

    for raw_line in sys.stdin:
        out = app.process_line(raw_line)
        if out == "EXIT":
            break
        if out is not None:
            print(out)


if __name__ == "__main__":
    main()

# Срочное исправление для релиза 1.0.1
