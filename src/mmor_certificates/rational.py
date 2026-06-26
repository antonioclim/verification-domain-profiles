"""Small exact-linear-algebra helpers based on :class:`fractions.Fraction`."""
from __future__ import annotations

from fractions import Fraction
from math import gcd
from functools import reduce
from typing import Iterable, Sequence

Q = Fraction


def q(value: int | float | str | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        return Fraction(str(value))
    return Fraction(value)


def dot(a: Sequence[Fraction], b: Sequence[Fraction]) -> Fraction:
    if len(a) != len(b):
        raise ValueError("dot-product dimension mismatch")
    return sum((x * y for x, y in zip(a, b)), Q(0))


def lcm(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return abs(a // gcd(a, b) * b)


def lcm_many(values: Iterable[int]) -> int:
    vals = list(values)
    return reduce(lcm, vals, 1)


def solve_square(
    rows: Sequence[Sequence[Fraction]], rhs: Sequence[Fraction]
) -> tuple[Fraction, ...] | None:
    """Solve a square rational system by full Gauss--Jordan elimination."""
    n = len(rows)
    if n == 0 or len(rhs) != n or any(len(row) != n for row in rows):
        return None
    aug = [list(map(q, row)) + [q(value)] for row, value in zip(rows, rhs)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if pivot is None:
            return None
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col]
        aug[col] = [value / divisor for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor:
                aug[row] = [x - factor * y for x, y in zip(aug[row], aug[col])]
    return tuple(aug[i][-1] for i in range(n))


def rank(rows: Sequence[Sequence[Fraction]]) -> int:
    """Return exact row rank."""
    if not rows:
        return 0
    matrix = [list(map(q, row)) for row in rows]
    nrows = len(matrix)
    ncols = len(matrix[0])
    r = 0
    for col in range(ncols):
        pivot = next((i for i in range(r, nrows) if matrix[i][col] != 0), None)
        if pivot is None:
            continue
        matrix[r], matrix[pivot] = matrix[pivot], matrix[r]
        divisor = matrix[r][col]
        matrix[r] = [value / divisor for value in matrix[r]]
        for i in range(nrows):
            if i == r:
                continue
            factor = matrix[i][col]
            if factor:
                matrix[i] = [x - factor * y for x, y in zip(matrix[i], matrix[r])]
        r += 1
        if r == nrows:
            break
    return r


def fraction_tuple(values: Iterable[int | str | Fraction]) -> tuple[Fraction, ...]:
    return tuple(q(value) for value in values)


def fraction_json(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def parse_fraction(value: str | int | Fraction) -> Fraction:
    return q(value)


def scale_rational_vector(values: Sequence[Fraction]) -> tuple[tuple[int, ...], int]:
    """Return primitive integer vector and positive common denominator."""
    den = lcm_many(value.denominator for value in values)
    ints = [value.numerator * (den // value.denominator) for value in values]
    common = reduce(gcd, (abs(v) for v in ints if v), 0)
    if common > 1:
        ints = [v // common for v in ints]
        den //= common
    if den < 0:
        den = -den
        ints = [-v for v in ints]
    return tuple(ints), den
