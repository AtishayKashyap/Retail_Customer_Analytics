"""Command line: retail fetch | build | report | all."""

from __future__ import annotations

import argparse
import logging
import sys

import duckdb

from .build import QualityGateError, build
from .config import Settings
from .fetch import ChecksumError, fetch
from .report import write_reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="retail", description=__doc__)
    parser.add_argument("command", choices=["fetch", "build", "report", "all"])
    parser.add_argument("--bootstrap-iterations", type=int, default=2000)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)-7s %(message)s")
    settings = Settings.from_env()
    try:
        if args.command in ("fetch", "all"):
            fetch(settings.raw_dir)
        if args.command in ("build", "all"):
            build(settings.raw_dir, settings.db_path)
        if args.command in ("report", "all"):
            with duckdb.connect(str(settings.db_path), read_only=True) as con:
                write_reports(con, settings.reports_dir, args.bootstrap_iterations)
            logging.info("reports written to %s", settings.reports_dir)
    except (QualityGateError, ChecksumError) as exc:
        logging.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
