import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPainter, QColor, QPen
from theme import OVERLAY_STYLE, OVL_BG, OVL_SURFACE, OVL_FG, OVL_MUTED, OVL_ACCENT
from theme import REST_STYLE, REST_FG, REST_MUTED, REST_BORDER, ACCENT
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


class BreathingRing(QWidget):
    """220×220 呼吸动画圆环（休息模式）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale_phase = 0.0
        self.setFixedSize(220, 220)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)  # ~20fps

    def _animate(self):
        self._scale_phase += 0.08
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = cy = 110
        pulse = 1.0 + 0.03 * math.sin(self._scale_phase)

        # 外圈 3（最外层，半透明）
        r3 = int(100 * pulse)
        pen3 = QPen(QColor(REST_BORDER), 1)
        c3 = QColor(REST_BORDER)
        c3.setAlpha(100)
        pen3.setColor(c3)
        p.setPen(pen3)
        p.drawEllipse(cx - r3, cy - r3, r3 * 2, r3 * 2)

        # 外圈 2
        r2 = int(90 * pulse)
        pen2 = QPen(QColor(REST_BORDER), 1)
        p.setPen(pen2)
        p.drawEllipse(cx - r2, cy - r2, r2 * 2, r2 * 2)

        # 主圈
        r1 = int(78 * pulse)
        pen1 = QPen(QColor(ACCENT), 3)
        p.setPen(pen1)
        p.drawEllipse(cx - r1, cy - r1, r1 * 2, r1 * 2)

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


class RestTimerWindow(QMainWindow):
    """休息计时窗口：浅绿主题 + 呼吸动画 + 进度条 + 统计"""

    def __init__(self, break_minutes=2, on_end_early=None):
        super().__init__()
        self._total_seconds = break_minutes * 60
        self._remaining = self._total_seconds
        self._on_end_early = on_end_early
        self._is_shown = False
        self._rest_count = 0
        self._today_work_seconds = 0
        self._today_rest_seconds = 0

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setStyleSheet(REST_STYLE)
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶部栏
        top = QHBoxLayout()
        top.setContentsMargins(24, 20, 24, 0)
        top.addStretch()

        end_btn = QPushButton("提前结束休息")
        end_btn.setObjectName("close")
        end_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        end_btn.clicked.connect(self._on_end)
        top.addWidget(end_btn)

        root.addLayout(top)

        # 中心内容
        center = QVBoxLayout()
        center.setContentsMargins(40, 0, 40, 40)
        center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.setSpacing(20)

        # 呼吸环 + 倒计时
        ring_wrap = QWidget()
        ring_wrap.setFixedSize(220, 220)
        ring_layout = QVBoxLayout(ring_wrap)
        ring_layout.setContentsMargins(0, 0, 0, 0)

        self._breath_ring = BreathingRing(ring_wrap)

        self._rest_time_label = QLabel("00:00")
        self._rest_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rest_time_label.setStyleSheet(
            f"font-size: 56px; font-weight: 700; color: {ACCENT}; "
            "font-variant-numeric: tabular-nums; letter-spacing: -0.03em; background: transparent;"
        )
        self._rest_time_label.setParent(ring_wrap)
        self._rest_time_label.setGeometry(0, 55, 220, 70)

        self._rest_status = QLabel("休息中")
        self._rest_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rest_status.setStyleSheet(
            f"font-size: 14px; color: {REST_MUTED}; text-transform: uppercase; "
            "letter-spacing: 0.1em; background: transparent;"
        )
        self._rest_status.setParent(ring_wrap)
        self._rest_status.setGeometry(0, 125, 220, 25)

        ring_layout.addWidget(self._breath_ring)
        center.addWidget(ring_wrap, alignment=Qt.AlignmentFlag.AlignCenter)

        # 消息
        msg = QLabel("做得好，休息一下")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(
            f"font-size: 22px; font-weight: 600; color: {REST_FG}; letter-spacing: -0.01em;"
        )
        center.addWidget(msg)

        sub = QLabel("起身走动、喝水、看看窗外，让眼睛和身体都放松一下")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"font-size: 15px; color: {REST_MUTED}; max-width: 360px;")
        center.addWidget(sub)

        # 进度条
        self._progress_bar = self._create_progress_bar()
        center.addWidget(self._progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # 统计行
        self._stats_layout = QHBoxLayout()
        self._stats_layout.setSpacing(32)
        self._stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stat_rest_count = self._create_stat("0", "今日休息次数")
        self._stat_work_time = self._create_stat("0m", "今日工作时长")
        self._stat_rest_time = self._create_stat("0m", "今日休息时长")

        self._stats_layout.addWidget(self._stat_rest_count)
        self._stats_layout.addWidget(self._stat_work_time)
        self._stats_layout.addWidget(self._stat_rest_time)

        center.addLayout(self._stats_layout)

        root.addLayout(center, 1)

        # 底部提示
        hint = QLabel("休息结束后自动返回工作计时")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"font-size: 12px; color: {REST_MUTED}; opacity: 0.5; padding-bottom: 20px;")
        root.addWidget(hint)

    def _create_progress_bar(self):
        container = QWidget()
        container.setFixedWidth(320)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)

        bar_bg = QFrame()
        bar_bg.setFixedHeight(6)
        bar_bg.setStyleSheet(f"background-color: {REST_BORDER}; border-radius: 3px;")

        self._bar_fill = QFrame(bar_bg)
        self._bar_fill.setFixedHeight(6)
        self._bar_fill.setStyleSheet(f"background-color: {ACCENT}; border-radius: 3px;")
        self._bar_fill.setGeometry(0, 0, 0, 6)

        layout.addWidget(bar_bg)

        labels = QHBoxLayout()
        self._elapsed_label = QLabel("0:00")
        self._elapsed_label.setStyleSheet(
            f"font-size: 12px; color: {REST_MUTED}; font-variant-numeric: tabular-nums;"
        )
        self._total_label = QLabel("0:00")
        self._total_label.setStyleSheet(
            f"font-size: 12px; color: {REST_MUTED}; font-variant-numeric: tabular-nums;"
        )
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        labels.addWidget(self._elapsed_label)
        labels.addStretch()
        labels.addWidget(self._total_label)
        layout.addLayout(labels)

        return container

    def _create_stat(self, value, label):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        val = QLabel(value)
        val.setObjectName("stat-value")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {ACCENT}; "
            "font-variant-numeric: tabular-nums;"
        )
        layout.addWidget(val)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"font-size: 12px; color: {REST_MUTED};")
        layout.addWidget(lbl)

        w._val_label = val
        return w

    def showEvent(self, event):
        super().showEvent(event)
        if not self._is_shown:
            self._is_shown = True
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.geometry()
                self.setFixedSize(geom.width(), geom.height())
                self.move(geom.x(), geom.y())

            self.setWindowOpacity(0.0)
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
            self._fade_anim.setDuration(300)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_anim.start()

    def show_rest(self, rest_count=0, today_work_seconds=0, today_rest_seconds=0):
        if self._is_shown:
            return
        self._remaining = self._total_seconds
        self._rest_count = rest_count
        self._today_work_seconds = today_work_seconds
        self._today_rest_seconds = today_rest_seconds

        self._total_label.setText(fmt_mmss(self._total_seconds))
        self._update_stats()
        self.show()
        self.update_countdown(self._remaining)

    def update_countdown(self, seconds):
        self._remaining = max(0, seconds)
        self._rest_time_label.setText(fmt_mmss(self._remaining))

        elapsed = self._total_seconds - self._remaining
        self._elapsed_label.setText(fmt_mmss(elapsed))

        ratio = elapsed / self._total_seconds if self._total_seconds > 0 else 0
        bar_w = int(ratio * 320)
        self._bar_fill.setGeometry(0, 0, bar_w, 6)

    def _update_stats(self):
        self._stat_rest_count._val_label.setText(str(self._rest_count))

        wt = self._today_work_seconds
        wh, wm = wt // 3600, (wt % 3600) // 60
        self._stat_work_time._val_label.setText(f"{wh}h {wm}m" if wh > 0 else f"{wm}m")

        rt = self._today_rest_seconds + self._total_seconds
        rh, rm = rt // 3600, (rt % 3600) // 60
        self._stat_rest_time._val_label.setText(f"{rh}h {rm}m" if rh > 0 else f"{rm}m")

    def _on_end(self):
        self.destroy_rest()

    def destroy_rest(self):
        if self._is_shown:
            self._is_shown = False
            self.hide()
            if self._on_end_early:
                self._on_end_early()
