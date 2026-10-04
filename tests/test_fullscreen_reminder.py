"""全屏场景迷你提醒：检测、屏幕映射与 OverlayManager 路由。"""
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QRect

import fullscreen
import overlay
from overlay import MiniOverlayWindow, OverlayManager


# ── Win32 API 伪造 ──────────────────────────────────────

def _make_fake_user32(win_rect=(0, 0, 2560, 1440), mon_rect=None,
                      style=0, class_name="Diablo IV",
                      get_rect_ok=True, mon_info_ok=True, hwnd=123):
    """构造一个伪造的 user32，模拟全屏前台窗口场景。"""
    if mon_rect is None:
        mon_rect = win_rect

    def fake_get_class_name(h, buf, n):
        buf.value = class_name
        return len(class_name)

    def fake_get_window_rect(h, rect):
        if not get_rect_ok:
            return 0
        r = rect._obj
        r.left, r.top, r.right, r.bottom = win_rect
        return 1

    def fake_get_monitor_info(m, info):
        if not mon_info_ok:
            return 0
        obj = info._obj
        obj.rcMonitor.left, obj.rcMonitor.top = mon_rect[0], mon_rect[1]
        obj.rcMonitor.right, obj.rcMonitor.bottom = mon_rect[2], mon_rect[3]
        obj.szDevice = "\\\\.\\DISPLAY1"
        return 1

    fake = MagicMock()
    fake.GetForegroundWindow.return_value = hwnd
    fake.GetClassNameW.side_effect = fake_get_class_name
    fake.GetWindowLongW.return_value = style
    fake.GetWindowRect.side_effect = fake_get_window_rect
    fake.MonitorFromWindow.return_value = 7
    fake.GetMonitorInfoW.side_effect = fake_get_monitor_info
    return fake


def _make_fake_screen(name="\\\\.\\DISPLAY1", geom=QRect(0, 0, 1920, 1080), dpr=1.0):
    screen = MagicMock()
    screen.name.return_value = name
    screen.geometry.return_value = geom
    screen.devicePixelRatio.return_value = dpr
    return screen


# ── 全屏检测 ────────────────────────────────────────────

def test_fullscreen_window_detected():
    fake = _make_fake_user32()
    with patch.object(fullscreen, "_user32", return_value=fake):
        info = fullscreen._get_fullscreen_monitor_info()
    assert info is not None
    assert info.szDevice == "\\\\.\\DISPLAY1"


def test_bordered_window_not_fullscreen():
    fake = _make_fake_user32(style=0x00C00000)  # WS_CAPTION
    with patch.object(fullscreen, "_user32", return_value=fake):
        assert fullscreen._get_fullscreen_monitor_info() is None


def test_window_not_covering_monitor_not_fullscreen():
    # 窗口矩形小于显示器矩形（如带边框的准全屏或窗口化）
    fake = _make_fake_user32(win_rect=(0, 0, 2558, 1438), mon_rect=(0, 0, 2560, 1440))
    with patch.object(fullscreen, "_user32", return_value=fake):
        assert fullscreen._get_fullscreen_monitor_info() is None


def test_shell_class_not_fullscreen():
    fake = _make_fake_user32(class_name="Progman")
    with patch.object(fullscreen, "_user32", return_value=fake):
        assert fullscreen._get_fullscreen_monitor_info() is None


def test_get_window_rect_failure_not_fullscreen():
    fake = _make_fake_user32(get_rect_ok=False)
    with patch.object(fullscreen, "_user32", return_value=fake):
        assert fullscreen._get_fullscreen_monitor_info() is None


def test_no_foreground_window_not_fullscreen():
    fake = _make_fake_user32(hwnd=0)
    with patch.object(fullscreen, "_user32", return_value=fake):
        assert fullscreen._get_fullscreen_monitor_info() is None


def test_user32_exception_swallowed():
    fake = MagicMock()
    fake.GetForegroundWindow.side_effect = OSError("boom")
    with patch.object(fullscreen, "_user32", return_value=fake):
        assert fullscreen._get_fullscreen_monitor_info() is None


# ── 显示器 → QScreen 映射 ───────────────────────────────

def _fake_app(screens, primary=None):
    app = MagicMock()
    app.screens.return_value = screens
    app.primaryScreen.return_value = primary or screens[0]
    return app


def test_screen_matched_by_device_name():
    s1 = _make_fake_screen("\\\\.\\DISPLAY1")
    s2 = _make_fake_screen("\\\\.\\DISPLAY2")
    fake = _fake_app([s1, s2], primary=s1)
    info = MagicMock()
    info.szDevice = "\\\\.\\DISPLAY2"
    with patch.object(overlay.QApplication, "instance", return_value=fake):
        assert fullscreen._screen_for_monitor(info) is s2


def test_screen_matched_by_physical_rect_fallback():
    # 名称匹配失败 → 按物理像素（逻辑几何 × DPR）包含回退
    s1 = _make_fake_screen("unknown-name", geom=QRect(0, 0, 1280, 720), dpr=1.0)
    s2 = _make_fake_screen("unknown-name-2", geom=QRect(1280, 0, 1920, 1080), dpr=1.5)
    fake = _fake_app([s1, s2], primary=s1)
    info = MagicMock()
    info.szDevice = "\\\\.\\DISPLAY9"  # 无名称匹配
    info.rcMonitor.left, info.rcMonitor.top = 1400, 100  # 物理像素，落在副屏
    info.rcMonitor.right, info.rcMonitor.bottom = 2900, 900
    with patch.object(overlay.QApplication, "instance", return_value=fake):
        assert fullscreen._screen_for_monitor(info) is s2


