from detectors.base import BaseDetector
from detectors.keyboard_mouse import KeyboardMouseDetector
from detectors.camera import CameraDetector

DETECTORS = {
    "keyboard_mouse": KeyboardMouseDetector,
    "camera": CameraDetector,
}


def create_detectors(mode: str, camera_index: int = 0) -> list[BaseDetector]:
    if mode == "keyboard_mouse":
        return [KeyboardMouseDetector()]
    elif mode == "camera":
        return [CameraDetector(camera_index=camera_index)]
    elif mode == "both":
        return [KeyboardMouseDetector(), CameraDetector(camera_index=camera_index)]
    return [KeyboardMouseDetector()]
