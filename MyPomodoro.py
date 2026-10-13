"""
Pomodoro Timer v5
- Volumen de tictac independiente y en tiempo real
- Modo compacto horizontal / modo expandido
- Transición automática trabajo -> descanso
- Sesiones consecutivas configurables + descanso largo cada 4
- Estadísticas de completados / incompletos / tiempo enfocado
"""

import os
import sys
import json
import time
import wave
import shutil
import warnings
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="pkg_resources")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import numpy as np
import pygame

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QSize
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QAction, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QDialog, QFormLayout, QSpinBox, QCheckBox,
    QSizePolicy, QSlider, QComboBox, QMenu, QSystemTrayIcon,
)

# CORRECCIÓN: Nombres de archivo exactos según tu requerimiento
SOUND_FILES = ("tick_normal.wav", "tick_slow.wav", "notification.wav")

# ==============================================================================
# FUNCIÓN AUXILIAR ROBUSTA PARA RUTAS DE PYINSTALLER
# ==============================================================================
def get_resource_path(relative_path: str) -> Path:
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent.resolve()
    return base_path / relative_path

def bundled_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent

# ============================================================================
# CONFIGURACIÓN
# ============================================================================
class ConfigManager:
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
        "sounds_installed": False,
    }

    def __init__(self):
        if sys.platform == "win32":
            base = Path.home() / "AppData" / "Roaming" / "PomodoroTimer"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "PomodoroTimer"
        else:
            base = Path.home() / ".config" / "PomodoroTimer"

        base.mkdir(parents=True, exist_ok=True)
        self.config_path = base / "config.json"
        self.sounds_dir = base / "sounds"
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    merged = self.DEFAULT_CONFIG.copy()
                    merged.update(json.load(f))
                    return merged
            except Exception:
                pass
        return self.DEFAULT_CONFIG.copy()

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key):
        return self.config.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save()

# ============================================================================
# GENERACIÓN DE SONIDOS DE RESPALDO
# ============================================================================
class SoundGenerator:
    @staticmethod
    def _write_wav(filename, samples, sample_rate=44100):
        peak = np.max(np.abs(samples))
        if peak > 0:
            samples = samples / peak
        pcm = (samples * 32767).astype(np.int16)
        stereo = np.column_stack((pcm, pcm))
        with wave.open(str(filename), "w") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(stereo.tobytes())

    @classmethod
    def tick(cls, filename, frequency=800, duration=0.05, decay=0.02):
        sr = 44100
        t = np.linspace(0, duration, int(sr * duration), False)
        sound = np.sin(2 * np.pi * frequency * t) * np.exp(-t / decay)
        cls._write_wav(filename, sound, sr)

    @classmethod
    def notification(cls, filename):
        sr = 44100
        half = 0.15
        t1 = np.linspace(0, half, int(sr * half), False)
        b1 = np.sin(2 * np.pi * 1000 * t1) * np.exp(-t1 / 0.1)
        pause = np.zeros(int(sr * 0.1))
        t2 = np.linspace(0, half, int(sr * half), False)
        b2 = np.sin(2 * np.pi * 1200 * t2) * np.exp(-t2 / 0.1)
        cls._write_wav(filename, np.concatenate([b1, pause, b2]), sr)

def install_sounds(config: ConfigManager):
    sd = config.sounds_dir
    src = bundled_dir()
    
    for name in SOUND_FILES:
        origin = src / name
        dest = sd / name
        if origin.exists() and not dest.exists():
            try:
                shutil.copy2(origin, dest)
            except Exception as e:
                print(f"No se pudo copiar {name}: {e}")

    # Respaldo: generar archivos sintéticos si aún faltan (CORREGIDO a tick_slow.wav)
    if not (sd / "tick_normal.wav").exists():
        SoundGenerator.tick(sd / "tick_normal.wav")
    if not (sd / "tick_slow.wav").exists():
        SoundGenerator.tick(sd / "tick_slow.wav", 600, 0.08, 0.03)
    if not (sd / "notification.wav").exists():
        SoundGenerator.notification(sd / "notification.wav")

