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
