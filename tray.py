from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath, QLinearGradient,
)
from PySide6.QtCore import Qt, QPointF, QRectF
from config import Config
from timer import TimerEngine, State as TimerState
from theme import STATUS_PRESENT, STATUS_ABSENT, STATUS_PAUSED, STATUS_SLEEPING, SURFACE, BORDER, FG, MUTED, fmt_mmss


# 白色图形描边线宽下限（设备像素）：16px 托盘图标下 2.0*scale 只有 0.5px，会糊成一团
_MIN_STROKE = 1.2


def _glyph_pen(scale, width=2.0):
    """状态图形统一的白色描边笔（含小尺寸线宽下限）"""
    pen = QPen(QColor("white"), max(width * scale, _MIN_STROKE))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw_person_icon(painter, cx, cy, scale):
    """绘制单人图标（头部圆 + 身体弧线）"""
    painter.setPen(_glyph_pen(scale))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    # 头部
    painter.drawEllipse(QPointF(cx, cy - 6 * scale), 4 * scale, 4 * scale)
    # 身体
    path = QPainterPath()
    path.moveTo(cx + 8 * scale, cy + 8 * scale)
    path.lineTo(cx + 8 * scale, cy + 5 * scale)
    path.arcTo(cx - 8 * scale, cy - 2 * scale, 16 * scale, 14 * scale, 0, 180)
    painter.drawPath(path)


def _draw_two_people_icon(painter, cx, cy, scale):
    """绘制双人图标"""
    painter.setPen(_glyph_pen(scale))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    # 左人头部
    painter.drawEllipse(QPointF(cx - 4 * scale, cy - 6 * scale), 3.5 * scale, 3.5 * scale)
    # 左人身体
    path1 = QPainterPath()
    path1.moveTo(cx + 4 * scale, cy + 8 * scale)
    path1.lineTo(cx + 4 * scale, cy + 5 * scale)
    path1.arcTo(cx - 11 * scale, cy - 2 * scale, 15 * scale, 13 * scale, 0, 180)
    painter.drawPath(path1)
    # 右人头部
    painter.drawEllipse(QPointF(cx + 7 * scale, cy - 4 * scale), 3 * scale, 3 * scale)
    # 右人身体
    path2 = QPainterPath()
    path2.moveTo(cx + 13 * scale, cy + 8 * scale)
    path2.arcTo(cx + 1 * scale, cy, 12 * scale, 11 * scale, 0, 180)
    painter.drawPath(path2)


def _draw_pause_icon(painter, cx, cy, scale):
    """绘制暂停图标（双竖条）"""
    painter.setPen(_glyph_pen(scale))
    painter.setBrush(QColor("white"))
    bar_w = max(3.5 * scale, 2.0)
    bar_h = max(14 * scale, 7.0)
    gap = max(4 * scale, 1.5)
    radius = min(1.5 * scale, bar_w / 2)
    painter.drawRoundedRect(cx - gap - bar_w, cy - bar_h / 2, bar_w, bar_h, radius, radius)
    painter.drawRoundedRect(cx + gap, cy - bar_h / 2, bar_w, bar_h, radius, radius)


def _draw_moon_icon(painter, cx, cy, scale):
    """绘制月亮图标"""
    painter.setPen(_glyph_pen(scale))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    r = 10 * scale
    # 用 arcMoveTo 起笔：空路径直接 arcTo 会从 (0,0) 拉出一条杂线
    path.arcMoveTo(cx - r, cy - r, r * 2, r * 2, 130)
    path.arcTo(cx - r, cy - r, r * 2, r * 2, 130, 280)
    path.arcTo(cx - r * 0.5, cy - r * 0.55, r * 1.2, r * 1.2, 30, -280)
    path.closeSubpath()
    painter.drawPath(path)