# ============================================================================
# AUDIO
# ============================================================================
class AudioManager:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.initialized = False
        self.tick_sound = None
        self.notification_sound = None
        self._channel = None
        self._mixer_paused = False
        self.error = None
        self._initialize()

    def _initialize(self):
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.initialized = True
        except Exception as e:
            self.error = str(e)
            return

        install_sounds(self.config)
        self._load_sounds()

    def _pause_mixer(self):
        if self.initialized and not self._mixer_paused:
            pygame.mixer.pause()
            self._mixer_paused = True

    def _unpause_mixer(self):
        if self.initialized and self._mixer_paused:
            pygame.mixer.unpause()
            self._mixer_paused = False

    def _load_sounds(self):
        if not self.initialized:
            return
        self.stop_tick()
        sd = self.config.sounds_dir

        name = self.config.get("tick_sound")
        path = sd / f"tick_{name}.wav"
        if not path.exists():
            path = sd / "tick_normal.wav"

        try:
            self.tick_sound = pygame.mixer.Sound(str(path))
        except Exception as e:
            self.tick_sound = None
            self.error = str(e)

        try:
            self.notification_sound = pygame.mixer.Sound(str(sd / "notification.wav"))
        except Exception as e:
            self.notification_sound = None

        self._apply_tick_volume()
        if self.notification_sound:
            self.notification_sound.set_volume(self.config.get("notification_volume") / 100.0)

    def _apply_tick_volume(self):
        volume = max(0.0, min(1.0, self.config.get("tick_volume") / 100.0))
        if self.tick_sound:
            self.tick_sound.set_volume(volume)
        if self._channel is not None:
            self._channel.set_volume(volume, volume)

    def start_tick(self):
        if not self.initialized or self.tick_sound is None or not self.config.get("tick_enabled"):
            return
        if self._channel is not None and self._channel.get_busy():
            return

        self._unpause_mixer()
        try:
            channel = pygame.mixer.Channel(0)
            volume = self.config.get("tick_volume") / 100.0
            channel.set_volume(volume, volume)
            channel.play(self.tick_sound, loops=-1)
            self._channel = channel
        except Exception as e:
            self.error = str(e)

    def stop_tick(self):
        self._unpause_mixer()
        if self._channel is not None:
            self._channel.stop()
            self._channel = None

    def pause_tick(self):
        if self._channel is not None and self._channel.get_busy():
            self._pause_mixer()

    def resume_tick(self):
        self._unpause_mixer()
        if self._channel is None or not self._channel.get_busy():
            self.start_tick()

    def play_notification(self):
        self._unpause_mixer()
        if self.initialized and self.notification_sound:
            self.notification_sound.play()

    def set_tick_volume(self, value):
        self.config.set("tick_volume", int(value))
        self._apply_tick_volume()

    def set_notification_volume(self, value):
        self.config.set("notification_volume", int(value))
        if self.notification_sound:
            self.notification_sound.set_volume(value / 100.0)

    def set_tick_sound(self, name):
        was_playing = self._channel is not None and self._channel.get_busy()
        was_paused = self._mixer_paused
        self.stop_tick()
        self.config.set("tick_sound", name)
        self._load_sounds()
        if was_playing:
            self.start_tick()
            if was_paused:
                self.pause_tick()

    def set_tick_enabled(self, enabled):
        self.config.set("tick_enabled", enabled)
        if not enabled:
            self.stop_tick()

    def cleanup(self):
        self.stop_tick()
        if self.initialized:
            pygame.mixer.quit()
            self.initialized = False

# ============================================================================
# ESTADÍSTICAS
# ============================================================================
class StatsManager:
    def __init__(self):
        self.completed = 0
        self.incomplete = 0
        self.chain = 0
        self.focus_seconds = 0

    def add_focus_seconds(self, seconds):
        self.focus_seconds += max(0, int(seconds))

    def complete_work(self):
        self.completed += 1
        self.chain += 1

    def mark_incomplete(self):
        self.incomplete += 1
        self.chain = 0

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

