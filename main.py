"""Punto de entrada de Pomodoro Timer.

La lógica original (v5) se conserva en ``MyPomodoro.py`` como respaldo.
Este archivo solo orquesta el arranque de la aplicación modularizada.
"""

import sys

from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import QApplication

from services.resource_manager import get_resource_path
from ui.main_window import MainWindow


def main():
    if sys.platform == "win32":
        import ctypes
        myappid = "com.pomodorotimer.app"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setApplicationName("Pomodoro Timer")
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
