import math
import re
from decimal import Decimal, ROUND_HALF_UP, localcontext
from fractions import Fraction


class MatrixError(Exception):
    pass


NUM_PATTERN = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
MATRIX_LITERAL_RE = re.compile(r"\[\s*\[.*?\]\s*\]", re.DOTALL)


def _parse_num(s: str):
    s = s.strip()
    if "." not in s and "e" not in s and "E" not in s:
        return int(s)
    return float(s)


def _parse_matrix(text: str):
    text = text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        raise MatrixError("матрица должна быть заключена в квадратные скобки [[...]]")

    inner = text[1:-1].strip()
    if not inner:
        raise MatrixError("пустая матрица")

    rows = []
    pos = 0
    n = len(inner)
    while pos < n:
        while pos < n and inner[pos] in " \t\r\n":
            pos += 1
        if pos >= n:
            break
        if inner[pos] != "[":
            raise MatrixError("ожидалась открывающая скобка строки '['")
        end_row = inner.find("]", pos)
        if end_row == -1:
            raise MatrixError("не найдена закрывающая скобка строки ']'")
        row_content = inner[pos + 1:end_row].strip()
        if not row_content:
            raise MatrixError("пустая строка в матрице")

        parts = [p.strip() for p in row_content.split(",")]
        row = []
        for p in parts:
            if not re.fullmatch(NUM_PATTERN, p, re.ASCII):
                raise MatrixError(f"некорректный элемент матрицы '{p}'")
            row.append(_parse_num(p))
        rows.append(row)

        pos = end_row + 1
        while pos < n and inner[pos] in " \t\r\n":
            pos += 1
        if pos < n:
            if inner[pos] != ",":
                raise MatrixError("ожидалась запятая между строками матрицы")
            pos += 1
            while pos < n and inner[pos] in " \t\r\n":
                pos += 1
            if pos >= n:
                raise MatrixError("лишняя запятая в конце матрицы")

    if not rows:
        raise MatrixError("пустая матрица")

    cols = len(rows[0])
    for r in rows:
        if len(r) != cols:
            raise MatrixError("строки матрицы имеют разную длину")

    return rows


def _format_elem(val, precision: int = 10) -> str:
    if isinstance(val, int):
        return str(val)
    x = float(val)
    if math.isnan(x) or math.isinf(x):
        raise MatrixError("недопустимое значение элемента матрицы")
    if x == 0.0:
        return "0.0"

    with localcontext() as ctx:
        ctx.prec = 80
        d = Decimal(repr(x))
        q = Decimal("1") if precision == 0 else Decimal("1e-" + str(precision))
        rounded = d.quantize(q, rounding=ROUND_HALF_UP)
        if rounded == 0:
            return "0.0"
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


def format_matrix(mat, precision: int = 10) -> str:
    formatted_rows = []
    for row in mat:
        elems = ", ".join(_format_elem(v, precision) for v in row)
        formatted_rows.append(f"[{elems}]")

    if len(formatted_rows) == 1:
        return f"[{formatted_rows[0]}]"

    lines = [f"[{formatted_rows[0]},"]
    for i in range(1, len(formatted_rows) - 1):
        lines.append(f"   {formatted_rows[i]},")
    lines.append(f"   {formatted_rows[-1]}]")
    return "\n".join(lines)


def _determinant(mat):
    n = len(mat)
    cols = len(mat[0])
    if n != cols:
        raise MatrixError(f"определитель определён только для квадратных матриц (получена {n}×{cols})")

    all_int = all(isinstance(x, int) for row in mat for x in row)
    if all_int:
        a = [[Fraction(x) for x in row] for row in mat]
        det = Fraction(1)
        for i in range(n):
            pivot = None
            for r in range(i, n):
                if a[r][i] != 0:
                    pivot = r
                    break
            if pivot is None:
                return 0
            if pivot != i:
                a[i], a[pivot] = a[pivot], a[i]
                det = -det
            det *= a[i][i]
            for r in range(i + 1, n):
                factor = a[r][i] / a[i][i]
                for c in range(i, n):
                    a[r][c] -= factor * a[i][c]
        return int(det)

    a = [[float(x) for x in row] for row in mat]
    det = 1.0
    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(a[r][i]))
        if abs(a[pivot][i]) < 1e-15:
            return 0.0
        if pivot != i:
            a[i], a[pivot] = a[pivot], a[i]
            det = -det
        det *= a[i][i]
        for r in range(i + 1, n):
            factor = a[r][i] / a[i][i]
            for c in range(i, n):
                a[r][c] -= factor * a[i][c]
    return det


