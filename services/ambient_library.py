import json
import re
import shutil
from pathlib import Path

SUPPORTED_EXTENSIONS = (".wav", ".ogg", ".mp3", ".flac")
META_FILENAME = "library.json"


class AmbientLibrary:
    """
    Biblioteca de sonidos ambientales del usuario.

    Guarda los archivos en ``base_dir`` y mantiene un mapa ``archivo -> nombre``
    legible en ``library.json``. No depende de Qt (logica de filesystem pura).
    """

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
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
        """Lista de {filename, name, path} ordenada por nombre legible."""
        result = []
        for path in self.base_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            result.append({
                "filename": path.name,
                "name": self.display_name(path.name),
                "path": path,
            })
        result.sort(key=lambda e: e["name"].lower())
        return result

    def exists(self, filename):
        return bool(filename) and (self.base_dir / filename).is_file()

    def path(self, filename):
        return self.base_dir / filename

    def display_name(self, filename):
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
        path = self.base_dir / filename
        if path.exists():
            path.unlink()
        self._names.pop(filename, None)
        self._save()

    def rename(self, filename, new_name):
        if not self.exists(filename):
            return
        clean = (new_name or "").strip()
        self._names[filename] = clean or Path(filename).stem
        self._save()

    # ------------------------------------------------------------------- helpers
    def _unique_name(self, original):
        path = Path(original)
        stem = self._sanitize(path.stem)
        ext = path.suffix.lower()
        candidate = f"{stem}{ext}"
        counter = 1
        while (self.base_dir / candidate).exists():
            candidate = f"{stem}_{counter}{ext}"
            counter += 1
        return candidate

    @staticmethod
    def _sanitize(stem):
        stem = re.sub(r"[^\w\-. ]+", "", stem, flags=re.UNICODE).strip()
        stem = re.sub(r"\s+", "_", stem)
        return stem or "sonido"
