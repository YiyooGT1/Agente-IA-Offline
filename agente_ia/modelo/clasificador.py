"""Clasificación por reglas (extensión). Pillow y lectura de contenido llegan en el paso siguiente."""
from pathlib import Path
import config

_MAPA = {ext: cat for cat, exts in config.CATEGORIAS.items() for ext in exts}


def es_video(extension: str) -> bool:
    return extension.lower() in config.EXTENSIONES_VIDEO


def clasificar(extension: str) -> str:
    return _MAPA.get(extension.lower(), config.CATEGORIA_POR_DEFECTO)


def extension_de(nombre: str) -> str:
    return Path(nombre).suffix.lower()
