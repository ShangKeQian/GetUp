import numpy as np
from unittest.mock import patch, MagicMock
from detectors.camera import CameraDetector


def test_camera_init_does_not_open_camera():
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        det = CameraDetector(camera_index=0)
        mock_cap.assert_not_called()


def test_camera_lazy_open_on_first_check():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (False, None)
        mock_cap.return_value = mock_instance
        mock_cap.assert_not_called()
        det.check_once()
        mock_cap.assert_called_once()


def test_camera_reuses_instance_across_checks():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (False, None)
        mock_cap.return_value = mock_instance
        det.check_once()
        det.check_once()
        det.check_once()
        mock_cap.assert_called_once()


def test_camera_release():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (False, None)
        mock_cap.return_value = mock_instance
        det.check_once()
        det.release()
        mock_instance.release.assert_called_once()


def test_camera_reopens_after_release():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (False, None)
        mock_cap.return_value = mock_instance
        det.check_once()
        det.release()
        mock_instance.release.assert_called_once()
        det.check_once()
        assert mock_cap.call_count == 2


def test_old_camera_released_when_reopen_fails():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap, \
         patch("detectors.camera.cv2.cvtColor") as mock_cvt, \
         patch("detectors.camera.mp.Image"), \
         patch.object(det._face_detector, "detect") as mock_detect:
        mock_cvt.return_value = MagicMock()
        mock_detect.return_value = MagicMock(detections=[])
        good_cap = MagicMock()
        good_cap.isOpened.return_value = True
        good_cap.read.return_value = (True, MagicMock())
        mock_cap.return_value = good_cap
        det.check_once()

        good_cap.isOpened.return_value = False
        new_cap = MagicMock()
        new_cap.isOpened.return_value = True
        new_cap.read.return_value = (False, None)
        mock_cap.side_effect = [good_cap, new_cap]
        det.check_once()

        good_cap.release.assert_called_once()


def test_close_frees_face_detector():
    det = CameraDetector(camera_index=0)
    with patch.object(det._face_detector, "close") as mock_close:
        det.close()
        mock_close.assert_called_once()


def test_release_only_frees_camera():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (False, None)
        mock_cap.return_value = mock_instance
        det.check_once()
        assert det._cap is not None
        det.release()
        assert det._cap is None
        assert det._face_detector is not None


def test_check_once_works_after_release_and_reopen():
    det = CameraDetector(camera_index=0)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap, \
         patch("detectors.camera.cv2.cvtColor") as mock_cvt, \
         patch("detectors.camera.mp.Image"), \
         patch.object(det._face_detector, "detect") as mock_detect:
        mock_cvt.return_value = MagicMock()
        mock_detect.return_value = MagicMock(detections=[MagicMock()])

        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (True, MagicMock())
        mock_cap.return_value = mock_instance

        result1 = det.check_once()
        assert result1 is True

        det.release()

        mock_instance2 = MagicMock()
        mock_instance2.isOpened.return_value = True
        mock_instance2.read.return_value = (True, MagicMock())
        mock_cap.return_value = mock_instance2

        result2 = det.check_once()
        assert result2 is True
