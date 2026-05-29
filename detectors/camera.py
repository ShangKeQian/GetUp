import os
from typing import Optional

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class CameraDetector:
    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        self._cap = None
        self._face_detector = None
        self._init_face_detector()

    def _init_face_detector(self):
        if self._face_detector is None:
            model_path = os.path.join(os.path.dirname(__file__), '..', 'blaze_face_short_range.tflite')
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceDetectorOptions(base_options=base_options)
            self._face_detector = vision.FaceDetector.create_from_options(options)

    def _ensure_open(self) -> bool:
        self._init_face_detector()
        if self._cap is not None and self._cap.isOpened():
            return True
        if self._cap is not None:
            self._cap.release()
        self._cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        return self._cap.isOpened()

    def check_once(self) -> Optional[bool]:
        if not self._ensure_open():
            return None
        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._face_detector.detect(mp_image)
        return len(result.detections) > 0

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def close(self):
        self.release()
        if self._face_detector is not None:
            self._face_detector.close()
            self._face_detector = None
