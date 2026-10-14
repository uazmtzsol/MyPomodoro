from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QComboBox, QCheckBox, QMenu,
)

from core.stats import StatsManager
from core.tasks import TaskManager
from core.break_tips import BreakTips
from core.timer import (
    PomodoroTimer, SessionType, TimerState, SESSION_NAMES,
)
from services.ambient_library import AmbientLibrary
from services.audio_manager import AudioManager
from services.config_manager import ConfigManager
from services.resource_manager import get_resources_dir
from ui.config_dialog import ConfigDialog
from ui.progress_circle import ProgressCircle
from ui.styles import get_stylesheet
from ui.system_tray import SystemTray
from ui.tasks_dialog import TasksDialog
from ui.widgets import TimeButton


class MainWindow(QMainWindow):
    COMPACT_SIZE = QSize(240, 56)
    EXPANDED_SIZE = QSize(300, 430)

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.stats = StatsManager()
        self.tasks = TaskManager()
        self.ambient_library = AmbientLibrary(
            self.config.ambient_dir, get_resources_dir()
        )
        self.audio = AudioManager(self.config, self.ambient_library)
        self.break_tips = BreakTips()
        self.timer = PomodoroTimer(
            self.stats, self._durations(), self.config.get("consecutive_sessions")
        )
        self._bind_timer_callbacks()

        self._drag_pos = None
        self._last_shown = None
        self._loading_ambient = False
        self._active_tip = None

        self._setup_window()
        self._setup_ui()
        self._setup_tray()

        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(self._on_tick)

        self._apply_window_flags()
        self._apply_mode()

        pos = self.config.get("window_position")
        if pos:
            self.move(pos.get("x", 100), pos.get("y", 100))

        self._update_display()

    # ------------------------------------------------------------------- setup
    def _durations(self):
        return {
            SessionType.WORK.value: self.config.get("work_duration"),
            SessionType.SHORT_BREAK.value: self.config.get("short_break_duration"),
            SessionType.LONG_BREAK.value: self.config.get("long_break_duration"),
        }

    def _bind_timer_callbacks(self):
        self.timer.on_update = self._update_display
        self.timer.on_counting_started = self._on_counting_started
        self.timer.on_paused = self._on_paused
        self.timer.on_resumed = self._on_resumed
        self.timer.on_stopped = self._on_stopped
        self.timer.on_session_complete = self._on_session_complete

    def _setup_window(self):
        self.setWindowTitle("Pomodoro Timer")
        self._apply_theme()

    def _apply_theme(self):
        theme = self.config.get("theme")
        self.setStyleSheet(get_stylesheet(theme))
        if hasattr(self, "circle"):
            self.circle.set_theme(theme)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        self.root_layout = QVBoxLayout(central)
        self.root_layout.setContentsMargins(8, 8, 8, 8)
        self.root_layout.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(4)

        self.btn_time = TimeButton("25:00")
        self.btn_time.setObjectName("btn_time")
        self.btn_time.setToolTip("Clic: iniciar / pausar / reanudar\nArrastra para mover la ventana")
        self.btn_time.clicked.connect(self._on_play_pause)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(40)
        self.btn_play.setToolTip("Iniciar / Pausar")
        self.btn_play.clicked.connect(self._on_play_pause)

        self.btn_gear = QPushButton("⚙")
        self.btn_gear.setFixedWidth(34)
        self.btn_gear.setToolTip("Mostrar / ocultar opciones")
        self.btn_gear.clicked.connect(self._toggle_mode)

        self.btn_min = QPushButton("➖")
        self.btn_min.setObjectName("btn_min")
        self.btn_min.setFixedWidth(34)
        self.btn_min.setToolTip("Minimizar a la bandeja")
        self.btn_min.clicked.connect(self._minimize_to_tray)

        for w in (self.btn_time, self.btn_play, self.btn_gear, self.btn_min):
            row.addWidget(w)
        self.root_layout.addLayout(row)

        self.expanded_widgets = []

        self.circle = ProgressCircle()
        self.circle.set_theme(self.config.get("theme"))
        self.root_layout.addWidget(self.circle, stretch=1)
        self.expanded_widgets.append(self.circle)

        self.lbl_status = QLabel("Listo para comenzar")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setObjectName("status_caption")
        self.root_layout.addWidget(self.lbl_status)
        self.expanded_widgets.append(self.lbl_status)

        self.lbl_task = QLabel("")
        self.lbl_task.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_task.setWordWrap(True)
        self.lbl_task.setObjectName("task_caption")
        self.root_layout.addWidget(self.lbl_task)
        self.expanded_widgets.append(self.lbl_task)

        self.lbl_tip = QLabel("")
        self.lbl_tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_tip.setWordWrap(True)
        self.lbl_tip.setObjectName("tip_caption")
        self.root_layout.addWidget(self.lbl_tip)
        self.expanded_widgets.append(self.lbl_tip)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(6)
        lbl_vol = QLabel("🔊 Tic-tac")
        lbl_vol.setStyleSheet("font-size: 11px;")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(self.config.get("tick_volume"))
        self.lbl_volume = QLabel(f"{self.config.get('tick_volume')}%")
        self.lbl_volume.setFixedWidth(34)
        self.lbl_volume.setObjectName("value_caption")
        vol_row.addWidget(lbl_vol)
        vol_row.addWidget(self.slider_volume)
        vol_row.addWidget(self.lbl_volume)
        self.root_layout.addLayout(vol_row)
        self.expanded_widgets.extend([lbl_vol, self.slider_volume, self.lbl_volume])

        self.slider_volume.valueChanged.connect(self._on_volume_changed)

        opts_row = QHBoxLayout()
        self.chk_tick = QCheckBox("Tictac")
        self.chk_tick.setChecked(self.config.get("tick_enabled"))
        self.combo_sound = QComboBox()
        self.combo_sound.addItem("Normal", "normal")
        self.combo_sound.addItem("Lento", "slow")
        idx = self.combo_sound.findData(self.config.get("tick_sound"))
        if idx >= 0:
            self.combo_sound.setCurrentIndex(idx)
        opts_row.addWidget(self.chk_tick)
        opts_row.addStretch()
        opts_row.addWidget(self.combo_sound)
        self.root_layout.addLayout(opts_row)
        self.expanded_widgets.extend([self.chk_tick, self.combo_sound])

        self.chk_tick.toggled.connect(self._on_tick_toggled)
        self.combo_sound.currentIndexChanged.connect(self._on_sound_changed)

        amb_row = QHBoxLayout()
        self.chk_ambient = QCheckBox("Ambiente")
        self.chk_ambient.setChecked(self.config.get("ambient_enabled"))
        self.combo_ambient = QComboBox()
        self.btn_preview = QPushButton("▶")
        self.btn_preview.setFixedWidth(30)
        self.btn_preview.setToolTip("Probar el sonido ambiental seleccionado")
        self.btn_preview.clicked.connect(self._on_preview_ambient)
        amb_row.addWidget(self.chk_ambient)
        amb_row.addStretch()
        amb_row.addWidget(self.btn_preview)
        amb_row.addWidget(self.combo_ambient)
        self.root_layout.addLayout(amb_row)
        self.expanded_widgets.extend([self.chk_ambient, self.btn_preview, self.combo_ambient])

        amb_vol_row = QHBoxLayout()
        amb_vol_row.setSpacing(6)
        lbl_amb = QLabel("🌧 Ambiente")
        lbl_amb.setStyleSheet("font-size: 11px;")
        self.slider_ambient = QSlider(Qt.Orientation.Horizontal)
        self.slider_ambient.setRange(0, 100)
        self.slider_ambient.setValue(self.config.get("ambient_volume"))
        self.lbl_ambient = QLabel(f"{self.config.get('ambient_volume')}%")
        self.lbl_ambient.setFixedWidth(34)
        self.lbl_ambient.setObjectName("value_caption")
        amb_vol_row.addWidget(lbl_amb)
        amb_vol_row.addWidget(self.slider_ambient)
        amb_vol_row.addWidget(self.lbl_ambient)
        self.root_layout.addLayout(amb_vol_row)
        self.expanded_widgets.extend([lbl_amb, self.slider_ambient, self.lbl_ambient])

        self._reload_ambient_controls()
        self.chk_ambient.toggled.connect(self._on_ambient_toggled)
        self.combo_ambient.currentIndexChanged.connect(self._on_ambient_track_changed)
        self.slider_ambient.valueChanged.connect(self._on_ambient_volume_changed)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setObjectName("stats_caption")
        self.root_layout.addWidget(self.lbl_stats)
        self.expanded_widgets.append(self.lbl_stats)

        action_row = QHBoxLayout()
        self.btn_tasks = QPushButton("📋 Tareas")
        self.btn_tasks.clicked.connect(self._on_tasks)
        self.btn_settings = QPushButton("⚙ Ajustes")
        self.btn_settings.clicked.connect(self._on_config)
        self.btn_collapse = QPushButton("⤡ Compactar")
        self.btn_collapse.clicked.connect(self._toggle_mode)
        action_row.addWidget(self.btn_tasks)
        action_row.addWidget(self.btn_settings)
        action_row.addWidget(self.btn_collapse)
        self.root_layout.addLayout(action_row)
        self.expanded_widgets.extend([self.btn_tasks, self.btn_settings, self.btn_collapse])

    def _setup_tray(self):
        self.tray = SystemTray(
            self,
            on_play_pause=self._on_play_pause,
            on_stop=self._on_stop,
            on_restart=self._on_restart,
            on_show=self._show_window,
            on_config=self._on_config,
            on_quit=self._quit_app,
            on_toggle=self._toggle_window_visibility,
        )

    # -------------------------------------------------------------------- modo
    def _apply_mode(self):
        expanded = self.config.get("expanded_mode")
        for w in self.expanded_widgets:
            w.setVisible(expanded)
        self.btn_gear.setToolTip("Compactar" if expanded else "Mostrar opciones")

        layout = self.centralWidget().layout()
        if layout:
            layout.invalidate()
            layout.activate()

        if expanded:
            self.setFixedSize(0, 0)
            self.resize(self.EXPANDED_SIZE)
        else:
            self.setFixedSize(self.COMPACT_SIZE)

    def _toggle_mode(self):
        self.config.set("expanded_mode", not self.config.get("expanded_mode"))
        self._apply_mode()
        self._update_display()

    # --------------------------------------------------------- bandeja/ventana
    def _toggle_window_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self._show_window()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _minimize_to_tray(self):
        self.hide()
        if self.tray.available:
            self.tray.show_message(
                "Pomodoro Timer", "Sigo ejecutándome en la bandeja.", 2000
            )

    def _quit_app(self):
        self.save_position()
        self.stats.save()
        self.tasks.save()
        if self.tray.available:
            self.tray.hide()
        self.audio.cleanup()
        QApplication.quit()

    def save_position(self):
        pos = self.pos()
        self.config.set("window_position", {"x": pos.x(), "y": pos.y()})

    def _apply_window_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if self.config.get("always_on_top"):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    # --------------------------------------------------------------- temporizador
    def _is_break(self):
        return self.timer.session_type in (
            SessionType.SHORT_BREAK, SessionType.LONG_BREAK
        )

    def _on_play_pause(self):
        self.timer.toggle()

    def _on_stop(self):
        self.timer.stop()

    def _on_restart(self):
        self.timer.restart()

    def _on_tick(self):
        self.timer.update()

    def _on_counting_started(self):
        self.ui_timer.start(200)
        self.audio.stop_preview()
        if (self.timer.session_type is SessionType.WORK
                or self.config.get("tick_during_breaks")):
            self.audio.start_tick()
        self.audio.start_ambient()
        if self._is_break():
            self._active_tip = self.break_tips.next()
        self._sync_preview_button()

    def _on_paused(self):
        self.ui_timer.stop()
        self.audio.pause_tick()
        self.audio.pause_ambient()
        self.audio.stop_preview()
        self._sync_preview_button()

    def _on_resumed(self):
        self.audio.resume_tick()
        self.audio.resume_ambient()

    def _on_stopped(self):
        self.ui_timer.stop()
        self.audio.stop_tick()
        self.audio.stop_ambient()
        self.audio.stop_preview()
        self._sync_preview_button()

    def _on_session_complete(self, finished):
        self.ui_timer.stop()
        self.audio.stop_tick()
        self.audio.stop_ambient()
        self.audio.stop_preview()
        self._sync_preview_button()
        self.audio.play_notification()

        task = None
        auto_done = False
        if finished is SessionType.WORK:
            task, auto_done = self.tasks.record_pomodoro()
            self._update_display()

        name = SESSION_NAMES.get(finished, "Sesión")
        if self.tray.available:
            if auto_done and task:
                message = f"¡Tarea completada! {task['title']}"
            else:
                message = f"¡{name} completado!"
            self.tray.show_message("Pomodoro Timer", message, 3000)

    # --------------------------------------------------------------- opciones UI
    def _on_volume_changed(self, value):
        self.audio.set_tick_volume(value)
        self.lbl_volume.setText(f"{value}%")

    def _on_tick_toggled(self, checked):
        self.audio.set_tick_enabled(checked)
        if checked and self.timer.state is TimerState.RUNNING:
            if (self.timer.session_type is SessionType.WORK
                    or self.config.get("tick_during_breaks")):
                self.audio.start_tick()

    def _on_sound_changed(self, index):
        name = self.combo_sound.currentData()
        if name:
            self.audio.set_tick_sound(name)

    def _reload_ambient_controls(self):
        self._loading_ambient = True
        try:
            self.combo_ambient.clear()
            self.combo_ambient.addItem("(Ninguno)", "")
            for entry in self.ambient_library.entries():
                label = f"🔒 {entry['name']}" if entry["builtin"] else entry["name"]
                self.combo_ambient.addItem(label, entry["filename"])
            current = self.config.get("ambient_track")
            idx = self.combo_ambient.findData(current)
            if idx < 0 and current:
                self.config.set("ambient_track", "")
                idx = 0
            self.combo_ambient.setCurrentIndex(idx if idx >= 0 else 0)
            self.chk_ambient.setChecked(bool(self.config.get("ambient_enabled")))
            volume = int(self.config.get("ambient_volume"))
            self.slider_ambient.setValue(volume)
            self.lbl_ambient.setText(f"{volume}%")
        finally:
            self._loading_ambient = False
        self._sync_preview_button()

    def _on_ambient_toggled(self, checked):
        if self._loading_ambient:
            return
        self.audio.set_ambient_enabled(checked)
        if checked and self.timer.is_running:
            self.audio.start_ambient()
        elif not checked:
            self.audio.stop_ambient()

    def _on_ambient_track_changed(self, index):
        if self._loading_ambient:
            return
        track = self.combo_ambient.currentData() or ""
        self.audio.set_ambient_track(track)
        if self.timer.is_running:
            self.audio.start_ambient()
        if self.audio.is_previewing() and track:
            self.audio.stop_preview()
            self.audio.preview_ambient(self.ambient_library.path(track))
        self._sync_preview_button()

    def _on_ambient_volume_changed(self, value):
        if self._loading_ambient:
            return
        self.audio.set_ambient_volume(value)
        self.lbl_ambient.setText(f"{value}%")

    def _on_preview_ambient(self):
        track = self.combo_ambient.currentData()
        if not track:
            return
        self.audio.toggle_preview(self.ambient_library.path(track))
        self._sync_preview_button()

    def _sync_preview_button(self):
        self.btn_preview.setText("⏹" if self.audio.is_previewing() else "▶")

    def _apply_ambient(self):
        self.audio.set_ambient_enabled(self.config.get("ambient_enabled"))
        self.audio.set_ambient_volume(self.config.get("ambient_volume"))
        self.audio.set_ambient_track(self.config.get("ambient_track"))
        if self.timer.is_running and self.config.get("ambient_enabled"):
            self.audio.start_ambient()
        else:
            self.audio.stop_ambient()

    def _update_display(self):
        state = self.timer.state
        active = self.tasks.get_active()
        task_key = (
            (active["id"], active["title"], active["completed"],
             active["estimated"], active["done"])
            if active else None
        )
        if self._is_break() and self.config.get("active_breaks_enabled"):
            if self._active_tip is None:
                self._active_tip = self.break_tips.next()
            tip_text = self._active_tip
        else:
            self._active_tip = None
            tip_text = ""
        key = (state, self.timer.session_type, self.timer.remaining_seconds,
               task_key, tip_text)
        if key == self._last_shown:
            return
        self._last_shown = key

        minutes = self.timer.remaining_seconds // 60
        seconds = self.timer.remaining_seconds % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        elapsed = max(0.0, min(1.0, self.timer.elapsed_ratio))

        self.btn_time.setText(time_str)
        light = self.config.get("theme") == "light"
        color = QColor.fromHsv(int(120 * (1 - elapsed)),
                               220 if light else 230, 190 if light else 240)
        self.btn_time.setStyleSheet(
            f"color: rgb({color.red()},{color.green()},{color.blue()});"
            "background: transparent; border: none;"
            "font-size: 18px; font-weight: bold; min-width: 86px;"
        )

        self.circle.set_elapsed(elapsed)
        self.circle.set_ring(elapsed if self.config.get("progress_mode") == "progressive"
                             else 1 - elapsed)
        self.circle.set_time_text(time_str)
        self.circle.set_session_type(SESSION_NAMES.get(self.timer.session_type, "Trabajo"))
        self.circle.refresh()

        if state is TimerState.IDLE:
            self.btn_play.setText("▶")
            self.status = "Listo para comenzar"
        elif state is TimerState.RUNNING:
            self.btn_play.setText("⏸")
            self.status = "En curso…"
        else:
            self.btn_play.setText("▶")
            self.status = "En pausa"

        session_name = SESSION_NAMES.get(self.timer.session_type, "")
        self.lbl_status.setText(f"{self.status} · {session_name}")
        self.lbl_stats.setText(
            self.stats.text(int(self.config.get("consecutive_sessions")))
        )

        task_text = self.tasks.progress_text(active)
        self.lbl_task.setText(f"📋 {task_text}" if task_text else "Sin tarea activa")

        self.lbl_tip.setText(f"🧘 {tip_text}" if tip_text else "")
        self.lbl_tip.setVisible(bool(tip_text) and self.config.get("expanded_mode"))

        if self.tray.available:
            self.tray.update(
                self.timer.remaining_seconds, state.value, session_name, task_text
            )

    def _on_tasks(self):
        dialog = TasksDialog(self, self.tasks)
        dialog.changed.connect(self._update_display)
        dialog.exec()
        self._update_display()

    def _on_config(self):
        dialog = ConfigDialog(self, self.config, self.audio, self.ambient_library)
        if dialog.exec():
            self.timer.set_config(
                self._durations(), int(self.config.get("consecutive_sessions"))
            )
            if self.timer.state is TimerState.IDLE:
                self.timer.load_session(self.timer.session_type)
            self._apply_window_flags()
            self._reload_ambient_controls()
            self._apply_ambient()
            self._apply_theme()
            self._update_display()
            self.show()

    # ------------------------------------------------------------------- eventos
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._on_play_pause()
        elif event.key() == Qt.Key.Key_Escape:
            self._on_stop()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            menu = QMenu(self)
            a = QAction("🔄 Reiniciar", self)
            a.triggered.connect(self._on_restart)
            menu.addAction(a)
            a = QAction("⏹ Detener", self)
            a.triggered.connect(self._on_stop)
            menu.addAction(a)
            menu.addSeparator()
            a = QAction("✕ Salir", self)
            a.triggered.connect(self._quit_app)
            menu.addAction(a)
            menu.exec(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self.save_position()

    def closeEvent(self, event):
        self._quit_app()
        event.accept()
