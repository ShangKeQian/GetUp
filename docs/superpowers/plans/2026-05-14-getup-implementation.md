# GetUp 久坐提醒软件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows system tray app that detects user presence and reminds them to stand up after 30 minutes of sitting.

**Architecture:** Event-driven Python app with pluggable detectors (keyboard/mouse via pynput, camera via OpenCV), a state-machine timer engine, and tkinter-based overlay for the reminder. System tray via pystray for background control.

**Tech Stack:** Python 3.10+, pynput, opencv-python, pystray, Pillow, tkinter

---

## File Structure

```
GetUp/
├── main.py                    # Entry point, wires everything together
├── config.py                  # JSON config load/save with defaults
├── detectors/
│   ├── __init__.py            # Exports base class + registry
│   ├── base.py                # Abstract base detector interface
│   ├── keyboard_mouse.py      # pynput-based input listener
│   └── camera.py              # OpenCV frame-diff detector
├── timer.py                   # State machine: idle → timing → overlay
├── overlay.py                 # Full-screen semi-transparent reminder
├── tray.py                    # System tray icon + menu
├── requirements.txt           # pip dependencies
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_detectors.py
│   ├── test_timer.py
│   └── test_overlay.py
└── docs/superpowers/
    ├── specs/
    └── plans/
```

---

### Task 1: Project Setup + Configuration

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create requirements.txt**

```
pynput>=1.7.6
opencv-python>=4.8.0
pystray>=0.19.0
Pillow>=10.0.0
pytest>=7.0.0
```

- [ ] **Step 2: Write the failing test for config**

Create `tests/__init__.py` (empty file).

Create `tests/test_config.py`:

```python
import os
import json
import tempfile
from config import Config


def test_default_values():
    cfg = Config()
    assert cfg.work_minutes == 30
    assert cfg.break_minutes == 2
    assert cfg.idle_timeout == 2
    assert cfg.detection_mode == "keyboard_mouse"
    assert cfg.camera_index == 0


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        cfg = Config(path)
        cfg.work_minutes = 45
        cfg.break_minutes = 5
        cfg.save()

        loaded = Config(path)
        assert loaded.work_minutes == 45
        assert loaded.break_minutes == 5


def test_load_missing_file_uses_defaults():
    cfg = Config("/nonexistent/path/config.json")
    assert cfg.work_minutes == 30
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd GetUp && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: Implement config.py**

```python
import json
import os

DEFAULTS = {
    "work_minutes": 30,
    "break_minutes": 2,
    "idle_timeout": 2,
    "detection_mode": "keyboard_mouse",
    "camera_index": 0,
}