def calculate_matrix(command: str, precision: int = 10) -> str:
    body = re.sub(r"^\s*matrix\s+", "", command, flags=re.IGNORECASE).strip()
    if not body:
        raise MatrixError("пустая команда matrix")

    m_det = re.match(r"^det\s+(.+)$", body, flags=re.IGNORECASE | re.DOTALL)
    if m_det:
        mat = _parse_matrix(m_det.group(1))
        det = _determinant(mat)
        return _format_elem(det, precision)

    m_tr = re.match(r"^(?:transpose|t)\s+(.+)$", body, flags=re.IGNORECASE | re.DOTALL)
    if m_tr:
        mat = _parse_matrix(m_tr.group(1))
        rows, cols = len(mat), len(mat[0])
        res = [[mat[r][c] for r in range(rows)] for c in range(cols)]
        return format_matrix(res, precision)

    matches = list(MATRIX_LITERAL_RE.finditer(body))
    if len(matches) == 2:
        m1_str = matches[0].group(0)
        m2_str = matches[1].group(0)
        prefix = body[:matches[0].start()].strip()
        between = body[matches[0].end():matches[1].start()].strip()
        suffix = body[matches[1].end():].strip()

        if prefix or suffix or between not in ("+", "-", "*"):
            raise MatrixError("неверный синтаксис операции над двумя матрицами")

        a = _parse_matrix(m1_str)
        b = _parse_matrix(m2_str)
        ra, ca = len(a), len(a[0])
        rb, cb = len(b), len(b[0])

        if between in ("+", "-"):
            if (ra, ca) != (rb, cb):
                raise MatrixError(f"несовместимые размеры матриц ({ra}×{ca} и {rb}×{cb})")
            if between == "+":
                res = [[a[i][j] + b[i][j] for j in range(ca)] for i in range(ra)]
            else:
                res = [[a[i][j] - b[i][j] for j in range(ca)] for i in range(ra)]
            return format_matrix(res, precision)

        if between == "*":
            if ca != rb:
                raise MatrixError(f"несовместимые размеры матриц ({ra}×{ca} и {rb}×{cb})")
            res = [
                [sum(a[i][k] * b[k][j] for k in range(ca)) for j in range(cb)]
                for i in range(ra)
            ]
            return format_matrix(res, precision)

    if len(matches) == 1:
        m_str = matches[0].group(0)
        left = body[:matches[0].start()].strip()
        right = body[matches[0].end():].strip()
        mat = _parse_matrix(m_str)

        if not left and not right:
            return format_matrix(mat, precision)

        if left and not right:
            if not left.endswith("*"):
                raise MatrixError("ожидался оператор '*' при умножении числа на матрицу")
            num_part = left[:-1].strip()
            if not re.fullmatch(NUM_PATTERN, num_part, re.ASCII):
                raise MatrixError(f"некорректный множитель '{num_part}'")
            scalar = _parse_num(num_part)
            res = [[elem * scalar for elem in row] for row in mat]
            return format_matrix(res, precision)

        if right and not left:
            if not right.startswith("*"):
                raise MatrixError("ожидался оператор '*' при умножении матрицы на число")
            num_part = right[1:].strip()
            if not re.fullmatch(NUM_PATTERN, num_part, re.ASCII):
                raise MatrixError(f"некорректный множитель '{num_part}'")
            scalar = _parse_num(num_part)
            res = [[elem * scalar for elem in row] for row in mat]
            return format_matrix(res, precision)

    raise MatrixError("не удалось распознать матричную команду")
