"""Preferencias del usuario para organizar: destinos por categoría, carpetas completas y protecciones."""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import config
from modelo.utiles import es_descendiente, norm

CLAVE_PREFS = "destinos"


def claves_destino():
    return list(config.CATEGORIAS) + [config.CATEGORIA_POR_DEFECTO, config.CARPETA_DUPLICADOS]


def _activa_por_defecto(clave):
    return clave not in config.CATEGORIAS_DESACTIVADAS_POR_DEFECTO


def accesos_rapidos():
    """Carpetas habituales del usuario que existan (inglés/español, con y sin OneDrive)."""
    home = Path.home()
    nombres = ["Desktop", "Escritorio", "Documents", "Documentos",
               "Downloads", "Descargas", "Pictures", "Imágenes"]
    vistos, res = set(), []
    for base in (home, home / "OneDrive"):
        for n in nombres:
            p = base / n
            try:
                if p.is_dir() and norm(str(p)) not in vistos:
                    vistos.add(norm(str(p)))
                    res.append(str(p))
            except OSError:
                pass
    return res


@dataclass
class Opciones:
    raiz: str
    destinos: dict = field(default_factory=dict)         # clave -> carpeta destino
    activas: dict = field(default_factory=dict)          # categoría -> ¿se mueve?
    carpetas_unidad: dict = field(default_factory=dict)  # carpeta -> carpeta padre destino
    protegidas: set = field(default_factory=set)         # carpetas que no se tocan

    def destino_defecto(self, clave):
        return os.path.join(self.raiz, clave)

    def restablecer(self):
        for k in claves_destino():
            self.destinos[k] = self.destino_defecto(k)
            self.activas[k] = _activa_por_defecto(k)


def cimas(carpetas):
    """Deja solo las carpetas de más arriba (si una contiene a otra, se queda la contenedora)."""
    lista = sorted(set(carpetas), key=lambda p: len(norm(p)))
    res = []
    for c in lista:
        if not any(norm(c) == norm(r) or es_descendiente(c, r) for r in res):
            res.append(c)
    return res


def crear_opciones(raiz, protegidas, prefs=None) -> Opciones:
    op = Opciones(raiz)
    op.restablecer()
    prefs = prefs or {}
    for k, d in prefs.get("destinos", {}).items():
        if k in op.destinos and d:
            op.destinos[k] = d
    for k, a in prefs.get("activas", {}).items():
        if k in op.activas:
            op.activas[k] = bool(a)
    op.protegidas = set(cimas(protegidas))
    return op


def cargar_prefs(db) -> dict:
    try:
        crudo = db.obtener_preferencia(CLAVE_PREFS)
        return json.loads(crudo) if crudo else {}
    except Exception:
        return {}


def guardar_prefs(db, op: Opciones):
    """Guarda solo lo que el usuario cambió respecto de los valores predeterminados."""
    destinos = {k: v for k, v in op.destinos.items() if norm(v) != norm(op.destino_defecto(k))}
    activas = {k: v for k, v in op.activas.items() if v != _activa_por_defecto(k)}
    db.guardar_preferencia(CLAVE_PREFS, json.dumps({"destinos": destinos, "activas": activas}))
