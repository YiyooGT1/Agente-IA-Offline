"""Plan de organización (vista previa), aplicación con registro e historial para Deshacer."""
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import config
from modelo.utiles import es_descendiente, norm


@dataclass
class Movimiento:
    origen: str
    destino: str
    motivo: str        # 'clasificacion' | 'duplicado' | 'carpeta'
    tamano: int = 0


@dataclass
class Plan:
    raiz: str
    movimientos: list = field(default_factory=list)
    grupos: list = field(default_factory=list)
    se_queda: dict = field(default_factory=dict)   # ruta -> motivo por el que NO se mueve

    def _n(self, motivo):
        return sum(1 for m in self.movimientos if m.motivo == motivo)

    @property
    def n_duplicados(self):
        return self._n("duplicado")

    @property
    def n_carpetas(self):
        return self._n("carpeta")

    @property
    def n_clasificacion(self):
        return self._n("clasificacion")

    @property
    def espacio_recuperable(self):
        return sum(m.tamano for m in self.movimientos if m.motivo == "duplicado")


@dataclass
class ResultadoAplicacion:
    lote: str = ""
    movidos: int = 0
    errores: list = field(default_factory=list)          # (ruta, mensaje)
    carpetas_vacias: list = field(default_factory=list)  # quedaron vacías tras mover


def _destino_libre(carpeta, nombre, reservados, es_carpeta=False):
    """Nunca sobrescribe: agrega ' (2)', ' (3)'... si el nombre ya existe o está reservado."""
    candidato = os.path.join(carpeta, nombre)
    stem, ext = (nombre, "") if es_carpeta else os.path.splitext(nombre)
    n = 2
    while os.path.exists(candidato) or norm(candidato) in reservados:
        candidato = os.path.join(carpeta, f"{stem} ({n}){ext}")
        n += 1
    return candidato


def _dentro_de_alguna(ruta, carpetas_norm):
    n = norm(ruta)
    return any(n.startswith(c.rstrip(os.sep) + os.sep) for c in carpetas_norm)


def construir_plan(raiz, archivos, grupos, op) -> Plan:
    prot = [norm(c) for c in op.protegidas]
    unid = [norm(c) for c in op.carpetas_unidad]
    sobrantes = {a.ruta for g in grupos for a in g.sobrantes}
    se_queda, reservados, movs = {}, set(), []

    for a in sorted(archivos, key=lambda x: x.ruta.lower()):
        if _dentro_de_alguna(a.ruta, prot):
            se_queda[a.ruta] = "carpeta protegida"
            continue
        if _dentro_de_alguna(a.ruta, unid):
            se_queda[a.ruta] = "se mueve con su carpeta"
            continue
        if not op.activas.get(a.categoria, True):
            se_queda[a.ruta] = f"categoría «{a.categoria}» desactivada"
            continue
        es_dup = a.ruta in sobrantes
        clave = config.CARPETA_DUPLICADOS if es_dup else a.categoria
        carpeta = op.destinos.get(clave) or os.path.join(raiz, clave)
        if norm(os.path.dirname(a.ruta)) == norm(carpeta):
            continue                                   # ya está en su lugar
        destino = _destino_libre(carpeta, a.nombre, reservados)
        reservados.add(norm(destino))
        movs.append(Movimiento(a.ruta, destino, "duplicado" if es_dup else "clasificacion", a.tamano))

    for carpeta, padre in op.carpetas_unidad.items():
        if not os.path.isdir(carpeta):
            continue
        if norm(os.path.dirname(carpeta)) == norm(padre):
            continue                                   # ya está ahí
        if norm(padre) == norm(carpeta) or es_descendiente(padre, carpeta):
            continue                                   # no se puede mover una carpeta dentro de sí misma
        destino = _destino_libre(padre, os.path.basename(carpeta), reservados, es_carpeta=True)
        reservados.add(norm(destino))
        tam = sum(a.tamano for a in archivos if es_descendiente(a.ruta, carpeta))
        movs.append(Movimiento(carpeta, destino, "carpeta", tam))

    return Plan(raiz, movs, grupos, se_queda)


