from unittest.mock import MagicMock
from overlay import OverlayWindow


def test_overlay_clamps_negative_seconds():
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay._window = True
    mock_label = MagicMock()
    overlay._countdown_label = mock_label

    overlay.update_countdown(-1)

    mock_label.config.assert_called_once_with(text="00:00")
