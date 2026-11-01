from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from retail_analytics import queries
from retail_analytics.build import QualityGateError

from .conftest import Dataset, standard_dataset


def one(db: Path, sql: str, *params: object) -> object:
    with duckdb.connect(str(db), read_only=True) as con:
        row = con.execute(sql, list(params)).fetchone()
        assert row is not None
        return row[0]


def segment(db: Path, person: str) -> str:
    return str(one(db, "SELECT segment FROM gold.mart_rfm WHERE customer_unique_id = ?", person))


def test_repeat_high_value_recent_customer_is_champion(warehouse: Path) -> None:
    assert segment(warehouse, "champion") == "Champions"


def test_one_time_buyer_is_never_champion_however_much_they_spend(warehouse: Path) -> None:
    assert segment(warehouse, "big_once") == "Promising"


def test_repeat_buyer_who_went_quiet_is_at_risk(warehouse: Path) -> None:
    assert segment(warehouse, "lapsed") == "At Risk"


def test_canceled_orders_do_not_count_as_revenue_or_frequency(warehouse: Path) -> None:
    assert one(warehouse, "SELECT frequency FROM gold.mart_rfm WHERE customer_unique_id='canceller'") == 1
    assert float(one(warehouse, "SELECT monetary_value FROM gold.mart_rfm WHERE customer_unique_id='canceller'")) == 80
    canceled_value = one(warehouse, "SELECT SUM(order_value) FROM gold.fct_orders WHERE NOT is_valid")
    total = float(one(warehouse, "SELECT revenue FROM gold.mart_scope_kpis WHERE scope='ALL'"))
    expected = float(one(warehouse, "SELECT SUM(order_value) FROM gold.fct_orders WHERE is_valid"))
    assert total == pytest.approx(expected)
    assert float(canceled_value) == pytest.approx(100009)


def test_delivery_later_on_the_promised_day_is_on_time(warehouse: Path) -> None:
    assert (
        one(
            warehouse,
            "SELECT c.customer_unique_id FROM gold.fct_orders o JOIN silver.customers c "
            "ON c.customer_unique_id = o.customer_unique_id WHERE o.is_late LIMIT 1",
        )
        == "lateone"
    )
    sameday = one(warehouse, "SELECT is_late FROM gold.fct_orders WHERE customer_unique_id='sameday'")
    assert sameday is False


def test_rfm_is_deterministic_across_builds(build_warehouse) -> None:  # type: ignore[no-untyped-def]
    first = build_warehouse(standard_dataset())
    with duckdb.connect(str(first), read_only=True) as con:
        a = con.execute("SELECT customer_unique_id, r_score, m_score, segment FROM gold.mart_rfm ORDER BY 1").fetchall()
    second = build_warehouse(standard_dataset())
    with duckdb.connect(str(second), read_only=True) as con:
        b = con.execute("SELECT customer_unique_id, r_score, m_score, segment FROM gold.mart_rfm ORDER BY 1").fetchall()
    assert a == b


def test_state_and_national_kpis_come_from_the_same_definition(build_warehouse) -> None:  # type: ignore[no-untyped-def]
    ds = standard_dataset()
    ds.order("rio1", "2017-07-01 10:00:00", 300, state="RJ")
    db = build_warehouse(ds)
    with duckdb.connect(str(db), read_only=True) as con:
        total = con.execute("SELECT orders, revenue FROM gold.mart_scope_kpis WHERE scope='ALL'").fetchone()
        parts = con.execute("SELECT SUM(orders), SUM(revenue) FROM gold.mart_scope_kpis WHERE scope<>'ALL'").fetchone()
        assert total == parts
        assert queries.scope_kpis(con, "RJ").orders == 1


def test_partial_months_are_flagged(build_warehouse) -> None:  # type: ignore[no-untyped-def]
    ds = standard_dataset()
    ds.order("early", "2016-09-04 10:00:00", 50)
    db = build_warehouse(ds)
    assert one(db, "SELECT is_partial FROM gold.dim_month WHERE order_month = DATE '2016-09-01'") is True
    assert one(db, "SELECT bool_or(is_partial) FROM gold.dim_month WHERE year(order_month) = 2017") is False


def test_cohorts_smaller_than_minimum_are_marked_unreliable(warehouse: Path) -> None:
    assert one(warehouse, "SELECT bool_and(NOT is_reliable) FROM gold.mart_cohort_retention") is True


def test_duplicate_order_ids_fail_the_build(build_warehouse, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ds = standard_dataset()
    ds.rows["olist_orders_dataset.csv"].append(list(ds.rows["olist_orders_dataset.csv"][0]))
    with pytest.raises(QualityGateError, match=r"orders\.order_id"):
        build_warehouse(ds)
    assert not (tmp_path / "warehouse" / "test.duckdb").exists(), "a failed build must not leave a database behind"


def test_orphan_order_lines_fail_the_build(build_warehouse) -> None:  # type: ignore[no-untyped-def]
    ds = standard_dataset()
    ds.rows["olist_order_items_dataset.csv"].append(["ghost", 1, "p1", "s1", "2017-01-01 00:00:00", 10, 1])
    with pytest.raises(QualityGateError, match="order_items -> orders"):
        build_warehouse(ds)


def test_unparseable_values_fail_the_build(build_warehouse) -> None:  # type: ignore[no-untyped-def]
    ds = standard_dataset()
    ds.rows["olist_order_items_dataset.csv"][0][5] = "12,50"
    with pytest.raises(QualityGateError, match="order_items money"):
        build_warehouse(ds)


def test_known_source_quirks_are_warnings_not_errors(build_warehouse) -> None:  # type: ignore[no-untyped-def]
    ds = standard_dataset()
    ds.rows["olist_order_payments_dataset.csv"][0][4] = 1.0  # payment differs from items + freight
    db = build_warehouse(ds)
    assert one(db, "SELECT failed_rows FROM quality.check_results WHERE check_name = 'payments = items + freight'") == 1


def test_dashboard_queries_run_for_all_and_state(warehouse: Path) -> None:
    with duckdb.connect(str(warehouse), read_only=True) as con:
        assert queries.states(con) == ["SP"]
        for scope in ("ALL", "SP"):
            assert not queries.monthly_kpis(con, scope).empty
            assert not queries.segment_summary(con, scope).empty
            assert not queries.category_kpis(con, scope).empty
            assert queries.insights(con, scope)
        assert queries.search_customers(con, "ALL", "champ").customer_unique_id.tolist() == ["champion"]
        assert len(queries.customer_orders(con, "champion")) == 2
        dist = queries.review_distribution(con)
        assert dist.groupby("delivery_group")["share"].sum().round(9).eq(1).all()
        assert not queries.cohort_retention(con).empty
        assert len(queries.quality_checks(con)) > 20


def test_empty_dataset_builder_has_every_file(tmp_path: Path) -> None:
    raw = Dataset().write(tmp_path / "raw")
    assert len(list(raw.glob("*.csv"))) == 8