def estado_carpeta(carpeta, op) -> str:
    """Texto para la pestaña Carpetas."""
    n = norm(carpeta)
    if n in {norm(c) for c in op.protegidas}:
        return "Protegida (parece un programa)"
    if any(es_descendiente(carpeta, c) for c in op.protegidas):
        return "Dentro de una carpeta protegida"
    for c, destino in op.carpetas_unidad.items():
        if norm(c) == n:
            return f"Se moverá completa a: {destino}"
    if any(es_descendiente(carpeta, c) for c in op.carpetas_unidad):
        return "Se mueve con su carpeta"
    return ""


def _carpetas_vacias(raiz, origenes):
    """Carpetas (ancestros de lo movido, dentro de la raíz) que quedaron sin ningún archivo."""
    candidatas = set()
    for o in origenes:
        d = os.path.dirname(o)
        while es_descendiente(d, raiz):
            candidatas.add(d)
            d = os.path.dirname(d)
    vacias = []
    for d in sorted(candidatas, key=lambda p: p.count(os.sep), reverse=True):
        if os.path.isdir(d) and not any(fs for _, _, fs in os.walk(d)):
            vacias.append(d)
    return vacias


def eliminar_carpetas_vacias(carpetas) -> int:
    """Solo elimina carpetas realmente vacías (os.rmdir falla si hay algo dentro). Más profundas primero."""
    n = 0
    for d in sorted(carpetas, key=lambda p: p.count(os.sep), reverse=True):
        try:
            os.rmdir(d)
            n += 1
        except OSError:
            pass
    return n


def aplicar(plan, db, progreso=None) -> ResultadoAplicacion:
    res = ResultadoAplicacion(lote=datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6])
    buffer, origenes_ok = [], []
    total = len(plan.movimientos)
    try:
        for i, m in enumerate(plan.movimientos, 1):
            try:
                if not os.path.exists(m.origen):
                    raise FileNotFoundError("ya no existe")
                if os.path.exists(m.destino):
                    raise FileExistsError("el destino ya existe")
                os.makedirs(os.path.dirname(m.destino), exist_ok=True)
                shutil.move(m.origen, m.destino)
                buffer.append((res.lote, m.origen, m.destino, m.motivo))
                origenes_ok.append(m.origen)
                res.movidos += 1
            except OSError as e:
                res.errores.append((m.origen, str(e)))
            if len(buffer) >= 25:                      # commit por lotes pequeños: rápido y seguro
                db.registrar_movimientos(buffer)
                buffer = []
            if progreso:
                progreso(i, total)
    finally:
        if buffer:
            db.registrar_movimientos(buffer)
    res.carpetas_vacias = _carpetas_vacias(plan.raiz, origenes_ok)
    return res


def deshacer(db, progreso=None):
    """Revierte el último lote activo. Devuelve (lote, revertidos, errores)."""
    lote = db.ultimo_lote_activo()
    if not lote:
        return None, 0, []
    filas = list(reversed(db.movimientos_activos_de_lote(lote)))
    revertidos, errores, ids_ok, carpetas = 0, [], [], set()
    for i, f in enumerate(filas, 1):
        try:
            if not os.path.exists(f["destino"]):
                raise FileNotFoundError("ya no está en su destino")
            if os.path.exists(f["origen"]):
                raise FileExistsError("la ubicación original está ocupada")
            os.makedirs(os.path.dirname(f["origen"]), exist_ok=True)
            shutil.move(f["destino"], f["origen"])
            ids_ok.append(f["id_movimiento"])
            carpetas.add(os.path.dirname(f["destino"]))
            revertidos += 1
        except OSError as e:
            errores.append((f["destino"], str(e)))
        if progreso:
            progreso(i, len(filas))
    db.marcar_revertidos(ids_ok)
    permitidas = set(config.CATEGORIAS) | {config.CATEGORIA_POR_DEFECTO, config.CARPETA_DUPLICADOS}
    for c in carpetas:                                 # limpia solo carpetas de categoría que quedaron vacías
        try:
            if os.path.basename(c) in permitidas and not os.listdir(c):
                os.rmdir(c)
        except OSError:
            pass
    return lote, revertidos, errores
