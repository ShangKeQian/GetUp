import sys
import time
import threading
import tkinter as tk
from config import Config
from timer import TimerEngine, State
from detectors import create_detectors
from detectors.camera import CameraDetector
from overlay import OverlayWindow
from settings import SettingsDialog
from tray import SystemTray


class GetUpApp:
    def __init__(self):
        self._config = Config()
        self._detectors = []
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
        self._timer.on_close_overlay = self._close_overlay
        self._settings = SettingsDialog(
            self._root,
            self._config,
            on_save=self._on_settings_saved,
        )
        self._tray = SystemTray(
            self._config,
            on_start=self._start_detection,
            on_stop=self._stop_detection,
            on_quit=self._quit,
            on_settings=self._open_settings,
        )
        self._tick_thread = None
        self._running = False
        self._last_presence = None

    def _start_detection(self, icon=None, item=None):
        if self._running:
            return
        self._running = True
        self._camera = CameraDetector(camera_index=self._config.camera_index)
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

    def _stop_detection(self, icon=None, item=None):
        self._running = False
        self._tray.update_paused()
        self._timer = TimerEngine(
            work_minutes=self._config.work_minutes,
            idle_timeout=1,
            break_minutes=self._config.break_minutes,
        )
        self._timer.on_show_overlay = self._show_overlay
        self._timer.on_update_countdown = self._update_countdown
        self._timer.on_close_overlay = self._close_overlay

    def _tick_loop(self):
        import pynput
        last_input_time = time.time()
        last_camera_check = 0

        def on_input(*args):
            nonlocal last_input_time
            last_input_time = time.time()

        mouse_listener = pynput.mouse.Listener(on_move=on_input, on_click=on_input)
        keyboard_listener = pynput.keyboard.Listener(on_press=on_input, on_release=on_input)
        mouse_listener.daemon = True
        keyboard_listener.daemon = True
        mouse_listener.start()
        keyboard_listener.start()

        tick_count = 0
        last_camera_found_time = 0
        last_camera_check_time = 0
        while self._running:
            now = time.time()
            idle_time = now - last_input_time
            camera_idle = now - last_camera_found_time

            person_present = False

            if idle_time < 5:
                person_present = True
            elif camera_idle < 5:
                person_present = True
            elif now - last_camera_check_time >= 5:
                last_camera_check_time = now
                if self._camera.check_once():
                    person_present = True
                    last_camera_found_time = now

            if person_present:
                self._timer.on_person_detected()
            else:
                self._timer.on_person_absent()

            if person_present != self._last_presence:
                self._last_presence = person_present
                self._tray.update_presence(person_present)
            self._timer.tick()
            time.sleep(1)

    def _show_overlay(self):
        self._root.after(0, self._overlay.show)

    def _update_countdown(self, seconds):
        self._root.after(0, self._overlay.update_countdown, seconds)

    def _close_overlay(self):
        self._root.after(0, self._overlay._on_close)

    def _on_overlay_close(self):
        self._timer.on_overlay_dismissed()

    def _open_settings(self, icon=None, item=None):
        self._root.after(0, self._settings.show)

    def _on_settings_saved(self):
        if self._running:
            self._stop_detection()
            self._start_detection()

    def _quit(self, icon=None, item=None):
        self._running = False
        for det in self._detectors:
            det.stop()
        self._root.after(0, self._root.destroy)
        if self._tray._icon:
            self._tray._icon.stop()

    def run(self):
        tray_thread = threading.Thread(target=self._tray.start, daemon=True)
        tray_thread.start()
        self._start_detection()
        self._root.mainloop()


def main():
    app = GetUpApp()
    app.run()


if __name__ == "__main__":
    main()
