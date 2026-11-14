#!/usr/bin/env python3
"""Configure, serve the sensor picker, and schedule the daily energy sync."""

from __future__ import annotations

import json
import logging
import os
import re
import signal
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

OPTIONS_PATH = Path("/data/options.json")
SELECTIONS_PATH = Path("/data/sensor_selections.json")
WEB_ROOT = Path("/app/www")
SYNC_SCRIPT = "/app/sync_energy_to_sqlite.py"
PANEL_HOST = "0.0.0.0"
PANEL_PORT = 8099
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
PANEL_SERVER: ThreadingHTTPServer | None = None
OPTIONS: dict = {}


def load_json_file(path: Path, default: dict) -> dict:
    try:
        with path.open(encoding="utf-8") as source:
            value = json.load(source)
        return value if isinstance(value, dict) else default.copy()
    except FileNotFoundError:
        return default.copy()
    except (OSError, json.JSONDecodeError) as exc:
        logging.warning("No se pudo leer %s: %s", path, exc)
        return default.copy()


def load_options() -> dict:
    options = load_json_file(OPTIONS_PATH, {})
    if not options:
        raise RuntimeError(f"No se pudieron leer opciones válidas desde {OPTIONS_PATH}")
    return options


def current_selections() -> dict[str, str]:
    saved = load_json_file(SELECTIONS_PATH, {})
    return {
        key: value for key, value in saved.items()
        if key in STAT_OPTIONS and isinstance(value, str) and re.fullmatch(r"sensor\.[a-z0-9_]+", value)
    }


def effective_options() -> dict:
    options = OPTIONS.copy()
    options.update(current_selections())
    return options


