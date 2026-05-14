import tkinter as tk
from overlay import OverlayWindow


def test_overlay_creates_window():
    root = tk.Tk()
    root.withdraw()
    overlay = OverlayWindow(root, break_minutes=2)
    assert overlay._window is None  # Not shown yet
    overlay.show()
    assert overlay._window is not None
    overlay.destroy()
    root.destroy()


def test_overlay_countdown_format():
    root = tk.Tk()
    root.withdraw()
    overlay = OverlayWindow(root, break_minutes=2)
    overlay.show()
    overlay.update_countdown(90)
    assert overlay._countdown_label.cget("text") == "01:30"
    overlay.destroy()
    root.destroy()


def test_overlay_on_close_callback():
    root = tk.Tk()
    root.withdraw()
    closed = []
    overlay = OverlayWindow(root, break_minutes=2, on_close=lambda: closed.append(True))
    overlay.show()
    overlay._on_close()
    assert len(closed) == 1
    overlay.destroy()
    root.destroy()