def test_screen_fallback_to_primary():
    s1 = _make_fake_screen("\\\\.\\DISPLAY1", geom=QRect(0, 0, 1280, 720), dpr=2.0)
    fake = _fake_app([s1], primary=s1)
    info = MagicMock()
    info.szDevice = "\\\\.\\DISPLAY9"
    info.rcMonitor.left, info.rcMonitor.top = 9999, 9999
    info.rcMonitor.right, info.rcMonitor.bottom = 10000, 10000
    with patch.object(overlay.QApplication, "instance", return_value=fake):
        assert fullscreen._screen_for_monitor(info) is s1


# ── 迷你卡片 ────────────────────────────────────────────

def _make_mini(total=120):
    mini = MiniOverlayWindow.__new__(MiniOverlayWindow)
    mini._total_seconds = total
    mini._remaining = total
    mini._is_shown = False
    mini._target_screen = None
    mini._on_close_callback = None
    mini._countdown_label = MagicMock()
    mini.show = MagicMock()
    mini.hide = MagicMock()
    return mini


def test_mini_countdown_clamps_and_formats():
    mini = _make_mini()
    mini.update_countdown(-5)
    assert mini._remaining == 0
    mini._countdown_label.setText.assert_called_with("00:00")
    mini.update_countdown(65)
    mini._countdown_label.setText.assert_called_with("01:05")


def test_mini_show_overlay_resets_remaining():
    mini = _make_mini(total=120)
    mini.update_countdown(5)
    mini._countdown_label.reset_mock()
    mini.show_overlay()
    assert mini._remaining == 120
    assert mini._target_screen is None
    mini.show.assert_called_once()
    mini._countdown_label.setText.assert_called_with("02:00")


def test_mini_destroy_calls_callback_once():
    mini = _make_mini()
    mini._is_shown = True
    callback = MagicMock()
    mini._on_close_callback = callback
    mini.destroy_overlay()
    assert not mini._is_shown
    callback.assert_called_once()
    # 幂等：再次销毁不重复触发回调
    mini.destroy_overlay()
    callback.assert_called_once()


def test_mini_position_uses_target_screen():
    mini = _make_mini()
    mini.move = MagicMock()
    mini.width = MagicMock(return_value=300)
    target = _make_fake_screen(geom=QRect(1280, 0, 1920, 1080))
    mini._target_screen = target
    with patch.object(overlay.QApplication, "primaryScreen", return_value=None):
        mini._position_on_screen()
    mini.move.assert_called_once_with(1280 + 1920 - 300 - 24, 24)


def test_mini_position_fallback_to_primary_screen():
    mini = _make_mini()
    mini.move = MagicMock()
    mini.width = MagicMock(return_value=300)
    primary = _make_fake_screen(geom=QRect(0, 0, 2560, 1440))
    mini._target_screen = None
    with patch.object(overlay.QApplication, "primaryScreen", return_value=primary):
        mini._position_on_screen()
    mini.move.assert_called_once_with(2560 - 300 - 24, 24)


# ── OverlayManager 路由 ─────────────────────────────────

def _make_manager(full_shown=False, mini_shown=False):
    mgr = OverlayManager.__new__(OverlayManager)
    mgr._full = MagicMock()
    mgr._mini = MagicMock()
    mgr._full._is_shown = full_shown
    mgr._mini._is_shown = mini_shown
    return mgr


def test_routes_to_mini_when_fullscreen():
    mgr = _make_manager()
    screen = MagicMock()
    with patch.object(overlay, "get_fullscreen_target", return_value=screen):
        mgr.show_overlay()
    mgr._mini.show_overlay.assert_called_once_with(screen)
    mgr._full.show_overlay.assert_not_called()


def test_routes_to_full_when_not_fullscreen():
    mgr = _make_manager()
    with patch.object(overlay, "get_fullscreen_target", return_value=None):
        mgr.show_overlay()
    mgr._full.show_overlay.assert_called_once_with()
    mgr._mini.show_overlay.assert_not_called()


def test_no_double_show_when_already_active():
    mgr = _make_manager(full_shown=True)
    with patch.object(overlay, "get_fullscreen_target", return_value=MagicMock()):
        mgr.show_overlay()
    mgr._mini.show_overlay.assert_not_called()
    mgr._full.show_overlay.assert_not_called()


def test_countdown_routed_to_active_mini():
    mgr = _make_manager(mini_shown=True)
    mgr.update_countdown(42)
    mgr._mini.update_countdown.assert_called_once_with(42)
    mgr._full.update_countdown.assert_not_called()


def test_countdown_routed_to_active_full():
    mgr = _make_manager(full_shown=True)
    mgr.update_countdown(42)
    mgr._full.update_countdown.assert_called_once_with(42)
    mgr._mini.update_countdown.assert_not_called()


def test_destroy_routed_to_active():
    mgr = _make_manager(mini_shown=True)
    mgr.destroy_overlay()
    mgr._mini.destroy_overlay.assert_called_once_with()
    mgr._full.destroy_overlay.assert_not_called()


def test_noop_when_nothing_shown():
    mgr = _make_manager()
    mgr.update_countdown(42)
    mgr.destroy_overlay()
    mgr._full.update_countdown.assert_not_called()
    mgr._mini.update_countdown.assert_not_called()
