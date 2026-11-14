# Energy Export

Add-on para **Home Assistant Supervisor** que recopila estadísticas diarias de energía y las guarda en una base de datos SQLite persistente. Incluye un panel Ingress para consultar los sensores de Home Assistant y ayudar a elegir los que corresponden a cada métrica.

> El repositorio de add-ons se añade en Home Assistant con la URL del repositorio GitHub. El manifiesto `repository.yaml` debe estar en su raíz y el add-on en `energy_export/`.

## Instalación

1. En Home Assistant, abre **Ajustes → Complementos → Tienda de complementos**.
2. Abre el menú **⋮ → Repositorios**.
3. Añade esta URL y confirma:

   ```text
   https://github.com/DIAZGZA/export-homeassistant-energy
   ```

4. Busca e instala **Energy Export**.
5. En **Configuración**, revisa las opciones y ajusta los statistic IDs a los disponibles en tu instalación. Guarda los cambios y arranca el add-on.
6. Abre el panel **Energía** para consultar sensores, revisar las sugerencias y guardar selecciones.

El add-on tiene `homeassistant_api: true`, por lo que Supervisor proporciona `SUPERVISOR_TOKEN`. No introduzcas un token en la configuración ni lo guardes en el repositorio. La URL local recomendada es `http://supervisor/core`.

### Publicarlo en un repositorio nuevo

Copia `repository.yaml` y toda la carpeta `energy_export/` a la raíz del nuevo repositorio. Cambia en `repository.yaml` y `energy_export/config.yaml` la URL para que apunte al nuevo repo; deja el `url` de la configuración del add-on y el `url` del manifiesto coherentes. Confirma los archivos en la rama predeterminada y añade la URL HTTPS del nuevo repo en la tienda de add-ons. La guía detallada está en [`README-addon-repo.md`](../README-addon-repo.md).

## Panel Ingress de sensores

El panel **Energía** consulta los estados de Home Assistant y muestra entidades del dominio `sensor`. Para cada métrica, ordena las sugerencias usando coincidencias de texto en el ID, nombre, unidad y clases del sensor. Puedes volver a cargar la lista cuando cambien tus entidades.

1. Abre el panel y espera a que carguen los sensores.
2. Selecciona la entidad que corresponda a cada métrica; verifica el ID antes de guardar.
3. Pulsa **Guardar selecciones**. Las selecciones persistidas se aplicarán en la siguiente sincronización.

Las sugerencias son orientativas: tener una entidad `sensor.*` no garantiza que Home Assistant la registre como estadística válida ni que represente la métrica deseada. Este add-on consulta las estadísticas Recorder para las métricas de cambio y el historial para la métrica de pico.

Las selecciones se guardan en `/data/sensor_selections.json` y prevalecen sobre los campos `*_stat` de la configuración nativa. Elige **— No cambiar —** para un campo y guarda para quitar su selección del panel y volver al valor configurado en la interfaz nativa. En instalaciones que usan `statistic_id` personalizado distinto del entity ID, introduce el ID personalizado en la configuración nativa; el panel solo propone entidades `sensor.*`.

## Configuración nativa

| Opción | Uso |
| --- | --- |
| `home_assistant_url` | URL de la API. Normalmente `http://supervisor/core`. |
| `start_date` | Fecha inicial (`YYYY-MM-DD`) cuando la base aún no tiene datos. Después, la sincronización es incremental desde la última fecha guardada + 1 día. |
| `database_file` | Nombre del archivo SQLite dentro de `/data`; debe ser un nombre de archivo, no una ruta. |
| `table` | Tabla de destino SQLite. Solo letras, números y `_`; debe comenzar por letra o `_`. |
| `timezone` | Zona horaria IANA para el horario, por ejemplo `Europe/Madrid`. |
| `sync_hour`, `sync_minute` | Hora diaria local en la zona elegida. Valor inicial: 01:00. |
| `run_on_startup` | Si está activado, intenta sincronizar al arrancar y después mantiene el horario diario. Un fallo de esa ejecución queda en los logs y no detiene el scheduler. |
| `healthchecks_ping_url` | URL opcional de Healthchecks.io. |
| `*_stat` | Statistic IDs para producción, consumo, importación/exportación, pico, tarifas F1/F2/F3 y descarga de batería. Son el valor manual de respaldo cuando no hay una selección guardada en el panel. |

La sincronización se limita al día anterior para evitar incluir datos incompletos del día actual. La base de datos y las selecciones del panel se guardan bajo `/data`, que Supervisor conserva al reiniciar o actualizar el add-on. Consulta los mensajes de ejecución en la pestaña **Registro**.

## Pruebas locales con Docker Compose

Compose permite probar la imagen, la conexión con Home Assistant y el panel web fuera de Supervisor. No reproduce la autenticación ni la navegación Ingress de Home Assistant; publica el panel únicamente en `127.0.0.1:8099`.

Requisitos: Docker Engine con el plugin Docker Compose y conectividad desde el host Docker a Home Assistant.

Desde esta carpeta (`energy_export/`):

1. Prepara los archivos locales:

   ```sh
   mkdir -p data
   cp options.local.example.json data/options.json
   cp .env.example .env
   ```

2. Edita `.env` y sustituye el valor de ejemplo por un token de Home Assistant válido para pruebas. No lo compartas ni lo subas a Git. Este token es solo para Compose: en Home Assistant Supervisor, el token se inyecta automáticamente.
3. Edita `data/options.json`: configura la URL alcanzable desde el contenedor, la zona horaria y tus statistic IDs. En Docker Desktop, `http://host.docker.internal:8123` suele servir para Home Assistant en el mismo equipo; en Linux, el Compose configura el alias `host-gateway`. Para otro host, especifica su URL de red.
4. Inicia el servicio y revisa sus logs:

   ```sh
   docker compose up --build -d
   docker compose logs -f energy-export
   ```

5. Abre `http://127.0.0.1:8099/`, carga los sensores y guarda las selecciones. La base y las selecciones quedan en `energy_export/data/`.

Para detener el servicio, ejecuta `docker compose down`. Para reconstruir después de cambiar código, ejecuta `docker compose up --build -d`.

> Si Home Assistant no responde desde el contenedor, comprueba la URL, el firewall y la conectividad de red. No publiques el puerto 8099 en una interfaz accesible desde Internet: fuera del Supervisor, Docker Compose no proporciona el proxy ni la autenticación de Ingress.

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
    ├── www/index.html
    ├── docker-compose.yml
    ├── options.local.example.json
    ├── .env.example
    └── README.md
```

La imagen instala sus dependencias desde el `requirements.txt` local y copia los scripts y la interfaz desde la propia carpeta del add-on. No necesita descargar código desde el repositorio Python original para compilar.

## Solución de problemas

- **No carga el panel o los sensores:** comprueba que el add-on está iniciado, `homeassistant_api: true` sigue habilitado y revisa el log del add-on.
- **No aparecen estadísticas al sincronizar:** comprueba los `statistic_id` y que Recorder tenga estadísticas disponibles para esas entidades.
- **No escribe la base:** revisa que `database_file` sea un nombre simple y busca errores de permisos o SQLite en los logs.
- **La hora de ejecución no coincide:** confirma `timezone`, `sync_hour` y `sync_minute`; el horario se calcula en la zona elegida.