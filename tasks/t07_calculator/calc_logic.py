import re


class LogicError(Exception):
    pass


LOGIC_TOKEN_RE = re.compile(
    r"[ \t\r\n]*(?:"
    r"(<=|>=|==|!=|<|>)|"
    r"([()+\-])|"
    r"([0-9]+(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?|\.[0-9]+(?:[eE][+-]?[0-9]+)?)|"
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r")",
    re.ASCII,
)


def is_logic_expression(expr: str) -> bool:
    for m in LOGIC_TOKEN_RE.finditer(expr):
        cmp_op, _, _, ident = m.groups()
        if cmp_op is not None:
            return True
        if ident is not None and ident.lower() in ("and", "or", "not", "true", "false"):
            return True
    return False


def _tokenize_logic(expr: str):
    tokens = []
    pos = 0
    while pos < len(expr):
        if expr[pos] in " \t\r\n":
            pos += 1
            continue
        m = LOGIC_TOKEN_RE.match(expr, pos)
        if not m:
            raise LogicError(f"неизвестный символ '{expr[pos]}' в логическом выражении")
        cmp_op, sym, num, ident = m.groups()
        if cmp_op is not None:
            tokens.append(("CMP", cmp_op))
        elif sym is not None:
            tokens.append((sym, sym))
        elif num is not None:
            val = float(num) if ("." in num or "e" in num or "E" in num) else int(num)
            tokens.append(("NUM", val))
        elif ident is not None:
            low = ident.lower()
            if low in ("and", "or", "not"):
                tokens.append(("LOGIC_OP", low))
            elif low == "true":
                tokens.append(("BOOL", True))
            elif low == "false":
                tokens.append(("BOOL", False))
            else:
                tokens.append(("ID", ident))
        pos = m.end()
    return tokens


class _LogicParser:
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
            raise LogicError("пустое логическое выражение")
        val = self.parse_or()
        if self.peek() is not None:
            raise LogicError(f"неожиданный токен '{self.peek()[1]}'")
        if not isinstance(val, bool):
            raise LogicError("результат выражения не является логическим значением")
        return val

    def parse_or(self):
        left = self.parse_and()
        while self.peek() == ("LOGIC_OP", "or"):
            self.consume()
            right = self.parse_and()
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise LogicError("оператор OR применим только к логическим значениям")
            left = left or right
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.peek() == ("LOGIC_OP", "and"):
            self.consume()
            right = self.parse_not()
            if not isinstance(left, bool) or not isinstance(right, bool):
                raise LogicError("оператор AND применим только к логическим значениям")
            left = left and right
        return left

    def parse_not(self):
        if self.peek() == ("LOGIC_OP", "not"):
            self.consume()
            val = self.parse_not()
            if not isinstance(val, bool):
                raise LogicError("оператор NOT применим только к логическому значению")
            return not val
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_atom()
        if self.peek() and self.peek()[0] == "CMP":
            op = self.consume()[1]
            right = self.parse_atom()

            if isinstance(left, bool) or isinstance(right, bool):
                if not (isinstance(left, bool) and isinstance(right, bool)):
                    raise LogicError("нельзя сравнивать число и логическое значение")
                if op == "==":
                    return left == right
                if op == "!=":
                    return left != right
                raise LogicError(f"оператор '{op}' не поддерживается для логических значений")

            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right

        return left

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            raise LogicError("неожиданный конец логического выражения")

        ttype, tval = tok
        if ttype in ("+", "-"):
            self.consume()
            val = self.parse_atom()
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise LogicError("унарный знак применим только к числам")
            return -val if ttype == "-" else +val

        if ttype in ("BOOL", "NUM"):
            self.consume()
            return tval

        if ttype == "ID":
            self.consume()
            if tval not in self.env:
                raise LogicError(f"неизвестная переменная '{tval}'")
            return self.env[tval]

        if ttype == "(":
            self.consume()
            val = self.parse_or()
            if self.peek() != (")", ")"):
                raise LogicError("ожидалась закрывающая скобка ')'")
            self.consume()
            return val

        raise LogicError(f"неожиданный элемент '{tval}'")


def calculate_logic(expr: str, env=None) -> str:
    env = env or {}
    tokens = _tokenize_logic(expr)
    parser = _LogicParser(tokens, env)
    res = parser.parse()
    return "true" if res else "false"
