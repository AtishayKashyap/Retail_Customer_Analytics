"""A tiny synthetic Olist dataset whose answers are known in advance."""

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import pytest

HEADERS = {
    "olist_customers_dataset.csv": [
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ],
    "olist_orders_dataset.csv": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_order_items_dataset.csv": [
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ],
    "olist_products_dataset.csv": [
        "product_category_name",
        "product_id",
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ],
    "olist_sellers_dataset.csv": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "olist_order_payments_dataset.csv": [
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ],
    "olist_order_reviews_dataset.csv": [
        "review_id",
        "order_id",
        "review_score",
        "review_comment_title",
        "review_comment_message",
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "product_category_name_translation.csv": ["product_category_name", "product_category_name_english"],
}


class Dataset:
    """Builder for Olist-shaped CSVs. Orders are added per person; ids are generated."""

    def __init__(self) -> None:
        self.rows: dict[str, list[list[object]]] = {name: [] for name in HEADERS}
        self.rows["olist_products_dataset.csv"] = [
            ["beleza_saude", "p1", 40, 300, 2, 500, 10, 10, 10],
            ["informatica_acessorios", "p2", 40, 300, 2, 800, 10, 10, 10],
        ]
        self.rows["olist_sellers_dataset.csv"] = [["s1", 1000, "sao paulo", "SP"]]
        self.rows["product_category_name_translation.csv"] = [
            ["beleza_saude", "health_beauty"],
            ["informatica_acessorios", "computers_accessories"],
        ]
        self._n = 0

    def order(
        self,
        person: str,
        purchased: str,
        price: float,
        *,
        state: str = "SP",
        status: str = "delivered",
        delivered: str | None = "auto",
        estimated: str | None = None,
        review: int | None = 5,
    ) -> str:
        self._n += 1
        oid, cid = f"o{self._n}", f"c{self._n}"
        if estimated is None:
            promised = datetime.fromisoformat(purchased) + timedelta(days=10)
            estimated = promised.strftime("%Y-%m-%d 00:00:00")
        if delivered == "auto":
            delivered = estimated[:10] + " 10:00:00"
        carrier = purchased if delivered else ""
        self.rows["olist_customers_dataset.csv"].append([cid, person, 1000, "city", state])
        self.rows["olist_orders_dataset.csv"].append(
            [oid, cid, status, purchased, purchased, carrier, delivered or "", estimated]
        )
        self.rows["olist_order_items_dataset.csv"].append([oid, 1, "p1", "s1", purchased, price, 10])
        self.rows["olist_order_payments_dataset.csv"].append([oid, 1, "credit_card", 1, price + 10])
        if review is not None:
            self.rows["olist_order_reviews_dataset.csv"].append(
                [f"r{self._n}", oid, review, "", "", purchased, purchased]
            )
        return oid

    def write(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        for name, header in HEADERS.items():
            with (directory / name).open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                writer.writerows(self.rows[name])
        return directory


def standard_dataset() -> Dataset:
    """Monthly volume Jan-Dec 2017 so no month is 'partial', plus people with known RFM profiles."""
    ds = Dataset()
    n = 0
    for month in range(1, 13):
        for _ in range(20):
            n += 1
            ds.order(f"filler{n}", f"2017-{month:02d}-10 12:00:00", 50 + (n % 7))
    # repeat, recent, big spender -> Champions
    ds.order("champion", "2017-06-01 10:00:00", 900)
    ds.order("champion", "2017-12-20 10:00:00", 900)
    # one order, recent, big spender -> Promising (never Champions)
    ds.order("big_once", "2017-12-21 10:00:00", 5000)
    # repeat buyer who went quiet -> At Risk
    ds.order("lapsed", "2017-01-02 10:00:00", 60)
    ds.order("lapsed", "2017-01-03 10:00:00", 60)
    # canceled orders are not revenue and not frequency
    ds.order("canceller", "2017-12-22 10:00:00", 70)
    ds.order("canceller", "2017-12-23 10:00:00", 99999, status="canceled", delivered=None, review=None)
    # delivered at 15:00 on the promised day -> on time
    ds.order(
        "sameday", "2017-11-01 10:00:00", 80, estimated="2017-11-10 00:00:00", delivered="2017-11-10 15:00:00", review=4
    )
    # delivered the day after the promise -> late
    ds.order(
        "lateone", "2017-11-02 10:00:00", 80, estimated="2017-11-10 00:00:00", delivered="2017-11-11 09:00:00", review=1
    )
    return ds


@pytest.fixture
def build_warehouse(tmp_path: Path) -> Callable[[Dataset], Path]:
    from retail_analytics.build import build

    def _build(ds: Dataset) -> Path:
        raw = ds.write(tmp_path / "raw")
        db = tmp_path / "warehouse" / "test.duckdb"
        db.unlink(missing_ok=True)
        build(raw, db)
        return db

    return _build


@pytest.fixture
def warehouse(build_warehouse: Callable[[Dataset], Path]) -> Path:
    return build_warehouse(standard_dataset())
