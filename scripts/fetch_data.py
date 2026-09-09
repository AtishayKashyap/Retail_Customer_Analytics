from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import RAW_DIR


BASE_URL = (
    "https://raw.githubusercontent.com/"
    "olist/work-at-olist-data/master/datasets"
)

FILES = {
    "olist_customers_dataset.csv":
        f"{BASE_URL}/olist_customers_dataset.csv",

    "olist_orders_dataset.csv":
        f"{BASE_URL}/olist_orders_dataset.csv",

    "olist_order_items_dataset.csv":
        f"{BASE_URL}/olist_order_items_dataset.csv",

    "olist_products_dataset.csv":
        f"{BASE_URL}/olist_products_dataset.csv",

    "olist_sellers_dataset.csv":
        f"{BASE_URL}/olist_sellers_dataset.csv",

    "olist_order_payments_dataset.csv":
        f"{BASE_URL}/olist_order_payments_dataset.csv",

    "olist_order_reviews_dataset.csv":
        f"{BASE_URL}/olist_order_reviews_dataset.csv",

    "product_category_name_translation.csv":
        f"{BASE_URL}/product_category_name_translation.csv",
}


def download_file(url: str, destination: Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    destination.write_bytes(response.content)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in FILES.items():
        destination = RAW_DIR / filename

        if destination.exists() and destination.stat().st_size > 0:
            print(f"Already exists: {filename}")
            continue

        print(f"Downloading: {filename}")
        download_file(url, destination)

    print("")
    print("Raw Olist data is ready.")


if __name__ == "__main__":
    main()
