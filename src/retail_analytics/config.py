"""Paths and analysis settings. Every path can be overridden with an environment variable."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = Path(__file__).resolve().parent / "sql"


@dataclass(frozen=True)
class Settings:
    raw_dir: Path
    db_path: Path
    reports_dir: Path

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            raw_dir=Path(os.environ.get("RETAIL_RAW_DIR", ROOT / "data" / "raw")),
            db_path=Path(os.environ.get("RETAIL_DB_PATH", ROOT / "data" / "warehouse" / "analytics.duckdb")),
            reports_dir=Path(os.environ.get("RETAIL_REPORTS_DIR", ROOT / "reports")),
        )


# Statuses that never turned into revenue. Every KPI uses the same definition.
INVALID_ORDER_STATUSES = ("canceled", "unavailable")

# Cohorts smaller than this are shown greyed out: one or two customers make the rate meaningless.
MIN_COHORT_SIZE = 30

# A month is "partial" (excluded from trends) when it has fewer than this share of the median monthly orders.
PARTIAL_MONTH_THRESHOLD = 0.10

CURRENCY_SYMBOL = "R$"
