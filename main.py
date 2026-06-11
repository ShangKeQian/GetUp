import sys
import time
import threading
import traceback
from collections import deque
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QObject, Signal, Slot
from config import Config
from timer import TimerEngine, State as TimerState
from detectors.presence import PresenceDetector
from overlay import OverlayWindow
from main_window import MainWindow
from tray import SystemTray, create_icon_pixmap


class _CallbackSignal(QObject):
    """跨线程回调分发器：通过 Qt 信号槽将回调安全投递到主线程执行。"""
    fired = Signal()

    def __init__(self):
        super().__init__()
        self._callbacks = deque()
        self.fired.connect(self._drain, type=Qt.ConnectionType.QueuedConnection)

    def post(self, fn):
        self._callbacks.append(fn)
        self.fired.emit()

    @Slot()
    def _drain(self):
        while self._callbacks:
            cb = self._callbacks.popleft()
            try:
                cb()
            except Exception:
                traceback.print_exc()


class GetUpApp:
    def __init__(self):
        self._app = QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)
        self._app.setWindowIcon(QIcon(create_icon_pixmap()))
        self._ui_cb = _CallbackSignal()

        self._config = Config()
        self._timer = TimerEngine(
            work_minutes=self._config.work_minutes,
            break_minutes=self._config.break_minutes,
        )
        self._detector = PresenceDetector(
            camera_index=self._config.camera_index,
            sleep_timeout_minutes=self._config.sleep_timeout_minutes,
        )

        self._overlay = OverlayWindow(
            break_minutes=self._config.break_minutes,
            on_close=self._on_overlay_close,
        )
        self._bind_timer_callbacks()

        self._main_window = MainWindow(
            config=self._config,
            on_save=self._on_settings_saved,
        )

        self._tray = SystemTray(
            config=self._config,
            timer=self._timer,
            on_toggle=self._toggle_detection,
            on_quit=self._quit,
            on_settings=self._open_main_window,
            on_wake=self._wake_from_sleep,
            on_manual_break=self._manual_break,
        )
        self._tray.show()

        self._tick_thread = None
        self._lock = threading.Lock()
        self._running = False
        self._tick_generation = 0
        self._last_presence = None
        self._last_sleeping = False

    def _toggle_detection(self):
        old_thread = None
        with self._lock:
            if self._running:
                self._running = False
                self._tick_generation += 1
                old_thread = self._tick_thread
                self._timer = TimerEngine(
                    work_minutes=self._config.work_minutes,
                    break_minutes=self._config.break_minutes,
                )
                self._bind_timer_callbacks()
                self._tray._timer = self._timer
                self._tray.update_paused()
            else:
                self._running = True
                self._tick_generation += 1
                self._tray.update_presence(True)
                self._tick_thread = threading.Thread(
                    target=self._tick_loop, args=(self._tick_generation,), daemon=True
                )
                self._tick_thread.start()
            self._tray.update_running(self._running)

        # 在锁外等待旧线程退出
        if old_thread and old_thread.is_alive():
            old_thread.join(timeout=3)

        # 旧线程退出后 finally 已调用 detector.close()，需重建
        if old_thread:
            self._detector = PresenceDetector(
                camera_index=self._config.camera_index,
                sleep_timeout_minutes=self._config.sleep_timeout_minutes,
            )

    def _tick_loop(self, generation):
        detector = self._detector
        timer = self._timer
        detector.start()

        try:
            while self._running and self._tick_generation == generation:
                try:
                    person_present = detector.tick()

                    if person_present:
                        timer.on_person_detected()
                    else:
                        timer.on_person_absent()

                    timer.tick()

                    sleeping = detector.is_sleeping
                    if person_present != self._last_presence or sleeping != self._last_sleeping:
                        self._last_presence = person_present
                        self._last_sleeping = sleeping
                        self._ui_cb.post(lambda s=sleeping: self._tray.update_sleeping(s))
                        self._update_main_window_status()
                except Exception:
                    traceback.print_exc()
                time.sleep(1)
        finally:
            detector.close()

    def _bind_timer_callbacks(self):
        self._timer.on_show_overlay = self._show_overlay
        self._timer.on_update_countdown = self._update_countdown
        self._timer.on_update_work_time = self._update_work_time
        self._timer.on_close_overlay = self._close_overlay
        self._timer.on_reset_work_time = self._reset_work_time
        self._timer.on_state_timing = None
        self._timer.on_state_idle = None

    def _show_overlay(self):
        self._ui_cb.post(self._overlay.show_overlay)

    def _update_countdown(self, seconds):
        self._ui_cb.post(lambda: self._overlay.update_countdown(seconds))

    def _update_work_time(self, elapsed):
        self._ui_cb.post(lambda: self._main_window.update_work_countdown(elapsed))
        self._ui_cb.post(lambda: self._tray.update_work_elapsed(elapsed, self._timer.remaining_seconds))

    def _reset_work_time(self):
        self._ui_cb.post(self._main_window.reset_countdown)

    def _close_overlay(self):
        self._ui_cb.post(self._overlay.destroy_overlay)

    def _manual_break(self):
        self._timer.manual_break()

    def _on_overlay_close(self):
        self._timer.on_overlay_dismissed()

    def _update_main_window_status(self):
        if self._detector.is_sleeping:
            status = "休眠"
        elif self._last_presence is None:
            status = "暂停"
        elif self._last_presence:
            status = "有人"
        else:
            status = "无人"
        self._ui_cb.post(lambda: self._main_window.update_status(status))
        if self._last_presence is not None:
            self._ui_cb.post(lambda p=self._last_presence: self._tray.update_presence(p))

    def _open_main_window(self):
        def _show():
            self._main_window.show()
            if self._timer.state == TimerState.IDLE:
                self._main_window.reset_countdown()
            else:
                self._main_window.update_work_countdown(int(self._timer.elapsed))
            self._update_main_window_status()
        self._ui_cb.post(_show)

    def _restart_detection(self):
        with self._lock:
            was_running = self._running
            old_thread = self._tick_thread
            if was_running:
                self._running = False
                self._tick_generation += 1

        # 在锁外等待旧线程退出，避免持锁阻塞 Qt 线程
        if old_thread and old_thread.is_alive():
            old_thread.join(timeout=3)

        with self._lock:
            # 先关闭遮罩（使用旧 timer 的回调链）
            self._overlay.destroy_overlay()
            self._timer = TimerEngine(
                work_minutes=self._config.work_minutes,
                break_minutes=self._config.break_minutes,
            )
            self._bind_timer_callbacks()
            self._tray._timer = self._timer
            self._overlay = OverlayWindow(
                break_minutes=self._config.break_minutes,
                on_close=self._on_overlay_close,
            )
            # 重建检测器（camera_index、sleep_timeout 可能已变更）
            self._detector.close()
            self._detector = PresenceDetector(
                camera_index=self._config.camera_index,
                sleep_timeout_minutes=self._config.sleep_timeout_minutes,
            )
            if was_running:
                self._running = True
                self._tick_generation += 1
                self._tray.update_presence(True)
                self._tick_thread = threading.Thread(
                    target=self._tick_loop, args=(self._tick_generation,), daemon=True
                )
                self._tick_thread.start()
            self._tray.update_running(self._running)
            self._update_main_window_status()

    def _wake_from_sleep(self):
        self._detector.wake()
        self._update_main_window_status()

    def _on_settings_saved(self):
        self._restart_detection()

    def _quit(self):
        with self._lock:
            self._running = False
            self._tick_generation += 1
            tick_thread = self._tick_thread
        if tick_thread and tick_thread.is_alive():
            tick_thread.join(timeout=3)
        self._detector.close()
        self._app.quit()

    def run(self):
        self._toggle_detection()
        return self._app.exec()


def main():
    app = GetUpApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
