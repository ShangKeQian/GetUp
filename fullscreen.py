"""全屏前台窗口检测（Windows）。

判定标准：前台窗口无边框（无 WS_CAPTION）且矩形恰好铺满某台显示器，
即视为全屏（游戏/视频/演示场景）。命中时返回该显示器对应的 QScreen，
供迷你提醒卡片定位到正确的屏幕。

非 Windows 平台、检测失败或未全屏时一律返回 None，调用方回退到居中遮罩。
"""
import ctypes
from ctypes import wintypes
import sys

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QApplication

GWL_STYLE = -16
WS_CAPTION = 0x00C00000
MONITOR_DEFAULTTONEAREST = 2

# 桌面外壳窗口点击后会成为前台且铺满屏幕，需排除（避免误判全屏）
_SHELL_CLASSES = ("Progman", "WorkerW", "Shell_TrayWnd")


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


def _user32():
    return ctypes.windll.user32


def get_fullscreen_target():
    """前台窗口为全屏时返回其所在显示器（QScreen），否则返回 None。"""
    info = _get_fullscreen_monitor_info()
    if info is None:
        return None
    return _screen_for_monitor(info)


def _get_fullscreen_monitor_info():
    """返回全屏前台窗口所在显示器的 MONITORINFOEXW，非全屏返回 None。"""
    if sys.platform != "win32":
        return None
    try:
        user32 = _user32()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value in _SHELL_CLASSES:
            return None

        # 有标题栏的窗口不算全屏（排除铺满但带边框的最大化窗口）
        if user32.GetWindowLongW(hwnd, GWL_STYLE) & WS_CAPTION:
            return None

        win_rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(win_rect)):
            return None

        mon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if not mon:
            return None

        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if not user32.GetMonitorInfoW(mon, ctypes.byref(info)):
            return None

        m = info.rcMonitor
        if (win_rect.left, win_rect.top, win_rect.right, win_rect.bottom) != (
            m.left, m.top, m.right, m.bottom,
        ):
            return None
        return info
    except Exception:
        # 检测失败不应阻断正常提醒流程
        return None


def _screen_for_monitor(info):
    """将 Win32 显示器信息映射到 Qt 的 QScreen。

    优先按显示设备名（\\\\.\\DISPLAYx）精确匹配；
    失败时按物理像素（逻辑几何 × DPR）包含关系回退；最终回退主屏。
    """
    app = QApplication.instance()
    if app is None:
        return None
    for screen in app.screens():
        if screen.name() == info.szDevice:
            return screen

    m = info.rcMonitor
    center = QPoint((m.left + m.right) // 2, (m.top + m.bottom) // 2)
    for screen in app.screens():
        geo = screen.geometry()
        dpr = screen.devicePixelRatio()
        if dpr <= 0:
            dpr = 1.0
        phys = QRect(
            round(geo.x() * dpr), round(geo.y() * dpr),
            round(geo.width() * dpr), round(geo.height() * dpr),
        )
        if phys.contains(center):
            return screen
    return app.primaryScreen()
