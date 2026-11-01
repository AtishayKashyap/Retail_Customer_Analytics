"""Download the Olist source files, verifying each one against a pinned SHA-256."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets"

# Pinned so a changed or truncated upstream file is caught instead of silently analysed.
SOURCE_FILES: dict[str, str] = {
    "olist_customers_dataset.csv": "c26c17f59f3027a6a0dbeb8f1fa373c38f3323ecc84f225a8f4820e5bb288df8",
    "olist_order_items_dataset.csv": "4f6abdbbc94036d0df4a76fa0520c072e31a40119d70f7f370fba1e2285d2bcb",
    "olist_order_payments_dataset.csv": "61674868ed7b872aac3dcd95bf774448a88f6426b183f21be55f75af021ffdec",
    "olist_order_reviews_dataset.csv": "012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7",
    "olist_orders_dataset.csv": "8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf",
    "olist_products_dataset.csv": "3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc",
    "olist_sellers_dataset.csv": "31eb9bd50d684526a78f2389413ce61841e97692de7b828fe7d956b534586312",
    "product_category_name_translation.csv": "a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278",
}


class ChecksumError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, destination: Path, attempts: int = 4) -> None:
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            tmp = destination.with_suffix(".part")
            tmp.write_bytes(response.content)
            tmp.replace(destination)
            return
        except requests.RequestException as exc:
            if attempt == attempts:
                raise
            wait = 2**attempt
            log.warning("download of %s failed (%s); retrying in %ss", url, exc, wait)
            time.sleep(wait)


def fetch(raw_dir: Path, verify: bool = True) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, expected in SOURCE_FILES.items():
        path = raw_dir / name
        if path.exists() and (not verify or sha256(path) == expected):
            log.info("ok        %s", name)
            continue
        log.info("download  %s", name)
        _download(f"{BASE_URL}/{name}", path)
        if verify and (actual := sha256(path)) != expected:
            raise ChecksumError(f"{name}: expected sha256 {expected}, got {actual}")
