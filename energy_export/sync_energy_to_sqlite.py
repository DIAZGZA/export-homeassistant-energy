#!/usr/bin/env python3
"""Sync Home Assistant daily energy statistics into SQLite for scheduled runs."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from export_energy_to_excel import COLUMNS, HomeAssistantClient, build_metrics, build_rows, collect_metric_data, default_stat, load_dotenv, parse_day

COLUMN_DEFS = {column: "REAL NOT NULL DEFAULT 0" for column in COLUMNS if column != "date"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("HASS_URL"), help="Home Assistant URL")
    parser.add_argument("--token", default=os.getenv("HASS_TOKEN"), help="Home Assistant token")
    parser.add_argument("--start", type=parse_day, default=None, help="Start date; defaults to DB max(date)+1 or configured initial date")
    parser.add_argument("--db-path", default=os.getenv("ENERGY_SQLITE_DB", "energy_daily.sqlite"))
    parser.add_argument("--table", default=os.getenv("ENERGY_SQLITE_TABLE", "daily_energy"))
    parser.add_argument("--healthchecks-url", default=os.getenv("HEALTHCHECKS_PING_URL"))
    parser.add_argument("--solar-stat", default=default_stat("solar_production"))
    parser.add_argument("--consumption-stat", default=default_stat("house_consumption"))
    parser.add_argument("--grid-import-stat", default=default_stat("grid_import"))
    parser.add_argument("--grid-export-stat", default=default_stat("grid_export"))
    parser.add_argument("--peak-stat", default=default_stat("peak"))
    parser.add_argument("--import-f1-stat", default=default_stat("import_f1"))
    parser.add_argument("--import-f2-stat", default=default_stat("import_f2"))
    parser.add_argument("--import-f3-stat", default=default_stat("import_f3"))
    parser.add_argument("--battery-discharge-f1-stat", default=default_stat("battery_discharge_f1"))
    parser.add_argument("--battery-discharge-f2-stat", default=default_stat("battery_discharge_f2"))
    parser.add_argument("--battery-discharge-f3-stat", default=default_stat("battery_discharge_f3"))
    return parser.parse_args()


def ping_healthchecks(base_url: str | None, suffix: str, body: str = "") -> None:
    if not base_url:
        return
    url = base_url.rstrip("/") + suffix
    cmd = ["curl", "-fsS", "--max-time", "10", "-X", "POST", "--data-binary", "@-", "-o", "/dev/null", url]
    proc = subprocess.run(cmd, input=body, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Warning: healthcheck ping failed: {proc.stderr.strip()}", file=sys.stderr)


def validate_table_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid table name: {name!r}")
    return name


def ensure_table(conn: sqlite3.Connection, table: str) -> None:
    column_sql = ",\n            ".join(f"{name} {definition}" for name, definition in COLUMN_DEFS.items())
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} (date TEXT PRIMARY KEY, {column_sql})")
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for name, definition in COLUMN_DEFS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def get_latest_date(conn: sqlite3.Connection, table: str) -> date | None:
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
        return None
    value = conn.execute(f"SELECT MAX(date) FROM {table}").fetchone()[0]
    return date.fromisoformat(value) if value else None


def upsert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    placeholders = ", ".join("?" for _ in COLUMNS)
    updates = ",\n            ".join(f"{name} = excluded.{name}" for name in COLUMN_DEFS)
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(COLUMNS)}) VALUES ({placeholders}) ON CONFLICT(date) DO UPDATE SET {updates}",
        [tuple(row[name] for name in COLUMNS) for row in rows],
    )


def main() -> int:
    load_dotenv()
    args = parse_args()
    run_log: list[str] = []

    def log(message: str, *, err: bool = False) -> None:
        run_log.append(message)
        print(message, file=sys.stderr if err else sys.stdout, flush=True)

    ping_healthchecks(args.healthchecks_url, "/start", "sync started")
    try:
        if not args.base_url:
            raise ValueError("Missing Home Assistant URL")
        if not args.token:
            raise ValueError("Missing Home Assistant token")
        table = validate_table_name(args.table)
        env_start = parse_day(os.getenv("ENERGY_SYNC_START_DATE", "2024-01-01"))
        metrics = build_metrics(args)
        client = HomeAssistantClient(args.base_url, args.token)
        config = client.get_config()
        timezone_name = config.get("time_zone", "UTC")
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = ZoneInfo("UTC")
        end_date = datetime.now(tz).date() - timedelta(days=1)
        with sqlite3.connect(args.db_path) as conn:
            latest = get_latest_date(conn, table)
            effective_start = args.start or (latest + timedelta(days=1) if latest else env_start)
            if effective_start > end_date:
                log(f"No sync needed: start {effective_start.isoformat()} is after previous day {end_date.isoformat()}.")
                ping_healthchecks(args.healthchecks_url, "", "\n".join(run_log))
                return 0
            stats = collect_metric_data(client, metrics, tz, effective_start, end_date)
            rows = build_rows(stats, tz, effective_start, end_date, metrics)
            ensure_table(conn, table)
            upsert_rows(conn, table, rows)
            conn.commit()
        log(f"Synced {len(rows)} daily rows into {args.db_path} (table: {table})")
        log(f"Date range: {effective_start.isoformat()} -> {end_date.isoformat()} ({timezone_name})")
        missing = [m.statistic_id for m in metrics if not stats.get(m.statistic_id)]
        if missing:
            log("Warning: no recorder statistics returned for: " + ", ".join(missing), err=True)
        ping_healthchecks(args.healthchecks_url, "", "\n".join(run_log))
        return 0
    except Exception as exc:
        log(f"Sync failed: {exc}", err=True)
        ping_healthchecks(args.healthchecks_url, "/fail", "\n".join(run_log))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())