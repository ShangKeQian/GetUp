import time
import threading
import numpy as np
import cv2
from detectors.base import BaseDetector


class CameraDetector(BaseDetector):
    def __init__(self, camera_index: int = 0, check_interval: float = 5.0,
                 learning_rate: float = 0.01, min_area: int = 5000):
        super().__init__()
        self._camera_index = camera_index
        self._check_interval = check_interval
        self._learning_rate = learning_rate
        self._min_area = min_area
        self._running = False
        self._thread = None

    def _capture_loop(self):
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self._running = False
            return
        try:
            bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=False
            )
            time.sleep(2)
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(self._check_interval)
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)
                fg_mask = bg_subtractor.apply(gray, learningRate=self._learning_rate)
                contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                person_detected = any(
                    cv2.contourArea(c) > self._min_area for c in contours
                )
                if person_detected:
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
