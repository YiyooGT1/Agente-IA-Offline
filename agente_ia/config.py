"""Configuración central del Agente IA local."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "datos" / "agente_ia.db"

# Carpetas que el escáner nunca recorre (comparación en minúsculas).
# Además se ignora toda carpeta oculta que empiece con ".".
CARPETAS_IGNORADAS = {
    "node_modules", "__pycache__", "venv", "env",
    "appdata", "$recycle.bin", "system volume information",
    "windows", "program files", "program files (x86)", "programdata",
}

# Los videos quedan fuera del alcance actual (fase futura).
EXTENSIONES_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}

CATEGORIAS = {
    "Documentos": {".doc", ".docx", ".odt", ".rtf", ".txt", ".md"},
    "PDFs": {".pdf"},
    "Hojas de cálculo": {".xls", ".xlsx", ".xlsm", ".ods", ".csv"},
    "Presentaciones": {".ppt", ".pptx", ".odp"},
    "Imágenes": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".heic", ".svg"},
    "Comprimidos": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "Código": {".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".cs",
               ".php", ".sql", ".json", ".xml", ".sh", ".bat"},
}
CATEGORIA_POR_DEFECTO = "Otros"

CARPETA_DUPLICADOS = "Duplicados"

# --- Protección de carpetas de programas ---
# Una carpeta que contiene librerías (.dll/.sys/.ocx), o un .exe fuera de la raíz escaneada,
# se considera un programa instalado y NO se toca salvo que el usuario la incluya.
EXT_PROGRAMA_FUERTE = {".dll", ".sys", ".ocx"}
EXT_EJECUTABLE = {".exe"}

# Categorías que no se mueven por defecto (suelen ser configuración de programas).
CATEGORIAS_DESACTIVADAS_POR_DEFECTO = {"Otros"}
