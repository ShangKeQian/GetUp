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
        self._pending = False
        self._lock = threading.Lock()
        self.fired.connect(self._drain, type=Qt.ConnectionType.QueuedConnection)

    def post(self, fn):
        with self._lock:
            self._callbacks.append(fn)
            need_emit = not self._pending
            self._pending = True
        if need_emit:
            self.fired.emit()

    @Slot()
    def _drain(self):
        with self._lock:
            self._pending = False
            callbacks = list(self._callbacks)
            self._callbacks.clear()
        for cb in callbacks:
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
        """暂停/恢复监控。

        修复要点：
        - 暂停时保留 TimerEngine 实例，不丢失工作进度（M5）
        - 检测器重建移入锁内，避免快速切换导致新线程捕获旧检测器（H1）
        - 所有共享状态访问均在锁内（H2）
        """
        old_thread = None
        old_detector = None
        with self._lock:
            if self._running:
                # 暂停：停止 tick 线程，保留 timer 进度
                self._running = False
                self._tick_generation += 1
                old_thread = self._tick_thread
                old_detector = self._detector
                # 重建新检测器供下次恢复使用
                self._detector = PresenceDetector(
                    camera_index=self._config.camera_index,
                    sleep_timeout_minutes=self._config.sleep_timeout_minutes,
                )
                self._tray.update_paused()
            else:
                # 恢复：复用现有 timer（保留 elapsed），启动新线程
                self._running = True
                self._tick_generation += 1
                self._tray.update_presence(True)
                self._tick_thread = threading.Thread(
                    target=self._tick_loop, args=(self._tick_generation,), daemon=True
                )
                self._tick_thread.start()
            self._tray.update_running(self._running)

        # 锁外等待旧线程退出，然后关闭旧检测器
        if old_thread and old_thread.is_alive():
            old_thread.join(timeout=3)
        if old_detector:
            old_detector.close()

    def _tick_loop(self, generation):
        """tick 线程：在锁内快照 detector/timer，循环条件也在锁内检查（H2）。"""
        with self._lock:
            detector = self._detector
            timer = self._timer
        detector.start()

        try:
            while True:
                with self._lock:
                    if not self._running or self._tick_generation != generation:
                        break
                try:
                    person_present = detector.tick()

                    if person_present:
                        timer.on_person_detected()
                    else:
                        timer.on_person_absent()

                    timer.tick()

                    with self._lock:
                        last_presence = self._last_presence
                        last_sleeping = self._last_sleeping
                        presence_changed = (person_present != last_presence
                                            or detector.is_sleeping != last_sleeping)
                        if presence_changed:
                            self._last_presence = person_present
                            self._last_sleeping = detector.is_sleeping
                            sleeping_now = detector.is_sleeping

                    if presence_changed:
                        self._ui_cb.post(lambda s=sleeping_now: self._tray.update_sleeping(s))
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
        """锁外调用：快照状态并投递 UI 更新。自行获取锁。"""
        with self._lock:
            sleeping = self._last_sleeping
            last_presence = self._last_presence
        self._post_status_update(sleeping, last_presence)

    def _post_status_update(self, sleeping, last_presence):
        """已快照后调用：根据值构造状态文案并投递到主线程。不获取锁。"""
        if sleeping:
            status = "休眠"
        elif last_presence is None:
            status = "暂停"
        elif last_presence:
            status = "有人"
        else:
            status = "无人"
        self._ui_cb.post(lambda: self._main_window.update_status(status))
        if last_presence is not None:
            self._ui_cb.post(lambda p=last_presence: self._tray.update_presence(p))

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
        """设置保存后重启检测。配置可能变更，需重建 timer 和 detector。"""
        with self._lock:
            was_running = self._running
            old_thread = self._tick_thread
            old_detector = self._detector
            if was_running:
                self._running = False
                self._tick_generation += 1
            # 标记检测器已废弃，新线程不会再使用它
            self._detector = None

        # 锁外等待旧线程退出
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
            self._tray.set_timer(self._timer)
            self._overlay = OverlayWindow(
                break_minutes=self._config.break_minutes,
                on_close=self._on_overlay_close,
            )
            # 重建检测器（camera_index、sleep_timeout 可能已变更）
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
            # 在锁内快照状态值（避免重入死锁，不调用 _update_main_window_status）
            sleeping = self._last_sleeping
            last_presence = self._last_presence

        # 锁外投递 UI 更新
        self._post_status_update(sleeping, last_presence)

        # 锁外关闭旧检测器
        if old_detector:
            old_detector.close()

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
            if tick_thread.is_alive():
                # 线程未在超时内退出，不调用 close 避免并发使用（M6）
                print("[GetUp] tick 线程未在超时内退出，跳过检测器关闭",
                      file=sys.stderr)
                self._app.quit()
                return
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
