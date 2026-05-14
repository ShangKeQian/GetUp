import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from config import Config
from camera_utils import enumerate_cameras


class SettingsDialog:
    def __init__(self, root: tk.Tk, config: Config, on_save: Optional[Callable] = None):
        self._root = root
        self._config = config
        self._on_save = on_save
        self._window: Optional[tk.Toplevel] = None
        self._cameras = []
        self._camera_names = []

    def show(self):
        if self._window is not None:
            return

        self._cameras = enumerate_cameras()
        self._camera_names = [c["name"] for c in self._cameras]
        if not self._camera_names:
            self._camera_names = ["未检测到摄像头"]

        self._window = tk.Toplevel(self._root)
        self._window.title("GetUp 设置")
        self._window.geometry("400x200")
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

        # 摄像头选择
        ttk.Label(frame, text="摄像头：").grid(row=2, column=0, sticky="w", pady=4)
        self._camera_var = tk.StringVar()
        camera_combo = ttk.Combobox(
            frame, textvariable=self._camera_var,
            values=self._camera_names, state="readonly", width=30
        )
        camera_combo.grid(row=2, column=1, pady=4)
        self._select_current_camera()

        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_frame, text="保存", command=self._save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="取消", command=self._close).pack(side="left", padx=5)

    def _select_current_camera(self):
        for i, cam in enumerate(self._cameras):
            if cam["index"] == self._config.camera_index:
                self._camera_var.set(self._camera_names[i])
                return
        if self._camera_names:
            self._camera_var.set(self._camera_names[0])

    def _save(self):
        self._config.work_minutes = self._work_var.get()
        self._config.break_minutes = self._break_var.get()
        selected_name = self._camera_var.get()
        for cam in self._cameras:
            if cam["name"] == selected_name:
                self._config.camera_index = cam["index"]
                break
        self._config.save()
        if self._on_save:
            self._on_save()
        self._close()

    def _close(self):
        if self._window:
            self._window.destroy()
            self._window = None
