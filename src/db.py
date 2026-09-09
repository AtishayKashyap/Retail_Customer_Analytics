from pathlib import Path

import duckdb
import pandas as pd


def connect(
    db_path: Path,
    read_only: bool = False,
) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(
        str(db_path),
        read_only=read_only,
    )


def query_df(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: tuple = (),
) -> pd.DataFrame:
    return con.execute(sql, params).df()
