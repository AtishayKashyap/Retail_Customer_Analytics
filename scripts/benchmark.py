from pathlib import Path
import json
import statistics
import sys
import time

import duckdb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DB_PATH, ARTIFACTS_DIR


RUNS = 5


RAW_QUERY = """
WITH order_level AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_status,
        SUM(oi.price + oi.freight_value) AS order_value
    FROM silver.customers c
    JOIN silver.orders o
        ON c.customer_id = o.customer_id
    LEFT JOIN silver.order_items oi
        ON o.order_id = oi.order_id
    GROUP BY
        c.customer_unique_id,
        o.order_id,
        o.order_status
)
SELECT
    customer_unique_id,

    COUNT(DISTINCT order_id) AS order_count,

    SUM(
        CASE
            WHEN order_status NOT IN ('canceled', 'unavailable')
            THEN order_value
            ELSE 0
        END
    ) AS total_value,

    AVG(
        CASE
            WHEN order_status NOT IN ('canceled', 'unavailable')
            THEN order_value
        END
    ) AS avg_order_value

FROM order_level
GROUP BY customer_unique_id
"""


OPTIMIZED_QUERY = """
SELECT
    customer_unique_id,
    order_count,
    total_revenue AS total_value,
    avg_order_value
FROM gold.customer_360
"""


def timed_query(con, sql):
    start = time.perf_counter()
    con.execute(sql).fetchall()
    return time.perf_counter() - start


def normalized_metrics(con, sql):
    rows = con.execute(sql).fetchall()

    return {
        row[0]: (
            int(row[1]),
            round(float(row[2] or 0), 2),
            round(float(row[3] or 0), 2),
        )
        for row in rows
    }


def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        # Warm-up
        con.execute(RAW_QUERY).fetchall()
        con.execute(OPTIMIZED_QUERY).fetchall()

        raw_times = [
            timed_query(con, RAW_QUERY)
            for _ in range(RUNS)
        ]

        optimized_times = [
            timed_query(con, OPTIMIZED_QUERY)
            for _ in range(RUNS)
        ]

        raw_metrics = normalized_metrics(con, RAW_QUERY)
        optimized_metrics = normalized_metrics(con, OPTIMIZED_QUERY)

        equivalent = raw_metrics == optimized_metrics

        raw_median = statistics.median(raw_times)
        optimized_median = statistics.median(optimized_times)

        speedup = (
            raw_median / optimized_median
            if optimized_median > 0
            else None
        )

        results = {
            "runs": RUNS,
            "raw_join_seconds": {
                "mean": statistics.mean(raw_times),
                "median": raw_median,
                "min": min(raw_times),
                "max": max(raw_times),
            },
            "optimized_mart_seconds": {
                "mean": statistics.mean(optimized_times),
                "median": optimized_median,
                "min": min(optimized_times),
                "max": max(optimized_times),
            },
            "median_speedup": speedup,
            "metric_equivalence": {
                "raw_rows": len(raw_metrics),
                "optimized_rows": len(optimized_metrics),
                "validated": equivalent,
            },
        }

        output_path = ARTIFACTS_DIR / "benchmark_results.json"

        output_path.write_text(
            json.dumps(results, indent=2),
            encoding="utf-8",
        )

        print("")
        print("Benchmark completed.")
        print(f"Runs: {RUNS}")
        print(f"Raw median:       {raw_median:.6f} s")
        print(f"Optimized median: {optimized_median:.6f} s")

        if speedup is not None:
            print(f"Median speedup:   {speedup:.2f}x")

        print(f"Raw customers:    {len(raw_metrics)}")
        print(f"Gold customers:   {len(optimized_metrics)}")
        print(f"Metric equivalent: {equivalent}")
        print(f"Saved to: {output_path}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
