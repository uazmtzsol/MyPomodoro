import json
import uuid
from datetime import datetime
from pathlib import Path

from services.resource_manager import get_tasks_path


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


class TaskManager:
    """
    Tareas del usuario con estimación y avance en pomodoros.

    Cada tarea es un dict:
        {
            "id": str,
            "title": str,
            "estimated": int,     # pomodoros estimados (>= 1)
            "completed": int,     # pomodoros completados (>= 0)
            "done": bool,
            "created": str,       # ISO
            "completed_at": str | None,
        }

    Solo una tarea puede estar activa a la vez (``active_id``). Al registrar un
    pomodoro se suma a la tarea activa y, si alcanza su estimación, se marca
    como completada automáticamente.
    """

    def __init__(self, path=None):
        self._path = Path(path) if path else get_tasks_path()
        self.tasks = []
        self.active_id = ""
        self.load()

    # ------------------------------------------------------------ persistencia
    def load(self):
        path = Path(self._path)
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        tasks = data.get("tasks", []) if isinstance(data, dict) else []
        self.tasks = [t for t in (self._normalize(t) for t in tasks) if t]
        active = data.get("active_id", "") if isinstance(data, dict) else ""
        self.active_id = active if self.get(active) else ""

    def save(self):
        path = Path(self._path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"active_id": self.active_id, "tasks": self.tasks}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"No se pudieron guardar las tareas: {e}")

    @staticmethod
    def _normalize(raw):
        if not isinstance(raw, dict):
            return None
        title = str(raw.get("title", "")).strip() or "Sin título"
        try:
            estimated = max(1, int(raw.get("estimated", 1)))
        except (TypeError, ValueError):
            estimated = 1
        try:
            completed = max(0, int(raw.get("completed", 0)))
        except (TypeError, ValueError):
            completed = 0
        return {
            "id": str(raw.get("id") or uuid.uuid4().hex),
            "title": title,
            "estimated": estimated,
            "completed": completed,
            "done": bool(raw.get("done", False)),
            "created": str(raw.get("created") or _now_iso()),
            "completed_at": raw.get("completed_at") or None,
        }

    # ---------------------------------------------------------------- consultas
    def get(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                return task
        return None

    def get_active(self):
        return self.get(self.active_id) if self.active_id else None

    def list_pending(self):
        return [t for t in self.tasks if not t["done"]]

    def list_done(self):
        return [t for t in self.tasks if t["done"]]

    def progress_text(self, task=None):
        task = task or self.get_active()
        if not task:
            return ""
        return f"{task['title']} ({task['completed']}/{task['estimated']})"

    # ---------------------------------------------------------------- mutaciones
    def add(self, title, estimated=1):
        title = str(title).strip() or "Sin título"
        try:
            estimated = max(1, int(estimated))
        except (TypeError, ValueError):
            estimated = 1
        task = {
            "id": uuid.uuid4().hex,
            "title": title,
            "estimated": estimated,
            "completed": 0,
            "done": False,
            "created": _now_iso(),
            "completed_at": None,
        }
        self.tasks.append(task)
        self.save()
        return task

    def update(self, task_id, title=None, estimated=None):
        task = self.get(task_id)
        if not task:
            return None
        if title is not None:
            task["title"] = str(title).strip() or task["title"]
        if estimated is not None:
            try:
                task["estimated"] = max(1, int(estimated))
            except (TypeError, ValueError):
                pass
        self.save()
        return task

    def remove(self, task_id):
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if self.active_id == task_id:
            self.active_id = ""
        if len(self.tasks) != before:
            self.save()
            return True
        return False

    def select_active(self, task_id):
        if task_id and not self.get(task_id):
            return False
        self.active_id = task_id or ""
        self.save()
        return True

    def set_done(self, task_id, done=True):
        task = self.get(task_id)
        if not task:
            return None
        task["done"] = bool(done)
        task["completed_at"] = _now_iso() if done else None
        if done and self.active_id == task_id:
            self.active_id = ""
        self.save()
        return task

    def record_pomodoro(self):
        """
        Suma un pomodoro a la tarea activa.

        Devuelve ``(task, auto_completed)``. ``auto_completed`` es True si la
        tarea alcanzó su estimación y se marcó como hecha automáticamente (la
        tarea deja de estar activa).
        """
        task = self.get_active()
        if not task:
            return None, False
        task["completed"] += 1
        auto_completed = False
        if not task["done"] and task["completed"] >= task["estimated"]:
            task["done"] = True
            task["completed_at"] = _now_iso()
            self.active_id = ""
            auto_completed = True
        self.save()
        return task, auto_completed
