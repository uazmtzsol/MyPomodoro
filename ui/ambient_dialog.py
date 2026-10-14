from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, QFileDialog,
)

from services.ambient_library import format_size

_AUDIO_FILTER = "Audio (*.wav *.ogg *.mp3 *.flac)"


class AmbientDialog(QDialog):
    """Subir, quitar, renombrar y probar los sonidos ambientales del usuario."""

    def __init__(self, parent, library, audio):
        super().__init__(parent)
        self.library = library
        self.audio = audio
        self.setWindowTitle("Sonidos ambientales")
        self.setModal(True)
        self.setMinimumSize(440, 340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        info = QLabel("Sube tus audios (.wav, .ogg, .mp3, .flac) y ponles un nombre.\n"
                      "Para ocupar menos espacio usa ogg/mp3: un wav pesa ~10× más "
                      "que el mismo audio comprimido.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list = QListWidget()
        layout.addWidget(self.list, stretch=1)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("Subir…")
        self.btn_rename = QPushButton("Renombrar")
        self.btn_remove = QPushButton("Quitar")
        self.btn_preview = QPushButton("▶ Probar")
        actions.addWidget(self.btn_add)
        actions.addWidget(self.btn_rename)
        actions.addWidget(self.btn_remove)
        actions.addWidget(self.btn_preview)
        actions.addStretch()
        layout.addLayout(actions)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_close = QPushButton("Cerrar")
        bottom.addWidget(self.btn_close)
        layout.addLayout(bottom)

        self.btn_add.clicked.connect(self._add)
        self.btn_rename.clicked.connect(self._rename)
        self.btn_remove.clicked.connect(self._remove)
        self.btn_preview.clicked.connect(self._preview)
        self.btn_close.clicked.connect(self.accept)
        self.list.currentItemChanged.connect(self._on_selection_changed)

        self._reload()

    # ------------------------------------------------------------------ helpers
    def _reload(self):
        self.list.clear()
        for entry in self.library.entries():
            size = format_size(entry["size"])
            if entry["builtin"]:
                label = f"🔒 {entry['name']}  ·  {size}"
                tip = f"{entry['filename']} · {size}\nIncluido con la app (no se puede gestionar)"
            else:
                label = f"{entry['name']}  ·  {size}"
                tip = f"{entry['filename']} · {size}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry["filename"])
            item.setToolTip(tip)
            self.list.addItem(item)
        self._update_buttons()
        self._update_preview_button()

    def _selected(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self, *_):
        if self.audio is not None and self.audio.is_previewing():
            self.audio.stop_preview()
        self._update_buttons()
        self._update_preview_button()

    def _update_buttons(self):
        filename = self._selected()
        has_selection = filename is not None
        builtin = bool(filename) and self.library.is_builtin(filename)
        self.btn_preview.setEnabled(has_selection and self.audio is not None)
        self.btn_rename.setEnabled(has_selection and not builtin)
        self.btn_remove.setEnabled(has_selection and not builtin)
        self.btn_rename.setToolTip(
            "Los sonidos incluidos no se pueden renombrar" if builtin else ""
        )
        self.btn_remove.setToolTip(
            "Los sonidos incluidos no se pueden quitar" if builtin else ""
        )

    def _update_preview_button(self):
        playing = self.audio is not None and self.audio.is_previewing()
        self.btn_preview.setText("⏹ Detener" if playing else "▶ Probar")

    # ------------------------------------------------------------------ acciones
    def _add(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Elegir audio ambiental", "", _AUDIO_FILTER
        )
        if not path:
            return
        default = Path(path).stem
        name, ok = QInputDialog.getText(
            self, "Nombre del sonido", "Nombre a mostrar:", text=default
        )
        if not ok:
            return
        try:
            self.library.add(path, name)
        except Exception as e:
            QMessageBox.warning(self, "No se pudo añadir", str(e))
            return
        self._reload()

    def _rename(self):
        filename = self._selected()
        if not filename:
            return
        current = self.library.display_name(filename)
        name, ok = QInputDialog.getText(
            self, "Renombrar sonido", "Nuevo nombre:", text=current
        )
        if not ok:
            return
        self.library.rename(filename, name)
        self._reload()

    def _remove(self):
        filename = self._selected()
        if not filename:
            return
        name = self.library.display_name(filename)
        reply = QMessageBox.question(
            self, "Quitar sonido", f"¿Quitar «{name}» de la biblioteca?"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.library.remove(filename)
        self._reload()

    def _preview(self):
        filename = self._selected()
        if not filename or self.audio is None:
            return
        self.audio.toggle_preview(self.library.path(filename))
        self._update_preview_button()

    def _stop_preview(self):
        if self.audio is not None:
            self.audio.stop_preview(resume_ambient=True)

    def accept(self):
        self._stop_preview()
        super().accept()

    def reject(self):
        self._stop_preview()
        super().reject()

    def closeEvent(self, event):
        self._stop_preview()
        super().closeEvent(event)
