import os
import threading
from typing import Optional


_heavy_loaded = False


def _ensure_heavy_loaded():
    """按需加载重库 cv2 / mediapipe 并绑定到模块全局。

    这两个库导入合计约 2.4s + 57MB 常驻，若在模块顶层导入会在应用启动（含开机
    自启）时立即加载。改为首次摄像头检测时才加载，把开销推迟到用户空闲 5s+ 后。
    函数内的 LOAD_GLOBAL 不会触发模块 __getattr__，故需在此显式加载并写入 globals。
    """
    global _heavy_loaded
    if _heavy_loaded:
        return
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    g = globals()
    g["cv2"] = cv2
    g["mp"] = mp
    g["python"] = python
    g["vision"] = vision
    _heavy_loaded = True


def __getattr__(name):
    """外部访问 detectors.camera.cv2 / .mp 等（如 mock.patch）时按需加载。"""
    if name in ("cv2", "mp", "python", "vision"):
        _ensure_heavy_loaded()
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class CameraDetector:
    def __init__(self, camera_index: int = 0):
        self._camera_index = camera_index
        self._cap = None
        self._face_detector = None
        self._lock = threading.Lock()
        self._read_failures = 0
        self._closed = False
        # 不在此加载模型：延迟到首次 _ensure_open()，避免开机自启时加载 mediapipe/模型

    def _init_face_detector(self):
        _ensure_heavy_loaded()
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
