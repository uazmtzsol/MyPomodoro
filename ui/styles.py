MAIN_STYLESHEET = """
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
"""
