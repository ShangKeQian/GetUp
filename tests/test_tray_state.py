from tray import SystemTray
from unittest.mock import MagicMock


def test_update_sleeping_preserves_paused_state():
    tray = SystemTray.__new__(SystemTray)
    mock_icon = MagicMock()
    tray._icon = mock_icon
    tray._running = False
    tray._present = True
    tray._sleeping = True

    tray.update_sleeping(False)

    assert tray._sleeping is False
    assert tray._running is False


def test_update_paused_resets_sleeping():
    tray = SystemTray.__new__(SystemTray)
    mock_icon = MagicMock()
    tray._icon = mock_icon
    tray._running = False
    tray._present = True
    tray._sleeping = True

    tray.update_paused()

    assert tray._sleeping is False
    assert tray._present is True
