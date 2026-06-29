---
name: skill_scanner_local
description: Escanea un directorio local del sistema, cuenta la cantidad de carpetas y archivos, y guarda un registro en una base de datos MySQL. Úsalo cada vez que el usuario te pida analizar una ruta, contar archivos en su disco duro o verificar un directorio.
---

# Skill Scanner Local

Esta habilidad le permite al Agente de IA ejecutar un escáner de archivos local. La lógica está construida en Python bajo el patrón MVC.

## Cómo ejecutar esta habilidad
El agente debe iniciar el proceso ejecutando el controlador principal:
`python controlador.py`

## Reglas de la habilidad
- La habilidad validará los permisos de lectura locales antes de intentar contar los archivos.
- Si el usuario no tiene permisos en la carpeta seleccionada, el escaneo se detiene.
- Cada intento de escaneo (exitoso o fallido) se guardará automáticamente en la base de datos MySQL local (`db_agente_ia`, tabla `log_escaneos`).