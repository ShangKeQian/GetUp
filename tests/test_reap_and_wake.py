"""回归测试：P2 主线程不再同步 join（消除 UI 冻结）与 Q1 _wake_from_sleep 安全性。

这些测试需要完整依赖（PySide6/cv2/mediapipe），与 test_deadlock_fix.py 同级。
运行：pytest tests/test_reap_and_wake.py -v
"""
import threading
import time
from unittest.mock import MagicMock, patch

from main import GetUpApp


def _make_app(running=True):
    """构造一个 mock 依赖的 GetUpApp 实例，绕过 __init__。"""
    app = GetUpApp.__new__(GetUpApp)
    app._lock = threading.Lock()
    app._running = running
    app._tick_generation = 1
    app._tick_thread = None
    app._last_presence = True
    app._last_sleeping = False
    app._config = MagicMock()
    app._config.work_minutes = 25
    app._config.break_minutes = 2
    app._config.camera_index = 0
    app._config.sleep_timeout_minutes = 15
    app._timer = MagicMock()
    app._detector = MagicMock()
    app._overlay = MagicMock()
    app._tray = MagicMock()
    app._main_window = MagicMock()
    app._ui_cb = MagicMock()
    app._app = MagicMock()
    app._bind_timer_callbacks = MagicMock()
    return app


class _BlockingThread:
    """模拟卡在摄像头打开的 tick 线程：join 阻塞直到 release() 被调用。"""

    def __init__(self):
        self._done = threading.Event()

    def is_alive(self):
        return not self._done.is_set()

    def join(self, timeout=None):
        self._done.wait(timeout=timeout)

    def release(self):
        self._done.set()


def _run_with_timeout(fn, timeout=1.0):
    """在子线程中运行 fn，返回 (是否在超时内完成, 异常)。"""
    box = {"done": False, "error": None}

    def run():
        try:
            fn()
            box["done"] = True
        except Exception as e:
            box["error"] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return (not t.is_alive()), box["error"]


def _wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


# ── Q1: _wake_from_sleep 在 _detector 为 None 时不崩溃 ──────────
def test_wake_from_sleep_when_detector_none():
    """_restart_detection 期间 _detector 被置 None，唤醒不应抛 AttributeError。"""
    app = _make_app()
    app._detector = None
    finished, err = _run_with_timeout(app._wake_from_sleep, timeout=2)
    assert finished, "_wake_from_sleep 在 _detector=None 时阻塞或崩溃"
    assert err is None, f"未预期异常: {err}"


def test_wake_from_sleep_calls_wake_when_detector_present():
    app = _make_app()
    detector = MagicMock()
    app._detector = detector
    app._wake_from_sleep()
    detector.wake.assert_called_once()


# ── P2: _toggle_detection 暂停不在主线程同步 join ───────────────
def test_toggle_pause_does_not_block_on_join():
    """暂停时旧 tick 线程卡住，_toggle_detection 仍应在主线程快速返回。"""
    app = _make_app(running=True)
    blocking = _BlockingThread()
    app._tick_thread = blocking
    old_detector = app._detector
    with patch("main.PresenceDetector"):
        finished, err = _run_with_timeout(app._toggle_detection, timeout=1.0)
    assert finished, "_toggle_detection 暂停时仍在主线程同步 join（UI 会冻结）"
    assert err is None, f"未预期异常: {err}"
    # 后台 reaper 应在旧线程退出后关闭旧检测器
    blocking.release()
    assert _wait_until(lambda: old_detector.close.called, timeout=2), \
        "后台 reaper 未关闭旧检测器"


def test_toggle_resume_does_not_reap():
    """恢复分支无旧线程/旧检测器，不应触发 reaper。"""
    app = _make_app(running=False)
    app._reap_worker = MagicMock()
    with patch("main.threading.Thread") as m_thread:
        m_thread.return_value.start = MagicMock()
        app._toggle_detection()
    assert m_thread.called, "恢复时应启动新工作线程"
    app._reap_worker.assert_not_called()


# ── P2: _restart_detection 不在主线程同步 join ─────────────────
def test_restart_detection_does_not_block_on_join():
    app = _make_app(running=False)
    blocking = _BlockingThread()
    app._tick_thread = blocking
    old_detector = app._detector
    old_timer = app._timer
    with patch("main.PresenceDetector"), patch("main.OverlayManager"), \
         patch("main.TimerEngine"):
        finished, err = _run_with_timeout(app._restart_detection, timeout=1.0)
    assert finished, "_restart_detection 仍在主线程同步 join（UI 会冻结）"
    assert err is None, f"未预期异常: {err}"
    # 旧 timer 回调应被断开，防止旧 tick 触发新 UI
    for name in ("on_show_overlay", "on_update_countdown", "on_update_work_time",
                 "on_close_overlay", "on_reset_work_time"):
        assert getattr(old_timer, name) is None, f"旧 timer 回调 {name} 未被断开"
    blocking.release()
    assert _wait_until(lambda: old_detector.close.called, timeout=2), \
        "后台 reaper 未关闭旧检测器"


# ── P2: _quit 不在主线程同步 join ──────────────────────────────
def test_quit_does_not_block_on_join():
    app = _make_app(running=True)
    blocking = _BlockingThread()
    app._tick_thread = blocking
    detector = app._detector
    finished, err = _run_with_timeout(app._quit, timeout=1.0)
    assert finished, "_quit 仍在主线程同步 join（UI 会冻结）"
    assert err is None, f"未预期异常: {err}"
    assert app._app.quit.called, "_quit 未调用 app.quit()"
    blocking.release()
    assert _wait_until(lambda: detector.close.called, timeout=2), \
        "后台 reaper 未关闭检测器"


# ── P2: _reap_worker 处理 None 入参 ────────────────────────────
def test_reap_worker_handles_none_thread():
    app = _make_app()
    detector = MagicMock()
    app._reap_worker(None, detector)
    assert _wait_until(lambda: detector.close.called, timeout=2), \
        "_reap_worker(None, detector) 未关闭检测器"
