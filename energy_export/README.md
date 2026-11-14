# Energy Export — add-on de Home Assistant

Add-on de Home Assistant Supervisor que sincroniza estadísticas diarias de energía en una base SQLite persistente. La sincronización consulta el Recorder de Home Assistant y guarda los resultados hasta el día anterior, para no incluir datos incompletos.

## Instalación directa

1. En Home Assistant, abre **Ajustes → Complementos → Tienda de complementos**.
2. Abre el menú **⋮ → Repositorios**.
3. Añade `https://github.com/DIAZGZA/export-homeassistant-energy` y confirma.
4. Actualiza la tienda si el repositorio no aparece inmediatamente.
5. Instala **Energy Export**.
6. Abre la pestaña **Configuración**, revisa los IDs de estadísticas y la zona horaria, guarda los cambios y pulsa **Iniciar**.

El Supervisor proporciona `SUPERVISOR_TOKEN` al add-on porque está habilitado `homeassistant_api`. No introduzcas ni guardes un token de larga duración. La URL recomendada es `http://supervisor/core`.

> Este repositorio también contiene el código fuente del exportador. El add-on instalable está en `energy_export/`, que es una carpeta de add-on en la raíz del repositorio.

## Configuración

| Opción | Valor inicial | Descripción |
| --- | --- | --- |
| `home_assistant_url` | `http://supervisor/core` | URL de la API de Home Assistant. |
| `start_date` | `2024-01-01` | Fecha desde la que se inicia la primera sincronización. Después, continúa desde la última fecha de la base de datos. Formato `YYYY-MM-DD`. |
| `database_file` | `energy_daily.sqlite` | Nombre del archivo SQLite dentro del almacenamiento persistente del add-on; no admite rutas. |
| `table` | `daily_energy` | Tabla SQLite destino. Solo letras, números y `_`; debe comenzar por letra o `_`. |
| `timezone` | `UTC` | Zona IANA usada para programar el horario, por ejemplo `Europe/Madrid`. |
| `sync_hour` / `sync_minute` | `01:00` | Hora diaria local en la zona seleccionada. |
| `run_on_startup` | `false` | Ejecuta una sincronización al arrancar. Si falla, el add-on sigue activo y lo vuelve a intentar en el siguiente horario. |
| `healthchecks_ping_url` | vacío | URL opcional de Healthchecks.io. |
| `*_stat` | IDs incluidos | Statistic IDs usados para producción, consumo, red, punta, tarifas F1/F2/F3 y descarga de batería. |

Los valores iniciales de los IDs `*_stat` son ejemplos del repositorio; cámbialos por los statistic IDs que existan en tu instalación. Los valores deben ser IDs de estadísticas de Home Assistant, normalmente con formato `sensor.nombre`.

## Datos y registros

- La base se conserva en el directorio persistente del add-on, bajo `/data`, incluso al reiniciar o actualizar.
- Consulta la pestaña **Registro** del add-on para ver inicio, próxima ejecución, resultado y errores. El token no se escribe en los registros.
- El proceso se ejecuta como usuario sin privilegios dentro del contenedor y responde a las señales de parada de Supervisor.
- El horario se expresa en la zona configurada en `timezone`; el acceso a la API de HA usa el token del Supervisor.

## Desarrollo y actualizaciones

El Dockerfile obtiene los scripts Python del proyecto desde un commit fijado para que las compilaciones sean reproducibles. Al publicar cambios en el código de sincronización, actualiza `SOURCE_COMMIT` en `energy_export/Dockerfile` y aumenta `version` en `energy_export/config.yaml`. La tienda compila la imagen del add-on a partir del `Dockerfile` local.

## Estructura

```text
.
├── repository.yaml
└── energy_export/
    ├── config.yaml
    ├── Dockerfile
    ├── addon_runner.py
    ├── run.sh
    └── README.md
```
