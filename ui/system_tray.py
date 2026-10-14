from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

_STATE_LABELS = {"idle": "Listo", "running": "En curso", "paused": "En pausa"}


class SystemTray:
    """
    Icono en la bandeja del sistema.

    No depende de la ventana: recibe los callbacks de las acciones para que la
    ventana principal (o cualquier otro consumidor) los implemente.
    """

    def __init__(self, parent, *, on_play_pause, on_stop, on_restart,
                 on_show, on_config, on_quit, on_toggle):
        self._tray = None
        self._action_play = None
        self._on_toggle = on_toggle

        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._tray = QSystemTrayIcon(parent)
        menu = QMenu()

        self._action_play = QAction("▶ Iniciar", parent)
        self._action_play.triggered.connect(on_play_pause)
        menu.addAction(self._action_play)

        action = QAction("⏹ Detener", parent)
        action.triggered.connect(on_stop)
        menu.addAction(action)

        action = QAction("🔄 Reiniciar", parent)
        action.triggered.connect(on_restart)
        menu.addAction(action)

        menu.addSeparator()

        action = QAction("Mostrar ventana", parent)
        action.triggered.connect(on_show)
        menu.addAction(action)

        action = QAction("⚙ Ajustes", parent)
        action.triggered.connect(on_config)
        menu.addAction(action)

        menu.addSeparator()

        action = QAction("✕ Salir", parent)
        action.triggered.connect(on_quit)
        menu.addAction(action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.setIcon(self._build_icon(0))
        self._tray.setToolTip("Pomodoro Timer")
        self._tray.show()

    @property
    def available(self) -> bool:
        return self._tray is not None

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger and self._on_toggle:
            self._on_toggle()

    def _build_icon(self, remaining_seconds):
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
                   f"{remaining_seconds // 60:02d}:{remaining_seconds % 60:02d}")
        p.end()
        return QIcon(pm)

    def update(self, remaining_seconds, state, session_name, task_text=""):
        """Redibuja el icono con el tiempo restante y ajusta tooltip/menú."""
        if not self._tray:
            return

        self._tray.setIcon(self._build_icon(remaining_seconds))

        tooltip = f"Pomodoro Timer — {_STATE_LABELS.get(state, '')} — {session_name}"
        if task_text:
            tooltip += f"\n📋 {task_text}"
        self._tray.setToolTip(tooltip)
        if self._action_play is not None:
            self._action_play.setText("⏸ Pausar" if state == "running" else "▶ Iniciar")

    def show_message(self, title, message, msec=3000):
        if self._tray and self._tray.supportsMessages():
            self._tray.showMessage(title, message,
                                   QSystemTrayIcon.MessageIcon.Information, msec)

    def hide(self):
        if self._tray:
            self._tray.hide()
