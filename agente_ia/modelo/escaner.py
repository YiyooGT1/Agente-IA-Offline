"""Escáner de carpetas: recursivo, iterativo, cancelable y tolerante a errores de permisos."""
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

import config
from modelo import clasificador
from modelo.utiles import norm


@dataclass
class ArchivoInfo:
    ruta: str
    nombre: str
    extension: str
    tamano: int
    fecha_modif: float
    categoria: str


@dataclass
class ResultadoEscaneo:
    archivos: list = field(default_factory=list)
    total_carpetas: int = 0
    omitidos_video: int = 0
    errores: list = field(default_factory=list)   # rutas sin permiso
    carpetas_programa: list = field(default_factory=list)  # carpetas que parecen programas instalados
    cancelado: bool = False


class Escaner:
    def __init__(self, cancelar=None):
        self.cancelar = cancelar  # threading.Event opcional

    def verificar_ruta(self, ruta: str) -> bool:
        return os.path.isdir(ruta)

    def validar_permisos(self, ruta: str) -> bool:
        return os.access(ruta, os.R_OK | os.X_OK)

    @staticmethod
    def _ignorar(nombre: str) -> bool:
        n = nombre.lower()
        return n.startswith(".") or n in config.CARPETAS_IGNORADAS

    def escanear(self, ruta: str, recursivo: bool = True,
                 progreso: Optional[Callable[[int, str], None]] = None) -> ResultadoEscaneo:
        res = ResultadoEscaneo()
        pendientes = [ruta]
        # La carpeta Duplicados de la raíz es salida del propio agente: no se vuelve a escanear.
        dup_dir = os.path.normcase(os.path.normpath(os.path.join(ruta, config.CARPETA_DUPLICADOS)))
        while pendientes:
            if self.cancelar is not None and self.cancelar.is_set():
                res.cancelado = True
                break
            actual = pendientes.pop()
            tiene_lib = tiene_exe = False
            try:
                with os.scandir(actual) as it:
                    for e in it:
                        try:
                            if e.is_dir(follow_symlinks=False):
                                if self._ignorar(e.name):
                                    continue
                                if os.path.normcase(os.path.normpath(e.path)) == dup_dir:
                                    continue
                                res.total_carpetas += 1
                                if recursivo:
                                    pendientes.append(e.path)
                            elif e.is_file(follow_symlinks=False):
                                if e.name.startswith("."):
                                    continue
                                ext = clasificador.extension_de(e.name)
                                if ext in config.EXT_PROGRAMA_FUERTE:
                                    tiene_lib = True
                                elif ext in config.EXT_EJECUTABLE:
                                    tiene_exe = True
                                if clasificador.es_video(ext):
                                    res.omitidos_video += 1
                                    continue
                                st = e.stat()
                                res.archivos.append(ArchivoInfo(
                                    e.path, e.name, ext, st.st_size, st.st_mtime,
                                    clasificador.clasificar(ext)))
                        except OSError:
                            res.errores.append(e.path)
                if tiene_lib or (tiene_exe and norm(actual) != norm(ruta)):
                    res.carpetas_programa.append(actual)
            except (PermissionError, OSError):
                res.errores.append(actual)
            if progreso:
                progreso(len(res.archivos), actual)
        return res
