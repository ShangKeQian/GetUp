from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPainter, QColor, QPen
from theme import OVERLAY_STYLE, OVL_BG, OVL_SURFACE, OVL_FG, OVL_MUTED, OVL_ACCENT
from theme import fmt_mmss
from fullscreen import get_fullscreen_target


class RingProgress(QWidget):
    """260×260 环形进度条（SVG 风格，带绿色辉光）"""

    def __init__(self, size=260, parent=None):
        super().__init__(parent)
        self._progress = 1.0  # 1.0 → 0.0
        self._size = size
        self.setFixedSize(size, size)

    def setProgress(self, value: float):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = cy = self._size // 2
        r = cx - 16
        lw = 8

        # 背景环
        pen = QPen(QColor(OVL_SURFACE), lw)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # 进度环 + 辉光
        if self._progress > 0:
            glow = QColor(OVL_ACCENT)
            glow.setAlpha(80)
            pen_glow = QPen(glow, lw + 8)
            pen_glow.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen_glow)
            start = 90 * 16
            span = -int(self._progress * 360 * 16)
            p.drawArc(cx - r, cy - r, r * 2, r * 2, start, span)

            pen_main = QPen(QColor(OVL_ACCENT), lw)
            pen_main.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen_main)
            p.drawArc(cx - r, cy - r, r * 2, r * 2, start, span)

        p.end()


