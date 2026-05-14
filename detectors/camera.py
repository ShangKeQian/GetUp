import time
import threading
import os
import numpy as np
import cv2
from detectors.base import BaseDetector


class CameraDetector(BaseDetector):
    def __init__(self, camera_index: int = 0, check_interval: float = 3.0,
                 scale_factor: float = 1.1, min_neighbors: int = 5):
        super().__init__()
        self._camera_index = camera_index
        self._check_interval = check_interval
        self._scale_factor = scale_factor
        self._min_neighbors = min_neighbors
        self._running = False
        self._thread = None
        self._face_cascade = None

    def _load_cascade(self) -> bool:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if not os.path.exists(cascade_path):
            return False
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        return not self._face_cascade.empty()

    def _capture_loop(self):
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self._running = False
            return
        try:
            if not self._load_cascade():
                self._running = False
                return
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(self._check_interval)
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self._face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=self._scale_factor,
                    minNeighbors=self._min_neighbors,
                    minSize=(60, 60)
                )
                if len(faces) > 0:
                    self.mark_activity()
                time.sleep(self._check_interval)
        finally:
            cap.release()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
