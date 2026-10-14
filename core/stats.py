import json
from pathlib import Path

from services.resource_manager import get_stats_path


class StatsManager:
    """
    Contadores de sesión (completados, incompletos, serie, tiempo enfocado).

    Los totales (completados, incompletos y segundos enfocados) se persisten en
    ``stats.json``. La ``serie`` es efímera: depende del ciclo en curso y no se
    guarda.
    """

    def __init__(self):
        self.completed = 0
        self.incomplete = 0
        self.chain = 0
        self.focus_seconds = 0
        self._stats_path = get_stats_path()
        self.load()

    # ------------------------------------------------------------ persistencia
    def load(self):
        path = Path(self._stats_path)
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        def as_int(key):
            try:
                return max(0, int(round(float(data.get(key, 0)))))
            except (TypeError, ValueError):
                return 0

        self.completed = as_int("completed")
        self.incomplete = as_int("incomplete")
        self.focus_seconds = as_int("focus_seconds")

    def save(self):
        path = Path(self._stats_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "completed": self.completed,
            "incomplete": self.incomplete,
            "focus_seconds": self.focus_seconds,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"No se pudieron guardar las estadísticas: {e}")

    # ------------------------------------------------------------------ estado
    def add_focus_seconds(self, seconds):
        self.focus_seconds += max(0, int(seconds))

    def complete_work(self):
        self.completed += 1
        self.chain += 1
        self.save()

    def mark_incomplete(self):
        self.incomplete += 1
        self.chain = 0
        self.save()

    def reset_chain(self):
        self.chain = 0

    def text(self, target):
        h = self.focus_seconds // 3600
        m = (self.focus_seconds % 3600) // 60
        focused = f"{h}h {m:02d}m" if h else f"{m}m"
        return (
            f"✓ Completados: {self.completed}   ·   ✗ Incompletos: {self.incomplete}\n"
            f"Serie: {self.chain}/{target}   ·   Enfocado: {focused}"
        )
