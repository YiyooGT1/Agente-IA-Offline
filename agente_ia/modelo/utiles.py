import os


def formatear_tamano(n: int) -> str:
    n = float(n)
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{int(n)} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024


def norm(p: str) -> str:
    """Ruta normalizada para comparar (separadores y mayúsculas según el sistema)."""
    return os.path.normcase(os.path.normpath(p))


def es_descendiente(ruta: str, carpeta: str) -> bool:
    """True si 'ruta' está estrictamente dentro de 'carpeta'."""
    r, c = norm(ruta), norm(carpeta)
    return r.startswith(c.rstrip(os.sep) + os.sep)
