from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QSpinBox, QCheckBox,
    QSlider, QPushButton, QComboBox,
)

from ui.ambient_dialog import AmbientDialog


class ConfigDialog(QDialog):
    """Diálogo de ajustes del temporizador."""

    def __init__(self, parent, config, audio, library):
        super().__init__(parent)
        self.config = config
        self.audio = audio
        self.library = library
        self.setWindowTitle("Ajustes")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        def spin(key, max_val=120):
            s = QSpinBox()
            s.setRange(1, max_val)
            s.setValue(config.get(key))
            return s

        self.spin_work = spin("work_duration")
        self.spin_work.setSuffix(" min")
        self.spin_short = spin("short_break_duration")
        self.spin_short.setSuffix(" min")
        self.spin_long = spin("long_break_duration")
        self.spin_long.setSuffix(" min")
        self.spin_consecutive = spin("consecutive_sessions", 10)

        layout.addRow("Trabajo:", self.spin_work)
        layout.addRow("Descanso corto:", self.spin_short)
        layout.addRow("Descanso largo:", self.spin_long)
        layout.addRow("Sesiones consecutivas:", self.spin_consecutive)

        self.slider_notif = QSlider(Qt.Orientation.Horizontal)
        self.slider_notif.setRange(0, 100)
        self.slider_notif.setValue(config.get("notification_volume"))
        layout.addRow("Volumen notificación:", self.slider_notif)

        self.chk_top = QCheckBox("Siempre encima de otras ventanas")
        self.chk_top.setChecked(config.get("always_on_top"))
        layout.addRow(self.chk_top)

        self.chk_light = QCheckBox("Tema claro")
        self.chk_light.setChecked(config.get("theme") == "light")
        layout.addRow(self.chk_light)

        self.chk_progressive = QCheckBox("Progreso progresivo (si no, regresivo)")
        self.chk_progressive.setChecked(config.get("progress_mode") == "progressive")
        layout.addRow(self.chk_progressive)

        self.chk_breaks = QCheckBox("Tictac también durante descansos")
        self.chk_breaks.setChecked(config.get("tick_during_breaks"))
        layout.addRow(self.chk_breaks)

        self.chk_active_breaks = QCheckBox("Sugerencias durante los descansos")
        self.chk_active_breaks.setChecked(config.get("active_breaks_enabled"))
        layout.addRow(self.chk_active_breaks)

        self.chk_ambient = QCheckBox("Sonido ambiental de fondo")
        self.chk_ambient.setChecked(config.get("ambient_enabled"))
        layout.addRow(self.chk_ambient)

        self.combo_ambient = QComboBox()
        layout.addRow("Sonido ambiental:", self.combo_ambient)

        self.slider_ambient = QSlider(Qt.Orientation.Horizontal)
        self.slider_ambient.setRange(0, 100)
        self.slider_ambient.setValue(config.get("ambient_volume"))
        layout.addRow("Volumen ambiente:", self.slider_ambient)

        self.btn_manage_ambient = QPushButton("Gestionar sonidos ambientales…")
        self.btn_manage_ambient.clicked.connect(self._manage_ambient)
        layout.addRow(self.btn_manage_ambient)

        self._reload_ambient()

        buttons = QHBoxLayout()
        btn_ok = QPushButton("Guardar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancel)
        layout.addRow(buttons)

    def _reload_ambient(self):
        self.combo_ambient.clear()
        self.combo_ambient.addItem("(Ninguno)", "")
        for entry in self.library.entries():
            self.combo_ambient.addItem(entry["name"], entry["filename"])
        idx = self.combo_ambient.findData(self.config.get("ambient_track"))
        self.combo_ambient.setCurrentIndex(idx if idx >= 0 else 0)

    def _manage_ambient(self):
        dialog = AmbientDialog(self, self.library, self.audio)
        dialog.exec()
        current = self.combo_ambient.currentData()
        self._reload_ambient()
        idx = self.combo_ambient.findData(current)
        self.combo_ambient.setCurrentIndex(idx if idx >= 0 else 0)

    def accept(self):
        self.config.set("work_duration", self.spin_work.value())
        self.config.set("short_break_duration", self.spin_short.value())
        self.config.set("long_break_duration", self.spin_long.value())
        self.config.set("consecutive_sessions", self.spin_consecutive.value())
        self.config.set("notification_volume", self.slider_notif.value())
        self.config.set("always_on_top", self.chk_top.isChecked())
        self.config.set("theme", "light" if self.chk_light.isChecked() else "dark")
        self.config.set("tick_during_breaks", self.chk_breaks.isChecked())
        self.config.set("active_breaks_enabled", self.chk_active_breaks.isChecked())
        self.config.set("progress_mode",
                        "progressive" if self.chk_progressive.isChecked() else "regressive")
        self.config.set("ambient_enabled", self.chk_ambient.isChecked())
        self.config.set("ambient_volume", self.slider_ambient.value())
        self.config.set("ambient_track", self.combo_ambient.currentData() or "")
        self.audio.set_notification_volume(self.slider_notif.value())
        super().accept()
