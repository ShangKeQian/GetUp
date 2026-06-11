from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPainter, QColor, QPen
from theme import OVERLAY_STYLE, OVL_BG, OVL_SURFACE, OVL_FG, OVL_MUTED, OVL_ACCENT
from theme import fmt_mmss


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
            ("☕", "站立伸展", "#22c55e"),
            ("🚶", "走动一下", "#3b82f6"),
            ("👀", "远眺放松", "#a855f7"),
        ]
        for icon, text, color in tips:
            tip = self._create_tip_card(icon, text, color)
            tips_layout.addWidget(tip)

        root.addLayout(tips_layout)

    def _create_tip_card(self, icon, text, color):
        card = QLabel(text)
        card.setStyleSheet(f"""
            QLabel {{
                color: {OVL_MUTED};
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
            self.hide()
            if self._on_close_callback:
                self._on_close_callback()
