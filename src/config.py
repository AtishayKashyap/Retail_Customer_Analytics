from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
ARTIFACTS_DIR = ROOT / "artifacts"

DB_PATH = WAREHOUSE_DIR / "analytics.duckdb"
