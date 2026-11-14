#!/bin/sh
set -eu

if [ ! -r /data/options.json ]; then
  echo "[energy-export] No se puede leer /data/options.json; comprueba la instalación del add-on." >&2
  exit 1
fi

# El directorio persistente puede estar montado con permisos de root por Supervisor.
# Cambiamos solo el propietario del directorio de datos y ejecutamos la aplicación sin privilegios.
chown appuser:appgroup /data
exec su-exec appuser:appgroup python3 /app/addon_runner.py