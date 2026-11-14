# Add-on de Home Assistant: Energy Export

Este add-on sincroniza diariamente las estadísticas de energía de Home Assistant con una base de datos SQLite persistente en `/data`. Usa la lógica de `sync_energy_to_sqlite.py` del repositorio y ejecuta la primera sincronización opcionalmente al arrancar.

## Instalación

1. En Home Assistant, abre **Ajustes → Complementos → Tienda de complementos**.
2. Abre el menú de la tienda (⋮) y elige **Repositorios**.
3. Añade `https://github.com/DIAZGZA/export-homeassistant-energy` y actualiza la tienda.
4. Instala **Energy Export**.
5. Configura los IDs de estadísticas según tus sensores y pulsa **Iniciar**.

El add-on usa el token del Supervisor automáticamente; no hace falta crear ni guardar un token de larga duración. La URL predeterminada es `http://supervisor/core`.

## Opciones

- `start_date`: fecha inicial para la primera sincronización (por defecto `2024-01-01`). Las sincronizaciones siguientes son incrementales, desde el último día guardado + 1.
- `database_file` y `table`: archivo y tabla SQLite. El archivo se guarda dentro de `/data` y el nombre no puede ser una ruta.
- `sync_hour` / `sync_minute`: hora diaria local a la que se ejecuta la sincronización (por defecto 01:00).
- `run_on_startup`: ejecuta una sincronización al arrancar el complemento además de mantener el horario diario.
- `healthchecks_ping_url`: URL opcional de Healthchecks.io.
- Los campos `*_stat` permiten personalizar los statistic IDs; sus valores iniciales coinciden con los del proyecto.

Se exportan los datos hasta el día anterior para evitar incluir un día incompleto. La base de datos se conserva al actualizar el add-on porque está en `/data`. Los registros están disponibles en la pestaña **Registro** del complemento.

## Nota de mantenimiento

La imagen descarga los scripts desde un commit fijo del repositorio durante la compilación, para que la versión del código sea reproducible. Al actualizar la lógica del exportador, actualiza `SOURCE_COMMIT` en `homeassistant-addon/Dockerfile` y la versión en `homeassistant-addon/config.yaml`.