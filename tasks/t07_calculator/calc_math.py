import math
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, localcontext


class MathError(Exception):
    pass


MAX_ABS = 10 ** 1000

TOKEN_RE = re.compile(
    r"[ \t\r\n]*(?:"
    r"([0-9]+(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?|\.[0-9]+(?:[eE][+-]?[0-9]+)?)|"
    r"(\*\*)|"
    r"([+\-*/^(),])|"
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r")",
    re.ASCII,
)


def tokenize(expr: str):
    tokens = []
    pos = 0
    while pos < len(expr):
        if expr[pos] in " \t\r\n":
            pos += 1
            continue
        m = TOKEN_RE.match(expr, pos)
        if not m:
            raise MathError(f"неизвестный символ '{expr[pos]}'")
        num, pow_op, sym, ident = m.groups()
        if num is not None:
            tokens.append(("NUM", num))
        elif pow_op is not None:
            tokens.append(("OP", "^"))
        elif sym is not None:
            tokens.append(("OP" if sym in "+-*/^" else sym, sym))
        elif ident is not None:
            tokens.append(("ID", ident))
        pos = m.end()
    return tokens


def _check_limit(val):
    if isinstance(val, int):
        if abs(val) >= MAX_ABS:
            raise MathError("число превышает 10^1000 по модулю")
    else:
        if math.isnan(val) or math.isinf(val) or abs(val) >= 1e308:
            raise MathError("число вышло за допустимые пределы")


def _parse_number_token(raw: str):
    if "." not in raw and "e" not in raw and "E" not in raw:
        val = int(raw)
        _check_limit(val)
        return val
    try:
        val = float(raw)
    except ValueError:
        raise MathError(f"некорректное число '{raw}'")
    _check_limit(val)
    return val


def _apply_func(name: str, args: list):
    if name == "sqrt":
        if len(args) != 1:
            raise MathError("sqrt принимает 1 аргумент")
        x = float(args[0])
        if x < 0:
            raise MathError("квадратный корень из отрицательного числа")
        return math.sqrt(x)

    if name == "ln":
        if len(args) != 1:
            raise MathError("ln принимает 1 аргумент")
        x = float(args[0])
        if x <= 0:
            raise MathError("логарифм определён только для положительных чисел")
        return math.log(x)

    if name == "log":
        if len(args) == 1:
            x = float(args[0])
            if x <= 0:
                raise MathError("логарифм определён только для положительных чисел")
            return math.log10(x)
        elif len(args) == 2:
            x = float(args[0])
            base = float(args[1])
            if x <= 0 or base <= 0 or base == 1.0:
                raise MathError("некорректные аргументы логарифма")
            return math.log(x, base)
        else:
            raise MathError("log принимает 1 или 2 аргумента")

    if name == "abs":
        if len(args) != 1:
            raise MathError("abs принимает 1 аргумент")
        return abs(args[0])

    if name == "exp":
        if len(args) != 1:
            raise MathError("exp принимает 1 аргумент")
        x = float(args[0])
        try:
            res = math.exp(x)
        except OverflowError:
            raise MathError("переполнение в exp")
        _check_limit(res)
        return res

    if name in ("sin", "cos", "tan"):
        if len(args) != 1:
            raise MathError(f"{name} принимает 1 аргумент")
        x = float(args[0])
        if name == "sin":
            res = math.sin(x)
        elif name == "cos":
            res = math.cos(x)
        else:
            if abs(math.cos(x)) < 1e-12:
                raise MathError("тангенс не определён для данного угла")
            res = math.tan(x)
        if abs(res) < 1e-12:
            return 0.0
        _check_limit(res)
        return res

    raise MathError(f"неизвестная функция '{name}'")


def _pow_values(base, exp):
    if base == 0 and exp == 0:
        raise MathError("неопределённость 0^0")

    if isinstance(base, int) and isinstance(exp, int):
        if exp >= 0:
            if abs(base) > 1 and exp > 4000:
                raise MathError("слишком большая степень")
            res = base ** exp
            _check_limit(res)
            return res
        else:
            if base == 0:
                raise MathError("деление на ноль при возведении в отрицательную степень")
            res = float(base) ** float(exp)
            _check_limit(res)
            return res

    b = float(base)
    e = float(exp)
    if b == 0.0 and e <= 0.0:
        raise MathError("недопустимое возведение нуля в неположительную степень")
    if b < 0 and not e.is_integer():
        raise MathError("возведение отрицательного числа в дробную степень")
    try:
        res = b ** e
    except OverflowError:
        raise MathError("переполнение при возведении в степень")
    _check_limit(res)
    return res


