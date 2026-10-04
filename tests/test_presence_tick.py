"""回归测试：P1 PresenceDetector.tick() 摄像头检测移出锁 + 失败指数退避。

需要 detectors.camera 的依赖（cv2/mediapipe），但通过 patch CameraDetector
避免真实模型加载与摄像头硬件；键鼠空闲时长通过 patch get_idle_seconds 注入，
使判定不依赖运行测试的机器的真实空闲状态。
"""
import threading
import time
from unittest.mock import MagicMock, patch

from detectors.presence import PresenceDetector, get_idle_seconds


def _make_detector(monkeypatch, idle=0.0):
    """构造 PresenceDetector，注入 mock 摄像头与固定的键鼠空闲时长。

    idle 可传数值或返回数值的可调用对象（后者用于让空闲时长在多次 tick 间变化）。
    """
    provider = idle if callable(idle) else (lambda: float(idle))
    monkeypatch.setattr("detectors.presence.get_idle_seconds", provider)
    with patch("detectors.presence.CameraDetector"):
        d = PresenceDetector(camera_index=0, sleep_timeout_minutes=15)
    d._camera = MagicMock()
    return d


def _force_camera_check(d):
    """将检测器置于"摄像头空闲 + 到节流间隔"状态，强制下次 tick 调摄像头。

    键鼠空闲时长由 _make_detector 的 idle 参数控制（需 >= 5 秒才算非近期输入）。
    """
    d._last_camera_found_time = time.monotonic() - 10
    d._last_camera_check_time = 0.0
    d._camera_backoff_until = 0.0


# ── 空闲时长来源（Win32 GetLastInputInfo）─────────────────────────
def test_get_idle_seconds_returns_sane_value():
    """ctypes 原型声明正确时，返回值应为非负有限浮点数（不因符号/截断而出错）。"""
    value = get_idle_seconds()
    assert isinstance(value, float)
    assert 0.0 <= value < 365 * 24 * 3600


# ── P1 核心：摄像头检测期间不持锁，wake() 可立即执行 ─────────────
def test_tick_releases_lock_during_camera_check(monkeypatch):
    d = _make_detector(monkeypatch, idle=10.0)
    _force_camera_check(d)

    in_check = threading.Event()
    release_check = threading.Event()

    def slow_check_once():
        in_check.set()
        release_check.wait(timeout=2)
        return True

    d._camera.check_once.side_effect = slow_check_once

    wake_done = threading.Event()
    t_tick = threading.Thread(target=d.tick, daemon=True)
    t_tick.start()

    assert in_check.wait(timeout=1), "check_once 未被调用"
    # check_once 进行中时，wake() 应能立即获取锁（证明检测已移出锁）
    threading.Thread(target=lambda: (d.wake(), wake_done.set()), daemon=True).start()
    assert wake_done.wait(timeout=1), "wake() 被 tick 持有的锁阻塞（摄像头检测未移出锁）"

    release_check.set()
    t_tick.join(timeout=2)


# ── P1：摄像头错误后指数退避，不每 5s 重试 ───────────────────────
def test_backoff_after_camera_error(monkeypatch):
    d = _make_detector(monkeypatch, idle=10.0)
    _force_camera_check(d)
    d._camera.check_once.return_value = None  # 摄像头错误/被占用

    d.tick()
    assert d._camera.check_once.call_count == 1
    assert d._consecutive_failures == 1

    # 紧接着再 tick：退避期内不应再次检测
    d.tick()
    assert d._camera.check_once.call_count == 1, "退避期内不应再次检测摄像头"
    assert d._camera_backoff_until > 0


def test_backoff_resets_on_success(monkeypatch):
    d = _make_detector(monkeypatch, idle=10.0)
    _force_camera_check(d)
    d._camera.check_once.return_value = None
    d.tick()  # 失败一次
    assert d._consecutive_failures == 1

    # 强制下次检测并返回成功
    _force_camera_check(d)
    d._camera.check_once.return_value = True
    d.tick()

    assert d._consecutive_failures == 0
    assert d._camera_backoff_until == 0.0


# ── 行为保持：原有判定逻辑 ─────────────────────────────────────
def test_recent_input_marks_present_without_camera(monkeypatch):
    d = _make_detector(monkeypatch, idle=1.0)
    d._last_camera_found_time = 0.0
    assert d.tick() is True
    d._camera.check_once.assert_not_called()


def test_recent_camera_match_marks_present_without_recheck(monkeypatch):
    d = _make_detector(monkeypatch, idle=100.0)
    d._last_camera_found_time = time.monotonic()  # camera_idle < 5
    assert d.tick() is True
    d._camera.check_once.assert_not_called()


def test_camera_detects_face_marks_present(monkeypatch):
    d = _make_detector(monkeypatch, idle=10.0)
    _force_camera_check(d)
    d._camera.check_once.return_value = True
    assert d.tick() is True


def test_camera_no_face_marks_absent(monkeypatch):
    d = _make_detector(monkeypatch, idle=10.0)
    _force_camera_check(d)
    d._camera.check_once.return_value = False
    assert d.tick() is False


def test_enters_sleep_after_idle_timeout(monkeypatch):
    d = _make_detector(monkeypatch, idle=100.0)
    d._camera.check_once.return_value = False
    d._sleep_timeout_seconds = 50
    d._last_camera_found_time = 0.0
    d._last_camera_check_time = 0.0
    d._idle_start_time = time.monotonic() - 60  # 已空闲 60s >= 50

    d.tick()

    assert d.is_sleeping is True
    d._camera.release.assert_called_once()


def test_sleeping_returns_false_until_input(monkeypatch):
    idle = [100.0]
    d = _make_detector(monkeypatch, idle=lambda: idle[0])
    d._sleeping = True
    assert d.tick() is False
    # 有输入后唤醒
    idle[0] = 0.0
    assert d.tick() is True
    assert d.is_sleeping is False


def test_closed_tick_returns_false_without_camera(monkeypatch):
    d = _make_detector(monkeypatch, idle=10.0)
    _force_camera_check(d)
    d._closed = True
    assert d.tick() is False
    d._camera.check_once.assert_not_called()
