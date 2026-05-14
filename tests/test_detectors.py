import time
from detectors.keyboard_mouse import KeyboardMouseDetector


def test_detector_starts_and_stops():
    det = KeyboardMouseDetector()
    det.start()
    assert det._running is True
    det.stop()
    assert det._running is False


def test_mark_activity_sets_timestamp():
    det = KeyboardMouseDetector()
    before = time.time()
    det.mark_activity()
    after = time.time()
    assert before <= det.last_activity <= after


def test_is_present_within_timeout():
    det = KeyboardMouseDetector()
    det.mark_activity()
    assert det.is_present(idle_timeout=120) is True


def test_is_present_after_timeout():
    det = KeyboardMouseDetector()
    det._last_activity = time.time() - 200
    assert det.is_present(idle_timeout=120) is False


import numpy as np
from unittest.mock import patch, MagicMock
from detectors.camera import CameraDetector


def test_camera_detector_no_camera():
    det = CameraDetector(camera_index=99)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = False
        mock_cap.return_value = mock_instance
        result = det.check_once()
        assert result is False
