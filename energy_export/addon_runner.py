#!/usr/bin/env python3
"""Configure and schedule the daily Home Assistant energy sync."""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

OPTIONS_PATH = Path("/data/options.json")
SYNC_SCRIPT = "/app/sync_energy_to_sqlite.py"
STAT_OPTIONS = {
    "solar_stat": "--solar-stat",
    "consumption_stat": "--consumption-stat",
    "grid_import_stat": "--grid-import-stat",
    "grid_export_stat": "--grid-export-stat",
    "peak_stat": "--peak-stat",
    "import_f1_stat": "--import-f1-stat",
    "import_f2_stat": "--import-f2-stat",
    "import_f3_stat": "--import-f3-stat",
    "battery_discharge_f1_stat": "--battery-discharge-f1-stat",
    "battery_discharge_f2_stat": "--battery-discharge-f2-stat",
    "battery_discharge_f3_stat": "--battery-discharge-f3-stat",
}
STOP = threading.Event()
ACTIVE_PROCESS: subprocess.Popen | None = None


def stop_handler(signum: int, _frame: object) -> None:
    logging.info("Señal %s recibida; deteniendo el complemento.", signum)
    STOP.set()
    if ACTIVE_PROCESS is not None and ACTIVE_PROCESS.poll() is None:
        ACTIVE_PROCESS.terminate()


def load_options() -> dict:
    try:
        with OPTIONS_PATH.open(encoding="utf-8") as options_file:
            options = json.load(options_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"No se pudieron leer las opciones de {OPTIONS_PATH}: {exc}") from exc
    if not isinstance(options, dict):
        raise RuntimeError("El archivo de opciones no contiene un objeto JSON.")
    return options


def configure(options: dict) -> tuple[list[str], ZoneInfo, int, int]:
    base_url = str(options.get("home_assistant_url", "http://supervisor/core")).strip().rstrip("/")
    token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN no está disponible. Comprueba homeassistant_api: true en config.yaml.")
    if not base_url.startswith(("http://", "https://")):
        raise RuntimeError("home_assistant_url debe comenzar por http:// o https://")

    start_date = str(options.get("start_date", "2024-01-01"))
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError as exc:
        raise RuntimeError("start_date debe tener formato YYYY-MM-DD") from exc

    filename = str(options.get("database_file", "energy_daily.sqlite"))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename) or filename in {".", ".."}:
        raise RuntimeError("database_file debe ser un nombre de archivo simple, sin rutas")

    table = str(options.get("table", "daily_energy"))
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise RuntimeError("table solo puede contener letras, números y guion bajo, y no puede empezar por número")

    try:
        timezone = ZoneInfo(str(options.get("timezone", "UTC")))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RuntimeError("timezone debe ser una zona horaria IANA válida, por ejemplo Europe/Madrid") from exc

    hour = int(options.get("sync_hour", 1))
    minute = int(options.get("sync_minute", 0))
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise RuntimeError("sync_hour debe estar entre 0-23 y sync_minute entre 0-59")

    os.environ.update(
        {
            "HASS_URL": base_url,
            "HASS_TOKEN": token,
            "ENERGY_SYNC_START_DATE": start_date,
            "ENERGY_SQLITE_DB": f"/data/{filename}",
            "ENERGY_SQLITE_TABLE": table,
            "HEALTHCHECKS_PING_URL": str(options.get("healthchecks_ping_url") or ""),
        }
    )

    command = [sys.executable, SYNC_SCRIPT, "--base-url", base_url, "--token", token, "--db-path", f"/data/{filename}", "--table", table]
    for key, flag in STAT_OPTIONS.items():
        value = str(options.get(key, "")).strip()
        if not value:
            raise RuntimeError(f"La opción {key} no puede estar vacía")
        command.extend([flag, value])
    return command, timezone, hour, minute


def run_sync(command: list[str], reason: str) -> int:
    global ACTIVE_PROCESS
    if STOP.is_set():
        return 0
    logging.info("Iniciando sincronización (%s).", reason)
    try:
        ACTIVE_PROCESS = subprocess.Popen(command, cwd="/app", env=os.environ.copy())
        while ACTIVE_PROCESS.poll() is None and not STOP.wait(0.5):
            pass
        if ACTIVE_PROCESS.poll() is None:
            ACTIVE_PROCESS.terminate()
        result = ACTIVE_PROCESS.wait()
    except OSError:
        logging.exception("No se pudo iniciar el proceso de sincronización.")
        return 1
    finally:
        ACTIVE_PROCESS = None
    if result == 0:
        logging.info("Sincronización finalizada correctamente.")
    elif not STOP.is_set():
        logging.error("La sincronización terminó con código %s; se volverá a intentar en el próximo horario.", result)
    return result


def next_run(now: datetime, hour: int, minute: int, timezone: ZoneInfo) -> datetime:
    local_now = now.astimezone(timezone)
    target = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= local_now:
        target += timedelta(days=1)
    return target


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S", stream=sys.stdout)
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)

    try:
        options = load_options()
        command, timezone, hour, minute = configure(options)
    except (RuntimeError, TypeError, ValueError) as exc:
        logging.error("Configuración inválida: %s", exc)
        return 2

    logging.info("Energy Export iniciado. Próxima zona horaria: %s; sincronización diaria a las %02d:%02d.", timezone.key, hour, minute)
    if options.get("run_on_startup", False):
        run_sync(command, "arranque")

    while not STOP.is_set():
        target = next_run(datetime.now(timezone), hour, minute, timezone)
        seconds = max(1.0, (target - datetime.now(timezone)).total_seconds())
        logging.info("Próxima sincronización: %s (%s).", target.strftime("%Y-%m-%d %H:%M:%S %Z"), timezone.key)
        if STOP.wait(seconds):
            break
        run_sync(command, "horario diario")

    logging.info("Energy Export detenido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())