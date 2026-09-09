from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DB_PATH


SQL_DIR = ROOT / "sql"


def run_sql_file(con, filename: str) -> None:
    sql_path = SQL_DIR / filename
    sql = sql_path.read_text(encoding="utf-8")
    con.execute(sql)


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))

    try:
        for filename in (
            "01_silver.sql",
            "02_gold.sql",
            "03_quality.sql",
            "04_performance.sql",
        ):
            print(f"Running {filename}...")
            run_sql_file(con, filename)

    finally:
        con.close()

    print("")
    print(f"Warehouse built successfully: {DB_PATH}")


if __name__ == "__main__":
    main()
