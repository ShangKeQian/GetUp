from unittest.mock import patch, MagicMock
from detectors.camera import CameraDetector


def test_check_once_returns_none_on_camera_failure():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = False
        mock_cap.return_value = mock_instance
        result = det.check_once()
        assert result is None


def test_check_once_returns_none_on_read_failure():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (False, None)
        mock_cap.return_value = mock_instance
        result = det.check_once()
        assert result is None


def test_check_once_returns_false_when_no_face():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap, \
         patch("detectors.camera.cv2.cvtColor") as mock_cvt, \
         patch("detectors.camera.mp.Image") as mock_image:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (True, MagicMock())
        mock_cap.return_value = mock_instance
        mock_cvt.return_value = MagicMock()
        mock_image.return_value = MagicMock()
        with patch.object(det._face_detector, "detect") as mock_detect:
            mock_detect.return_value = MagicMock(detections=[])
            result = det.check_once()
            assert result is False


def test_check_once_returns_true_when_face_detected():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap, \
         patch("detectors.camera.cv2.cvtColor") as mock_cvt, \
         patch("detectors.camera.mp.Image") as mock_image:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (True, MagicMock())
        mock_cap.return_value = mock_instance
        mock_cvt.return_value = MagicMock()
        mock_image.return_value = MagicMock()
        with patch.object(det._face_detector, "detect") as mock_detect:
            mock_detect.return_value = MagicMock(detections=[MagicMock()])
            result = det.check_once()
            assert result is True