def _draw_rising_person_icon(painter, cx, cy, scale):
    """绘制“起身”品牌图形（人形 + 向上箭头）"""
    painter.setPen(_glyph_pen(scale, 2.6))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # 人形（头 + 肩），偏左下
    px = cx - 7 * scale
    painter.drawEllipse(QPointF(px, cy - 3 * scale), 5.0 * scale, 5.0 * scale)
    body = QPainterPath()
    body.moveTo(px + 10 * scale, cy + 16 * scale)
    body.lineTo(px + 10 * scale, cy + 11 * scale)
    body.arcTo(px - 10 * scale, cy + 2 * scale, 20 * scale, 18 * scale, 0, 180)
    painter.drawPath(body)

    # 向上箭头，偏右上
    ax = cx + 11 * scale
    painter.drawLine(QPointF(ax, cy + 16 * scale), QPointF(ax, cy - 14 * scale))
    head = QPainterPath()
    head.moveTo(ax - 7 * scale, cy - 7 * scale)
    head.lineTo(ax, cy - 14 * scale)
    head.lineTo(ax + 7 * scale, cy - 7 * scale)
    painter.drawPath(head)


# 品牌图标导出尺寸（QIcon 与 .ico 共用）
APP_ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)

# 托盘图标渲染尺寸（覆盖 100%~300% DPI 下通知区域的实际取值）
TRAY_ICON_SIZES = (16, 20, 24, 32, 48, 64)


def create_app_icon_pixmap(size=256):
    """创建品牌图标：Fluent 圆角方形 + 蓝色渐变 + 起身图形

    32px 以下退化为单个人形：人形 + 箭头两个元素在 16/24px 会糊在一起。
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    inset = size * 0.05
    side = size - 2 * inset
    rect = QRectF(inset, inset, side, side)

    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#60a5fa"))
    gradient.setColorAt(1.0, QColor("#2563eb"))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawRoundedRect(rect, side * 0.22, side * 0.22)

    cx = cy = size / 2
    if size < 32:
        _draw_person_icon(painter, cx, cy, size / 64.0 * 1.5)
    else:
        _draw_rising_person_icon(painter, cx, cy, size / 64.0)
    painter.end()
    return pixmap


def create_app_icon():
    """创建多尺寸品牌 QIcon（窗口/任务栏用它，避免缩放发虚）"""
    icon = QIcon()
    for size in APP_ICON_SIZES:
        icon.addPixmap(create_app_icon_pixmap(size))
    return icon


def create_icon_pixmap(present=True, paused=False, sleeping=False, size=64):
    """创建状态图标（彩色圆 + 白色图形）"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if sleeping:
        fill = QColor(STATUS_SLEEPING)
    elif paused:
        fill = QColor(STATUS_PAUSED)
    elif present:
        fill = QColor(STATUS_PRESENT)
    else:
        fill = QColor(STATUS_ABSENT)

    # 背景圆（内缩按比例，保证 16px 图标圆面也够大）
    inset = size * 0.0625
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(fill))
    painter.drawEllipse(QRectF(inset, inset, size - 2 * inset, size - 2 * inset))

    # 绘制状态图标（小尺寸轻微放大图形，抵消像素级细节丢失）
    cx = cy = size / 2
    scale = size / 64.0 * (1.15 if size <= 24 else 1.0)

    if sleeping:
        _draw_moon_icon(painter, cx, cy, scale)
    elif paused:
        _draw_pause_icon(painter, cx, cy, scale)
    elif present:
        _draw_person_icon(painter, cx, cy, scale)
    else:
        _draw_two_people_icon(painter, cx, cy, scale)

    painter.end()
    return pixmap