class OverlayWindow(QMainWindow):
    """久坐提醒遮罩：暗色全屏 + SVG 环形倒计时 + 提示卡片 + 跳过按钮"""

    def __init__(self, break_minutes=2, on_close=None):
        super().__init__()
        self._on_close_callback = on_close
        self._total_seconds = break_minutes * 60
        self._remaining = self._total_seconds
        self._is_shown = False

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setStyleSheet(OVERLAY_STYLE)
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 顶部栏 ──
        top = QHBoxLayout()
        top.setContentsMargins(24, 4, 24, 0)
        top.addStretch()

        self._close_btn = QPushButton("✕ 关闭")
        self._close_btn.setObjectName("close")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._on_close)
        top.addWidget(self._close_btn)

        root.addLayout(top)

        # ── 环形进度条 + 倒计时（偏上） ──
        ring_size = 240
        ring_container = QWidget()
        ring_container.setFixedSize(ring_size, ring_size)
        ring_layout = QVBoxLayout(ring_container)
        ring_layout.setContentsMargins(0, 0, 0, 0)

        self._ring = RingProgress(ring_size, ring_container)

        self._countdown_label = QLabel("00:00")
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setStyleSheet(
            f"font-size: 56px; font-weight: 700; color: {OVL_FG}; "
            "font-variant-numeric: tabular-nums; letter-spacing: -0.03em; background: transparent;"
        )
        self._countdown_label.setParent(ring_container)
        self._countdown_label.setGeometry(0, 55, ring_size, 70)

        self._ring_label = QLabel("休息倒计时")
        self._ring_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ring_label.setStyleSheet(
            f"font-size: 14px; color: {OVL_MUTED}; text-transform: uppercase; "
            "letter-spacing: 0.1em; background: transparent;"
        )
        self._ring_label.setParent(ring_container)
        self._ring_label.setGeometry(0, 125, ring_size, 25)

        ring_layout.addWidget(self._ring)
        root.addWidget(ring_container, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ── 下方弹性空间（把卡片推到底部） ──
        root.addStretch(1)

        # ── 提示卡片（底部） ──
        tips_layout = QHBoxLayout()
        tips_layout.setSpacing(24)
        tips_layout.setContentsMargins(0, 0, 0, 24)
        tips_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tips = [
            ("☕", "站立伸展", "#06b6d4"),
            ("🚶", "走动一下", "#3b82f6"),
            ("👀", "远眺放松", "#a855f7"),
        ]
        for icon, text, color in tips:
            tip = self._create_tip_card(icon, text, color)
            tips_layout.addWidget(tip)

        root.addLayout(tips_layout)

    def _create_tip_card(self, icon, text, color):
        card = QLabel(f"{icon}  {text}")
        card.setStyleSheet(f"""
            QLabel {{
                color: {color};
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 14px;
            }}
        """)
        return card

    def showEvent(self, event):
        super().showEvent(event)
        if not self._is_shown:
            self._is_shown = True
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.geometry()
                h = geom.height() // 3
                self.setFixedSize(geom.width(), h)
                self.move(geom.x(), geom.y() + (geom.height() - h) // 2)

            self.setWindowOpacity(0.0)
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
            self._fade_anim.setDuration(300)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_anim.start()

    def show_overlay(self):
        if self._is_shown:
            return
        self._remaining = self._total_seconds
        self.setStyleSheet(OVERLAY_STYLE)
        self._close_btn.setText("✕ 关闭")
        self.show()
        self.update_countdown(self._remaining)

    def update_countdown(self, seconds):
        self._remaining = max(0, seconds)
        self._countdown_label.setText(fmt_mmss(self._remaining))
        progress = self._remaining / self._total_seconds if self._total_seconds > 0 else 0
        self._ring.setProgress(progress)

    def _on_close(self):
        self.destroy_overlay()

    def destroy_overlay(self):
        if self._is_shown:
            self._is_shown = False
            # 停止可能正在进行的淡入动画，避免对已隐藏窗口操作
            if hasattr(self, '_fade_anim'):
                self._fade_anim.stop()
            self.hide()
            if self._on_close_callback:
                self._on_close_callback()


MINI_CARD_STYLE = f"""
QWidget#mini-card {{
    background-color: rgba(15, 23, 42, 0.92);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
}}
QLabel {{
    background: transparent;
}}
QLabel#mini-title {{
    color: {OVL_MUTED};
    font-size: 12px;
    letter-spacing: 0.08em;
}}
QLabel#mini-countdown {{
    color: {OVL_ACCENT};
    font-size: 34px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
}}
QPushButton#mini-skip {{
    background-color: rgba(255, 255, 255, 0.08);
    color: {OVL_MUTED};
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    font-size: 13px;
    padding: 6px 14px;
}}
QPushButton#mini-skip:hover {{
    background-color: rgba(255, 255, 255, 0.15);
    color: {OVL_FG};
}}
"""


class MiniOverlayWindow(QMainWindow):
    """全屏场景迷你提醒：右上角悬浮卡片，不遮挡画面中心。

    语义与居中遮罩一致：出现即进入休息倒计时，倒计时归零自动关闭，
    点击"跳过"提前结束。区别仅在形态——无背景遮罩、不占中心区域。
    """

    def __init__(self, break_minutes=2, on_close=None):
        super().__init__()
        self._on_close_callback = on_close
        self._total_seconds = break_minutes * 60
        self._remaining = self._total_seconds
        self._is_shown = False
        self._target_screen = None

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._init_ui()

    def _init_ui(self):
        central = QWidget(objectName="mini-card")
        central.setStyleSheet(MINI_CARD_STYLE)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(20, 14, 16, 14)
        root.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title_label = QLabel("该起身活动了")
        self._title_label.setObjectName("mini-title")
        self._countdown_label = QLabel("00:00")
        self._countdown_label.setObjectName("mini-countdown")
        text_col.addWidget(self._title_label)
        text_col.addWidget(self._countdown_label)
        root.addLayout(text_col)

        root.addStretch()

        self._skip_btn = QPushButton("跳过")
        self._skip_btn.setObjectName("mini-skip")
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(self._on_close)
        root.addWidget(self._skip_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        self.setFixedSize(300, 104)

    def show_overlay(self, screen=None):
        """显示迷你提醒。screen 为全屏窗口所在显示器，缺省回退主屏。"""
        if self._is_shown:
            return
        self._target_screen = screen
        self._remaining = self._total_seconds
        self.show()
        self.update_countdown(self._remaining)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._is_shown:
            self._is_shown = True
            self._position_on_screen()
            self.setWindowOpacity(0.0)
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
            self._fade_anim.setDuration(300)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_anim.start()

    def _position_on_screen(self):
        screen = self._target_screen or QApplication.primaryScreen()
        if screen is None:
            return
        geom = screen.geometry()
        self.move(geom.x() + geom.width() - self.width() - 24, geom.y() + 24)

    def update_countdown(self, seconds):
        self._remaining = max(0, seconds)
        self._countdown_label.setText(fmt_mmss(self._remaining))

    def _on_close(self):
        self.destroy_overlay()

    def destroy_overlay(self):
        if self._is_shown:
            self._is_shown = False
            if hasattr(self, '_fade_anim'):
                self._fade_anim.stop()
            self.hide()
            if self._on_close_callback:
                self._on_close_callback()


class OverlayManager:
    """提醒路由器：对 main.py 暴露与 OverlayWindow 相同的接口。

    提醒触发时检测前台窗口是否全屏：
    - 全屏 → 右上角迷你卡片（不遮挡画面中心，定位到全屏窗口所在显示器）
    - 非全屏 → 原居中遮罩
    """

    def __init__(self, break_minutes=2, on_close=None):
        self._full = OverlayWindow(break_minutes=break_minutes, on_close=on_close)
        self._mini = MiniOverlayWindow(break_minutes=break_minutes, on_close=on_close)

    def _active(self):
        if self._full._is_shown:
            return self._full
        if self._mini._is_shown:
            return self._mini
        return None

    def show_overlay(self):
        if self._active() is not None:
            return
        target = get_fullscreen_target()
        if target is not None:
            self._mini.show_overlay(target)
        else:
            self._full.show_overlay()

    def update_countdown(self, seconds):
        active = self._active()
        if active is not None:
            active.update_countdown(seconds)

    def destroy_overlay(self):
        active = self._active()
        if active is not None:
            active.destroy_overlay()