def request_ha(path: str) -> object:
    base_url = str(OPTIONS.get("home_assistant_url", "http://supervisor/core")).strip().rstrip("/")
    token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN no está disponible; comprueba homeassistant_api: true.")
    request = Request(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(12 * 1024 * 1024 + 1)
    except HTTPError as exc:
        raise RuntimeError(f"Home Assistant respondió HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"No se pudo consultar Home Assistant: {exc.reason if isinstance(exc, URLError) else exc}") from exc
    if len(payload) > 12 * 1024 * 1024:
        raise RuntimeError("La respuesta de Home Assistant supera el límite permitido.")
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Home Assistant devolvió una respuesta JSON no válida.") from exc


def available_sensors() -> list[dict]:
    response = request_ha("/api/states")
    if not isinstance(response, list):
        raise RuntimeError("La API de estados devolvió un formato inesperado.")
    sensors = []
    for item in response:
        if not isinstance(item, dict):
            continue
        entity_id = item.get("entity_id")
        if not isinstance(entity_id, str) or not re.fullmatch(r"sensor\.[a-z0-9_]+", entity_id):
            continue
        attributes = item.get("attributes") or {}
        sensors.append({
            "entity_id": entity_id,
            "name": str(attributes.get("friendly_name") or entity_id),
            "unit": str(attributes.get("unit_of_measurement") or ""),
            "device_class": str(attributes.get("device_class") or ""),
            "state_class": str(attributes.get("state_class") or ""),
            "state": str(item.get("state") or ""),
        })
    return sorted(sensors, key=lambda sensor: sensor["name"].casefold())


def save_selections(data: object) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON.")
    valid_ids = {sensor["entity_id"] for sensor in available_sensors()}
    cleaned: dict[str, str] = {}
    for key, value in data.items():
        if key not in STAT_OPTIONS:
            continue
        if value in (None, ""):
            continue
        if not isinstance(value, str) or value not in valid_ids:
            raise ValueError(f"El valor seleccionado para {key} no es un sensor disponible.")
        cleaned[key] = value
    temp_path = SELECTIONS_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(SELECTIONS_PATH)
    return cleaned


def stop_handler(signum: int, _frame: object) -> None:
    logging.info("Señal %s recibida; deteniendo el complemento.", signum)
    STOP.set()
    if ACTIVE_PROCESS is not None and ACTIVE_PROCESS.poll() is None:
        ACTIVE_PROCESS.terminate()
    if PANEL_SERVER is not None:
        threading.Thread(target=PANEL_SERVER.shutdown, daemon=True).start()


def configure() -> tuple[ZoneInfo, int, int]:
    token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN no está disponible; comprueba homeassistant_api: true.")
    base_url = str(OPTIONS.get("home_assistant_url", "http://supervisor/core")).strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise RuntimeError("home_assistant_url debe comenzar por http:// o https://")
    start_date = str(OPTIONS.get("start_date", "2024-01-01"))
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError as exc:
        raise RuntimeError("start_date debe tener formato YYYY-MM-DD") from exc
    filename = str(OPTIONS.get("database_file", "energy_daily.sqlite"))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename) or filename in {".", ".."}:
        raise RuntimeError("database_file debe ser un nombre de archivo simple, sin rutas")
    table = str(OPTIONS.get("table", "daily_energy"))
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
        raise RuntimeError("table solo puede contener letras, números y guion bajo, y no puede empezar por número")
    try:
        timezone = ZoneInfo(str(OPTIONS.get("timezone", "UTC")))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RuntimeError("timezone debe ser una zona horaria IANA válida, por ejemplo Europe/Madrid") from exc
    hour, minute = int(OPTIONS.get("sync_hour", 1)), int(OPTIONS.get("sync_minute", 0))
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise RuntimeError("sync_hour debe estar entre 0-23 y sync_minute entre 0-59")
    os.environ.update({
        "HASS_URL": base_url,
        "HASS_TOKEN": token,
        "ENERGY_SYNC_START_DATE": start_date,
        "ENERGY_SQLITE_DB": f"/data/{filename}",
        "ENERGY_SQLITE_TABLE": table,
        "HEALTHCHECKS_PING_URL": str(OPTIONS.get("healthchecks_ping_url") or ""),
    })
    return timezone, hour, minute


def build_sync_command() -> list[str]:
    options = effective_options()
    command = [sys.executable, SYNC_SCRIPT, "--db-path", os.environ["ENERGY_SQLITE_DB"], "--table", os.environ["ENERGY_SQLITE_TABLE"]]
    for key, flag in STAT_OPTIONS.items():
        value = str(options.get(key, "")).strip()
        if not value:
            raise RuntimeError(f"La opción {key} no puede estar vacía")
        command.extend([flag, value])
    return command


def run_sync(reason: str) -> int:
    global ACTIVE_PROCESS
    if STOP.is_set():
        return 0
    try:
        command = build_sync_command()
    except RuntimeError as exc:
        logging.error("No se pudo preparar la sincronización: %s", exc)
        return 1
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
        logging.error("La sincronización terminó con código %s; se reintentará en el siguiente horario.", result)
    return result


def next_run(now: datetime, hour: int, minute: int, timezone: ZoneInfo) -> datetime:
    local_now = now.astimezone(timezone)
    target = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= local_now:
        target += timedelta(days=1)
    return target


class PanelHandler(BaseHTTPRequestHandler):
    server_version = "EnergyExportPanel/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        logging.info("Panel: %s", fmt % args)

    def send_json(self, status: int, value: object) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            try:
                payload = (WEB_ROOT / "index.html").read_bytes()
            except OSError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
        elif path == "/api/sensors":
            try:
                self.send_json(200, {"sensors": available_sensors(), "selections": effective_options()})
            except RuntimeError as exc:
                self.send_json(502, {"error": str(exc)})
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/selections":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("Tamaño de solicitud no válido.")
            data = json.loads(self.rfile.read(length))
            selections = save_selections(data)
            self.send_json(200, {"selections": selections})
            logging.info("Selecciones de sensores guardadas desde el panel.")
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except RuntimeError as exc:
            self.send_json(502, {"error": str(exc)})


def start_panel() -> None:
    global PANEL_SERVER
    PANEL_SERVER = ThreadingHTTPServer((PANEL_HOST, PANEL_PORT), PanelHandler)
    PANEL_SERVER.daemon_threads = True
    threading.Thread(target=PANEL_SERVER.serve_forever, name="ingress-panel", daemon=True).start()
    logging.info("Panel de selección disponible mediante Ingress en el puerto %d.", PANEL_PORT)


def main() -> int:
    global OPTIONS
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S", stream=sys.stdout)
    signal.signal(signal.SIGTERM, stop_handler)
    signal.signal(signal.SIGINT, stop_handler)
    try:
        OPTIONS = load_options()
        timezone, hour, minute = configure()
    except (RuntimeError, TypeError, ValueError) as exc:
        logging.error("Configuración inválida: %s", exc)
        return 2

    try:
        start_panel()
    except OSError:
        logging.exception("No se pudo iniciar el panel Ingress.")
        return 1

    logging.info("Energy Export iniciado. Zona horaria: %s; sincronización diaria a las %02d:%02d.", timezone.key, hour, minute)
    if OPTIONS.get("run_on_startup", False):
        run_sync("arranque")
    while not STOP.is_set():
        target = next_run(datetime.now(timezone), hour, minute, timezone)
        wait_seconds = max(1.0, (target - datetime.now(timezone)).total_seconds())
        logging.info("Próxima sincronización: %s (%s).", target.strftime("%Y-%m-%d %H:%M:%S %Z"), timezone.key)
        if STOP.wait(wait_seconds):
            break
        run_sync("horario diario")
    if PANEL_SERVER is not None:
        PANEL_SERVER.server_close()
    logging.info("Energy Export detenido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())