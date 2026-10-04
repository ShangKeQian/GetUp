"""在位检测融合：键鼠空闲轮询 + 摄像头人脸检测 + 休眠超时。

空闲时长用 Win32 ``GetLastInputInfo()`` 轮询，而不是全局键鼠监听器：
GetUp 只需要"最近有无输入"这一个语义，轮询即可覆盖键盘、鼠标移动与点击。
旧实现用 pynput 安装 ``WH_KEYBOARD_LL`` 全局低级键盘钩子——那是键记录器的
特征 API，会显著抬高安全软件（Defender / SmartScreen 启发式）的误报面，
且引入一个可避免的第三方依赖。
"""
import ctypes
import sys
import threading
import time
from ctypes import wintypes

from detectors.camera import CameraDetector


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


if sys.platform == "win32":
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _user32.GetLastInputInfo.argtypes = (ctypes.POINTER(_LASTINPUTINFO),)
    _user32.GetLastInputInfo.restype = wintypes.BOOL
    # GetTickCount64 返回 ULONGLONG，必须显式声明，否则 ctypes 默认按 c_int 截断
    _kernel32.GetTickCount64.argtypes = ()
    _kernel32.GetTickCount64.restype = ctypes.c_ulonglong
else:  # pragma: no cover - 非 Windows 平台不做输入检测
    _user32 = None
    _kernel32 = None


def get_idle_seconds() -> float:
    """返回距上一次键鼠输入经过的秒数。

    非 Windows 平台或调用失败时返回 0.0（视作"刚有输入"，与旧实现的初始值一致）。
    """
    if _user32 is None:
        return 0.0
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    try:
        if not _user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        # dwTime 是 64 位 tick 的低 32 位。差值对 2**32 取模即为真实空闲毫秒
        # （只要真实空闲不超过 49.7 天），这样无需单独处理 32 位计数回绕。
        delta = (_kernel32.GetTickCount64() - info.dwTime) & 0xFFFFFFFF
    except OSError:
        return 0.0
    return delta / 1000.0


class PresenceDetector:
    # 摄像头检测节流间隔（秒）
    _CHECK_INTERVAL = 5
    # 视为"刚刚还在用电脑"的空闲时长上限（秒）
    _INPUT_ACTIVE_WINDOW = 5
    # 摄像头打开失败后的退避参数（秒）：30 → 60 → 120 封顶
    _BACKOFF_BASE = 30
    _BACKOFF_MAX = 120

    def __init__(self, camera_index=0, sleep_timeout_minutes=15):
        self._camera = CameraDetector(camera_index=camera_index)
        self._sleep_timeout_seconds = sleep_timeout_minutes * 60
        self._lock = threading.Lock()

        self._last_camera_found_time = time.monotonic()
        self._last_camera_check_time = 0.0
        self._sleeping = False
        self._idle_start_time = None
        self._is_present = False
        # 摄像头连续失败计数与退避截止时间（P1：避免被占用时每 5s 重试阻塞 tick 线程）
        self._consecutive_failures = 0
        self._camera_backoff_until = 0.0

        self._closed = False

    def tick(self):
        # Phase 0：查询系统空闲时长（锁外，避免持锁做系统调用）
        idle_time = get_idle_seconds()
        now = time.monotonic()

        # Phase 1：锁内判定是否需要摄像头检测。
        # check_once 不再持锁，避免摄像头打开（1.5-2.5s）阻塞 wake()/is_sleeping（P1）。
        with self._lock:
            if self._closed:
                return False

            if self._sleeping:
                if idle_time < self._INPUT_ACTIVE_WINDOW:
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
            if idle_time < self._INPUT_ACTIVE_WINDOW or camera_idle < self._CHECK_INTERVAL:
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
        """关闭检测器：先在锁内标记 _closed，阻止 tick 继续使用，再释放摄像头。"""
        with self._lock:
            if self._closed:
                return
            self._closed = True
        self._camera.close()
