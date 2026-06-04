from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
from PySide6.QtCore import Qt, QPointF
from config import Config
from theme import STATUS_PRESENT, STATUS_ABSENT, STATUS_PAUSED, STATUS_SLEEPING, SURFACE, BORDER, FG, MUTED, fmt_mmss


def _draw_person_icon(painter, cx, cy, scale):
    """绘制单人图标（头部圆 + 身体弧线）"""
    pen = QPen(QColor("white"), 2.0 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
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
    pen = QPen(QColor("white"), 2.0 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
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
    pen = QPen(QColor("white"), 2.0 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(QColor("white"))
    bar_w = 3.5 * scale
    bar_h = 14 * scale
    gap = 4 * scale
    painter.drawRoundedRect(cx - gap - bar_w, cy - bar_h / 2, bar_w, bar_h, 1.5 * scale, 1.5 * scale)
    painter.drawRoundedRect(cx + gap, cy - bar_h / 2, bar_w, bar_h, 1.5 * scale, 1.5 * scale)


def _draw_moon_icon(painter, cx, cy, scale):
    """绘制月亮图标"""
    pen = QPen(QColor("white"), 2.0 * scale)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    r = 10 * scale
    path.arcTo(cx - r, cy - r, r * 2, r * 2, 130, 280)
    path.arcTo(cx - r * 0.5, cy - r * 0.55, r * 1.2, r * 1.2, 30, -280)
    path.closeSubpath()
    painter.drawPath(path)


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

    # 背景圆
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(fill))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # 绘制状态图标
    cx = cy = size / 2
    scale = size / 64.0

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
    def __init__(self, config: Config, on_toggle=None, on_quit=None, on_settings=None, on_wake=None, parent=None):
        super().__init__(parent)
        self._config = config
        self._on_toggle = on_toggle
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._on_wake = on_wake
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

        # 工作/离开时间
        if self._running and not self._sleeping:
            if self._present:
                work_str = fmt_mmss(self._work_elapsed)
                work_item = menu.addAction(f"⏱  已工作 {work_str}")
                work_item.setEnabled(False)

                remaining = max(0, self._config.work_minutes * 60 - self._work_elapsed)
                next_str = fmt_mmss(remaining)
                next_item = menu.addAction(f"📅  下次休息: {next_str}")
                next_item.setEnabled(False)
            else:
                away_item = menu.addAction("⏱  无人状态")
                away_item.setEnabled(False)
        elif self._sleeping:
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
        pixmap = create_icon_pixmap(
            present=self._present,
            paused=not self._running,
            sleeping=self._sleeping
        )
        self.setIcon(QIcon(pixmap))

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
        self._update_icon()


