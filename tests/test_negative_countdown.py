from unittest.mock import MagicMock
from overlay import OverlayWindow


def test_overlay_clamps_negative_seconds():
    """update_countdown 收到负数时应显示 00:00"""
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay._is_shown = True
    overlay._total_seconds = 120
    overlay._remaining = 120
    mock_label = MagicMock()
    overlay._countdown_label = mock_label
    mock_ring = MagicMock()
    overlay._ring = mock_ring

    overlay.update_countdown(-1)

    mock_label.setText.assert_called_once_with("00:00")
