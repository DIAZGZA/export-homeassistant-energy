#!/bin/sh
set -eu

# Home Assistant injects SUPERVISOR_TOKEN when homeassistant_api is enabled.
export HASS_URL="$(python3 -c 'import json; print(json.load(open("/data/options.json")).get("home_assistant_url", "http://supervisor/core"))')"
export HASS_TOKEN="${SUPERVISOR_TOKEN:-}"

python3 - <<'PY'
import json
import os
import re

with open("/data/options.json", encoding="utf-8") as options_file:
    options = json.load(options_file)

mapping = {
    "start_date": "ENERGY_SYNC_START_DATE",
    "table": "ENERGY_SQLITE_TABLE",
    "sync_hour": "SYNC_HOUR",
    "sync_minute": "SYNC_MINUTE",
    "healthchecks_ping_url": "HEALTHCHECKS_PING_URL",
    "solar_stat": "SOLAR_STAT",
    "consumption_stat": "CONSUMPTION_STAT",
    "grid_import_stat": "GRID_IMPORT_STAT",
    "grid_export_stat": "GRID_EXPORT_STAT",
    "peak_stat": "PEAK_STAT",
    "import_f1_stat": "IMPORT_F1_STAT",
    "import_f2_stat": "IMPORT_F2_STAT",
    "import_f3_stat": "IMPORT_F3_STAT",
    "battery_discharge_f1_stat": "BATTERY_DISCHARGE_F1_STAT",
    "battery_discharge_f2_stat": "BATTERY_DISCHARGE_F2_STAT",
    "battery_discharge_f3_stat": "BATTERY_DISCHARGE_F3_STAT",
}
for option, variable in mapping.items():
    value = options.get(option)
    if value is not None:
        os.environ[variable] = str(value)

filename = options.get("database_file", "energy_daily.sqlite")
if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename) or filename in (".", ".."):
    raise SystemExit("database_file must be a filename (not a path)")
os.environ["ENERGY_SQLITE_DB"] = f"/data/{filename}"

if options.get("run_on_startup", False):
    os.chdir("/app")
    os.system("python3 /app/sync_energy_to_sqlite.py")

os.chdir("/app")
os.execv("/usr/local/bin/python3", ["python3", "/app/scheduler_loop.py"])
PY