# ============================================================================
# CÍRCULO DE PROGRESO
# ============================================================================
class ProgressCircle(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ring = 1.0
        self.elapsed = 0.0
        self.time_text = "25:00"
        self.session_type = "Trabajo"
        self.setMinimumSize(110, 110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_ring(self, value):
        self.ring = max(0.0, min(1.0, value))

    def set_elapsed(self, value):
        self.elapsed = max(0.0, min(1.0, value))

    def set_time_text(self, text):
        self.time_text = text

    def set_session_type(self, text):
        self.session_type = text

    def color(self):
        return QColor.fromHsv(int(120 * (1 - self.elapsed)), 230, 240)

    def refresh(self):
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        size = min(rect.width(), rect.height())
        pen_w = max(6, size // 16)
        radius = size / 2 - 8 - pen_w / 2
        c = QPointF(rect.center())
        ring_rect = QRectF(c.x() - radius, c.y() - radius, radius * 2, radius * 2)

        bg = QPen(QColor(60, 60, 70))
        bg.setWidth(pen_w)
        bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(bg)
        p.drawArc(ring_rect, 0, 360 * 16)

        fg = QPen(self.color())
        fg.setWidth(pen_w)
        fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(fg)
        p.drawArc(ring_rect, 90 * 16, -int(360 * 16 * self.ring))

        p.setFont(QFont("Segoe UI", int(size / 6), QFont.Weight.Bold))
        p.setPen(self.color())
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.time_text)

        p.setFont(QFont("Segoe UI", max(8, int(size / 14))))
        p.setPen(QColor(180, 180, 195))
        label_rect = QRectF(rect)
        label_rect.setTop(c.y() + size / 8)
        p.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.session_type)
        p.end()

# ============================================================================
# BOTÓN DE TIEMPO
# ============================================================================
class TimeButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._press_pos = None
        self._window_origin = None
        self._moved = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._window_origin = self.window().frameGeometry().topLeft()
            self._moved = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self._press_pos
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                self._moved = True
                self.window().move(self._window_origin + delta)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        moved = self._moved
        self._press_pos = None
        self._moved = False
        if moved:
            self.window().save_position()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

# ============================================================================
# VENTANA PRINCIPAL
# ============================================================================
class MainWindow(QMainWindow):
    COMPACT_SIZE = QSize(240, 56)
    EXPANDED_SIZE = QSize(300, 430)

    SESSION_NAMES = {
        "work": "Trabajo",
        "short_break": "Descanso corto",
        "long_break": "Descanso largo",
    }
    DURATION_KEYS = {
        "work": "work_duration",
        "short_break": "short_break_duration",
        "long_break": "long_break_duration",
    }

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.audio = AudioManager(self.config)
        self.stats = StatsManager()

        self.timer_state = "idle"
        self.session_type = "work"
        self.total_seconds = 25 * 60
        self.remaining_seconds = self.total_seconds
        self.last_tick_time = None
        self._drag_pos = None
        self._last_shown = None

        self._load_session("work")
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

    def _setup_window(self):
        self.setWindowTitle("Pomodoro Timer")
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #1e1e24; color: #e6e6eb; }
            QPushButton {
                background-color: #2d2d38; border: 1px solid #3d3d4a;
                border-radius: 6px; padding: 4px 8px; color: #e6e6eb;
                font-size: 12px; min-height: 28px;
            }
            QPushButton:hover { background-color: #3d3d4a; border-color: #5a5a6e; }
            QPushButton:pressed { background-color: #1a1a22; }
            QPushButton#btn_time {
                background: transparent; border: none;
                font-size: 18px; font-weight: bold; min-width: 86px;
            }
            QPushButton#btn_time:hover { background-color: #2a2a33; border-radius: 6px; }
            QPushButton#btn_min { background-color: #2d382d; border-color: #3d4a3d; }
            QPushButton#btn_min:hover { background-color: #3d4a3d; }
            QSlider::groove:horizontal {
                height: 6px; background: #2d2d38;
                border: 1px solid #3d3d4a; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #5a5a6e; border: 1px solid #7a7a8e;
                width: 14px; margin: -5px 0; border-radius: 7px;
            }
            QComboBox {
                background-color: #2d2d38; border: 1px solid #3d3d4a;
                border-radius: 4px; padding: 3px 6px; color: #e6e6eb;
            }
            QCheckBox { color: #c8c8d2; }
        """)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Guardamos referencia al layout para poder manipularlo después
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
        self.root_layout.addWidget(self.circle, stretch=1)
        self.expanded_widgets.append(self.circle)

        self.lbl_status = QLabel("Listo para comenzar")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 10px; color: #9999a8;")
        self.root_layout.addWidget(self.lbl_status)
        self.expanded_widgets.append(self.lbl_status)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(6)
        lbl_vol = QLabel("🔊 Tic-tac")
        lbl_vol.setStyleSheet("font-size: 11px;")
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(self.config.get("tick_volume"))
        self.lbl_volume = QLabel(f"{self.config.get('tick_volume')}%")
        self.lbl_volume.setFixedWidth(34)
        self.lbl_volume.setStyleSheet("font-size: 10px; color: #9999a8;")
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
        # CORRECCIÓN: Cambiado de "lento" a "slow" para coincidir con el nombre del archivo
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

        self.lbl_stats = QLabel("")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setStyleSheet("font-size: 10px; color: #a8a8b8; padding: 4px;")
        self.root_layout.addWidget(self.lbl_stats)
        self.expanded_widgets.append(self.lbl_stats)

        action_row = QHBoxLayout()
        self.btn_settings = QPushButton("⚙ Ajustes")
        self.btn_settings.clicked.connect(self._on_config)
        self.btn_collapse = QPushButton("⤡ Compactar")
        self.btn_collapse.clicked.connect(self._toggle_mode)
        action_row.addWidget(self.btn_settings)
        action_row.addWidget(self.btn_collapse)
        self.root_layout.addLayout(action_row)
        self.expanded_widgets.extend([self.btn_settings, self.btn_collapse])

    def _apply_mode(self):
        expanded = self.config.get("expanded_mode")
        for w in self.expanded_widgets:
            w.setVisible(expanded)
        self.btn_gear.setToolTip("Compactar" if expanded else "Mostrar opciones")
        
        # SOLUCIÓN AL PROBLEMA DE REDIMENSIONAMIENTO:
        # 1. Forzamos al layout a recalcular su geometría con los widgets ahora visibles/ocultos
        layout = self.centralWidget().layout()
        if layout:
            layout.invalidate()
            layout.activate()
        
        # 2. Aplicamos la estrategia de tamaño
        if expanded:
            # Liberamos cualquier restricción de tamaño fijo previa
            self.setFixedSize(0, 0)
            self.resize(self.EXPANDED_SIZE)
        else:
            # Forzamos el tamaño compacto exacto para evitar espacio fantasma
            self.setFixedSize(self.COMPACT_SIZE)

    def _toggle_mode(self):
        self.config.set("expanded_mode", not self.config.get("expanded_mode"))
        self._apply_mode()
        self._update_display()

    def _setup_tray(self):
        self.tray_icon = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        menu = QMenu()

        self.action_play = QAction("▶ Iniciar", self)
        self.action_play.triggered.connect(self._on_play_pause)
        menu.addAction(self.action_play)

        a_stop = QAction("⏹ Detener", self)
        a_stop.triggered.connect(self._on_stop)
        menu.addAction(a_stop)

        a_restart = QAction("🔄 Reiniciar", self)
        a_restart.triggered.connect(self._on_restart)
        menu.addAction(a_restart)

        menu.addSeparator()

        a_show = QAction("Mostrar ventana", self)
        a_show.triggered.connect(self._show_window)
        menu.addAction(a_show)

        a_config = QAction("⚙ Ajustes", self)
        a_config.triggered.connect(self._on_config)
        menu.addAction(a_config)

        menu.addSeparator()

        a_quit = QAction("✕ Salir", self)
        a_quit.triggered.connect(self._quit_app)
        menu.addAction(a_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        self._update_tray_icon()

    def _update_tray_icon(self):
        if not self.tray_icon:
            return
        pm = QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(45, 45, 56))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 60, 60)
        p.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        p.setPen(QColor(230, 230, 235))
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
                   f"{self.remaining_seconds // 60:02d}:{self.remaining_seconds % 60:02d}")
        p.end()
        self.tray_icon.setIcon(QIcon(pm))
        state = {"idle": "Listo", "running": "En curso", "paused": "En pausa"}
        self.tray_icon.setToolTip(
            f"Pomodoro Timer — {state.get(self.timer_state, '')} — "
            f"{self.SESSION_NAMES.get(self.session_type, '')}"
        )

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
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
        if self.tray_icon:
            self.tray_icon.showMessage(
                "Pomodoro Timer", "Sigo ejecutándome en la bandeja.",
                QSystemTrayIcon.MessageIcon.Information, 2000
            )

    def _quit_app(self):
        self.save_position()
        if self.tray_icon:
            self.tray_icon.hide()
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

    def _load_session(self, kind):
        self.session_type = kind
        self.total_seconds = int(self.config.get(self.DURATION_KEYS[kind]) * 60)
        self.remaining_seconds = self.total_seconds

    def _begin_counting(self):
        self.timer_state = "running"
        self.last_tick_time = time.time()
        self.ui_timer.start(200)
        if self.session_type == "work" or self.config.get("tick_during_breaks"):
            self.audio.start_tick()

    def _on_play_pause(self):
        if self.timer_state == "idle":
            if self.session_type == "work":
                self.stats.reset_chain()
            self._begin_counting()
        elif self.timer_state == "running":
            self.timer_state = "paused"
            self.ui_timer.stop()
            self.audio.pause_tick()
        elif self.timer_state == "paused":
            self._begin_counting()
            self.audio.resume_tick()
        self._update_display()

    def _on_stop(self):
        if (self.session_type == "work" and self.timer_state != "idle"
                and self.remaining_seconds < self.total_seconds):
            self.stats.mark_incomplete()
        else:
            self.stats.reset_chain()

        self.ui_timer.stop()
        self.audio.stop_tick()
        self.timer_state = "idle"
        self._load_session("work")
        self._update_display()

    def _on_restart(self):
        if (self.session_type == "work" and self.timer_state != "idle"
                and self.remaining_seconds < self.total_seconds):
            self.stats.mark_incomplete()

        was_running = self.timer_state == "running"
        was_paused = self.timer_state == "paused"
        kind = self.session_type

        self.ui_timer.stop()
        self.audio.stop_tick()
        self._load_session(kind)

        if was_running:
            self._begin_counting()
        elif was_paused:
            self.timer_state = "paused"
        else:
            self.timer_state = "idle"
        self._update_display()

    def _on_tick(self):
        now = time.time()
        elapsed = now - self.last_tick_time
        if elapsed < 1.0:
            return

        step = int(elapsed)
        self.last_tick_time += step

        counted = min(step, self.remaining_seconds)
        if self.session_type == "work":
            self.stats.add_focus_seconds(counted)

        self.remaining_seconds -= step

        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self._on_session_complete()
            return

        self._update_display()
        self._update_tray_icon()

    def _on_session_complete(self):
        self.ui_timer.stop()
        self.audio.stop_tick()
        self.audio.play_notification()

        finished = self.SESSION_NAMES.get(self.session_type, "Sesión")

        if self.session_type == "work":
            self.stats.complete_work()

            if self.stats.completed % 4 == 0:
                self._load_session("long_break")
            else:
                self._load_session("short_break")

            self._begin_counting()
        else:
            target = int(self.config.get("consecutive_sessions"))
            is_long = self.session_type == "long_break"

            if is_long:
                self.stats.reset_chain()

            should_continue = (
                not is_long
                and self.stats.chain < target
                and self.stats.completed % 4 != 0
            )

            if should_continue:
                self._load_session("work")
                self._begin_counting()
            else:
                self.timer_state = "idle"
                self._load_session("work")

        if self.tray_icon and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(
                "Pomodoro Timer", f"¡{finished} completado!",
                QSystemTrayIcon.MessageIcon.Information, 3000
            )

        self._update_display()
        self._update_tray_icon()

    def _on_volume_changed(self, value):
        self.audio.set_tick_volume(value)
        self.lbl_volume.setText(f"{value}%")

    def _on_tick_toggled(self, checked):
        self.audio.set_tick_enabled(checked)
        if checked and self.timer_state == "running":
            if self.session_type == "work" or self.config.get("tick_during_breaks"):
                self.audio.start_tick()

    def _on_sound_changed(self, index):
        name = self.combo_sound.currentData()
        if name:
            self.audio.set_tick_sound(name)

    def _update_display(self):
        key = (self.timer_state, self.session_type, self.remaining_seconds)
        if key == self._last_shown:
            return
        self._last_shown = key

        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        elapsed = 1 - (self.remaining_seconds / self.total_seconds) if self.total_seconds else 0
        elapsed = max(0.0, min(1.0, elapsed))

        self.btn_time.setText(time_str)
        color = QColor.fromHsv(int(120 * (1 - elapsed)), 230, 240)
        self.btn_time.setStyleSheet(
            f"color: rgb({color.red()},{color.green()},{color.blue()});"
            "background: transparent; border: none;"
            "font-size: 18px; font-weight: bold; min-width: 86px;"
        )

        self.circle.set_elapsed(elapsed)
        self.circle.set_ring(elapsed if self.config.get("progress_mode") == "progressive"
                             else 1 - elapsed)
        self.circle.set_time_text(time_str)
        self.circle.set_session_type(self.SESSION_NAMES.get(self.session_type, "Trabajo"))
        self.circle.refresh()

        if self.timer_state == "idle":
            self.btn_play.setText("▶")
            self.status = "Listo para comenzar"
        elif self.timer_state == "running":
            self.btn_play.setText("⏸")
            self.status = "En curso…"
        else:
            self.btn_play.setText("▶")
            self.status = "En pausa"

        if self.tray_icon:
            self.action_play.setText(
                "⏸ Pausar" if self.timer_state == "running" else "▶ Iniciar"
            )

        self.lbl_status.setText(
            f"{self.status} · {self.SESSION_NAMES.get(self.session_type, '')}"
        )
        self.lbl_stats.setText(
            self.stats.text(int(self.config.get("consecutive_sessions")))
        )

    def _on_config(self):
        dialog = ConfigDialog(self, self.config, self.audio)
        if dialog.exec():
            if self.timer_state == "idle":
                self._load_session(self.session_type)
            self._apply_window_flags()
            self._update_display()
            self.show()

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

# ============================================================================
# DIÁLOGO DE AJUSTES
# ============================================================================
class ConfigDialog(QDialog):
    def __init__(self, parent, config, audio):
        super().__init__(parent)
        self.config = config
        self.audio = audio
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

        self.chk_progressive = QCheckBox("Progreso progresivo (si no, regresivo)")
        self.chk_progressive.setChecked(config.get("progress_mode") == "progressive")
        layout.addRow(self.chk_progressive)

        self.chk_breaks = QCheckBox("Tictac también durante descansos")
        self.chk_breaks.setChecked(config.get("tick_during_breaks"))
        layout.addRow(self.chk_breaks)

        buttons = QHBoxLayout()
        btn_test = QPushButton("Probar sonido")
        btn_test.clicked.connect(self._test)
        btn_ok = QPushButton("Guardar")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        buttons.addWidget(btn_test)
        buttons.addStretch()
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancel)
        layout.addRow(buttons)

    def _test(self):
        self.audio.set_notification_volume(self.slider_notif.value())
        self.audio.play_notification()

    def accept(self):
        self.config.set("work_duration", self.spin_work.value())
        self.config.set("short_break_duration", self.spin_short.value())
        self.config.set("long_break_duration", self.spin_long.value())
        self.config.set("consecutive_sessions", self.spin_consecutive.value())
        self.config.set("notification_volume", self.slider_notif.value())
        self.config.set("always_on_top", self.chk_top.isChecked())
        self.config.set("tick_during_breaks", self.chk_breaks.isChecked())
        self.config.set("progress_mode",
                        "progressive" if self.chk_progressive.isChecked() else "regressive")
        self.audio.set_notification_volume(self.slider_notif.value())
        super().accept()

# ============================================================================
# ENTRADA
# ============================================================================
def main():
    if sys.platform == "win32":
        import ctypes
        myappid = "com.pomodorotimer.app"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setQuitOnLastWindowClosed(False)
    
    icon_path = get_resource_path("ModernPomodoro.ico")
    
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)
    else:
        print(f"ADVERTENCIA: No se encontró el icono en la ruta: {icon_path}")
        app_icon = QIcon()
    
    window = MainWindow()
    window.setWindowIcon(app_icon)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
	