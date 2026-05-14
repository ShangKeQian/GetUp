import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from config import Config


class SettingsDialog:
    def __init__(self, root: tk.Tk, config: Config, on_save: Optional[Callable] = None):
        self._root = root
        self._config = config
        self._on_save = on_save
        self._window: Optional[tk.Toplevel] = None

    def show(self):
        if self._window is not None:
            return

        self._window = tk.Toplevel(self._root)
        self._window.title("GetUp 设置")
        self._window.geometry("320x280")
        self._window.resizable(False, False)
        self._window.attributes("-topmost", True)

        frame = ttk.Frame(self._window, padding=15)
        frame.pack(fill="both", expand=True)

        # 工作时间
        ttk.Label(frame, text="连续工作时间（分钟）：").grid(row=0, column=0, sticky="w", pady=4)
        self._work_var = tk.IntVar(value=self._config.work_minutes)
        ttk.Spinbox(frame, from_=5, to=120, textvariable=self._work_var, width=8).grid(row=0, column=1, pady=4)

        # 活动时间
        ttk.Label(frame, text="建议活动时间（分钟）：").grid(row=1, column=0, sticky="w", pady=4)
        self._break_var = tk.IntVar(value=self._config.break_minutes)
        ttk.Spinbox(frame, from_=1, to=30, textvariable=self._break_var, width=8).grid(row=1, column=1, pady=4)

        # 摄像头编号
        ttk.Label(frame, text="摄像头编号：").grid(row=2, column=0, sticky="w", pady=4)
        self._camera_var = tk.IntVar(value=self._config.camera_index)
        ttk.Spinbox(frame, from_=0, to=9, textvariable=self._camera_var, width=8).grid(row=2, column=1, pady=4)

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="取消", command=self._close).pack(side="left", padx=5)

    def _save(self):
        self._config.work_minutes = self._work_var.get()
        self._config.break_minutes = self._break_var.get()
        self._config.camera_index = self._camera_var.get()
        self._config.save()
        if self._on_save:
            self._on_save()
        self._close()

    def _close(self):
        if self._window:
            self._window.destroy()
            self._window = None
