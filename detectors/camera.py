import os
import time
import threading
import traceback
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class CameraDetector:
    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        self._cap = None
        self._frame = None
        self._ret = False
        self._running = False
        self._lock = threading.Lock()
        self._thread = None

        # 初始化 MediaPipe
        model_path = os.path.join(os.path.dirname(__file__), '..', 'blaze_face_short_range.tflite')
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceDetectorOptions(base_options=base_options)
        self._face_detector = vision.FaceDetector.create_from_options(options)

    def start(self):
        """启动后台摄像头线程"""
        if self._running:
            return

        # 指定 DSHOW 加速，锁死单帧缓冲
        self._cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # 读取首帧
        self._ret, self._frame = self._cap.read()

        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()

    def _update(self):
        """后台线程：持续抓图"""
        while self._running:
            try:
                ret, frame = self._cap.read()
                if ret:
                    with self._lock:
                        self._ret = ret
                        self._frame = frame
            except Exception:
                traceback.print_exc()
            time.sleep(0.1)
        if self._cap:
            self._cap.release()
            self._cap = None

    def check_once(self) -> bool:
        """从内存获取最新帧并检测"""
        if not self._running:
            return False

        with self._lock:
            if self._frame is None:
                return False
            frame = self._frame.copy()

        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._face_detector.detect(mp_image)
            return len(result.detections) > 0
        except Exception:
            traceback.print_exc()
            return False

    def stop(self):
        """停止后台线程（线程内部会释放摄像头）"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
