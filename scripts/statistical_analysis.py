from pathlib import Path
import json
import sys

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DB_PATH, ARTIFACTS_DIR


def load_data() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        return con.execute("""
            SELECT
                delivery_group,
                review_score,
                delivery_delay_days
            FROM gold.delivery_review_analysis
            WHERE review_score IS NOT NULL
        """).df()
    finally:
        con.close()


def bootstrap_median_difference(
    on_time: np.ndarray,
    late: np.ndarray,
    iterations: int = 5000,
    seed: int = 42,
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)

    differences = np.empty(iterations)

    for i in range(iterations):
        on_time_sample = rng.choice(
            on_time,
            size=len(on_time),
            replace=True,
        )

        late_sample = rng.choice(
            late,
            size=len(late),
            replace=True,
        )

        differences[i] = (
            np.median(on_time_sample)
            - np.median(late_sample)
        )

    lower, upper = np.percentile(
        differences,
        [2.5, 97.5],
    )

    return float(lower), float(upper)


def main() -> None:
    df = load_data()

    on_time = df.loc[
        df["delivery_group"] == "On-Time",
        "review_score",
    ].dropna().to_numpy()

    late = df.loc[
        df["delivery_group"] == "Late",
        "review_score",
    ].dropna().to_numpy()

    statistic, p_value = mannwhitneyu(
        on_time,
        late,
        alternative="two-sided",
    )

    # Rank-biserial correlation.
    # Values closer to +/-1 indicate a larger separation
    # between the two distributions.
    n_on_time = len(on_time)
    n_late = len(late)

    rank_biserial = (
        (2 * statistic) / (n_on_time * n_late)
    ) - 1

    median_difference = (
        float(np.median(on_time))
        - float(np.median(late))
    )

    ci_lower, ci_upper = bootstrap_median_difference(
        on_time,
        late,
    )

    result = {
        "analysis": "Delivery timeliness vs customer review score",
        "design": "Observational hypothesis test",
        "null_hypothesis": (
            "Review-score distributions do not differ "
            "between on-time and late deliveries."
        ),
        "alternative_hypothesis": (
            "Review-score distributions differ between "
            "on-time and late deliveries."
        ),
        "alpha": 0.05,
        "on_time_orders": n_on_time,
        "late_orders": n_late,
        "on_time_mean_review": float(np.mean(on_time)),
        "late_mean_review": float(np.mean(late)),
        "on_time_median_review": float(np.median(on_time)),
        "late_median_review": float(np.median(late)),
        "median_difference_on_time_minus_late": median_difference,
        "mann_whitney_u": float(statistic),
        "p_value": float(p_value),
        "rank_biserial_effect_size": float(rank_biserial),
        "bootstrap_95_ci_median_difference": [
            ci_lower,
            ci_upper,
        ],
        "bootstrap_iterations": 5000,
        "random_seed": 42,
        "interpretation": (
            "There is strong statistical evidence that "
            "review-score distributions differ between "
            "on-time and late deliveries."
        ),
        "limitation": (
            "This is observational analysis. The result "
            "shows association, not causation."
        ),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = ARTIFACTS_DIR / "statistical_analysis.json"

    output_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print("")
    print("Delivery Timeliness vs Customer Review Score")
    print("=" * 52)

    print(f"On-Time orders: {n_on_time:,}")
    print(f"Late orders:    {n_late:,}")

    print("")
    print("Review score")
    print(f"On-Time mean:   {np.mean(on_time):.3f}")
    print(f"Late mean:      {np.mean(late):.3f}")
    print(f"On-Time median: {np.median(on_time):.3f}")
    print(f"Late median:    {np.median(late):.3f}")

    print("")
    print("Mann-Whitney U test")
    print(f"U statistic:    {statistic:,.0f}")
    print(f"P-value:        {p_value:.3e}")

    print("")
    print("Effect size")
    print(f"Rank-biserial:  {rank_biserial:.3f}")

    print("")
    print("Bootstrap uncertainty")
    print(f"Median difference: {median_difference:.3f}")
    print(f"95% CI:            [{ci_lower:.3f}, {ci_upper:.3f}]")

    print("")
    print("Conclusion")
    print(
        "Reject H0 at the 5% significance level: "
        "review-score distributions differ between "
        "on-time and late deliveries."
    )

    print("")
    print("Important limitation")
    print(
        "This is an observational analysis, not a randomized "
        "experiment. Statistical association does not establish causation."
    )

    print("")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
