# Home Assistant Energy Export

Este repositorio contiene el código del exportador y el add-on de Home Assistant en `energy_export/`.

## Instalar desde este repositorio

En Home Assistant, abre **Ajustes → Complementos → Tienda de complementos → ⋮ → Repositorios**, añade `https://github.com/DIAZGZA/export-homeassistant-energy` y luego instala **Energy Export**.

La guía del add-on, las opciones y el panel Ingress están en [`energy_export/README.md`](energy_export/README.md).

## Crear un repositorio de add-ons independiente

Para publicar solo el add-on en un repositorio nuevo, copia `repository.yaml` y toda la carpeta `energy_export/` a la raíz del nuevo repositorio. Actualiza las URLs de `repository.yaml` y `energy_export/config.yaml` para que apunten al nuevo repositorio. Instrucciones detalladas: [`README-addon-repo.md`](README-addon-repo.md).

## Pruebas locales con Docker Compose

Consulta [`energy_export/README.md`](energy_export/README.md#pruebas-locales-con-docker-compose). La prueba levanta el panel local en `127.0.0.1:8099`; Docker Compose no reproduce la autenticación ni la navegación Ingress de Supervisor.
