# Energy Export — add-on de Home Assistant

Add-on de Home Assistant Supervisor que sincroniza estadísticas diarias de energía en SQLite. El paquete contiene localmente los scripts y `requirements.txt`; la imagen no descarga código desde el repositorio principal ni durante la compilación.

## Instalación

1. Abre **Ajustes → Complementos → Tienda de complementos → ⋮ → Repositorios**.
2. Añade la URL de este repositorio y confirma.
3. Actualiza la tienda si hace falta e instala **Energy Export**.
4. Revisa las opciones de configuración, guarda y pulsa **Iniciar**.

Con `homeassistant_api: true`, Supervisor proporciona `SUPERVISOR_TOKEN`. No es necesario guardar un token de larga duración. La URL recomendada es `http://supervisor/core`.

## Configuración

| Opción | Descripción |
| --- | --- |
| `home_assistant_url` | URL de Home Assistant, normalmente `http://supervisor/core`. |
| `start_date` | Inicio de la primera sincronización, formato `YYYY-MM-DD`. Luego continúa desde el último día guardado. |
| `database_file` / `table` | Archivo persistente y tabla SQLite. El archivo debe ser un nombre simple, sin ruta. |
| `timezone` | Zona horaria IANA para el horario diario; por ejemplo `Europe/Madrid`. |
| `sync_hour` / `sync_minute` | Hora diaria local de ejecución. |
| `run_on_startup` | Ejecuta una sincronización al arrancar. Si falla, se reintentará en el siguiente horario. |
| `healthchecks_ping_url` | URL opcional de Healthchecks.io. |
| `*_stat` | Statistic IDs usados para las métricas de energía. Ajusta cada uno a tu instalación. |

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
    └── README.md
```

El Dockerfile instala las dependencias desde el `requirements.txt` local y copia los scripts locales. Al actualizar el código, actualiza los archivos de esta carpeta y aumenta `version` en `config.yaml`. No se requiere modificar ni descargar código desde el repositorio Python original.