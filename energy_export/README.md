# Energy Export — add-on de Home Assistant

Add-on de Home Assistant Supervisor que sincroniza estadísticas diarias de energía en SQLite. Incluye un panel Ingress para consultar sensores de HA y sugerir/guardar los que corresponden a cada métrica; el resto de ajustes sigue en la configuración nativa.

## Instalación desde este repositorio

1. En Home Assistant, abre **Ajustes → Complementos → Tienda de complementos → ⋮ → Repositorios**.
2. Añade `https://github.com/DIAZGZA/export-homeassistant-energy` y confirma.
3. Actualiza la tienda si hace falta e instala **Energy Export**.
4. Revisa las opciones de configuración nativas, guarda y pulsa **Iniciar**.
5. Abre el panel **Energía** del add-on para cargar sensores, revisar sugerencias y guardar selecciones.

Para crear un repositorio independiente, copia `repository.yaml` y la carpeta completa `energy_export/` en la raíz de un nuevo repositorio. Consulta [`README-addon-repo.md`](../README-addon-repo.md).

Con `homeassistant_api: true`, Supervisor proporciona `SUPERVISOR_TOKEN`. No lo guardes en las opciones ni en Git. La URL recomendada en Home Assistant es `http://supervisor/core`.

## Panel de sensores

El panel Ingress consulta `/api/states` y ordena los sensores por coincidencias en nombre, entity ID, unidad y clases. Las recomendaciones son orientativas: confirma que el sensor registra la estadística correcta. Las selecciones se persisten en `/data/sensor_selections.json` y prevalecen sobre los campos `*_stat` en la próxima sincronización. En el panel, “No cambiar” elimina la selección guardada para ese campo y devuelve el control a la configuración nativa.

La interfaz propone entidades `sensor.*` como statistic IDs. Si tu instalación usa statistic IDs personalizados, introduce el ID exacto en la configuración nativa.

## Opciones nativas

- `home_assistant_url`: dirección de Home Assistant (normalmente `http://supervisor/core`).
- `start_date`: fecha inicial para llenar una base vacía (`YYYY-MM-DD`); las siguientes sincronizaciones son incrementales.
- `database_file` y `table`: archivo y tabla SQLite. El archivo debe ser un nombre simple, sin rutas.
- `timezone`, `sync_hour` y `sync_minute`: zona IANA y hora local de la sincronización diaria.
- `run_on_startup`: sincroniza al iniciar, además del horario diario.
- `healthchecks_ping_url`: URL opcional de Healthchecks.io.
- `*_stat`: IDs manuales de reserva para las estadísticas de energía.

Se exportan días completos hasta ayer. SQLite se almacena bajo `/data`, persistente entre reinicios. Los logs están en la pestaña **Registro** del add-on.

## Pruebas locales con Docker Compose

Docker Compose sirve para probar la compilación, la conexión con Home Assistant y la interfaz del selector fuera de Supervisor. No reproduce Ingress: el panel se publica en `http://127.0.0.1:8099/`, limitado al equipo local.

Requisitos: Docker Engine y el plugin Docker Compose. El equipo donde corre Docker necesita acceso de red a Home Assistant.

1. Desde este directorio, crea las opciones y el archivo de entorno local:

   ```sh
   mkdir -p data
   cp options.local.example.json data/options.json
   cp .env.example .env
   ```

2. Edita `.env` y sustituye el valor de `SUPERVISOR_TOKEN` por un token válido de Home Assistant para pruebas locales. No lo compartas ni lo confirmes en Git. En Docker Compose local este valor lo proporcionas tú; en el add-on instalado en Supervisor, Supervisor lo inyecta automáticamente.

3. Edita `data/options.json`. Para Home Assistant accesible desde el mismo host Docker, `http://host.docker.internal:8123` suele funcionar; el Compose incluye el alias `host-gateway` para Linux. Si HA está en otra máquina, usa su URL alcanzable desde el contenedor. Ajusta la zona horaria y los statistic IDs reales.

4. Arranca el contenedor:

   ```sh
   docker compose up --build -d
   docker compose logs -f energy-export
   ```

5. Abre `http://127.0.0.1:8099/`, vuelve a cargar sensores, elige sugerencias y guarda. Las selecciones y la base SQLite quedarán en `data/`.

Para detenerlo: `docker compose down`. Para reconstruir tras cambios de código: `docker compose up --build -d`.

> El formulario de configuración de Supervisor no se utiliza en Compose: el contenedor lee `data/options.json`. Si el puerto 8123 no responde desde el contenedor, comprueba el firewall y que Home Assistant permita conexiones desde el host Docker. No publiques el puerto 8099 en una interfaz accesible desde Internet; el proxy Ingress/autenticación solo lo proporciona Supervisor.

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
    ├── docker-compose.yml
    ├── options.local.example.json
    ├── README.md
    └── www/index.html
```

El `Dockerfile` instala dependencias desde el `requirements.txt` local y copia código/interfaz locales; no descarga código desde el proyecto Python original durante la compilación.