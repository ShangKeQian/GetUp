import time
import threading
from pynput import mouse, keyboard
from detectors.base import BaseDetector


class KeyboardMouseDetector(BaseDetector):
    def __init__(self):
        super().__init__()
        self._running = False
        self._mouse_listener = None
        self._keyboard_listener = None

    def _on_input(self, *args, **kwargs):
        self.mark_activity()

    def start(self):
        if self._running:
            return
        self._running = True

        self._mouse_listener = mouse.Listener(
            on_move=self._on_input,
            on_click=self._on_input,
            on_scroll=self._on_input,
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_input,
            on_release=self._on_input,
        )

        self._mouse_listener.daemon = True
        self._keyboard_listener.daemon = True

        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self):
        self._running = False
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
