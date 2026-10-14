PALETTES = {
    "dark": {
        "bg": "#1e1e24",
        "fg": "#e6e6eb",
        "btn_bg": "#2d2d38",
        "btn_border": "#3d3d4a",
        "btn_hover_bg": "#3d3d4a",
        "btn_hover_border": "#5a5a6e",
        "btn_pressed": "#1a1a22",
        "btn_time_hover": "#2a2a33",
        "btn_min_bg": "#2d382d",
        "btn_min_border": "#3d4a3d",
        "btn_min_hover": "#3d4a3d",
        "slider_groove": "#2d2d38",
        "slider_border": "#3d3d4a",
        "slider_handle": "#5a5a6e",
        "slider_handle_border": "#7a7a8e",
        "combo_bg": "#2d2d38",
        "combo_border": "#3d3d4a",
        "checkbox": "#c8c8d2",
        "muted": "#9999a8",
        "stats": "#a8a8b8",
        "task": "#c8c8d8",
        "tip": "#8fbf8f",
    },
    "light": {
        "bg": "#f4f4f7",
        "fg": "#22222a",
        "btn_bg": "#e6e6ec",
        "btn_border": "#c8c8d2",
        "btn_hover_bg": "#dcdce4",
        "btn_hover_border": "#a8a8b8",
        "btn_pressed": "#d0d0da",
        "btn_time_hover": "#e2e2ea",
        "btn_min_bg": "#dfeadd",
        "btn_min_border": "#c2d6c2",
        "btn_min_hover": "#d0e2d0",
        "slider_groove": "#dcdce4",
        "slider_border": "#c8c8d2",
        "slider_handle": "#9a9aae",
        "slider_handle_border": "#7a7a8e",
        "combo_bg": "#e6e6ec",
        "combo_border": "#c8c8d2",
        "checkbox": "#3a3a44",
        "muted": "#6a6a78",
        "stats": "#5a5a68",
        "task": "#3a3a44",
        "tip": "#3f7a3f",
    },
}


def get_stylesheet(theme="dark"):
    p = PALETTES.get(theme, PALETTES["dark"])
    return f"""
    QMainWindow, QWidget {{ background-color: {p['bg']}; color: {p['fg']}; }}
    QPushButton {{
        background-color: {p['btn_bg']}; border: 1px solid {p['btn_border']};
        border-radius: 6px; padding: 4px 8px; color: {p['fg']};
        font-size: 12px; min-height: 28px;
    }}
    QPushButton:hover {{ background-color: {p['btn_hover_bg']}; border-color: {p['btn_hover_border']}; }}
    QPushButton:pressed {{ background-color: {p['btn_pressed']}; }}
    QPushButton#btn_time {{
        background: transparent; border: none;
        font-size: 18px; font-weight: bold; min-width: 86px;
    }}
    QPushButton#btn_time:hover {{ background-color: {p['btn_time_hover']}; border-radius: 6px; }}
    QPushButton#btn_min {{ background-color: {p['btn_min_bg']}; border-color: {p['btn_min_border']}; }}
    QPushButton#btn_min:hover {{ background-color: {p['btn_min_hover']}; }}
    QSlider::groove:horizontal {{
        height: 6px; background: {p['slider_groove']};
        border: 1px solid {p['slider_border']}; border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {p['slider_handle']}; border: 1px solid {p['slider_handle_border']};
        width: 14px; margin: -5px 0; border-radius: 7px;
    }}
    QComboBox {{
        background-color: {p['combo_bg']}; border: 1px solid {p['combo_border']};
        border-radius: 4px; padding: 3px 6px; color: {p['fg']};
    }}
    QCheckBox {{ color: {p['checkbox']}; }}
    QLabel#status_caption {{ font-size: 10px; color: {p['muted']}; }}
    QLabel#value_caption {{ font-size: 10px; color: {p['muted']}; }}
    QLabel#stats_caption {{ font-size: 10px; color: {p['stats']}; padding: 4px; }}
    QLabel#task_caption {{ font-size: 10px; color: {p['task']}; }}
    QLabel#tip_caption {{ font-size: 10px; color: {p['tip']}; padding: 2px; }}
"""


MAIN_STYLESHEET = get_stylesheet("dark")