class _Parser:
    def __init__(self, tokens, env):
        self.tokens = tokens
        self.pos = 0
        self.env = env

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse(self):
        if not self.tokens:
            raise MathError("пустое выражение")
        val = self.parse_expr()
        if self.peek() is not None:
            raise MathError(f"неожиданный токен '{self.peek()[1]}'")
        return val

    def parse_expr(self):
        left = self.parse_term()
        while self.peek() and self.peek() in (("OP", "+"), ("OP", "-")):
            op = self.consume()[1]
            right = self.parse_term()
            if op == "+":
                left = left + right
            else:
                left = left - right
            _check_limit(left)
        return left

    def parse_term(self):
        left = self.parse_unary()
        while self.peek() and self.peek() in (("OP", "*"), ("OP", "/")):
            op = self.consume()[1]
            right = self.parse_unary()
            if op == "*":
                left = left * right
            else:
                if right == 0:
                    raise MathError("деление на ноль")
                left = float(left) / float(right)
            _check_limit(left)
        return left

    def parse_unary(self):
        tok = self.peek()
        if tok in (("OP", "+"), ("OP", "-")):
            op = self.consume()[1]
            val = self.parse_unary()
            res = -val if op == "-" else +val
            _check_limit(res)
            return res
        return self.parse_power()

    def parse_power(self):
        base = self.parse_primary()
        if self.peek() == ("OP", "^"):
            self.consume()
            exp = self.parse_unary()
            return _pow_values(base, exp)
        return base

    def parse_primary(self):
        tok = self.peek()
        if tok is None:
            raise MathError("неожиданный конец выражения")

        ttype, tval = tok
        if ttype == "NUM":
            self.consume()
            return _parse_number_token(tval)

        if ttype == "(":
            self.consume()
            val = self.parse_expr()
            if self.peek() != (")", ")"):
                raise MathError("ожидалась закрывающая скобка ')'")
            self.consume()
            return val

        if ttype == "ID":
            self.consume()
            if self.peek() == ("(", "("):
                self.consume()
                args = []
                if self.peek() != (")", ")"):
                    args.append(self.parse_expr())
                    while self.peek() == (",", ","):
                        self.consume()
                        args.append(self.parse_expr())
                if self.peek() != (")", ")"):
                    raise MathError("ожидалась закрывающая скобка ')' после аргументов")
                self.consume()
                res = _apply_func(tval, args)
                _check_limit(res)
                return res
            else:
                if tval in self.env:
                    val = self.env[tval]
                    if isinstance(val, bool):
                        raise MathError(f"переменная '{tval}' имеет логический тип")
                    _check_limit(val)
                    return val
                if tval == "pi":
                    return math.pi
                if tval == "e":
                    return math.e
                raise MathError(f"неизвестная переменная или константа '{tval}'")

        raise MathError(f"неожиданный элемент '{tval}'")


def eval_math_raw(expr: str, env=None):
    env = env or {}
    tokens = tokenize(expr)
    parser = _Parser(tokens, env)
    return parser.parse()


def format_number(val, precision: int = 10) -> str:
    if isinstance(val, int):
        return str(val)

    x = float(val)
    if math.isnan(x) or math.isinf(x):
        raise MathError("недопустимое числовое значение")

    if x == 0.0:
        return "0.0"

    with localcontext() as ctx:
        ctx.prec = 80
        try:
            d = Decimal(repr(x))
        except InvalidOperation:
            d = Decimal(str(x))

        abs_d = abs(d)
        if abs_d >= Decimal("1e15") or (abs_d > 0 and abs_d < Decimal("1e-6")):
            exp = d.adjusted()
            mantissa = d.scaleb(-exp)
            q = Decimal("1") if precision == 0 else Decimal("1e-" + str(precision))
            mantissa_rounded = mantissa.quantize(q, rounding=ROUND_HALF_UP)
            if abs(mantissa_rounded) >= Decimal("10"):
                mantissa_rounded /= Decimal("10")
                exp += 1
            m_str = format(mantissa_rounded, "f")
            if "." in m_str:
                m_str = m_str.rstrip("0").rstrip(".")
            if m_str == "-0":
                m_str = "0"
            sign_exp = "+" if exp >= 0 else "-"
            return f"{m_str}e{sign_exp}{abs(exp)}"

        q = Decimal("1") if precision == 0 else Decimal("1e-" + str(precision))
        rounded = d.quantize(q, rounding=ROUND_HALF_UP)

        if rounded == 0:
            return "0.0"

        abs_r = abs(rounded)
        if abs_r >= Decimal("1e15"):
            exp = rounded.adjusted()
            mantissa = rounded.scaleb(-exp)
            mantissa_rounded = mantissa.quantize(q, rounding=ROUND_HALF_UP)
            m_str = format(mantissa_rounded, "f")
            if "." in m_str:
                m_str = m_str.rstrip("0").rstrip(".")
            sign_exp = "+" if exp >= 0 else "-"
            return f"{m_str}e{sign_exp}{abs(exp)}"

        s = format(rounded, "f")
        if "." in s:
            s = s.rstrip("0")
            if s.endswith("."):
                s += "0"
        else:
            s += ".0"
        if s == "-0.0":
            s = "0.0"
        return s


def calculate_math(expr: str, env=None, precision: int = 10) -> str:
    val = eval_math_raw(expr, env=env)
    return format_number(val, precision=precision)
