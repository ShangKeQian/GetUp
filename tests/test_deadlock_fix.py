"""回归测试：验证 _restart_detection 不会重入死锁。"""
import threading
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
    app._ui_cb = MagicMock()
    app._bind_timer_callbacks = MagicMock()
    return app


def test_restart_detection_no_deadlock():
    """_restart_detection 不应因重入锁而死锁。

    回归场景：_restart_detection 在持 self._lock 时调用
    _update_main_window_status，后者再次获取 self._lock，
    threading.Lock 不可重入 → 永久死锁 → UI 冻结。
    """
    app = _make_app(running=False)  # 不启动新线程，聚焦测试锁重入

    with patch("main.PresenceDetector"), \
         patch("main.OverlayWindow"), \
         patch("main.TimerEngine"):
        # 在子线程中调用，设超时检测死锁
        result = {"done": False, "error": None}

        def call_restart():
            try:
                app._restart_detection()
                result["done"] = True
            except Exception as e:
                result["error"] = e

        t = threading.Thread(target=call_restart)
        t.start()
        t.join(timeout=5)

        assert t.is_alive() is False, "_restart_detection 死锁（5秒未返回）"
        assert result["done"] is True, \
            f"_restart_detection 未正常完成, error={result['error']}"


def test_update_main_window_status_acquires_lock_safely():
    """_update_main_window_status 应能安全获取锁，不依赖调用方持锁。"""
    app = _make_app()
    app._main_window = MagicMock()
    app._tray = MagicMock()

    app._update_main_window_status()
    assert app._ui_cb.post.call_count >= 1


def test_post_status_update_does_not_acquire_lock():
    """_post_status_update 不应获取锁，可在持锁状态下调用。"""
    app = _make_app()
    app._main_window = MagicMock()
    app._tray = MagicMock()

    # 先持有锁，再调用 _post_status_update，不应死锁
    with app._lock:
        app._post_status_update(False, True)

    assert app._ui_cb.post.call_count >= 1
