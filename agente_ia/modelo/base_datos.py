"""Capa SQLite (stdlib, sin servidor). Una conexión por operación: segura para hilos."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS log_escaneos (
    id_escaneo       INTEGER PRIMARY KEY AUTOINCREMENT,
    ruta_analizada   TEXT    NOT NULL,
    acceso_permitido INTEGER NOT NULL,
    total_carpetas   INTEGER NOT NULL DEFAULT 0,
    total_archivos   INTEGER NOT NULL DEFAULT 0,
    fecha_escaneo    TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS archivos (
    id_archivo   INTEGER PRIMARY KEY AUTOINCREMENT,
    id_escaneo   INTEGER NOT NULL REFERENCES log_escaneos(id_escaneo) ON DELETE CASCADE,
    ruta         TEXT    NOT NULL,
    nombre       TEXT    NOT NULL,
    extension    TEXT,
    categoria    TEXT,
    tamano       INTEGER,
    fecha_modif  REAL,
    hash         TEXT
);
CREATE INDEX IF NOT EXISTS idx_archivos_escaneo ON archivos(id_escaneo);
CREATE INDEX IF NOT EXISTS idx_archivos_tamano  ON archivos(tamano);

-- Historial de movimientos: base del botón "Deshacer" (se usa en el paso de organización).
CREATE TABLE IF NOT EXISTS movimientos (
    id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
    lote          TEXT NOT NULL,
    origen        TEXT NOT NULL,
    destino       TEXT NOT NULL,
    motivo        TEXT NOT NULL,           -- 'clasificacion' | 'duplicado'
    fecha         TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    revertido     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_mov_lote ON movimientos(lote);

-- Preferencias del usuario (destinos personalizados, etc.): el agente recuerda cómo ordena cada persona.
CREATE TABLE IF NOT EXISTS preferencias (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);
"""


class BaseDatos:
    def __init__(self, ruta_db):
        self.ruta_db = Path(ruta_db)
        self.ruta_db.parent.mkdir(parents=True, exist_ok=True)
        with self._conexion() as con:
            con.executescript(ESQUEMA)

    @contextmanager
    def _conexion(self):
        con = sqlite3.connect(self.ruta_db)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def registrar_escaneo(self, ruta, acceso, carpetas, archivos, lista_archivos=None) -> int:
        """Guarda el log y, si se entrega, el detalle de archivos. Devuelve el id del escaneo."""
        with self._conexion() as con:
            cur = con.execute(
                "INSERT INTO log_escaneos (ruta_analizada, acceso_permitido, total_carpetas, total_archivos) "
                "VALUES (?, ?, ?, ?)", (ruta, int(acceso), carpetas, archivos))
            id_escaneo = cur.lastrowid
            if lista_archivos:
                con.executemany(
                    "INSERT INTO archivos (id_escaneo, ruta, nombre, extension, categoria, tamano, fecha_modif) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [(id_escaneo, a.ruta, a.nombre, a.extension, a.categoria, a.tamano, a.fecha_modif)
                     for a in lista_archivos])
            return id_escaneo

    def listar_escaneos(self, limite=20):
        with self._conexion() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM log_escaneos ORDER BY id_escaneo DESC LIMIT ?", (limite,))]

    # ---- hashes ----
    def actualizar_hashes(self, id_escaneo, hashes: dict):
        if not hashes:
            return
        with self._conexion() as con:
            con.executemany("UPDATE archivos SET hash = ? WHERE id_escaneo = ? AND ruta = ?",
                            [(h, id_escaneo, ruta) for ruta, h in hashes.items()])

    # ---- historial de movimientos (Deshacer) ----
    def registrar_movimientos(self, filas):
        """filas: lista de (lote, origen, destino, motivo)."""
        with self._conexion() as con:
            con.executemany("INSERT INTO movimientos (lote, origen, destino, motivo) VALUES (?, ?, ?, ?)", filas)

    def ultimo_lote_activo(self):
        with self._conexion() as con:
            r = con.execute("SELECT lote FROM movimientos WHERE revertido = 0 "
                            "ORDER BY id_movimiento DESC LIMIT 1").fetchone()
            return r["lote"] if r else None

    def movimientos_activos_de_lote(self, lote):
        with self._conexion() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM movimientos WHERE lote = ? AND revertido = 0 ORDER BY id_movimiento", (lote,))]

    def marcar_revertidos(self, ids):
        if not ids:
            return
        with self._conexion() as con:
            con.executemany("UPDATE movimientos SET revertido = 1 WHERE id_movimiento = ?", [(i,) for i in ids])

    # ---- preferencias ----
    def obtener_preferencia(self, clave):
        with self._conexion() as con:
            r = con.execute("SELECT valor FROM preferencias WHERE clave = ?", (clave,)).fetchone()
            return r["valor"] if r else None

    def guardar_preferencia(self, clave, valor):
        with self._conexion() as con:
            con.execute("INSERT INTO preferencias (clave, valor) VALUES (?, ?) "
                        "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor", (clave, valor))
