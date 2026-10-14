from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton


class TimeButton(QPushButton):
    """Botón de tiempo que además permite arrastrar la ventana sin bordes."""

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
