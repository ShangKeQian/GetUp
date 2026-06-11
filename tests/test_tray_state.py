import sys
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)

from tray import SystemTray


def _make_tray():
    """创建一个 mock 的 SystemTray 实例"""
    with patch.object(SystemTray, '__init__', lambda self, *a, **kw: None):
        tray = SystemTray.__new__(SystemTray)
        tray._running = False
        tray._present = True
        tray._sleeping = False
        tray._work_elapsed = 0
        tray._break_remaining = 0
        tray._camera_active = False
        tray._config = MagicMock()
        tray._timer = MagicMock()
        tray._on_toggle = None
        tray._on_quit = None
        tray._on_settings = None
        tray.setIcon = MagicMock()
        tray.setToolTip = MagicMock()
        tray._build_menu = MagicMock()
        return tray


def test_update_sleeping_preserves_paused_state():
    tray = _make_tray()
    tray._running = False
    tray._sleeping = True

    tray.update_sleeping(False)

    assert tray._sleeping is False
    assert tray._running is False


def test_update_paused_resets_sleeping():
    tray = _make_tray()
    tray._sleeping = True

    tray.update_paused()

    assert tray._sleeping is False
    assert tray._present is True
