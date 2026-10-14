from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox,
)


class TasksDialog(QDialog):
    """Crear, editar y elegir la tarea activa del usuario."""

    changed = pyqtSignal()

    def __init__(self, parent, tasks):
        super().__init__(parent)
        self.tasks = tasks
        self.setWindowTitle("Tareas")
        self.setModal(True)
        self.setMinimumSize(440, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        info = QLabel("Define tareas y su estimación en pomodoros. La tarea activa "
                      "suma avance al completar cada sesión de trabajo.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _: self._edit())
        layout.addWidget(self.list, stretch=1)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("Añadir")
        self.btn_edit = QPushButton("Editar")
        self.btn_done = QPushButton("Marcar hecha")
        self.btn_remove = QPushButton("Eliminar")
        actions.addWidget(self.btn_add)
        actions.addWidget(self.btn_edit)
        actions.addWidget(self.btn_done)
        actions.addWidget(self.btn_remove)
        actions.addStretch()
        layout.addLayout(actions)

        active_row = QHBoxLayout()
        self.btn_active = QPushButton("Usar como activa")
        self.lbl_active = QLabel("")
        self.lbl_active.setStyleSheet("font-size: 11px; color: #9999a8;")
        active_row.addWidget(self.btn_active)
        active_row.addWidget(self.lbl_active)
        active_row.addStretch()
        layout.addLayout(active_row)

        self.btn_clear = QPushButton("Limpiar completadas")

        bottom = QHBoxLayout()
        bottom.addWidget(self.btn_clear)
        bottom.addStretch()
        self.btn_close = QPushButton("Cerrar")
        bottom.addWidget(self.btn_close)
        layout.addLayout(bottom)

        self.btn_add.clicked.connect(self._add)
        self.btn_edit.clicked.connect(self._edit)
        self.btn_done.clicked.connect(self._mark_done)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_active.clicked.connect(self._set_active)
        self.btn_clear.clicked.connect(self._clear_done)
        self.btn_close.clicked.connect(self.accept)

        self.list.currentItemChanged.connect(self._update_buttons)
        self._reload()

    # ------------------------------------------------------------------ helpers
    def _reload(self):
        self.list.clear()
        for task in self.tasks.list_pending():
            marker = "★ " if task["id"] == self.tasks.active_id else ""
            item = QListWidgetItem(
                f"{marker}{task['title']}  ({task['completed']}/{task['estimated']})"
            )
            item.setData(Qt.ItemDataRole.UserRole, task["id"])
            self.list.addItem(item)

        done_count = len(self.tasks.list_done())
        self.btn_clear.setEnabled(done_count > 0)
        self.btn_clear.setText(f"Limpiar completadas ({done_count})")

        active = self.tasks.get_active()
        self.lbl_active.setText(
            f"Activa: {self.tasks.progress_text(active)}" if active
            else "Sin tarea activa"
        )
        self._update_buttons()

    def _selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_buttons(self):
        has = self._selected_id() is not None
        for btn in (self.btn_edit, self.btn_done, self.btn_remove, self.btn_active):
            btn.setEnabled(has)

    def _notify(self):
        self.changed.emit()
        self._reload()

    # ------------------------------------------------------------------ acciones
    def _add(self):
        title, ok = QInputDialog.getText(self, "Nueva tarea", "Título:")
        if not ok or not title.strip():
            return
        estimated, ok = QInputDialog.getInt(
            self, "Nueva tarea", "Pomodoros estimados:", 1, 1, 99
        )
        if not ok:
            return
        task = self.tasks.add(title, estimated)
        if not self.tasks.get_active():
            self.tasks.select_active(task["id"])
        self._notify()

    def _edit(self):
        task_id = self._selected_id()
        task = self.tasks.get(task_id) if task_id else None
        if not task:
            return
        title, ok = QInputDialog.getText(
            self, "Editar tarea", "Título:", text=task["title"]
        )
        if not ok:
            return
        estimated, ok = QInputDialog.getInt(
            self, "Editar tarea", "Pomodoros estimados:",
            task["estimated"], 1, 99,
        )
        if not ok:
            return
        self.tasks.update(task_id, title=title, estimated=estimated)
        self._notify()

    def _mark_done(self):
        task_id = self._selected_id()
        if task_id:
            self.tasks.set_done(task_id, True)
            self._notify()

    def _remove(self):
        task_id = self._selected_id()
        task = self.tasks.get(task_id) if task_id else None
        if not task:
            return
        reply = QMessageBox.question(
            self, "Eliminar tarea", f"¿Eliminar «{task['title']}»?"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.tasks.remove(task_id)
        self._notify()

    def _set_active(self):
        task_id = self._selected_id()
        if task_id:
            self.tasks.select_active(task_id)
            self._notify()

    def _clear_done(self):
        for task in self.tasks.list_done():
            self.tasks.remove(task["id"])
        self._notify()