class Config:
    def __init__(self, path: str | None = None):
        self._path = path or os.path.join(
            os.path.dirname(__file__), "config.json"
        )
        self._data = dict(DEFAULTS)
        if os.path.exists(self._path):
            with open(self._path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for key in DEFAULTS:
                if key in saved:
                    self._data[key] = saved[key]

    def __getattr__(self, name: str):
        if name.startswith("_"):
            return super().__getattribute__(name)
        data = object.__getattribute__(self, "_data")
        if name in data:
            return data[name]
        raise AttributeError(f"Config has no attribute '{name}'")

    def __setattr__(self, name: str, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            data = object.__getattribute__(self, "_data")
            if name in DEFAULTS:
                data[name] = value
            else:
                raise AttributeError(f"Config has no attribute '{name}'")

    def save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> dict:
        return dict(self._data)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd GetUp && python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt config.py tests/
git commit -m "feat: add config management with JSON persistence"
```

---

### Task 2: Base Detector Interface

**Files:**
- Create: `detectors/__init__.py`
- Create: `detectors/base.py`

- [ ] **Step 1: Create base detector interface**

Create `detectors/__init__.py`:

```python
from detectors.base import BaseDetector
from detectors.keyboard_mouse import KeyboardMouseDetector
from detectors.camera import CameraDetector

DETECTORS = {
    "keyboard_mouse": KeyboardMouseDetector,
    "camera": CameraDetector,
}
```

Create `detectors/base.py`:

```python
from abc import ABC, abstractmethod
import time


class BaseDetector(ABC):
    """Abstract base for all presence detectors."""

    def __init__(self):
        self._last_activity: float = 0.0

    @property
    def last_activity(self) -> float:
        return self._last_activity

    def mark_activity(self):
        self._last_activity = time.time()

    def is_present(self, idle_timeout: float = 120.0) -> bool:
        if self._last_activity == 0.0:
            return False
        return (time.time() - self._last_activity) < idle_timeout

    @abstractmethod
    def start(self):
        """Start monitoring for activity."""

    @abstractmethod
    def stop(self):
        """Stop monitoring and release resources."""
```

- [ ] **Step 2: Commit**

```bash
git add detectors/
git commit -m "feat: add base detector interface"
```

---

### Task 3: Keyboard/Mouse Detector

**Files:**
- Create: `detectors/keyboard_mouse.py`
- Create: `tests/test_detectors.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_detectors.py`:

```python
import time
from detectors.keyboard_mouse import KeyboardMouseDetector


def test_detector_starts_and_stops():
    det = KeyboardMouseDetector()
    det.start()
    assert det._running is True
    det.stop()
    assert det._running is False


def test_mark_activity_sets_timestamp():
    det = KeyboardMouseDetector()
    before = time.time()
    det.mark_activity()
    after = time.time()
    assert before <= det.last_activity <= after


def test_is_present_within_timeout():
    det = KeyboardMouseDetector()
    det.mark_activity()
    assert det.is_present(idle_timeout=120) is True


def test_is_present_after_timeout():
    det = KeyboardMouseDetector()
    det._last_activity = time.time() - 200
    assert det.is_present(idle_timeout=120) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd GetUp && python -m pytest tests/test_detectors.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'detectors.keyboard_mouse'`

- [ ] **Step 3: Implement keyboard_mouse.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd GetUp && python -m pytest tests/test_detectors.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add detectors/keyboard_mouse.py tests/test_detectors.py
git commit -m "feat: add keyboard/mouse detector with pynput"
```

---

### Task 4: Camera Detector

**Files:**
- Create: `detectors/camera.py`
- Modify: `tests/test_detectors.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_detectors.py`:

```python
import numpy as np
from unittest.mock import patch, MagicMock
from detectors.camera import CameraDetector


def test_camera_detector_no_camera():
    det = CameraDetector(camera_index=99)
    with patch("detectors.camera.cv2.VideoCapture") as mock_cap:
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = False
        mock_cap.return_value = mock_instance
        det.start()
        assert det._running is False


def test_camera_frame_diff_detects_change():
    det = CameraDetector(camera_index=0)
    frame1 = np.zeros((100, 100), dtype=np.uint8)
    frame2 = np.full((100, 100), 255, dtype=np.uint8)
    assert det._frames_differ(frame1, frame2) is True


def test_camera_frame_diff_no_change():
    det = CameraDetector(camera_index=0)
    frame1 = np.zeros((100, 100), dtype=np.uint8)
    frame2 = np.zeros((100, 100), dtype=np.uint8)
    assert det._frames_differ(frame1, frame2) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd GetUp && python -m pytest tests/test_detectors.py::test_camera_frame_diff_detects_change -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement camera.py**

```python
import time
import threading
import numpy as np
import cv2
from detectors.base import BaseDetector


class CameraDetector(BaseDetector):
    def __init__(self, camera_index: int = 0, check_interval: float = 5.0, threshold: int = 5000):
        super().__init__()
        self._camera_index = camera_index
        self._check_interval = check_interval
        self._threshold = threshold
        self._running = False
        self._thread = None
        self._prev_frame = None

    def _frames_differ(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        diff = cv2.absdiff(frame1, frame2)
        return int(np.sum(diff)) > self._threshold

    def _capture_loop(self):
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self._running = False
            return
        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(self._check_interval)
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if self._prev_frame is not None:
                    if self._frames_differ(self._prev_frame, gray):
                        self.mark_activity()
                self._prev_frame = gray
                time.sleep(self._check_interval)
        finally:
            cap.release()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd GetUp && python -m pytest tests/test_detectors.py -v`
Expected: 7 passed (4 from Task 3 + 3 new)

- [ ] **Step 5: Commit**

```bash
git add detectors/camera.py tests/test_detectors.py
git commit -m "feat: add camera detector with frame-diff algorithm"
```

---

### Task 5: Timer Engine (State Machine)

**Files:**
- Create: `timer.py`
- Create: `tests/test_timer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_timer.py`:

```python
import time
from unittest.mock import MagicMock
from timer import TimerEngine, State


def test_initial_state_is_idle():
    engine = TimerEngine(work_minutes=30, idle_timeout=2)
    assert engine.state == State.IDLE


def test_person_detected_transitions_to_timing():
    engine = TimerEngine(work_minutes=30, idle_timeout=2)
    engine.on_person_detected()
    assert engine.state == State.TIMING
    assert engine.elapsed > 0


def test_person_left_resets_to_idle():
    engine = TimerEngine(work_minutes=30, idle_timeout=2)
    engine.on_person_detected()
    engine._last_activity = time.time() - 300
    engine.tick()
    assert engine.state == State.IDLE
    assert engine.elapsed == 0


def test_overlay_shows_when_time_reached():
    engine = TimerEngine(work_minutes=1, idle_timeout=2)
    engine.on_person_detected()
    engine._elapsed = 60
    on_overlay = MagicMock()
    engine.on_show_overlay = on_overlay
    engine.tick()
    assert engine.state == State.OVERLAY
    on_overlay.assert_called_once()


def test_overlay_dismissed_resets():
    engine = TimerEngine(work_minutes=30, idle_timeout=2)
    engine._state = State.OVERLAY
    engine.on_overlay_dismissed()
    assert engine.state == State.TIMING
    assert engine.elapsed == 0


def test_overlay_paused_when_person_returns():
    engine = TimerEngine(work_minutes=30, idle_timeout=2)
    engine._state = State.OVERLAY
    engine.on_person_detected()
    assert engine._overlay_paused is True


def test_elapsed_format():
    engine = TimerEngine(work_minutes=30, idle_timeout=2)
    engine._elapsed = 125
    assert engine.elapsed_formatted == "02:05"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd GetUp && python -m pytest tests/test_timer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'timer'`

- [ ] **Step 3: Implement timer.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd GetUp && python -m pytest tests/test_timer.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add timer.py tests/test_timer.py
git commit -m "feat: add timer engine with state machine"
```

---

### Task 6: Overlay Window

**Files:**
- Create: `overlay.py`
- Create: `tests/test_overlay.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_overlay.py`:

```python
import tkinter as tk
from overlay import OverlayWindow


def test_overlay_creates_window():
    root = tk.Tk()
    root.withdraw()
    overlay = OverlayWindow(root, break_minutes=2)
    assert overlay._window is not None
    overlay.destroy()
    root.destroy()


def test_overlay_countdown_format():
    root = tk.Tk()
    root.withdraw()
    overlay = OverlayWindow(root, break_minutes=2)
    overlay.update_countdown(90)
    assert overlay._countdown_label.cget("text") == "01:30"
    overlay.destroy()
    root.destroy()


def test_overlay_on_close_callback():
    root = tk.Tk()
    root.withdraw()
    closed = []
    overlay = OverlayWindow(root, break_minutes=2, on_close=lambda: closed.append(True))
    overlay._on_close()
    assert len(closed) == 1
    overlay.destroy()
    root.destroy()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd GetUp && python -m pytest tests/test_overlay.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'overlay'`

- [ ] **Step 3: Implement overlay.py**

```python
import tkinter as tk
from typing import Optional, Callable


class OverlayWindow:
    def __init__(self, root: tk.Tk, break_minutes: int = 2, on_close: Optional[Callable] = None):
        self._root = root
        self._break_minutes = break_minutes
        self._on_close_callback = on_close
        self._window: Optional[tk.Toplevel] = None
        self._countdown_label: Optional[tk.Label] = None
        self._remaining = break_minutes * 60

    def show(self):
        if self._window is not None:
            return

        self._remaining = self._break_minutes * 60
        self._window = tk.Toplevel(self._root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.attributes("-alpha", 0.85)
        self._window.configure(bg="black")

        screen_w = self._window.winfo_screenwidth()
        screen_h = self._window.winfo_screenheight()
        self._window.geometry(f"{screen_w}x{screen_h}+0+0")

        self._window.bind("<Escape>", lambda e: self._on_close())

        frame = tk.Frame(self._window, bg="black")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame, text="请起身活动", font=("Microsoft YaHei", 36),
            fg="white", bg="black"
        ).pack(pady=(0, 20))

        self._countdown_label = tk.Label(
            frame, text="", font=("Consolas", 72, "bold"),
            fg="#00FF88", bg="black"
        )
        self._countdown_label.pack()

        tk.Label(
            frame, text="按 Esc 或点击关闭", font=("Microsoft YaHei", 14),
            fg="#888888", bg="black"
        ).pack(pady=(30, 0))

        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_countdown(self._remaining)

    def update_countdown(self, seconds: int):
        self._remaining = seconds
        if self._countdown_label and self._window:
            minutes = seconds // 60
            secs = seconds % 60
            self._countdown_label.config(text=f"{minutes:02d}:{secs:02d}")

    def _on_close(self):
        if self._window:
            self._window.destroy()
            self._window = None
            self._countdown_label = None
        if self._on_close_callback:
            self._on_close_callback()

    def destroy(self):
        if self._window:
            self._window.destroy()
            self._window = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd GetUp && python -m pytest tests/test_overlay.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add overlay.py tests/test_overlay.py
git commit -m "feat: add fullscreen overlay with countdown"
```

---

### Task 7: System Tray

**Files:**
- Create: `tray.py`

- [ ] **Step 1: Implement tray.py**

```python
import sys
import threading
import pystray
from PIL import Image, ImageDraw
from config import Config
from detectors import DETECTORS


def create_icon_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill="#00CC66", outline="#009944", width=2)
    draw.text((20, 16), "G", fill="white")
    return img


class SystemTray:
    def __init__(self, config: Config, on_start, on_stop, on_quit):
        self._config = config
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_quit = on_quit
        self._icon = None
        self._running = False

    def _build_menu(self):
        modes = [
            pystray.MenuItem(
                "键盘鼠标", lambda: self._set_mode("keyboard_mouse"),
                radio=True, checked=lambda: self._config.detection_mode == "keyboard_mouse"
            ),
            pystray.MenuItem(
                "摄像头", lambda: self._set_mode("camera"),
                radio=True, checked=lambda: self._config.detection_mode == "camera"
            ),
            pystray.MenuItem(
                "同时启用", lambda: self._set_mode("both"),
                radio=True, checked=lambda: self._config.detection_mode == "both"
            ),
        ]

        return pystray.Menu(
            pystray.MenuItem("启动", self._on_start, default=True),
            pystray.MenuItem("停止", self._on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("检测模式", pystray.Menu(*modes)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    def _set_mode(self, mode: str):
        self._config.detection_mode = mode
        self._config.save()
        if self._icon:
            self._icon.update_menu()

    def start(self):
        self._running = True
        self._icon = pystray.Icon(
            "GetUp",
            create_icon_image(),
            "GetUp - 久坐提醒",
            self._build_menu(),
        )
        self._icon.run()

    def stop(self):
        self._running = False
        if self._icon:
            self._icon.stop()
```

- [ ] **Step 2: Commit**

```bash
git add tray.py
git commit -m "feat: add system tray with mode switching"
```

---

### Task 8: Main Entry Point + Integration

**Files:**
- Create: `main.py`
- Modify: `detectors/__init__.py`

- [ ] **Step 1: Update detectors/__init__.py**

```python
from detectors.base import BaseDetector
from detectors.keyboard_mouse import KeyboardMouseDetector
from detectors.camera import CameraDetector

DETECTORS = {
    "keyboard_mouse": KeyboardMouseDetector,
    "camera": CameraDetector,
}


def create_detectors(mode: str, camera_index: int = 0) -> list[BaseDetector]:
    if mode == "keyboard_mouse":
        return [KeyboardMouseDetector()]
    elif mode == "camera":
        return [CameraDetector(camera_index=camera_index)]
    elif mode == "both":
        return [KeyboardMouseDetector(), CameraDetector(camera_index=camera_index)]
    return [KeyboardMouseDetector()]
```

- [ ] **Step 2: Implement main.py**

```python
import sys
import time
import threading
import tkinter as tk
from config import Config
from timer import TimerEngine, State
from detectors import create_detectors
from overlay import OverlayWindow
from tray import SystemTray


class GetUpApp:
    def __init__(self):
        self._config = Config()
        self._detectors = []
        self._timer = TimerEngine(
            work_minutes=self._config.work_minutes,
            idle_timeout=self._config.idle_timeout * 60,
        )
        self._root = tk.Tk()
        self._root.withdraw()
        self._overlay = OverlayWindow(
            self._root,
            break_minutes=self._config.break_minutes,
            on_close=self._on_overlay_close,
        )
        self._timer.on_show_overlay = self._show_overlay
        self._tray = SystemTray(
            self._config,
            on_start=self._start_detection,
            on_stop=self._stop_detection,
            on_quit=self._quit,
        )
        self._tick_thread = None
        self._running = False

    def _start_detection(self, icon=None, item=None):
        if self._running:
            return
        self._running = True
        self._detectors = create_detectors(
            self._config.detection_mode,
            self._config.camera_index,
        )
        for det in self._detectors:
            det.start()
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._tick_thread.start()

    def _stop_detection(self, icon=None, item=None):
        self._running = False
        for det in self._detectors:
            det.stop()
        self._detectors = []
        self._timer = TimerEngine(
            work_minutes=self._config.work_minutes,
            idle_timeout=self._config.idle_timeout * 60,
        )
        self._timer.on_show_overlay = self._show_overlay

    def _tick_loop(self):
        while self._running:
            any_present = False
            for det in self._detectors:
                if det.is_present(self._config.idle_timeout * 60):
                    self._timer.on_person_detected()
                    any_present = True
                    break
            if not any_present and self._timer.state == State.TIMING:
                pass
            self._timer.tick()
            time.sleep(1)

    def _show_overlay(self):
        self._root.after(0, self._overlay.show)

    def _on_overlay_close(self):
        self._timer.on_overlay_dismissed()

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
```

- [ ] **Step 3: Commit**

```bash
git add main.py detectors/__init__.py
git commit -m "feat: integrate all components into main app"
```

---

### Task 9: Manual Smoke Test

**Files:**
- None (verification only)

- [ ] **Step 1: Install dependencies and run**

Run: `cd GetUp && pip install -r requirements.txt && python main.py`

Expected:
- System tray icon appears (green circle with "G")
- Keyboard/mouse activity detected (timer starts)
- After 30 min of activity, overlay appears with countdown
- Pressing Esc dismisses overlay
- Tray menu allows mode switching

- [ ] **Step 2: Fix any issues found, commit if needed**

```bash
git add -A
git commit -m "fix: address smoke test issues"
```

---

### Task 10: Package as EXE

**Files:**
- Create: `build.py` (optional build script)

- [ ] **Step 1: Install PyInstaller**

Run: `pip install pyinstaller`

- [ ] **Step 2: Build**

Run: `cd GetUp && pyinstaller --onefile --windowed --name GetUp main.py`

Expected: `dist/GetUp.exe` (~30-50MB)

- [ ] **Step 3: Test the packaged exe**

Run: `dist\GetUp.exe`

Expected: Same behavior as `python main.py` but as standalone exe.

- [ ] **Step 4: Commit build config**

```bash
git add build.py GetUp.spec
git commit -m "feat: add PyInstaller build configuration"
```
