import time
from enum import Enum
from typing import Callable, Optional


class State(Enum):
    IDLE = "idle"
    TIMING = "timing"
    OVERLAY = "overlay"


class TimerEngine:
    def __init__(self, work_minutes: int = 30, idle_timeout: int = 120):
        self._work_seconds = work_minutes * 60
        self._idle_timeout = idle_timeout
        self._state = State.IDLE
        self._elapsed = 0
        self._last_activity = 0.0
        self._overlay_paused = False
        self.on_show_overlay: Optional[Callable] = None

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
        if self._state == State.IDLE:
            self._state = State.TIMING
            self._elapsed = 1
        elif self._state == State.OVERLAY:
            self._overlay_paused = True

    def on_overlay_dismissed(self):
        self._state = State.TIMING
        self._elapsed = 0
        self._overlay_paused = False

    def tick(self):
        if self._state == State.TIMING:
            idle_time = time.time() - self._last_activity
            if idle_time >= self._idle_timeout:
                self._state = State.IDLE
                self._elapsed = 0
                return
            self._elapsed += 1
            if self._elapsed >= self._work_seconds:
                self._state = State.OVERLAY
                if self.on_show_overlay:
                    self.on_show_overlay()
        elif self._state == State.OVERLAY:
            if not self._overlay_paused:
                idle_time = time.time() - self._last_activity
                if idle_time >= self._idle_timeout:
                    self._state = State.IDLE
                    self._elapsed = 0
