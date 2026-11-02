---
name: skill_scanner_local
description: Agente de IA local y offline que escanea una carpeta (incluyendo subcarpetas), clasifica archivos por categoría, detecta duplicados y propone una organización personalizable (destinos por categoría, carpetas completas, protección de programas) con vista previa y opción de deshacer, registrando todo en SQLite. Úsalo cuando el usuario pida analizar, ordenar o limpiar archivos de una ruta de su equipo.
---

# Skill Scanner Local

Agente local, 100% offline, Python con patrón MVC. Sin dependencias externas en esta fase (`tkinter`, `sqlite3`).

## Cómo ejecutar esta habilidad
`python controlador.py`

## Estructura
- `controlador.py`: punto de entrada; coordina hilos de trabajo e interfaz.
- `config.py`: rutas, categorías, carpetas ignoradas.
- `modelo/base_datos.py`: SQLite (`datos/agente_ia.db`): `log_escaneos`, `archivos`, `movimientos`.
- `modelo/escaner.py`: escaneo recursivo cancelable.
- `modelo/clasificador.py`: clasificación por reglas.
- `modelo/duplicados.py`: duplicados en dos pasos (tamaño, luego SHA-256).
- `modelo/organizador.py`: plan, aplicación, limpieza de carpetas vacías e historial para deshacer.
- `modelo/opciones.py`: destinos personalizados, carpetas completas, protecciones y preferencias guardadas.
- `vista/ventana.py` y `vista/vista_previa.py`: interfaz Tkinter.

## Reglas de la habilidad
- Valida permisos de lectura antes de escanear; sin permiso el escaneo se detiene y se registra el intento.
- Ignora carpetas ocultas y de sistema; no sigue enlaces simbólicos; los videos quedan fuera del alcance.
- Nunca borra ni sobrescribe: los archivos se mueven y los nombres repetidos reciben sufijo ` (2)`.
- En cada grupo de duplicados se propone conservar la copia más antigua; el usuario puede cambiarla.
- Nada se mueve sin confirmación del usuario en la vista previa.
- El usuario elige el destino de cada categoría (y si se mueve o no); sus elecciones se recuerdan en SQLite.
- Las carpetas que parecen programas instalados (.dll/.sys/.ocx, o .exe fuera de la raíz) están protegidas por defecto; la categoría «Otros» no se mueve por defecto.
- Una carpeta puede moverse completa como unidad; sus archivos no se clasifican por separado.
- Tras organizar, se ofrece eliminar las carpetas que quedaron vacías (nunca se borran archivos).
- Cada movimiento queda registrado por lote y la última organización puede deshacerse.
- Un escaneo cancelado no se registra.
