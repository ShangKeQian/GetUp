import time
from enum import Enum
from typing import Callable, Optional


class State(Enum):
    IDLE = "idle"
    TIMING = "timing"
    OVERLAY = "overlay"


class TimerEngine:
    def __init__(self, work_minutes: int = 30, idle_timeout: int = 1, break_minutes: int = 2):
        self._work_seconds = work_minutes * 60
        self._idle_timeout = idle_timeout
        self._break_seconds = break_minutes * 60
        self._state = State.IDLE
        self._elapsed = 0
        self._break_remaining = 0
        self._last_activity = 0.0
        self._absence_start = 0.0
        self._is_absent = False
        self._overlay_paused = False
        self.on_show_overlay: Optional[Callable] = None
        self.on_update_countdown: Optional[Callable] = None
        self.on_close_overlay: Optional[Callable] = None

    @property
    def state(self) -> State:
        return self._state

    @property
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def elapsed_formatted(self) -> str:
        minutes = int(self._elapsed) // 60
        seconds = int(self._elapsed) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def on_person_detected(self):
        self._last_activity = time.time()
        if self._is_absent:
            self._is_absent = False
            absence_duration = time.time() - self._absence_start
            if self._state == State.TIMING and absence_duration >= self._break_seconds:
                self._state = State.IDLE
                self._elapsed = 0
        if self._state == State.IDLE:
            self._state = State.TIMING
            self._elapsed = 1
        elif self._state == State.OVERLAY:
            self._overlay_paused = True

    def on_person_absent(self):
        if not self._is_absent and self._state == State.TIMING:
            self._is_absent = True
            self._absence_start = time.time()
        if self._state == State.OVERLAY:
            self._overlay_paused = False

    def on_overlay_dismissed(self):
        self._state = State.TIMING
        self._elapsed = 0
        self._break_remaining = 0
        self._overlay_paused = False

    def tick(self):
        import time as _time
        if self._state == State.TIMING:
            if self._is_absent:
                absence_duration = time.time() - self._absence_start
                if absence_duration >= self._break_seconds:
                    self._state = State.IDLE
                    self._elapsed = 0
                    self._is_absent = False
                    return
            self._elapsed += 1
            if self._elapsed >= self._work_seconds:
                self._state = State.OVERLAY
                self._break_remaining = self._break_seconds
                self._overlay_paused = False
                if self.on_show_overlay:
                    self.on_show_overlay()
                if self.on_update_countdown:
                    self.on_update_countdown(self._break_remaining)
        elif self._state == State.OVERLAY:
            if not self._overlay_paused:
                self._break_remaining -= 1
                print(f"[TIMER] tick at {_time.time():.3f}, break_remaining={self._break_remaining}", flush=True)
                if self.on_update_countdown:
                    self.on_update_countdown(self._break_remaining)
                if self._break_remaining <= 0:
                    if self.on_close_overlay:
                        self.on_close_overlay()
                    self._state = State.TIMING
                    self._elapsed = 0
                    self._break_remaining = 0