class SystemTray(QSystemTrayIcon):
    def __init__(self, config: Config, timer: TimerEngine, on_toggle=None, on_quit=None, on_settings=None, on_wake=None, on_manual_break=None, parent=None):
        super().__init__(parent)
        self._config = config
        self._timer = timer
        self._on_toggle = on_toggle
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._on_wake = on_wake
        self._on_manual_break_cb = on_manual_break
        self._running = False
        self._present = True
        self._sleeping = False
        self._work_elapsed = 0
        self._remaining = 0

        self._update_icon()
        self._build_menu()
        if self._on_settings:
            self.activated.connect(self._on_activated)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {SURFACE};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 4px 0;
                font-family: "Segoe UI", "Microsoft YaHei";
                font-size: 14px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                color: {FG};
            }}
            QMenu::item:selected {{
                background-color: #f3f4f6;
            }}
            QMenu::item:disabled {{
                color: {MUTED};
            }}
            QMenu::separator {{
                height: 1px;
                background: {BORDER};
                margin: 4px 0;
            }}
        """)

        # 标题头
        state_text, _ = self._get_state_info()
        header = menu.addAction(f"● GetUp · {state_text}")
        header.setEnabled(False)
        menu.addSeparator()

        if self._sleeping:
            sleep_item = menu.addAction("🌙  智能休眠中")
            sleep_item.setEnabled(False)
        elif not self._running:
            pause_item = menu.addAction("⏸  监控已暂停")
            pause_item.setEnabled(False)

        menu.addSeparator()

        # 检测状态
        detect_text = "开启" if self._running else "关闭"
        detect_item = menu.addAction(f"🛡  在位检测: {detect_text}")
        detect_item.setEnabled(False)

        cam_text = "已释放" if self._sleeping else ("运行中" if self._running else "待机")
        cam_item = menu.addAction(f"📷  摄像头: {cam_text}")
        cam_item.setEnabled(False)

        menu.addSeparator()

        # 操作
        # 立即休息：操作区第一位（仅在非休眠、非暂停时启用）
        break_action = menu.addAction("🧘  立即休息")
        break_action.setEnabled(self._running and not self._sleeping and self._timer.state == TimerState.TIMING)
        if self._on_manual_break_cb:
            break_action.triggered.connect(self._on_manual_break_cb)

        if self._sleeping:
            wake_action = menu.addAction("▶  唤醒")
            if self._on_wake:
                wake_action.triggered.connect(self._on_wake)
        elif self._running:
            toggle_action = menu.addAction("⏸  暂停监控")
            if self._on_toggle:
                toggle_action.triggered.connect(self._on_toggle)
        else:
            toggle_action = menu.addAction("▶  恢复监控")
            if self._on_toggle:
                toggle_action.triggered.connect(self._on_toggle)

        if self._on_settings:
            settings_action = menu.addAction("⚙  设置")
            settings_action.triggered.connect(self._on_settings)

        menu.addSeparator()

        quit_action = menu.addAction("⏻  退出 GetUp")
        if self._on_quit:
            quit_action.triggered.connect(self._on_quit)

        self.setContextMenu(menu)

    def _get_state_info(self):
        if self._sleeping:
            return "休眠", STATUS_SLEEPING
        elif not self._running:
            return "已暂停", STATUS_PAUSED
        elif self._present:
            return "工作中", STATUS_PRESENT
        else:
            return "无人", STATUS_ABSENT

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self._on_settings:
                self._on_settings()

    def _update_icon(self):
        # 逐尺寸渲染：只给 QIcon 一张 64px 位图的话，托盘缩放到 16px 会发虚
        icon = QIcon()
        for size in TRAY_ICON_SIZES:
            icon.addPixmap(create_icon_pixmap(
                present=self._present,
                paused=not self._running,
                sleeping=self._sleeping,
                size=size,
            ))
        self.setIcon(icon)
        self._update_tooltip()

    def _update_tooltip(self):
        state_text, _ = self._get_state_info()
        if self._running and not self._sleeping:
            if self._present:
                remaining_str = fmt_mmss(self._remaining)
                self.setToolTip(f"GetUp · {state_text}\n下次休息: {remaining_str}")
            else:
                self.setToolTip(f"GetUp · {state_text}")
        else:
            self.setToolTip(f"GetUp · {state_text}")

    def update_presence(self, present):
        self._present = present
        self._update_icon()
        self._build_menu()

    def update_paused(self):
        self._present = True
        self._sleeping = False
        self._update_icon()
        self._build_menu()

    def update_sleeping(self, sleeping):
        self._sleeping = sleeping
        self._update_icon()
        self._build_menu()

    def update_running(self, running):
        self._running = running
        self._build_menu()
        self._update_icon()

    def update_work_elapsed(self, seconds, remaining=0):
        self._work_elapsed = seconds
        self._remaining = remaining
        # 仅更新 tooltip，不重建图标像素图（避免每秒 QPainter 开销）
        self._update_tooltip()

    def set_timer(self, timer):
        """替换内部 timer 引用（封装私有属性访问）"""
        self._timer = timer
        self._build_menu()
        self._update_icon()

