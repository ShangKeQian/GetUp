import time
import threading
import pynput
from detectors.camera import CameraDetector


class PresenceDetector:
    def __init__(self, camera_index=0, sleep_timeout_minutes=15):
        self._camera = CameraDetector(camera_index=camera_index)
        self._sleep_timeout_seconds = sleep_timeout_minutes * 60
        self._lock = threading.Lock()

        self._last_input_time = time.time()
        self._last_camera_found_time = time.time()
        self._last_camera_check_time = 0.0
        self._sleeping = False
        self._idle_start_time = None
        self._is_present = False

        self._mouse_listener = None
        self._keyboard_listener = None
        self._closed = False

    def start(self):
        def on_input(*args):
            self._last_input_time = time.time()

        self._mouse_listener = pynput.mouse.Listener(on_move=on_input, on_click=on_input)
        self._keyboard_listener = pynput.keyboard.Listener(on_press=on_input, on_release=on_input)
        self._mouse_listener.daemon = True
        self._keyboard_listener.daemon = True
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def tick(self):
        now = time.time()

        with self._lock:
            idle_time = now - self._last_input_time
            person_present = False

            if self._sleeping:
                if idle_time < 5:
                    self._sleeping = False
                    self._idle_start_time = None
                    person_present = True
                    self._last_camera_found_time = now
                    self._last_camera_check_time = now
            else:
                camera_idle = now - self._last_camera_found_time

                if idle_time < 5:
                    person_present = True
                elif camera_idle < 5:
                    person_present = True
                elif now - self._last_camera_check_time >= 5:
                    self._last_camera_check_time = now
                    result = self._camera.check_once()
                    if result is True:
                        person_present = True
                        self._last_camera_found_time = now
                    elif result is False:
                        self._last_camera_found_time = 0

                if person_present:
                    self._idle_start_time = None
                elif self._idle_start_time is None:
                    self._idle_start_time = now
                elif now - self._idle_start_time >= self._sleep_timeout_seconds:
                    self._sleeping = True
                    self._idle_start_time = None
                    self._camera.release()

            self._is_present = person_present
            return person_present

    @property
    def is_sleeping(self):
        return self._sleeping

    def wake(self):
        with self._lock:
            self._sleeping = False
            self._idle_start_time = None

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        self._camera.close()
