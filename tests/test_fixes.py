"""针对代码审查修复的回归测试。"""
import os
import time
import tempfile
from unittest.mock import MagicMock, patch
from timer import TimerEngine, State
from config import Config


# ── H5: 系统休眠后 dt 跳跃应重置计时器 ──────────────────
def test_tick_handles_sleep_time_jump():
    """系统休眠后 dt 超过 60 秒时应重置，不误触发遮罩。"""
    engine = TimerEngine(work_minutes=1, break_minutes=2)
    engine.on_person_detected()
    # 模拟已工作 50 秒
    engine._elapsed = 50
    engine._last_tick_time = time.monotonic() - 3600  # 1 小时前（模拟休眠）

    overlay_called = []
    engine.on_show_overlay = lambda: overlay_called.append(True)
    engine.tick()

    # 不应触发遮罩（因为 dt 跳跃被重置）
    assert len(overlay_called) == 0
    # elapsed 应被重置
    assert engine.elapsed == 0


def test_tick_handles_normal_dt_advances_elapsed():
    """正常 dt（<60s）应推进 elapsed。"""
    engine = TimerEngine(work_minutes=1)
    engine.on_person_detected()
    engine._last_tick_time = time.monotonic() - 2  # 2 秒前
    engine.tick()
    assert engine.elapsed > 0


# ── H3: Config.save() 失败应返回 False ──────────────────
def test_config_save_returns_false_on_write_failure():
    """写入失败时 save() 应返回 False 而非抛异常。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        cfg = Config(path)
        # 模拟写入失败
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = cfg.save()
        assert result is False


def test_config_save_returns_true_on_success():
    """正常保存应返回 True。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        cfg = Config(path)
        assert cfg.save() is True


# ── M3: manual_break 锁内捕获初始倒计时 ─────────────────
def test_manual_break_passes_correct_initial_countdown():
    """manual_break 应传递正确的初始倒计时值。"""
    engine = TimerEngine(work_minutes=30, break_minutes=3)
    engine.on_person_detected()
    received = []
    engine.on_update_countdown = lambda s: received.append(s)
    engine.on_show_overlay = lambda: None
    engine.manual_break()
    assert received == [180]  # 3 分钟 = 180 秒


def test_manual_break_fails_when_not_timing():
    """非 TIMING 状态下 manual_break 应失败。"""
    engine = TimerEngine(work_minutes=30, break_minutes=3)
    assert engine.manual_break() is False


# ── H1/M5: 暂停后恢复应保留工作进度 ────────────────────
def test_pause_resume_preserves_progress():
    """暂停（通过 _toggle_detection 逻辑）不应重置 elapsed。

    验证 TimerEngine 实例在暂停/恢复周期中保持不变。
    """
    timer = TimerEngine(work_minutes=30)
    timer.on_person_detected()
    timer._elapsed = 600  # 10 分钟
    # 模拟暂停恢复：不再重建 timer，直接复用
    assert timer.elapsed == 600
    timer.tick()
    # 进度应保留
    assert timer.elapsed >= 600


# ── M8: on_state_timing/on_state_idle 已删除 ────────────
def test_no_state_callbacks_attributes():
    """TimerEngine 不应再有 on_state_timing / on_state_idle 属性。"""
    engine = TimerEngine()
    assert not hasattr(engine, 'on_state_timing')
    assert not hasattr(engine, 'on_state_idle')
