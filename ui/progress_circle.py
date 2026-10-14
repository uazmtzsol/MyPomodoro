from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtWidgets import QWidget, QSizePolicy


PALETTES = {
    "dark": {"ring_bg": QColor(60, 60, 70), "label": QColor(180, 180, 195),
             "sat": 230, "value": 240},
    "light": {"ring_bg": QColor(210, 210, 218), "label": QColor(90, 90, 105),
              "sat": 220, "value": 190},
}


class ProgressCircle(QWidget):
    """Círculo de progreso con el tiempo restante en el centro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ring = 1.0
        self.elapsed = 0.0
        self.time_text = "25:00"
        self.session_type = "Trabajo"
        self.theme = "dark"
        self.setMinimumSize(110, 110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_theme(self, theme):
        self.theme = theme if theme in PALETTES else "dark"
        self.update()

    def set_ring(self, value):
        self.ring = max(0.0, min(1.0, value))

    def set_elapsed(self, value):
        self.elapsed = max(0.0, min(1.0, value))

    def set_time_text(self, text):
        self.time_text = text

    def set_session_type(self, text):
        self.session_type = text

    def color(self):
        p = PALETTES[self.theme]
        return QColor.fromHsv(int(120 * (1 - self.elapsed)), p["sat"], p["value"])

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

        bg = QPen(PALETTES[self.theme]["ring_bg"])
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
        p.setPen(PALETTES[self.theme]["label"])
        label_rect = QRectF(rect)
        label_rect.setTop(c.y() + size / 8)
        p.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   self.session_type)
        p.end()
