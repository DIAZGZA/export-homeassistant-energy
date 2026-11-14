# Home Assistant Energy Export

Este repositorio contiene la herramienta Python para exportar estadísticas de energía de Home Assistant a Excel y SQLite, además de un add-on instalable para Home Assistant Supervisor.

## Instalar como add-on

Añade `https://github.com/DIAZGZA/export-homeassistant-energy` en **Ajustes → Complementos → Tienda de complementos → ⋮ → Repositorios** y luego instala **Energy Export**. La carpeta instalable es `energy_export/`.

La guía completa en español está en [energy_export/README.md](energy_export/README.md), con opciones de configuración, persistencia de datos y solución de problemas.

## Usar los scripts directamente

Consulta las instrucciones de exportación Excel y sincronización SQLite más abajo en este documento. El add-on utiliza el sincronizador SQLite y conserva la base en el almacenamiento persistente de Supervisor.
