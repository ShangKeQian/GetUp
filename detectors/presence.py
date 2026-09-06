import time
import threading
import pynput
from detectors.camera import CameraDetector


class PresenceDetector:
    # 摄像头检测节流间隔（秒）
    _CHECK_INTERVAL = 5
    # 摄像头打开失败后的退避参数（秒）：30 → 60 → 120 封顶
    _BACKOFF_BASE = 30
    _BACKOFF_MAX = 120

    def __init__(self, camera_index=0, sleep_timeout_minutes=15):
        self._camera = CameraDetector(camera_index=camera_index)
        self._sleep_timeout_seconds = sleep_timeout_minutes * 60
        self._lock = threading.Lock()

        self._last_input_time = time.monotonic()
        self._last_camera_found_time = time.monotonic()
        self._last_camera_check_time = 0.0
        self._sleeping = False
        self._idle_start_time = None
        self._is_present = False
        # 摄像头连续失败计数与退避截止时间（P1：避免被占用时每 5s 重试阻塞 tick 线程）
        self._consecutive_failures = 0
        self._camera_backoff_until = 0.0

        self._mouse_listener = None
        self._keyboard_listener = None
        self._closed = False

    def start(self):
        def on_input(*args):
            self._last_input_time = time.monotonic()

        self._mouse_listener = pynput.mouse.Listener(on_move=on_input, on_click=on_input)
        self._keyboard_listener = pynput.keyboard.Listener(on_press=on_input, on_release=on_input)
        self._mouse_listener.daemon = True
        self._keyboard_listener.daemon = True
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def tick(self):
        now = time.monotonic()

        # Phase 1：锁内判定是否需要摄像头检测。
        # check_once 不再持锁，避免摄像头打开（1.5-2.5s）阻塞 wake()/is_sleeping（P1）。
        with self._lock:
            if self._closed:
                return False
            idle_time = now - self._last_input_time

            if self._sleeping:
                if idle_time < 5:
                    self._sleeping = False
                    self._idle_start_time = None
                    self._last_camera_found_time = now
                    self._last_camera_check_time = now
                    self._is_present = True
                    return True
                self._is_present = False
                return False

            camera_idle = now - self._last_camera_found_time
            need_camera = False
            cached_present = False
            if idle_time < 5 or camera_idle < 5:
                cached_present = True
            elif (now - self._last_camera_check_time >= self._CHECK_INTERVAL
                  and now >= self._camera_backoff_until):
                self._last_camera_check_time = now
                need_camera = True

        # Phase 2：锁外执行摄像头检测（打开/读帧可达数百毫秒至数秒）
        camera_result = None
        if need_camera:
            camera_result = self._camera.check_once()

        # Phase 3：锁内应用检测结果并更新在位/休眠状态
        with self._lock:
            if self._closed:
                return False
            now = time.monotonic()
            if need_camera:
                if camera_result is True:
                    person_present = True
                    self._last_camera_found_time = now
                    self._consecutive_failures = 0
                    self._camera_backoff_until = 0.0
                elif camera_result is False:
                    person_present = False
                    self._last_camera_found_time = 0
                    self._consecutive_failures = 0
                    self._camera_backoff_until = 0.0
                else:  # None：摄像头错误/被占用，指数退避避免每 5s 重试阻塞
                    person_present = False
                    self._consecutive_failures += 1
                    backoff = min(
                        self._BACKOFF_MAX,
                        self._BACKOFF_BASE * (2 ** (self._consecutive_failures - 1)),
                    )
                    self._camera_backoff_until = now + backoff
            else:
                person_present = cached_present

            if person_present:
                self._idle_start_time = None
            elif self._idle_start_time is None:
                self._idle_start_time = now
            elif now - self._idle_start_time >= self._sleep_timeout_seconds:
                self._sleeping = True
                self._idle_start_time = None
                self._camera.release()

            self._is_present = person_present
            return person_present

    @property
    def is_sleeping(self):
        with self._lock:
            return self._sleeping

    def wake(self):
        with self._lock:
            self._sleeping = False
            self._idle_start_time = None

    def close(self):
        """关闭检测器。先在锁内标记 _closed，阻止 tick 继续使用；锁外停止监听器。"""
        with self._lock:
            if self._closed:
                return
            self._closed = True
        # 锁外停止监听器（stop 可能阻塞）
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        self._camera.close()
