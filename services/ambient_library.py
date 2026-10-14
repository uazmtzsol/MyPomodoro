import json
import re
import shutil
from pathlib import Path

from services.resource_manager import get_resources_dir

SUPPORTED_EXTENSIONS = (".wav", ".ogg", ".mp3", ".flac")
META_FILENAME = "library.json"

# Sonidos incluidos con la app (en resources/). No se pueden gestionar ni borrar.
BUILTIN_SOUNDS = (
    {"filename": "rain.ogg", "name": "Lluvia"},
    {"filename": "ambience.ogg", "name": "Ambiente"},
)


def format_size(num_bytes):
    """Tamaño legible: 512 B, 4.2 KB, 5.0 MB, 1.2 GB."""
    size = float(max(0, num_bytes))
    if size < 1024:
        return f"{int(size)} B"
    for unit in ("KB", "MB", "GB"):
        size /= 1024
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"


class AmbientLibrary:
    """
    Biblioteca de sonidos ambientales.

    Combina dos origenes:
    - **Incluidos** (``BUILTIN_SOUNDS``): vienen con la app en el directorio de
      recursos (bundle o ``resources/``). Siempre existen y no se gestionan.
    - **Del usuario**: archivos en ``base_dir`` con nombre legible en
      ``library.json``. Se pueden subir, renombrar y quitar.

    No depende de Qt (logica de filesystem pura).
    """

    def __init__(self, base_dir, builtin_dir=None):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.builtin_dir = Path(builtin_dir) if builtin_dir else get_resources_dir()
        self.meta_path = self.base_dir / META_FILENAME
        self._names = self._load()

    # ------------------------------------------------------------------ metadatos
    def _load(self):
        if self.meta_path.exists():
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self._names, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ consultas
    def entries(self):
        """Incluidos primero, luego los del usuario (ordenados por nombre)."""
        return self.builtin_entries() + self.user_entries()

    def builtin_entries(self):
        result = []
        for spec in BUILTIN_SOUNDS:
            path = self.builtin_dir / spec["filename"]
            if not path.is_file():
                continue
            result.append({
                "filename": spec["filename"],
                "name": spec["name"],
                "path": path,
                "size": self._size(path),
                "builtin": True,
            })
        return result

    def user_entries(self):
        result = []
        for path in self.base_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            result.append({
                "filename": path.name,
                "name": self.display_name(path.name),
                "path": path,
                "size": self._size(path),
                "builtin": False,
            })
        result.sort(key=lambda e: e["name"].lower())
        return result

    @staticmethod
    def _size(path):
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def is_builtin(self, filename):
        return any(spec["filename"] == filename for spec in BUILTIN_SOUNDS)

    def exists(self, filename):
        return bool(filename) and self.path(filename).is_file()

    def path(self, filename):
        if self.is_builtin(filename):
            return self.builtin_dir / filename
        return self.base_dir / filename

    def display_name(self, filename):
        for spec in BUILTIN_SOUNDS:
            if spec["filename"] == filename:
                return spec["name"]
        return self._names.get(filename) or Path(filename).stem

    def is_supported(self, filename):
        return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS

    # ------------------------------------------------------------------- cambios
    def add(self, src_path, name):
        """Copia un archivo a la biblioteca y le asigna un nombre. Devuelve el filename."""
        src = Path(src_path)
        if not src.is_file():
            raise FileNotFoundError(src)
        if not self.is_supported(src.name):
            raise ValueError(f"Formato no soportado: {src.suffix}")

        filename = self._unique_name(src.name)
        shutil.copy2(src, self.base_dir / filename)
        clean = (name or "").strip()
        self._names[filename] = clean or src.stem
        self._save()
        return filename

    def remove(self, filename):
        if self.is_builtin(filename):
            raise ValueError("Los sonidos incluidos no se pueden eliminar.")
        path = self.base_dir / filename
        if path.exists():
            path.unlink()
        self._names.pop(filename, None)
        self._save()

    def rename(self, filename, new_name):
        if self.is_builtin(filename) or not self.exists(filename):
            return
        clean = (new_name or "").strip()
        self._names[filename] = clean or Path(filename).stem
        self._save()

    # ------------------------------------------------------------------- helpers
    def _unique_name(self, original):
        path = Path(original)
        stem = self._sanitize(path.stem)
        ext = path.suffix.lower()
        reserved = {spec["filename"].lower() for spec in BUILTIN_SOUNDS}
        candidate = f"{stem}{ext}"
        counter = 1
        while (self.base_dir / candidate).exists() or candidate.lower() in reserved:
            candidate = f"{stem}_{counter}{ext}"
            counter += 1
        return candidate

    @staticmethod
    def _sanitize(stem):
        stem = re.sub(r"[^\w\-. ]+", "", stem, flags=re.UNICODE).strip()
        stem = re.sub(r"\s+", "_", stem)
        return stem or "sonido"
