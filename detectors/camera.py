import time
import threading
import os
import numpy as np
import cv2
from detectors.base import BaseDetector


class CameraDetector(BaseDetector):
    def __init__(self, camera_index: int = 0, check_interval: float = 3.0,
                 scale_factor: float = 1.1, min_neighbors: int = 3):
        super().__init__()
        self._camera_index = camera_index
        self._check_interval = check_interval
        self._scale_factor = scale_factor
        self._min_neighbors = min_neighbors
        self._running = False
        self._thread = None
        self._face_cascade = None
        self._save_dir = os.path.join(os.getcwd(), "camera_debug")
        os.makedirs(self._save_dir, exist_ok=True)

    def _load_cascade(self) -> bool:
        frontal_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
        self._cascades = []
        if os.path.exists(frontal_path):
            c = cv2.CascadeClassifier(frontal_path)
            if not c.empty():
                self._cascades.append(c)
        if os.path.exists(profile_path):
            c = cv2.CascadeClassifier(profile_path)
            if not c.empty():
                self._cascades.append(c)
        return len(self._cascades) > 0

    def _capture_loop(self):
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self._running = False
            return
        try:
            if not self._load_cascade():
                self._running = False
                return
            frame_count = 0
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(self._check_interval)
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                all_faces = []
                for cascade in self._cascades:
                    faces = cascade.detectMultiScale(
                        gray,
                        scaleFactor=self._scale_factor,
                        minNeighbors=self._min_neighbors,
                        minSize=(30, 30)
                    )
                    all_faces.extend(faces)
                faces = []
                for f in all_faces:
                    x, y, w, h = f
                    cx, cy = x + w//2, y + h//2
                    overlap = False
                    for fx, fy, fw, fh in faces:
                        fcx, fcy = fx + fw//2, fy + fh//2
                        if abs(cx - fcx) < 50 and abs(cy - fcy) < 50:
                            overlap = True
                            break
                    if not overlap:
                        faces.append(f)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                save_path = os.path.join(self._save_dir, f"frame_{frame_count:04d}.jpg")
                cv2.imwrite(save_path, frame)
                frame_count += 1
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
