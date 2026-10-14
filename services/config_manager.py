import json
from pathlib import Path

from services.resource_manager import get_config_dir


class ConfigManager:
    """Configuración persistente del usuario (config.json)."""

    DEFAULT_CONFIG = {
        "work_duration": 25,
        "short_break_duration": 5,
        "long_break_duration": 15,
        "consecutive_sessions": 1,
        "always_on_top": False,
        "window_position": {"x": 100, "y": 100},
        "expanded_mode": False,
        "progress_mode": "regressive",
        "tick_enabled": True,
        "tick_volume": 50,
        "tick_sound": "normal",
        "tick_during_breaks": False,
        "notification_volume": 80,
        "ambient_enabled": False,
        "ambient_volume": 40,
        "ambient_track": "",
        "active_breaks_enabled": True,
        "theme": "dark",
        "sounds_installed": False,
    }

    def __init__(self):
        self.config_dir = get_config_dir()
        self.config_path = self.config_dir / "config.json"
        self.sounds_dir = self.config_dir / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        self.ambient_dir = self.config_dir / "ambient"
        self.ambient_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                return self._merge(loaded)
            except Exception:
                pass
        return json.loads(json.dumps(self.DEFAULT_CONFIG))

    @classmethod
    def _merge(cls, loaded):
        """
        Fusiona un archivo cargado con los valores por defecto.

        - Ignora claves desconocidas (esquemas antiguos).
        - Fuerza el tipo del valor por defecto para evitar crashes.
        - Migra volúmenes guardados como fracción (0.0-1.0) a porcentaje.
        """
        merged = json.loads(json.dumps(cls.DEFAULT_CONFIG))

        for key, default in cls.DEFAULT_CONFIG.items():
            if key not in loaded:
                continue
            value = loaded[key]
            try:
                if isinstance(default, bool):
                    merged[key] = bool(value)
                elif isinstance(default, int):
                    merged[key] = int(round(float(value)))
                elif isinstance(default, float):
                    merged[key] = float(value)
                elif isinstance(default, dict) and isinstance(value, dict):
                    merged[key] = value
                elif isinstance(default, str) and isinstance(value, str):
                    merged[key] = value
            except (TypeError, ValueError):
                merged[key] = default

        for key in ("tick_volume", "notification_volume", "ambient_volume"):
            raw = loaded.get(key)
            if isinstance(raw, float) and 0.0 <= raw <= 1.0:
                merged[key] = int(round(raw * 100))

        for key in ("tick_volume", "notification_volume", "ambient_volume"):
            merged[key] = max(0, min(100, merged[key]))
        return merged

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key):
        return self.config.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save()
