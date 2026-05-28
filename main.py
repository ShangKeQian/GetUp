import sys
import time
import threading
import traceback
import tkinter as tk
import pynput
from config import Config
from timer import TimerEngine, State
from detectors.camera import CameraDetector
from overlay import OverlayWindow
from main_window import MainWindow
from tray import SystemTray


class GetUpApp:
    def __init__(self):
        self._config = Config()
        self._timer = TimerEngine(
            work_minutes=self._config.work_minutes,
            idle_timeout=1,
            break_minutes=self._config.break_minutes,
        )
        self._root = tk.Tk()
        self._root.withdraw()
        self._overlay = OverlayWindow(
            self._root,
            break_minutes=self._config.break_minutes,
            on_close=self._on_overlay_close,
        )
        self._timer.on_show_overlay = self._show_overlay
        self._timer.on_update_countdown = self._update_countdown
        self._timer.on_update_work_time = self._update_work_time
        self._timer.on_close_overlay = self._close_overlay
        self._timer.on_reset_work_time = self._reset_work_time
        self._main_window = MainWindow(
            self._root,
            self._config,
            on_save=self._on_settings_saved,
        )
        self._tray = SystemTray(
            self._config,
            on_toggle=self._toggle_detection,
            on_quit=self._quit,
            on_settings=self._open_main_window,
            on_double_click=self._open_main_window,
        )
        self._tick_thread = None
        self._running = False
        self._last_presence = None
        self._last_sleeping = False
        self._sleeping = False
        self._idle_start_time = None

    def _toggle_detection(self, icon=None, item=None):
        if self._running:
            self._running = False
            self._tray.update_paused()
            if hasattr(self, '_camera'):
                self._camera.stop()
            self._timer = TimerEngine(
                work_minutes=self._config.work_minutes,
                idle_timeout=1,
                break_minutes=self._config.break_minutes,
            )
            self._timer.on_show_overlay = self._show_overlay
            self._timer.on_update_countdown = self._update_countdown
            self._timer.on_update_work_time = self._update_work_time
            self._timer.on_close_overlay = self._close_overlay
            self._timer.on_reset_work_time = self._reset_work_time
        else:
            self._running = True
            self._tray.update_presence(True)
            self._camera = CameraDetector(camera_index=self._config.camera_index)
            self._camera.start()
            self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
            self._tick_thread.start()
        self._tray.update_running(self._running)

    def _tick_loop(self):
        last_input_time = time.time()

        def on_input(*args):
            nonlocal last_input_time
            last_input_time = time.time()

        mouse_listener = pynput.mouse.Listener(on_move=on_input, on_click=on_input)
        keyboard_listener = pynput.keyboard.Listener(on_press=on_input, on_release=on_input)
        mouse_listener.daemon = True
        keyboard_listener.daemon = True
        mouse_listener.start()
        keyboard_listener.start()

        last_camera_found_time = 0
        last_camera_check_time = 0
        try:
            while self._running:
                try:
                    now = time.time()
                    idle_time = now - last_input_time
                    person_present = False

                    # 休眠时只检测键鼠，跳过摄像头
                    if self._sleeping:
                        if idle_time < 5:
                            # 检测到输入 → 唤醒
                            self._sleeping = False
                            self._idle_start_time = None
                            self._camera = CameraDetector(camera_index=self._config.camera_index)
                            self._camera.start()
                            person_present = True
                            last_camera_found_time = now
                            last_camera_check_time = now
                    else:
                        camera_idle = now - last_camera_found_time

                        if idle_time < 5:
                            person_present = True
                        elif camera_idle < 5:
                            person_present = True
                        elif now - last_camera_check_time >= 5:
                            last_camera_check_time = now
                            try:
                                if self._camera.check_once():
                                    person_present = True
                                    last_camera_found_time = now
                                else:
                                    last_camera_found_time = 0
                            except Exception:
                                traceback.print_exc()
                                last_camera_check_time = now

                    if person_present:
                        self._timer.on_person_detected()
                        self._idle_start_time = None
                    else:
                        self._timer.on_person_absent()
                        # 追踪空闲时间以触发休眠
                        if self._timer.state == State.IDLE:
                            if self._idle_start_time is None:
                                self._idle_start_time = now
                            elif now - self._idle_start_time >= self._config.sleep_timeout_minutes * 60:
                                self._sleeping = True
                                self._idle_start_time = None
                                if hasattr(self, '_camera'):
                                    self._camera.stop()

                    if person_present != self._last_presence or self._sleeping != self._last_sleeping:
                        self._last_presence = person_present
                        self._last_sleeping = self._sleeping
                        self._tray.update_sleeping(self._sleeping)
                        self._update_main_window_status()
                    self._timer.tick()
                except Exception:
                    traceback.print_exc()
                time.sleep(1)
        finally:
            mouse_listener.stop()
            keyboard_listener.stop()

    def _show_overlay(self):
        self._root.after(0, self._overlay.show)

    def _update_countdown(self, seconds):
        self._root.after(0, self._overlay.update_countdown, seconds)

    def _update_work_time(self, elapsed):
        self._root.after(0, self._main_window.update_work_countdown, elapsed)

    def _reset_work_time(self):
        self._root.after(0, self._main_window.reset_countdown)

    def _close_overlay(self):
        self._root.after(0, self._overlay._on_close)

    def _on_overlay_close(self):
        self._timer.on_overlay_dismissed()

    def _update_main_window_status(self):
        if self._sleeping:
            status = "休眠"
        elif self._last_presence is None:
            status = "暂停"
        elif self._last_presence:
            status = "有人"
        else:
            status = "无人"
        self._main_window.update_status(status)

    def _open_main_window(self, icon=None, item=None):
        def _show_and_sync():
            self._main_window.show()
            self._main_window.update_countdown(self._timer.remaining_seconds)
            self._update_main_window_status()
        self._root.after(0, _show_and_sync)

    def _on_settings_saved(self):
        if self._running:
            self._toggle_detection()
            self._toggle_detection()
        self._update_main_window_status()

    def _quit(self, icon=None, item=None):
        self._running = False
        if hasattr(self, '_camera'):
            self._camera.stop()
        self._root.after(0, self._root.destroy)
        if self._tray._icon:
            self._tray._icon.stop()

    def run(self):
        tray_thread = threading.Thread(target=self._tray.start, daemon=True)
        tray_thread.start()
        self._toggle_detection()
        self._root.mainloop()


def main():
    app = GetUpApp()
    app.run()


if __name__ == "__main__":
    main()
