"""Do late deliveries get worse reviews?

Two-sided Mann-Whitney U on order-level review scores (on-time vs late), with
rank-biserial effect size and a bootstrap CI for it, plus the share of 1-2 star
reviews in each group with Wilson intervals. Interpretation text is derived from
the numbers, never hard-coded.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from scipy.stats import mannwhitneyu, norm

ALPHA = 0.05


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float


@dataclass(frozen=True)
class DeliveryReviewResult:
    n_on_time: int
    n_late: int
    mean_on_time: float
    mean_late: float
    median_on_time: float
    median_late: float
    u_statistic: float
    p_value: float
    rank_biserial: Interval
    low_review_share_on_time: Interval
    low_review_share_late: Interval
    low_review_share_difference: Interval
    alpha: float
    significant: bool
    interpretation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> Interval:
    if n == 0:
        return Interval(math.nan, math.nan, math.nan)
    z = float(norm.ppf(0.5 + confidence / 2))
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return Interval(p, centre - half, centre + half)


def proportion_difference(a: Interval, n_a: int, b: Interval, n_b: int, confidence: float = 0.95) -> Interval:
    """Newcombe's hybrid score interval for p_a - p_b, built from two Wilson intervals."""
    d = a.estimate - b.estimate
    low = d - math.sqrt((a.estimate - a.low) ** 2 + (b.high - b.estimate) ** 2)
    high = d + math.sqrt((a.high - a.estimate) ** 2 + (b.estimate - b.low) ** 2)
    return Interval(d, low, high)


def rank_biserial(u_first: float, n_first: int, n_second: int) -> float:
    """r = P(X > Y) - P(X < Y) for X from the first sample; +1 means the first group always scores higher."""
    return 2 * u_first / (n_first * n_second) - 1


def bootstrap_rank_biserial(
    first: np.ndarray, second: np.ndarray, iterations: int = 2000, seed: int = 42
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    estimates = np.empty(iterations)
    for i in range(iterations):
        a = rng.choice(first, size=first.size, replace=True)
        b = rng.choice(second, size=second.size, replace=True)
        u = mannwhitneyu(a, b, alternative="two-sided").statistic
        estimates[i] = rank_biserial(float(u), a.size, b.size)
    low, high = np.percentile(estimates, [2.5, 97.5])
    return float(low), float(high)


def format_p(p_value: float) -> str:
    """scipy reports p = 0 when it underflows double precision; say so instead of printing 0."""
    return "< 1e-300" if p_value < 1e-300 else f"= {p_value:.3g}"


def interpret(significant: bool, r: float, p_value: float) -> str:
    magnitude = abs(r)
    size = "negligible" if magnitude < 0.1 else "small" if magnitude < 0.3 else "medium" if magnitude < 0.5 else "large"
    if not significant:
        return (
            f"No evidence of a difference at alpha={ALPHA} (p {format_p(p_value)}); "
            f"the observed effect is {size} (r={r:.2f})."
        )
    direction = "higher" if r > 0 else "lower"
    return (
        f"On-time orders receive systematically {direction} review scores than late orders "
        f"(p {format_p(p_value)}); the effect is {size} (rank-biserial r={r:.2f})."
    )


def analyse(on_time: np.ndarray, late: np.ndarray, iterations: int = 2000, seed: int = 42) -> DeliveryReviewResult:
    on_time = np.asarray(on_time, dtype=float)
    late = np.asarray(late, dtype=float)
    test = mannwhitneyu(on_time, late, alternative="two-sided")
    u, p_value = float(test.statistic), float(test.pvalue)
    r = rank_biserial(u, on_time.size, late.size)
    r_low, r_high = bootstrap_rank_biserial(on_time, late, iterations, seed)

    low_on_time = wilson_interval(int((on_time <= 2).sum()), on_time.size)
    low_late = wilson_interval(int((late <= 2).sum()), late.size)
    significant = p_value < ALPHA

    return DeliveryReviewResult(
        n_on_time=int(on_time.size),
        n_late=int(late.size),
        mean_on_time=float(on_time.mean()),
        mean_late=float(late.mean()),
        median_on_time=float(np.median(on_time)),
        median_late=float(np.median(late)),
        u_statistic=u,
        p_value=p_value,
        rank_biserial=Interval(r, r_low, r_high),
        low_review_share_on_time=low_on_time,
        low_review_share_late=low_late,
        low_review_share_difference=proportion_difference(low_late, late.size, low_on_time, on_time.size),
        alpha=ALPHA,
        significant=significant,
        interpretation=interpret(significant, r, p_value),
    )
