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

        # 右上角关闭按钮
        close_btn = tk.Button(
            self._window, text="✕", font=("Arial", 16, "bold"),
            fg="white", bg="#444444", activebackground="#666666",
            bd=0, padx=8, pady=2, command=self._on_close,
        )
        close_btn.place(x=screen_w - 50, y=10)

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
            frame, text="点击右上角 ✕ 关闭", font=("Microsoft YaHei", 14),
            fg="#888888", bg="black"
        ).pack(pady=(30, 0))

        self._window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.update_countdown(self._remaining)

    def update_countdown(self, seconds: int):
        import time as _time
        print(f"[OVERLAY] update_countdown called: seconds={seconds}, time={_time.time():.3f}", flush=True)
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
