from __future__ import annotations

import argparse
import json
import os

from marketing_diagnosis.data import normalize_dataset
from marketing_diagnosis.excel_loader import load_excel_dataset
from marketing_diagnosis.db_loader import load_database_dataset, load_mysql_dsn_dataset
from marketing_diagnosis.reporting import write_reports
from marketing_diagnosis.rules import process


def _run(raw_dataset, output):
    normalized = normalize_dataset(raw_dataset)
    result = process(normalized)
    paths = write_reports(result, output)
    return {"status": result.get("status"), **paths, "data_quality": result.get("data_quality")}


def command_excel(args):
    raw_dataset = load_excel_dataset(args.excel)
    print(json.dumps(_run(raw_dataset, args.output), ensure_ascii=False, indent=2))


def command_config(args):
    raw_dataset = load_database_dataset(args.config)
    print(json.dumps(_run(raw_dataset, args.output), ensure_ascii=False, indent=2))


def command_db(args):
    dsn = args.dsn or os.environ.get(args.dsn_env)
    if not dsn:
        raise SystemExit(f"missing DSN: pass --dsn or set {args.dsn_env}")
    raw_dataset = load_mysql_dsn_dataset(dsn, limit=args.limit)
    print(json.dumps(_run(raw_dataset, args.output), ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Independent OTA marketing report tool")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("diagnose-excel")
    p.add_argument("--excel", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=command_excel)
    p = sub.add_parser("diagnose-config")
    p.add_argument("--config", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=command_config)
    p = sub.add_parser("diagnose-db")
    p.add_argument("--dsn", required=False)
    p.add_argument("--dsn-env", default="S14_DB_DSN")
    p.add_argument("--limit", type=int, default=5000)
    p.add_argument("--output", required=True)
    p.set_defaults(func=command_db)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
