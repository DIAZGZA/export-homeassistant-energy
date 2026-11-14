# Crear un repositorio independiente del add-on

Esta guía crea un repositorio de add-ons separado que contiene únicamente Energy Export. La estructura incluida en este proyecto ya es autocontenida: el add-on tiene su propio `Dockerfile`, `requirements.txt`, scripts Python y panel Ingress.

## Estructura requerida

Crea un repositorio GitHub nuevo (público si quieres poder añadirlo desde una instalación Home Assistant sin credenciales) y copia estos elementos a su raíz:

```text
nuevo-repo-addon/
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

Desde el clon de este proyecto, por ejemplo:

```sh
mkdir ../energy-export-addons
cp repository.yaml ../energy-export-addons/
cp -R energy_export ../energy-export-addons/
```

Después actualiza las URL del repositorio en `repository.yaml` y `energy_export/config.yaml`, confirma y sube los archivos a la rama predeterminada del nuevo repositorio. Comprueba que `repository.yaml` está directamente en la raíz y que `energy_export/config.yaml` está un nivel debajo.

## Instalar en Home Assistant

1. Abre **Ajustes → Complementos → Tienda de complementos**.
2. En el menú **⋮**, selecciona **Repositorios**.
3. Añade la URL HTTPS del nuevo repositorio y confirma.
4. Instala **Energy Export**, configura sus opciones nativas y arráncalo.
5. Abre el panel **Energía** para buscar y seleccionar sensores.

El token de Supervisor se inyecta automáticamente con `homeassistant_api: true`. No lo añadas al repositorio ni al `config.yaml`.

## Prueba de desarrollo local

Antes de subir, sigue la sección **Pruebas locales con Docker Compose** de [`energy_export/README.md`](energy_export/README.md#pruebas-locales-con-docker-compose). Docker Compose permite verificar la imagen, la API y el panel en local, pero no sustituye la instalación de prueba en Supervisor: Ingress y la gestión de opciones dependen de Home Assistant.
