import sys
from pathlib import Path


def is_bundled() -> bool:
    """True cuando la app corre empaquetada con PyInstaller."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def bundled_dir() -> Path:
    """
    Directorio base de datos empaquetados.
    - Empaquetado: carpeta temporal de PyInstaller (_MEIPASS).
    - Desarrollo: raíz del proyecto.
    """
    if is_bundled():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_resource_path(relative_path: str) -> Path:
    """
    Ruta absoluta de un recurso estático (iconos, sonidos).
    - Empaquetado: los datos se colocan en la raíz del bundle (ver instalador.bat).
    - Desarrollo: carpeta ``resources/``.
    """
    if is_bundled():
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent.parent / "resources" / relative_path


def get_resources_dir() -> Path:
    """
    Directorio base de recursos estáticos incluidos.
    - Empaquetado: raíz del bundle (_MEIPASS).
    - Desarrollo: carpeta ``resources/``.
    """
    if is_bundled():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent / "resources"


def get_config_dir() -> Path:
    """
    Directorio de configuración persistente del usuario.
    - Windows: %APPDATA%/PomodoroTimer
    - macOS:   ~/Library/Application Support/PomodoroTimer
    - Linux:   ~/.config/PomodoroTimer
    """
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Roaming" / "PomodoroTimer"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "PomodoroTimer"
    else:
        base = Path.home() / ".config" / "PomodoroTimer"

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_stats_path() -> Path:
    """Ruta del archivo de estadísticas persistentes (stats.json)."""
    return get_config_dir() / "stats.json"


def get_tasks_path() -> Path:
    """Ruta del archivo de tareas persistentes (tasks.json)."""
    return get_config_dir() / "tasks.json"
