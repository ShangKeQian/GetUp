import threading
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QComboBox, QSpinBox,
)
from PySide6.QtCore import Qt, Signal, QTimer as QSingleShotTimer
from PySide6.QtGui import QPainter, QColor, QPen
from config import Config, set_startup
from camera_utils import enumerate_cameras
from theme import MAIN_WINDOW_STYLE, BG, SURFACE, FG, MUTED, BORDER, ACCENT, ACCENT_DIM, STATUS_MAP, fmt_mmss


class FluentSpinbox(QWidget):
    """Fluent 风格数字调节器（水平 -/+ 按钮，浅色主题）"""

    _BTN_STYLE = """
        QPushButton {{
            background-color: {bg};
            color: {fg};
            border: none;
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
            font-size: 16px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
        QPushButton:pressed {{
            background-color: {pressed};
        }}
        QPushButton:disabled {{
            background-color: {bg};
            color: #d1d5db;
        }}
    """

    def __init__(self, min_val=0, max_val=100, value=0, step=1, parent=None):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._step = step

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 减号按钮
        self._btn_minus = QPushButton("−")
        self._btn_minus.setStyleSheet(self._BTN_STYLE.format(
            bg=BG, fg=FG, hover=BORDER, pressed="#d1d5db"
        ))
        self._btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_minus.clicked.connect(self._decrease)
        layout.addWidget(self._btn_minus)

        # 数值
        self._spin = QSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setValue(value)
        self._spin.setSingleStep(step)
        self._spin.setFixedSize(48, 32)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: transparent;
                color: {FG};
                border-top: 1px solid {BORDER};
                border-bottom: 1px solid {BORDER};
                border-left: none;
                border-right: none;
                font-size: 14px;
                font-weight: 600;
            }}
            QSpinBox:focus {{
                border-color: {ACCENT};
            }}
        """)
        self._spin.valueChanged.connect(self._update_buttons)
        layout.addWidget(self._spin)

        # 加号按钮
        self._btn_plus = QPushButton("+")
        self._btn_plus.setStyleSheet(self._BTN_STYLE.format(
            bg=BG, fg=FG, hover=BORDER, pressed="#d1d5db"
        ))
        self._btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_plus.clicked.connect(self._increase)
        layout.addWidget(self._btn_plus)

        self._update_buttons()

    def _decrease(self):
        self._spin.setValue(self._spin.value() - self._spin.singleStep())

    def _increase(self):
        self._spin.setValue(self._spin.value() + self._spin.singleStep())

    def _update_buttons(self):
        v = self._spin.value()
        self._btn_minus.setEnabled(v > self._min)
        self._btn_plus.setEnabled(v < self._max)

    def value(self):
        return self._spin.value()

    def setValue(self, v):
        self._spin.setValue(v)


class FluentToggle(QWidget):
    """Fluent 风格开关（带滑块，绿色主题）"""

    WIDTH = 44
    HEIGHT = 24
    KNOB_R = 9
    PAD = 3

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(FluentToggle.WIDTH, FluentToggle.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, v):
        self._checked = v
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = FluentToggle.WIDTH, FluentToggle.HEIGHT
        pad = FluentToggle.PAD

        # 轨道
        track_color = QColor(ACCENT) if self._checked else QColor(BORDER)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(pad, pad, w - 2 * pad, h - 2 * pad,
                                (h - 2 * pad) / 2, (h - 2 * pad) / 2)

        # 滑块
        r = FluentToggle.KNOB_R
        if self._checked:
            cx = w - pad - r - 1
        else:
            cx = pad + r + 1
        cy = h // 2

        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor(0, 0, 0, 20), 1))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        painter.end()


class StatusPill(QWidget):
    """Fluent 风格状态指示器（圆角药丸形标签）"""

    _COLORS = {label: color for label, color in STATUS_MAP.values()}

    def __init__(self, text="", color=ACCENT, parent=None):
        super().__init__(parent)
        self._text = text
        self._color = QColor(color)
        self.setFixedHeight(24)
        self._update_width()

    def setText(self, text):
        self._text = text
        c = self._COLORS.get(text, MUTED)
        self._color = QColor(c)
        self._update_width()
        self.update()

    def _update_width(self):
        fm = self.fontMetrics()
        w = fm.horizontalAdvance(self._text) + 24
        self.setFixedWidth(max(w, 60))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        bg = QColor(self._color)
        bg.setAlpha(30)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)

        # 圆点
        painter.setBrush(self._color)
        painter.drawEllipse(8, self.height() // 2 - 3, 6, 6)

        # 文字
        painter.setPen(self._color)
        painter.drawText(20, 0, self.width() - 20, self.height(),
                         Qt.AlignmentFlag.AlignVCenter, self._text)
        painter.end()


def _create_setting_icon(icon_text, bg_color, fg_color):
    """创建设置行的彩色图标方块"""
    lbl = QLabel(icon_text)
    lbl.setFixedSize(32, 32)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"""
        font-size: 16px;
        background-color: {bg_color};
        color: {fg_color};
        border-radius: 8px;
    """)
    return lbl


class MainWindow(QMainWindow):
    cameras_scanned = Signal(list, list)

    def __init__(self, config: Config, on_save=None):
        super().__init__()
        self._config = config
        self._on_save = on_save
        self._cameras = []
        self._camera_names = []
        self._cameras_cached = False
        self.cameras_scanned.connect(self._on_cameras_scanned)

        self.setWindowTitle("GetUp 设置")
        self.setFixedSize(520, 760)
        self.setStyleSheet(MAIN_WINDOW_STYLE)

        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 20)
        main_layout.setSpacing(16)

        # ── 标题栏 ──
        header = QHBoxLayout()
        header.setSpacing(14)

        logo = QLabel("☕")
        logo.setFixedSize(44, 44)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"""
            font-size: 22px;
            background-color: {ACCENT};
            color: white;
            border-radius: 12px;
        """)
        header.addWidget(logo)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title = QLabel("GetUp 设置")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {FG}; letter-spacing: -0.02em;")
        title_col.addWidget(title)
        version = QLabel("v1.2.0")
        version.setStyleSheet(f"font-size: 13px; color: {MUTED};")
        title_col.addWidget(version)
        header.addLayout(title_col)
        header.addStretch()

        main_layout.addLayout(header)

        # ── 状态卡片 ──
        status_card = QFrame()
        status_card.setObjectName("card")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 20, 20, 20)

        self._status_pill = StatusPill("有人", ACCENT)
        status_layout.addWidget(self._status_pill)

        status_layout.addSpacing(8)

        countdown_hint = QLabel("距休息还有")
        countdown_hint.setStyleSheet(f"color: {MUTED}; font-size: 13px;")
        status_layout.addWidget(countdown_hint)

        self._countdown_display = QLabel(f"{self._config.work_minutes:02d}:00")
        self._countdown_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_display.setStyleSheet(
            f"color: {FG}; font-size: 48px; font-weight: bold; font-variant-numeric: tabular-nums;"
        )
        status_layout.addWidget(self._countdown_display)

        main_layout.addWidget(status_card)

        # ── 可滚动内容 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)

        # ── 计时器 ──
        timer_card = self._create_section("计时器")
        self._work_spin = FluentSpinbox(5, 120, self._config.work_minutes, step=5)
        self._add_setting_row(timer_card, "⏱", "#dcfce7", ACCENT,
                              "工作时长", "连续工作多久后提醒休息", "分钟", self._work_spin)
        self._break_spin = FluentSpinbox(1, 30, self._config.break_minutes)
        self._add_setting_row(timer_card, "☕", "#dbeafe", "#3b82f6",
                              "休息时长", "每次休息的倒计时时长", "分钟", self._break_spin)
        scroll_layout.addWidget(timer_card)

        # ── 在位检测 ──
        detect_card = self._create_section("在位检测")
        self._camera_combo = QComboBox()
        self._camera_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {SURFACE};
                color: {FG};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 140px;
                font-size: 13px;
            }}
            QComboBox:hover {{ border-color: {ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
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
        """)
        self._camera_combo.addItems(["检测中..."])
        self._add_setting_row(detect_card, "📷", "#ede9fe", "#8b5cf6",
                              "摄像头索引", "选择使用的摄像头设备", "", self._camera_combo)
        scroll_layout.addWidget(detect_card)

        # ── 智能休眠 ──
        sleep_card = self._create_section("智能休眠")
        self._sleep_spin = FluentSpinbox(5, 120, self._config.sleep_timeout_minutes, step=5)
        self._add_setting_row(sleep_card, "⏱", "#f3f4f6", MUTED,
                              "休眠阈值", "离开多久后进入休眠状态", "分钟", self._sleep_spin)
        scroll_layout.addWidget(sleep_card)

        # ── 系统 ──
        system_card = self._create_section("系统")
        self._startup_toggle = FluentToggle(self._config.startup_enabled)
        self._add_setting_row(system_card, "💻", "#dcfce7", ACCENT,
                              "开机自启动", "通过 Windows 注册表设置开机自动启动", "", self._startup_toggle)
        scroll_layout.addWidget(system_card)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll, 1)

        # ── 底部按钮 ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._reset_btn = QPushButton("恢复默认")
        self._reset_btn.setObjectName("secondary")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row.addWidget(self._reset_btn)

        self._save_btn = QPushButton("保存设置")
        self._save_btn.setObjectName("accent")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        btn_row.addWidget(self._save_btn)

        main_layout.addLayout(btn_row)

        # 后台扫描摄像头
        self._cache_cameras()

    def _create_section(self, title):
        card = QFrame()
        card.setObjectName("section-card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        lbl = QLabel(title)
        lbl.setObjectName("section-title")
        lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; text-transform: uppercase; "
            f"letter-spacing: 0.06em; color: {MUTED}; padding: 16px 20px 0;"
        )
        layout.addWidget(lbl)

        return card

    def _add_setting_row(self, card, icon_text, icon_bg, icon_fg, label, desc, unit, widget):
        layout = card.layout()

        row = QFrame()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(20, 14, 20, 14)
        row_layout.setSpacing(14)

        # 图标
        icon = _create_setting_icon(icon_text, icon_bg, icon_fg)
        row_layout.addWidget(icon)

        # 信息
        info = QVBoxLayout()
        info.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 14px; font-weight: 500; color: {FG};")
        info.addWidget(lbl)
        if desc:
            d = QLabel(desc)
            d.setStyleSheet(f"font-size: 12px; color: {MUTED};")
            info.addWidget(d)
        row_layout.addLayout(info, 1)

        # 控件
        if unit:
            ctrl = QHBoxLayout()
            ctrl.setSpacing(8)
            ctrl.addWidget(widget)
            unit_lbl = QLabel(unit)
            unit_lbl.setStyleSheet(f"font-size: 13px; color: {MUTED};")
            ctrl.addWidget(unit_lbl)
            row_layout.addLayout(ctrl)
        else:
            row_layout.addWidget(widget)

        layout.addWidget(row)
        return row

    def _cache_cameras(self):
        if self._cameras_cached:
            return
        self._cameras_cached = True

        def _scan():
            cameras = enumerate_cameras()
            names = [c["name"] for c in cameras] or ["未检测到摄像头"]
            self.cameras_scanned.emit(cameras, names)

        threading.Thread(target=_scan, daemon=True).start()

    def _on_cameras_scanned(self, cameras, names):
        self._cameras = cameras
        self._camera_names = names
        self._camera_combo.clear()
        self._camera_combo.addItems(names)
        for i, name in enumerate(names):
            self._camera_combo.setItemData(i, name, Qt.ItemDataRole.ToolTipRole)
        for i, cam in enumerate(cameras):
            if cam["index"] == self._config.camera_index:
                self._camera_combo.setCurrentIndex(i)
                break

    def _save(self):
        self._config.work_minutes = self._work_spin.value()
        self._config.break_minutes = self._break_spin.value()
        self._config.sleep_timeout_minutes = self._sleep_spin.value()

        selected = self._camera_combo.currentText()
        for cam in self._cameras:
            if cam["name"] == selected:
                self._config.camera_index = cam["index"]
                break

        startup = self._startup_toggle.isChecked()
        if startup != self._config.startup_enabled:
            self._config.startup_enabled = startup
            set_startup(startup)

        self._config.save()
        if self._on_save:
            self._on_save()

        # 保存反馈
        self._save_btn.setText("已保存 ✓")
        self._save_btn.setStyleSheet(
            f"background-color: {ACCENT}; color: white; border: none; "
            "border-radius: 8px; padding: 10px 24px; font-size: 14px; font-weight: bold;"
        )
        QSingleShotTimer.singleShot(1500, self._restore_save_btn)

    def _restore_save_btn(self):
        self._save_btn.setText("保存设置")
        self._save_btn.setStyleSheet("")

    def update_status(self, status: str):
        self._status_pill.setText(status)

    def update_work_countdown(self, elapsed_seconds: int):
        remaining = max(0, self._config.work_minutes * 60 - elapsed_seconds)
        self._countdown_display.setText(fmt_mmss(remaining))

    def reset_countdown(self):
        self._countdown_display.setText(fmt_mmss(self._config.work_minutes * 60))
