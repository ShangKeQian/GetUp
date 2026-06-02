from unittest.mock import MagicMock
from overlay import OverlayWindow


def test_overlay_destroy_calls_callback():
    """destroy_overlay 应该调用回调"""
    mock_callback = MagicMock()
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay._is_shown = True
    overlay._on_close_callback = mock_callback
    overlay._countdown_label = MagicMock()
    overlay._ring = MagicMock()
    overlay.hide = MagicMock()  # Mock Qt method

    overlay.destroy_overlay()

    mock_callback.assert_called_once()


def test_overlay_update_countdown_clamps_negative():
    """update_countdown 应该 clamp 负数到 0"""
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay._is_shown = True
    overlay._total_seconds = 120
    overlay._remaining = 120
    overlay._countdown_label = MagicMock()
    overlay._ring = MagicMock()

    overlay.update_countdown(-1)

    assert overlay._remaining == 0
