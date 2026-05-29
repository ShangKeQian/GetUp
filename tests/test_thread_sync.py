import threading
import time
from timer import TimerEngine, State


def test_concurrent_tick_and_dismiss():
    timer = TimerEngine(work_minutes=1, break_minutes=2)

    timer.on_person_detected()
    timer._elapsed = 60
    timer.tick()
    assert timer.state == State.OVERLAY

    errors = []

    def tick_loop():
        for _ in range(100):
            try:
                timer.tick()
            except Exception as e:
                errors.append(e)

    def dismiss_loop():
        for _ in range(100):
            try:
                timer.on_overlay_dismissed()
            except Exception as e:
                errors.append(e)

    t1 = threading.Thread(target=tick_loop)
    t2 = threading.Thread(target=dismiss_loop)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert len(errors) == 0, f"Concurrent access caused {len(errors)} errors"


def test_state_stays_consistent_under_concurrent_access():
    timer = TimerEngine(work_minutes=1, break_minutes=2)

    errors = []
    valid_states = {State.IDLE, State.TIMING, State.OVERLAY}

    def tick_loop():
        for _ in range(200):
            try:
                timer.tick()
                assert timer.state in valid_states, f"Invalid state: {timer.state}"
            except Exception as e:
                errors.append(e)

    def dismiss_loop():
        for _ in range(200):
            try:
                timer.on_overlay_dismissed()
                assert timer.state in valid_states, f"Invalid state: {timer.state}"
            except Exception as e:
                errors.append(e)

    def detect_loop():
        for _ in range(200):
            try:
                timer.on_person_detected()
                assert timer.state in valid_states, f"Invalid state: {timer.state}"
                timer.on_person_absent()
                assert timer.state in valid_states, f"Invalid state: {timer.state}"
            except Exception as e:
                errors.append(e)

    threads = [
        threading.Thread(target=tick_loop),
        threading.Thread(target=dismiss_loop),
        threading.Thread(target=detect_loop),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(errors) == 0, f"Concurrent access caused {len(errors)} errors: {errors[:5]}"
    assert timer.state in valid_states, f"Final state invalid: {timer.state}"
