"""Detección de duplicados en dos pasos: 1) mismo tamaño, 2) mismo hash SHA-256."""
import hashlib
from collections import defaultdict
from dataclasses import dataclass

TAM_BLOQUE = 1024 * 1024


@dataclass
class GrupoDuplicados:
    hash: str
    tamano: int
    archivos: list              # ordenados: el más antiguo / ruta más corta primero
    indice_conservado: int = 0  # propuesta por defecto; el usuario puede cambiarla

    @property
    def conservado(self):
        return self.archivos[self.indice_conservado]

    @property
    def sobrantes(self):
        return [a for i, a in enumerate(self.archivos) if i != self.indice_conservado]

    @property
    def espacio_recuperable(self) -> int:
        return self.tamano * (len(self.archivos) - 1)


def calcular_hash(ruta, cancelar=None):
    """SHA-256 por bloques. Devuelve None si se cancela."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        while True:
            bloque = f.read(TAM_BLOQUE)
            if not bloque:
                break
            if cancelar is not None and cancelar.is_set():
                return None
            h.update(bloque)
    return h.hexdigest()


def _clave_propuesta(a):
    # Más antiguo primero; a igualdad, ruta más corta; luego alfabético.
    return (a.fecha_modif, len(a.ruta), a.ruta.lower())


def detectar(archivos, cancelar=None, progreso=None):
    """Devuelve (grupos, hashes{ruta: hash}). Si se cancela, devuelve ([], {})."""
    por_tamano = defaultdict(list)
    for a in archivos:
        if a.tamano > 0:                       # los archivos vacíos no cuentan como duplicados
            por_tamano[a.tamano].append(a)
    candidatos = [g for g in por_tamano.values() if len(g) > 1]
    total = sum(len(g) for g in candidatos)

    hechos = 0
    hashes = {}
    por_hash = defaultdict(list)
    for grupo in candidatos:
        for a in grupo:
            if cancelar is not None and cancelar.is_set():
                return [], {}
            try:
                h = calcular_hash(a.ruta, cancelar)
            except OSError:
                h = None                       # archivo bloqueado o movido: se omite
            hechos += 1
            if progreso:
                progreso(hechos, total)
            if h is None:
                if cancelar is not None and cancelar.is_set():
                    return [], {}
                continue
            hashes[a.ruta] = h
            por_hash[(a.tamano, h)].append(a)

    grupos = []
    for (tam, h), lista in por_hash.items():
        if len(lista) > 1:
            lista.sort(key=_clave_propuesta)
            grupos.append(GrupoDuplicados(h, tam, lista))
    grupos.sort(key=lambda g: g.espacio_recuperable, reverse=True)
    return grupos, hashes
