import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, localcontext


class ConvertError(Exception):
    pass


LENGTH_TO_M = {
    "m": Decimal("1"),
    "km": Decimal("1000"),
    "cm": Decimal("0.01"),
    "mm": Decimal("0.001"),
    "mi": Decimal("1609.344"),
    "mile": Decimal("1609.344"),
    "miles": Decimal("1609.344"),
    "ft": Decimal("0.3048"),
    "foot": Decimal("0.3048"),
    "feet": Decimal("0.3048"),
    "in": Decimal("0.0254"),
    "inch": Decimal("0.0254"),
    "inches": Decimal("0.0254"),
    "yd": Decimal("0.9144"),
    "yard": Decimal("0.9144"),
    "yards": Decimal("0.9144"),
}

MASS_TO_KG = {
    "kg": Decimal("1"),
    "g": Decimal("0.001"),
    "mg": Decimal("0.000001"),
    "t": Decimal("1000"),
    "ton": Decimal("1000"),
    "tonnes": Decimal("1000"),
    "lb": Decimal("0.45359237"),
    "lbs": Decimal("0.45359237"),
    "pound": Decimal("0.45359237"),
    "pounds": Decimal("0.45359237"),
    "oz": Decimal("0.028349523125"),
    "ounce": Decimal("0.028349523125"),
    "ounces": Decimal("0.028349523125"),
}

TIME_TO_S = {
    "s": Decimal("1"),
    "sec": Decimal("1"),
    "min": Decimal("60"),
    "h": Decimal("3600"),
    "hr": Decimal("3600"),
    "hour": Decimal("3600"),
    "hours": Decimal("3600"),
    "day": Decimal("86400"),
    "days": Decimal("86400"),
}

TEMP_MAP = {
    "c": "C",
    "°c": "C",
    "celsius": "C",
    "f": "F",
    "°f": "F",
    "fahrenheit": "F",
    "k": "K",
    "kelvin": "K",
}

LINEAR_GROUPS = [LENGTH_TO_M, MASS_TO_KG, TIME_TO_S]

CONVERT_RE = re.compile(
    r"^\s*convert\s+([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\s+(\S+)\s+(?:to|in)\s+(\S+)\s*$",
    re.IGNORECASE,
)


def _format_convert_value(d: Decimal) -> str:
    if d == 0:
        return "0"

    abs_d = abs(d)
    if abs_d >= Decimal("1e15") or (abs_d > 0 and abs_d < Decimal("1e-6")):
        exp = d.adjusted()
        mantissa = d.scaleb(-exp)
        mantissa_r = mantissa.quantize(Decimal("1e-5"), rounding=ROUND_HALF_UP)
        if abs(mantissa_r) >= Decimal("10"):
            mantissa_r /= Decimal("10")
            exp += 1
        m_str = format(mantissa_r, "f")
        if "." in m_str:
            m_str = m_str.rstrip("0").rstrip(".")
        if m_str == "-0":
            m_str = "0"
        sign_exp = "+" if exp >= 0 else "-"
        return f"{m_str}e{sign_exp}{abs(exp)}"

    exp = d.adjusted()
    shift = 5 - exp
    if shift >= 0:
        q = Decimal(10) ** (-shift)
        rounded = d.quantize(q, rounding=ROUND_HALF_UP)
    else:
        factor = Decimal(10) ** (-shift)
        rounded = (d / factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * factor

    if rounded == 0:
        return "0"

    abs_r = abs(rounded)
    if abs_r >= Decimal("1e15"):
        exp2 = rounded.adjusted()
        mantissa2 = rounded.scaleb(-exp2).quantize(Decimal("1e-5"), rounding=ROUND_HALF_UP)
        m_str = format(mantissa2, "f")
        if "." in m_str:
            m_str = m_str.rstrip("0").rstrip(".")
        sign_exp = "+" if exp2 >= 0 else "-"
        return f"{m_str}e{sign_exp}{abs(exp2)}"

    s = format(rounded, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s == "-0":
        s = "0"
    return s


def convert_units(command: str) -> str:
    m = CONVERT_RE.match(command)
    if not m:
        raise ConvertError("неверный формат команды convert (ожидается: convert <число> <из> to <в>)")

    num_str, src_raw, dst_raw = m.groups()
    src = src_raw.lower()
    dst = dst_raw.lower()

    with localcontext() as ctx:
        ctx.prec = 50
        try:
            val = Decimal(num_str)
        except InvalidOperation:
            raise ConvertError(f"некорректное число '{num_str}'")

        if src in TEMP_MAP or dst in TEMP_MAP:
            if src not in TEMP_MAP or dst not in TEMP_MAP:
                raise ConvertError(f"несовместимые единицы измерения: '{src_raw}' и '{dst_raw}'")
            s_t = TEMP_MAP[src]
            d_t = TEMP_MAP[dst]

            if s_t == "C":
                k_val = val + Decimal("273.15")
            elif s_t == "F":
                k_val = (val - Decimal("32")) * Decimal("5") / Decimal("9") + Decimal("273.15")
            else:
                k_val = val

            if k_val < Decimal("0"):
                raise ConvertError("температура не может быть ниже абсолютного нуля (0 K)")

            c_val = k_val - Decimal("273.15")
            if d_t == "C":
                res = c_val
            elif d_t == "F":
                res = c_val * Decimal("9") / Decimal("5") + Decimal("32")
            else:
                res = k_val

            return f"{_format_convert_value(res)} {dst_raw}"

        for group in LINEAR_GROUPS:
            if src in group and dst in group:
                res = val * group[src] / group[dst]
                return f"{_format_convert_value(res)} {dst_raw}"
            if (src in group) != (dst in group):
                raise ConvertError(f"несовместимые единицы измерения: '{src_raw}' и '{dst_raw}'")

        raise ConvertError(f"неизвестная единица измерения: '{src_raw}' или '{dst_raw}'")
