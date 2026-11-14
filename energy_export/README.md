# Energy Export — add-on de Home Assistant

Add-on de Home Assistant Supervisor que sincroniza estadísticas diarias de energía en SQLite. Incluye un panel Ingress para consultar sensores de HA y sugerir/guardar los que corresponden a cada métrica; el resto de ajustes sigue en la configuración nativa del add-on.

## Instalación

1. Abre **Ajustes → Complementos → Tienda de complementos → ⋮ → Repositorios**.
2. Añade la URL de este repositorio y confirma.
3. Actualiza la tienda si hace falta e instala **Energy Export**.
4. Revisa las opciones de configuración nativas, guarda y pulsa **Iniciar**.
5. Abre el panel **Energía** del add-on para cargar la lista de sensores, seleccionar sugerencias y guardar.

Con `homeassistant_api: true`, Supervisor proporciona `SUPERVISOR_TOKEN`. El panel no muestra ni almacena el token. No es necesario guardar un token de larga duración. La URL recomendada es `http://supervisor/core`.

## Panel de selección

El panel Ingress consulta `/api/states` de Home Assistant y lista entidades del dominio `sensor`, ordenadas por una puntuación de coincidencia con cada métrica (nombre, entity ID, unidad y clases del sensor). Las sugerencias solo ayudan a encontrar entidades: verifica que el sensor registre la estadística correcta y que Home Assistant tenga estadísticas Recorder disponibles.

Al guardar, las selecciones se persisten en `/data/sensor_selections.json`. Tienen precedencia sobre los campos `*_stat` del formulario nativo y se aplican en la próxima sincronización. Para volver a los valores del formulario nativo, elige “No cambiar” en todos los campos correspondientes y guarda. Las demás opciones —URL, horario, base, tabla, timezone y fecha inicial— se siguen administrando en el formulario de configuración habitual.

> El panel selecciona entity IDs `sensor.*` como statistic IDs. En instalaciones que usan IDs de estadísticas personalizados que no coinciden con el entity ID, utiliza el campo `*_stat` en la configuración nativa; deja ese campo como fuente de verdad.

## Configuración nativa

| Opción | Descripción |
| --- | --- |
| `home_assistant_url` | URL de Home Assistant, normalmente `http://supervisor/core`. |
| `start_date` | Inicio de la primera sincronización, formato `YYYY-MM-DD`; después continúa desde la última fecha guardada. |
| `database_file` / `table` | Archivo persistente y tabla SQLite. El archivo debe ser un nombre simple, sin ruta. |
| `timezone` | Zona horaria IANA para el horario diario; por ejemplo `Europe/Madrid`. |
| `sync_hour` / `sync_minute` | Hora diaria local de ejecución. |
| `run_on_startup` | Ejecuta una sincronización al arrancar. Si falla, se reintentará en el siguiente horario. |
| `healthchecks_ping_url` | URL opcional de Healthchecks.io. |
| `*_stat` | Statistic IDs de respaldo/edición manual para las métricas de energía. |

Se sincronizan días completos hasta ayer. La base queda en `/data`, que Supervisor conserva al reiniciar o actualizar. Los logs se consultan en la pestaña **Registro**.

## Estructura del paquete

```text
.
├── repository.yaml
└── energy_export/
    ├── config.yaml
    ├── Dockerfile
    ├── requirements.txt
    ├── export_energy_to_excel.py
    ├── sync_energy_to_sqlite.py
    ├── addon_runner.py
    ├── run.sh
    ├── README.md
    └── www/
        └── index.html
```

El Dockerfile instala las dependencias desde el `requirements.txt` local y copia los scripts y la interfaz locales. No descarga código desde el repositorio Python original durante la compilación.