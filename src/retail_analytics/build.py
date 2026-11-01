"""Build the DuckDB warehouse: staging -> star schema -> marts -> quality gate.

The warehouse is written to a temporary file and only moved into place once every
step and every error-level quality check has passed, so readers never see a
half-built database.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
from filelock import FileLock

from . import config
from .config import SQL_DIR

log = logging.getLogger(__name__)

SQL_FILES = ("01_staging.sql", "02_model.sql", "03_marts.sql", "04_quality.sql")


class QualityGateError(RuntimeError):
    """Raised when an error-severity data-quality check fails."""


@dataclass(frozen=True)
class CheckResult:
    check_group: str
    check_name: str
    severity: str
    failed_rows: int
    description: str

    @property
    def passed(self) -> bool:
        return self.failed_rows == 0


def render_sql(filename: str, raw_dir: Path) -> str:
    template = (SQL_DIR / filename).read_text(encoding="utf-8")
    params = {
        "raw_dir": raw_dir.resolve().as_posix().replace("'", "''"),
        "partial_month_threshold": repr(config.PARTIAL_MONTH_THRESHOLD),
        "min_cohort_size": str(config.MIN_COHORT_SIZE),
    }
    for key, value in params.items():
        template = template.replace("{" + key + "}", value)
    return template


def quality_results(con: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    rows = con.execute(
        "SELECT check_group, check_name, severity, failed_rows, description "
        "FROM quality.check_results ORDER BY check_group, check_name"
    ).fetchall()
    return [CheckResult(*row) for row in rows]


def enforce_quality_gate(results: list[CheckResult]) -> None:
    failures = [r for r in results if r.severity == "error" and not r.passed]
    for r in results:
        if not r.passed:
            level = logging.ERROR if r.severity == "error" else logging.WARNING
            log.log(level, "%-8s %s: %d rows (%s)", r.severity, r.check_name, r.failed_rows, r.description)
    if failures:
        names = ", ".join(f"{r.check_name} ({r.failed_rows})" for r in failures)
        raise QualityGateError(f"{len(failures)} error-level data-quality check(s) failed: {names}")


def build(raw_dir: Path, db_path: Path) -> list[CheckResult]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_name(f".{db_path.name}.{os.getpid()}.tmp")
    tmp_path.unlink(missing_ok=True)

    started = time.perf_counter()
    con = duckdb.connect(str(tmp_path))
    try:
        for filename in SQL_FILES:
            step = time.perf_counter()
            con.execute(render_sql(filename, raw_dir))
            log.info("%-18s %.2fs", filename, time.perf_counter() - step)
        results = quality_results(con)
        enforce_quality_gate(results)
        con.execute("CHECKPOINT")
    except BaseException:
        con.close()
        tmp_path.unlink(missing_ok=True)
        raise
    con.close()

    os.replace(tmp_path, db_path)
    log.info("warehouse ready: %s (%.1fs)", db_path, time.perf_counter() - started)
    return results


def ensure_warehouse(raw_dir: Path, db_path: Path) -> None:
    """Fetch and build if needed. Safe to call from several processes at once."""
    from .fetch import fetch

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(db_path) + ".lock", timeout=900):
        if db_path.exists():
            return
        fetch(raw_dir)
        build(raw_dir, db_path)
