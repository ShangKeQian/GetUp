import os
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class CameraDetector:
    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        model_path = os.path.join(os.path.dirname(__file__), '..', 'blaze_face_short_range.tflite')
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceDetectorOptions(base_options=base_options)
        self._face_detector = vision.FaceDetector.create_from_options(options)

    def check_once(self) -> bool:
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            return False
        try:
            ret, frame = cap.read()
            if not ret:
                return False
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._face_detector.detect(mp_image)
            return len(result.detections) > 0
        finally:
            cap.release()

    def start(self):
        pass

    def stop(self):
        pass
