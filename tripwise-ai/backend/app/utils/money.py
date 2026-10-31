from decimal import Decimal, ROUND_HALF_UP


TWOPLACES = Decimal("0.01")


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def as_float(value: Decimal) -> float:
    return float(value)
