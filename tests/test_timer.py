import time
from unittest.mock import MagicMock
from timer import TimerEngine, State


def test_initial_state_is_idle():
    engine = TimerEngine(work_minutes=30)
    assert engine.state == State.IDLE


def test_person_detected_transitions_to_timing():
    engine = TimerEngine(work_minutes=30)
    engine.on_person_detected()
    assert engine.state == State.TIMING
    assert engine.elapsed == 0


def test_person_left_resets_to_idle():
    engine = TimerEngine(work_minutes=30, break_minutes=2)
    engine.on_person_detected()
    engine.on_person_absent()
    engine._absence_start = time.monotonic() - 300
    engine.tick()
    assert engine.state == State.IDLE
    assert engine.elapsed == 0


def test_overlay_shows_when_time_reached():
    engine = TimerEngine(work_minutes=1)
    engine.on_person_detected()
    engine._elapsed = 60
    on_overlay = MagicMock()
    engine.on_show_overlay = on_overlay
    engine.tick()
    assert engine.state == State.OVERLAY
    on_overlay.assert_called_once()


def test_overlay_dismissed_resets():
    engine = TimerEngine(work_minutes=30)
    engine._state = State.OVERLAY
    engine.on_overlay_dismissed()
    assert engine.state == State.TIMING
    assert engine.elapsed == 0


def test_overlay_paused_when_person_returns():
    engine = TimerEngine(work_minutes=30)
    engine._state = State.OVERLAY
    engine.on_person_detected()
    assert engine._overlay_paused is True


def test_elapsed_format():
    engine = TimerEngine(work_minutes=30)
    engine._elapsed = 125
    assert engine.elapsed_formatted == "02:05"
