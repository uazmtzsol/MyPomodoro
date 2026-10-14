from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, QFileDialog,
)

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

        info = QLabel("Sube tus audios (.wav, .ogg, .mp3, .flac) y ponles un nombre.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list = QListWidget()
        layout.addWidget(self.list, stretch=1)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("Subir…")
        self.btn_rename = QPushButton("Renombrar")
        self.btn_remove = QPushButton("Quitar")
        self.btn_preview = QPushButton("Probar")
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

        self._reload()

    # ------------------------------------------------------------------ helpers
    def _reload(self):
        self.list.clear()
        for entry in self.library.entries():
            item = QListWidgetItem(entry["name"])
            item.setData(Qt.ItemDataRole.UserRole, entry["filename"])
            item.setToolTip(entry["filename"])
            self.list.addItem(item)
        has_items = self.list.count() > 0
        for btn in (self.btn_rename, self.btn_remove, self.btn_preview):
            btn.setEnabled(has_items)

    def _selected(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

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
        if filename:
            self.audio.preview_ambient(self.library.path(filename))

    def _stop_preview(self):
        self.audio.stop_preview()

    def accept(self):
        self._stop_preview()
        super().accept()

    def reject(self):
        self._stop_preview()
        super().reject()

    def closeEvent(self, event):
        self._stop_preview()
        super().closeEvent(event)
