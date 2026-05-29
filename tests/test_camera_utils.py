from unittest.mock import patch, MagicMock
from camera_utils import enumerate_cameras


def test_camera_released_on_exception():
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.side_effect = RuntimeError("camera error")

    with patch("camera_utils.cv2.VideoCapture", return_value=mock_cap):
        result = enumerate_cameras(max_index=1)

    assert result == []
    mock_cap.release.assert_called_once()


def test_camera_released_on_normal_path():
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.return_value = 640
    mock_cap.getBackendName.return_value = "DSHOW"

    with patch("camera_utils.cv2.VideoCapture", return_value=mock_cap):
        result = enumerate_cameras(max_index=1)

    assert len(result) == 1
    mock_cap.release.assert_called_once()
