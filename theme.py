"""Fluent Design QSS 样式表 — 匹配前端设计稿"""


def fmt_mmss(seconds: int) -> str:
    """将秒数格式化为 MM:SS 字符串"""
    m, s = int(seconds) // 60, int(seconds) % 60
    return f"{m:02d}:{s:02d}"


# ── 状态 → (显示标签, 颜色) 映射 ─────────────────────────
STATUS_MAP = {
    "present": ("有人", "#22c55e"),
    "absent": ("无人", "#f59e0b"),
    "paused": ("暂停", "#6366f1"),
    "sleeping": ("休眠", "#6b7280"),
}


# ── 主色板 ──────────────────────────────────────────────
BG = "#f8faf9"
SURFACE = "#ffffff"
FG = "#1a1d1b"
MUTED = "#6b7280"
BORDER = "#e5e7eb"
ACCENT = "#22c55e"
ACCENT_HOVER = "#16a34a"
ACCENT_DIM = "#dcfce7"
RADIUS = "10px"

# ── 遮罩色板 ────────────────────────────────────────────
OVL_BG = "#0f172a"
OVL_SURFACE = "#1e293b"
OVL_FG = "#f1f5f9"
OVL_MUTED = "#94a3b8"
OVL_ACCENT = "#22c55e"

# ── 状态色 ──────────────────────────────────────────────
STATUS_PRESENT = "#22c55e"
STATUS_ABSENT = "#f59e0b"
STATUS_PAUSED = "#6366f1"
STATUS_SLEEPING = "#6b7280"

# ── 休息页面色板 ─────────────────────────────────────────
REST_BG = "#f0fdf4"
REST_FG = "#14532d"
REST_MUTED = "#577a64"
REST_BORDER = "#bbf7d0"


MAIN_WINDOW_STYLE = f"""
QMainWindow {{
    background-color: {BG};
}}
QWidget {{
    background-color: {BG};
    color: {FG};
    font-family: "Segoe UI", "Microsoft YaHei";
}}
QLabel {{
    background: transparent;
}}
QFrame#card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
}}
QFrame#section-card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: {RADIUS};
}}
QFrame#separator {{
    background-color: {BORDER};
    min-height: 1px;
    max-height: 1px;
}}
QLabel#section-title {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {MUTED};
}}
QPushButton#accent {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton#accent:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#accent:pressed {{
    background-color: #15803d;
}}
QPushButton#accent:disabled {{
    background-color: {BORDER};
    color: {MUTED};
}}
QPushButton#secondary {{
    background-color: {SURFACE};
    color: {FG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 500;
}}
QPushButton#secondary:hover {{
    background-color: {BG};
}}
QPushButton#close {{
    background-color: transparent;
    color: {MUTED};
    border: none;
    border-radius: 4px;
    font-size: 14px;
}}
QPushButton#close:hover {{
    background-color: #f3f4f6;
    color: {FG};
}}
QPushButton#close:pressed {{
    background-color: #e5e7eb;
}}
QComboBox {{
    background-color: {SURFACE};
    color: {FG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 140px;
    max-width: 200px;
    font-size: 13px;
}}
QComboBox:hover {{
    border-color: {ACCENT};
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {MUTED};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    color: {FG};
    selection-background-color: {ACCENT_DIM};
    selection-color: {FG};
    border: 1px solid {BORDER};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #d1d5db;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""

OVERLAY_STYLE = f"""
QMainWindow {{
    background-color: {OVL_BG};
}}
QWidget {{
    background-color: {OVL_BG};
    color: {OVL_FG};
    font-family: "Segoe UI", "Microsoft YaHei";
}}
QLabel {{
    background: transparent;
}}
QPushButton#close {{
    background-color: rgba(255, 255, 255, 0.08);
    color: {OVL_MUTED};
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    font-size: 14px;
    padding: 8px 16px;
}}
QPushButton#close:hover {{
    background-color: rgba(255, 255, 255, 0.15);
    color: {OVL_FG};
    border-color: rgba(255, 255, 255, 0.25);
}}
QPushButton#close:pressed {{
    background-color: rgba(255, 255, 255, 0.2);
}}
"""

REST_STYLE = f"""
QMainWindow {{
    background-color: {REST_BG};
}}
QWidget {{
    background-color: {REST_BG};
    color: {REST_FG};
    font-family: "Segoe UI", "Microsoft YaHei";
}}
QLabel {{
    background: transparent;
}}
QPushButton#close {{
    background-color: {SURFACE};
    color: {REST_FG};
    border: 1px solid {REST_BORDER};
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    padding: 8px 16px;
}}
QPushButton#close:hover {{
    background-color: rgba(34, 197, 94, 0.08);
    border-color: {ACCENT};
}}
QPushButton#close:pressed {{
    background-color: rgba(34, 197, 94, 0.15);
}}
"""
