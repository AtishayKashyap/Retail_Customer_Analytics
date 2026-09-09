from pathlib import Path
import sys

import duckdb


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DB_PATH


def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def test_core_tables_exist():
    con = get_connection()

    try:
        tables = {
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema IN ('silver', 'gold', 'quality', 'performance')
                """
            ).fetchall()
        }

        expected = {
            "customers",
            "orders",
            "order_items",
            "products",
            "sellers",
            "payments",
            "reviews",
            "category_translation",
            "order_review_summary",
            "customer_order_history",
            "customer_360",
            "monthly_kpis",
            "category_kpis",
            "cohort_retention",
            "customer_rfm",
            "customer_segments",
            "row_counts",
            "required_field_checks",
            "duplicate_key_checks",
            "referential_integrity_checks",
            "chronology_checks",
            "monetary_checks",
            "summary",
            "table_stats",
            "benchmark_config",
        }

        missing = expected - tables
        assert not missing, f"Missing tables: {sorted(missing)}"

    finally:
        con.close()


def test_customer_360_has_customers():
    con = get_connection()

    try:
        count = con.execute(
            "SELECT COUNT(*) FROM gold.customer_360"
        ).fetchone()[0]

        assert count > 0

    finally:
        con.close()


def test_customer_order_history_has_orders():
    con = get_connection()

    try:
        history_count = con.execute(
            "SELECT COUNT(*) FROM gold.customer_order_history"
        ).fetchone()[0]

        orders_count = con.execute(
            "SELECT COUNT(*) FROM silver.orders"
        ).fetchone()[0]

        assert history_count > 0
        assert history_count <= orders_count

    finally:
        con.close()


def test_no_orphan_orders():
    con = get_connection()

    try:
        orphan_count = con.execute(
            """
            SELECT COUNT(*)
            FROM silver.orders o
            LEFT JOIN silver.customers c
                ON o.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
            """
        ).fetchone()[0]

        assert orphan_count == 0

    finally:
        con.close()


def test_no_duplicate_order_keys():
    con = get_connection()

    try:
        duplicate_count = con.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT order_id
                FROM silver.orders
                GROUP BY order_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        assert duplicate_count == 0

    finally:
        con.close()


def test_category_mart_has_revenue():
    con = get_connection()

    try:
        row_count = con.execute(
            "SELECT COUNT(*) FROM gold.category_kpis"
        ).fetchone()[0]

        revenue = con.execute(
            """
            SELECT COALESCE(SUM(gross_merchandise_value), 0)
            FROM gold.category_kpis
            """
        ).fetchone()[0]

        assert row_count > 0
        assert revenue > 0

    finally:
        con.close()


def test_quality_summary_exists():
    con = get_connection()

    try:
        count = con.execute(
            "SELECT COUNT(*) FROM quality.summary"
        ).fetchone()[0]

        assert count > 0

    finally:
        con.close()
