import os
import threading
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
        self._lock = threading.Lock()
        self._read_failures = 0
        self._closed = False
        self._init_face_detector()

    def _init_face_detector(self):
        if self._face_detector is None and not self._closed:
            model_path = os.path.join(os.path.dirname(__file__), '..', 'blaze_face_short_range.tflite')
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceDetectorOptions(base_options=base_options)
            self._face_detector = vision.FaceDetector.create_from_options(options)

    def _ensure_open(self) -> bool:
        if self._closed:
            return False
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
        with self._lock:
            if not self._ensure_open():
                return None
            ret, frame = self._cap.read()
            if not ret or frame is None:
                # 连续读取失败时释放摄像头，下次 check_once 会重新打开
                self._read_failures += 1
                if self._read_failures >= 3:
                    self._cap.release()
                    self._cap = None
                    self._read_failures = 0
                return None
            self._read_failures = 0
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._face_detector.detect(mp_image)
            return len(result.detections) > 0

    def release(self):
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def close(self):
        """终态关闭：释放摄像头和人脸检测器，阻止后续复活。"""
        with self._lock:
            self._closed = True
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            if self._face_detector is not None:
                self._face_detector.close()
                self._face_detector = None
