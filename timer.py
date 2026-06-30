import time
import threading
from enum import Enum
from typing import Callable, Optional


class State(Enum):
    IDLE = "idle"
    TIMING = "timing"
    OVERLAY = "overlay"


class TimerEngine:
    def __init__(self, work_minutes: int = 30, break_minutes: int = 2):
        self._work_seconds = work_minutes * 60
        self._break_seconds = break_minutes * 60
        self._state = State.IDLE
        self._elapsed = 0
        self._break_remaining = 0
        self._last_activity = 0.0
        self._absence_start = 0.0
        self._is_absent = False
        self._overlay_paused = False
        self._last_tick_time = 0.0
        self._lock = threading.Lock()
        self.on_show_overlay: Optional[Callable] = None
        self.on_update_countdown: Optional[Callable] = None
        self.on_update_work_time: Optional[Callable] = None
        self.on_close_overlay: Optional[Callable] = None
        self.on_reset_work_time: Optional[Callable] = None

    @property
    def state(self) -> State:
        with self._lock:
            return self._state

    @property
    def elapsed(self) -> float:
        with self._lock:
            return self._elapsed

    @property
    def elapsed_formatted(self) -> str:
        with self._lock:
            minutes = int(self._elapsed) // 60
            seconds = int(self._elapsed) % 60
            return f"{minutes:02d}:{seconds:02d}"

    @property
    def remaining_seconds(self) -> int:
        with self._lock:
            return max(0, int(self._work_seconds - self._elapsed))

    def on_person_detected(self):
        callbacks = []
        with self._lock:
            self._last_activity = time.monotonic()
            if self._is_absent:
                self._is_absent = False
                absence_duration = time.monotonic() - self._absence_start
                if self._state == State.TIMING and absence_duration >= self._break_seconds:
                    self._state = State.IDLE
                    self._elapsed = 0
            if self._state == State.IDLE:
                self._state = State.TIMING
                self._elapsed = 0
                if self.on_reset_work_time:
                    callbacks.append(self.on_reset_work_time)
            elif self._state == State.OVERLAY:
                self._overlay_paused = True
        for cb in callbacks:
            cb()

    def on_person_absent(self):
        with self._lock:
            if not self._is_absent and self._state == State.TIMING:
                self._is_absent = True
                self._absence_start = time.monotonic()
            if self._state == State.OVERLAY:
                self._overlay_paused = False

    def on_overlay_dismissed(self):
        with self._lock:
            if self._state != State.OVERLAY:
                return
            self._state = State.TIMING
            self._elapsed = 0
            self._break_remaining = 0
            self._overlay_paused = False

    def manual_break(self) -> bool:
        with self._lock:
            if self._state != State.TIMING:
                return False
            self._state = State.OVERLAY
            self._break_remaining = self._break_seconds
            self._overlay_paused = False
            initial_countdown = int(self._break_remaining)

        if self.on_show_overlay:
            self.on_show_overlay()
        if self.on_update_countdown:
            self.on_update_countdown(initial_countdown)
        return True

    def tick(self):
        callbacks = []
        with self._lock:
            now = time.monotonic()
            if self._last_tick_time == 0:
                self._last_tick_time = now
            dt = now - self._last_tick_time
            self._last_tick_time = now

            # 系统休眠/挂起后 dt 会跳跃（数千秒），重置计时避免误触发遮罩或秒关
            if dt > 60:
                self._elapsed = 0
                self._break_remaining = self._break_seconds
                return

            if self._state == State.TIMING:
                if self._is_absent:
                    absence_duration = now - self._absence_start
                    if absence_duration >= self._break_seconds:
                        self._state = State.IDLE
                        self._elapsed = 0
                        self._is_absent = False
                        if self.on_reset_work_time:
                            callbacks.append(self.on_reset_work_time)
                else:
                    self._elapsed += dt
                    if self.on_update_work_time:
                        elapsed_now = int(self._elapsed)
                        callbacks.append(lambda e=elapsed_now: self.on_update_work_time(e))
                if self._state == State.TIMING and self._elapsed >= self._work_seconds:
                    self._state = State.OVERLAY
                    self._break_remaining = self._break_seconds
                    self._overlay_paused = False
                    if self.on_show_overlay:
                        callbacks.append(self.on_show_overlay)
                    if self.on_update_countdown:
                        remaining_now = int(self._break_remaining)
                        callbacks.append(lambda r=remaining_now: self.on_update_countdown(r))
            elif self._state == State.OVERLAY:
                if not self._overlay_paused:
                    self._break_remaining -= dt
                    if self.on_update_countdown:
                        remaining_now = int(self._break_remaining)
                        callbacks.append(lambda r=remaining_now: self.on_update_countdown(r))
                    if self._break_remaining <= 0:
                        if self.on_close_overlay:
                            callbacks.append(self.on_close_overlay)
                        self._state = State.TIMING
                        self._elapsed = 0
                        self._break_remaining = 0
        for cb in callbacks:
            cb()
