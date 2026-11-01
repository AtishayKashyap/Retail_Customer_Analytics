from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest
import requests

from retail_analytics import fetch as fetch_module
from retail_analytics.cli import main
from retail_analytics.report import write_reports

from .conftest import standard_dataset


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self.content = body
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise requests.HTTPError(f"status {self.status}")


@pytest.fixture
def one_file(monkeypatch: pytest.MonkeyPatch) -> bytes:
    body = b"a,b\n1,2\n"
    monkeypatch.setattr(fetch_module, "SOURCE_FILES", {"x.csv": hashlib.sha256(body).hexdigest()})
    monkeypatch.setattr(fetch_module.time, "sleep", lambda _s: None)
    return body


def test_fetch_downloads_and_verifies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, one_file: bytes) -> None:
    calls: list[str] = []

    def fake_get(url: str, timeout: int) -> FakeResponse:
        calls.append(url)
        return FakeResponse(one_file)

    monkeypatch.setattr(fetch_module.requests, "get", fake_get)
    fetch_module.fetch(tmp_path)
    fetch_module.fetch(tmp_path)  # second run: file already verified, no download
    assert (tmp_path / "x.csv").read_bytes() == one_file
    assert len(calls) == 1


def test_fetch_retries_transient_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, one_file: bytes) -> None:
    responses = iter([FakeResponse(b"", 503), FakeResponse(one_file)])
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, timeout: next(responses))
    fetch_module.fetch(tmp_path)
    assert (tmp_path / "x.csv").read_bytes() == one_file


def test_fetch_rejects_a_changed_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, one_file: bytes) -> None:
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, timeout: FakeResponse(b"tampered"))
    with pytest.raises(fetch_module.ChecksumError):
        fetch_module.fetch(tmp_path)


def test_reports_are_written(warehouse: Path, tmp_path: Path) -> None:
    with duckdb.connect(str(warehouse), read_only=True) as con:
        write_reports(con, tmp_path / "reports", iterations=50)
    result = json.loads((tmp_path / "reports" / "delivery_review_test.json").read_text())
    assert result["n_late"] == 1 and result["n_on_time"] > 200
    text = (tmp_path / "reports" / "RESULTS.md").read_text()
    assert "R$" in text and "Rank-biserial" in text
    assert (tmp_path / "reports" / "quality_checks.csv").exists()


def test_cli_build_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = standard_dataset().write(tmp_path / "raw")
    monkeypatch.setenv("RETAIL_RAW_DIR", str(raw))
    monkeypatch.setenv("RETAIL_DB_PATH", str(tmp_path / "w.duckdb"))
    monkeypatch.setenv("RETAIL_REPORTS_DIR", str(tmp_path / "reports"))
    assert main(["build"]) == 0
    assert main(["report", "--bootstrap-iterations", "20"]) == 0
    assert (tmp_path / "reports" / "RESULTS.md").exists()


def test_cli_returns_nonzero_when_quality_gate_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ds = standard_dataset()
    ds.rows["olist_orders_dataset.csv"].append(list(ds.rows["olist_orders_dataset.csv"][0]))
    monkeypatch.setenv("RETAIL_RAW_DIR", str(ds.write(tmp_path / "raw")))
    monkeypatch.setenv("RETAIL_DB_PATH", str(tmp_path / "w.duckdb"))
    assert main(["build"]) == 1
    assert not (tmp_path / "w.duckdb").exists()
