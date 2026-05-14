import time
import threading
import numpy as np
import cv2
from detectors.base import BaseDetector


class CameraDetector(BaseDetector):
    def __init__(self, camera_index: int = 0, check_interval: float = 5.0, threshold: int = 5000):
        super().__init__()
        self._camera_index = camera_index
        self._check_interval = check_interval
        self._threshold = threshold
        self._running = False
        self._thread = None
        self._prev_frame = None

    def _frames_differ(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        diff = cv2.absdiff(frame1, frame2)
        return int(np.sum(diff)) > self._threshold

    def _capture_loop(self):
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self._running = False
            return
        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(self._check_interval)
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if self._prev_frame is not None:
                    if self._frames_differ(self._prev_frame, gray):
                        self.mark_activity()
                self._prev_frame = gray
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
