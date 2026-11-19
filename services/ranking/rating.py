"""Pure Elo math for validated completed matches, not a result-ingestion API.

The authoritative service must check identities, rules, and duplicate match IDs
before calling this once per completed match/series. No storage or I/O here.
"""

from dataclasses import dataclass
import math

INITIAL_RATING = 1000.0
K_FACTOR = 24.0


@dataclass(frozen=True)
class RatingChange:
    old_a: float
    old_b: float
    new_a: float
    new_b: float
    delta_a: float
    delta_b: float


def _finite_number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite number')
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f'{name} must be a finite number') from exc
    if not math.isfinite(number):
        raise ValueError(f'{name} must be a finite number')
    return number


def expected_score(rating: float, opponent: float) -> float:
    """Return expected score; use a nonpositive exponent to avoid overflow."""
    own = _finite_number(rating, 'rating')
    other = _finite_number(opponent, 'opponent')
    power = (other / 400.0 - own / 400.0) * math.log(10.0)
    if power >= 0:
        tail = math.exp(-power)
        return tail / (1.0 + tail)
    return 1.0 / (1.0 + math.exp(power))


def rate_match(rating_a: float, rating_b: float, result_a: float) -> RatingChange:
    """Rate one win (1), loss (0), or officially permitted draw (0.5)."""
    a = _finite_number(rating_a, 'rating_a')
    b = _finite_number(rating_b, 'rating_b')
    result = _finite_number(result_a, 'result_a')
    if result not in (0.0, 0.5, 1.0):
        raise ValueError('result_a must be 0, 0.5, or 1')
    delta = K_FACTOR * (result - expected_score(a, b))
    return RatingChange(a, b, a + delta, b - delta, delta, -delta)
