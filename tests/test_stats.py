from __future__ import annotations

import numpy as np
import pytest

from retail_analytics.stats import analyse, format_p, proportion_difference, rank_biserial, wilson_interval


def test_wilson_interval_matches_reference_values() -> None:
    # Reference: Wilson score interval for 81/263 at 95% (Brown, Cai & DasGupta 2001 style example).
    i = wilson_interval(81, 263)
    assert i.estimate == pytest.approx(0.30798, abs=1e-4)
    assert i.low == pytest.approx(0.2553, abs=1e-3)
    assert i.high == pytest.approx(0.3662, abs=1e-3)


def test_wilson_interval_stays_inside_0_1_at_the_edges() -> None:
    zero = wilson_interval(0, 20)
    assert zero.low == pytest.approx(0, abs=1e-12) and 0 < zero.high < 0.2
    full = wilson_interval(20, 20)
    assert full.high == pytest.approx(1, abs=1e-12) and 0.8 < full.low < 1


def test_proportion_difference_contains_the_point_estimate() -> None:
    a, b = wilson_interval(60, 100), wilson_interval(10, 100)
    d = proportion_difference(a, 100, b, 100)
    assert d.estimate == pytest.approx(0.5)
    assert d.low < 0.5 < d.high


def test_rank_biserial_extremes() -> None:
    assert rank_biserial(u_first=100, n_first=10, n_second=10) == 1
    assert rank_biserial(u_first=0, n_first=10, n_second=10) == -1
    assert rank_biserial(u_first=50, n_first=10, n_second=10) == 0


def test_clear_difference_is_significant_and_says_so() -> None:
    rng = np.random.default_rng(1)
    on_time = rng.choice([4, 5], size=400, p=[0.3, 0.7])
    late = rng.choice([1, 2, 3], size=200)
    result = analyse(on_time, late, iterations=200)
    assert result.significant
    assert result.rank_biserial.estimate > 0.9
    assert result.rank_biserial.low <= result.rank_biserial.estimate <= result.rank_biserial.high
    assert "higher" in result.interpretation and "large" in result.interpretation


def test_identical_distributions_are_not_reported_as_a_difference() -> None:
    rng = np.random.default_rng(2)
    sample = rng.integers(1, 6, size=600)
    result = analyse(sample[:300], sample[300:], iterations=200)
    assert not result.significant
    assert result.interpretation.startswith("No evidence")


def test_underflowed_p_value_is_not_printed_as_zero() -> None:
    assert format_p(0.0) == "< 1e-300"
    assert format_p(0.0123) == "= 0.0123"
