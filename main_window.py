import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from config import Config, set_startup
from camera_utils import enumerate_cameras


class AppleSpinbox(tk.Frame):
    """Apple风格的数字调节器"""

    def __init__(self, parent, from_=0, to=100, variable=None, **kwargs):
        super().__init__(parent, bg="#2C2C2E", **kwargs)
        self._from = from_
        self._to = to
        self._variable = variable or tk.IntVar(value=from_)

        self._minus_btn = tk.Button(
            self, text="−", font=("SF Pro Text", 16, "bold"),
            fg="#FFFFFF", bg="#3A3A3C", activebackground="#4A4A4C",
            activeforeground="#FFFFFF", relief="flat", width=3, height=1,
            command=self._decrease, cursor="hand2"
        )
        self._minus_btn.pack(side="left", padx=(2, 1), pady=2)

        # 可编辑输入框
        self._entry = tk.Entry(
            self, textvariable=self._variable,
            font=("SF Pro Text", 15), fg="#FFFFFF", bg="#2C2C2E",
            width=4, justify="center", relief="flat",
            insertbackground="#FFFFFF", selectbackground="#0A84FF"
        )
        self._entry.pack(side="left", padx=2, pady=2)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Return>", self._on_focus_out)

        self._plus_btn = tk.Button(
            self, text="+", font=("SF Pro Text", 16, "bold"),
            fg="#FFFFFF", bg="#3A3A3C", activebackground="#4A4A4C",
            activeforeground="#FFFFFF", relief="flat", width=3, height=1,
            command=self._increase, cursor="hand2"
        )
        self._plus_btn.pack(side="left", padx=(1, 2), pady=2)

    def _decrease(self):
        current = self._variable.get()
        if current > self._from:
            self._variable.set(current - 1)

    def _increase(self):
        current = self._variable.get()
        if current < self._to:
            self._variable.set(current + 1)

    def _on_focus_out(self, event=None):
        """输入框失去焦点或按回车时验证输入"""
        try:
            value = self._variable.get()
            if value < self._from:
                self._variable.set(self._from)
            elif value > self._to:
                self._variable.set(self._to)
        except (tk.TclError, ValueError):
            # 输入无效时恢复为最小值
            self._variable.set(self._from)


class AppleToggle(tk.Canvas):
    """Apple风格的开关控件"""

    def __init__(self, parent, variable=None, command=None, **kwargs):
        super().__init__(parent, width=51, height=31, highlightthickness=0, **kwargs)
        self._variable = variable or tk.BooleanVar(value=False)
        self._command = command
        self._draw()
        self.bind("<Button-1>", self._toggle)

    def _draw(self):
        self.delete("all")
        is_on = self._variable.get()
        bg = "#34C759" if is_on else "#39393D"
        # 背景圆角矩形
        self.create_rectangle(2, 2, 49, 29, fill=bg, outline="", width=0)
        self.create_oval(2, 2, 30, 30, fill=bg, outline="")
        self.create_oval(21, 2, 49, 30, fill=bg, outline="")
        # 滑块
        x = 27 if is_on else 4
        self.create_oval(x, 3, x + 25, 28, fill="white", outline="")

    def _toggle(self, event=None):
        self._variable.set(not self._variable.get())
        self._draw()
        if self._command:
            self._command()


class MainWindow:
    def __init__(self, root: tk.Tk, config: Config, on_save: Optional[Callable] = None):
        self._root = root
        self._config = config
        self._on_save = on_save
        self._window: Optional[tk.Toplevel] = None
        self._cameras = []
        self._camera_names = []
        self._status_label = None
        self._status_dot = None
        self._countdown_label = None
        self._cameras_cached = False

    def _cache_cameras(self):
        if self._cameras_cached:
            return
        self._camera_names = ["检测中..."]
        self._cameras_cached = True

        def _scan():
            cameras = enumerate_cameras()
            names = [c["name"] for c in cameras] or ["未检测到摄像头"]
            self._root.after(0, self._on_cameras_scanned, cameras, names)

        threading.Thread(target=_scan, daemon=True).start()

    def _on_cameras_scanned(self, cameras, names):
        self._cameras = cameras
        self._camera_names = names
        if hasattr(self, '_camera_combo') and self._camera_combo is not None:
            self._camera_combo['values'] = names
            self._select_current_camera()

    def show(self):
        if self._window is not None:
            try:
                self._window.lift()
                self._window.focus_force()
                return
            except Exception:
                try:
                    self._window.destroy()
                except Exception:
                    pass
                self._window = None

        self._cache_cameras()

        self._window = tk.Toplevel(self._root)
        self._window.title("GetUp")
        self._window.geometry("380x740")
        self._window.resizable(False, False)
        self._window.configure(bg="#000000")
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)

        self._create_ui()

    def _create_ui(self):
        main_frame = tk.Frame(self._window, bg="#000000")
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # 标题
        header_frame = tk.Frame(main_frame, bg="#000000")
        header_frame.pack(fill="x", pady=(12, 16))

        tk.Label(
            header_frame, text="GetUp",
            font=("SF Pro Display", 28, "bold"), fg="#FFFFFF", bg="#000000"
        ).pack(anchor="w")

        tk.Label(
            header_frame, text="久坐提醒助手",
            font=("SF Pro Text", 15), fg="#8E8E93", bg="#000000"
        ).pack(anchor="w", pady=(4, 0))

        # 状态卡片（固定在顶部）
        status_card = tk.Frame(main_frame, bg="#1C1C1E", highlightbackground="#2C2C2E", highlightthickness=1)
        status_card.pack(fill="x", pady=(0, 8))

        # 状态行
        status_row = tk.Frame(status_card, bg="#1C1C1E")
        status_row.pack(fill="x", padx=20, pady=(20, 16))

        self._status_dot = tk.Canvas(status_row, width=10, height=10, bg="#1C1C1E", highlightthickness=0)
        self._status_dot.pack(side="left", padx=(0, 8))
        self._status_dot.create_oval(1, 1, 9, 9, fill="#34C759", outline="")

        self._status_label = tk.Label(
            status_row, text="有人", font=("SF Pro Text", 15, "bold"),
            fg="#34C759", bg="#1C1C1E"
        )
        self._status_label.pack(side="left")

        # 倒计时
        countdown_frame = tk.Frame(status_card, bg="#1C1C1E")
        countdown_frame.pack(fill="x", padx=20, pady=(0, 20))

        tk.Label(
            countdown_frame, text="剩余工作时间",
            font=("SF Pro Text", 13), fg="#8E8E93", bg="#1C1C1E"
        ).pack(anchor="w", pady=(0, 8))

        self._countdown_label = tk.Label(
            countdown_frame, text=f"{self._config.work_minutes:02d}:00",
            font=("SF Pro Display", 48, "bold"), fg="#FFFFFF", bg="#1C1C1E"
        )
        self._countdown_label.pack(anchor="w")

        # 可滚动的设置区域
        scroll_canvas = tk.Canvas(main_frame, bg="#000000", highlightthickness=0)
        scroll_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=scroll_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_frame = tk.Frame(scroll_canvas, bg="#000000")
        scroll_window = scroll_canvas.create_window(0, 0, window=scroll_frame, anchor="nw", width=scroll_canvas.winfo_reqwidth())

        def _on_frame_configure(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            scroll_canvas.itemconfig(scroll_window, width=scroll_canvas.winfo_width())

        def _on_canvas_configure(event):
            scroll_canvas.itemconfig(scroll_window, width=event.width)

        scroll_frame.bind("<Configure>", _on_frame_configure)
        scroll_canvas.bind("<Configure>", _on_canvas_configure)
        scroll_canvas.bind("<Enter>", lambda e: scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        scroll_canvas.bind("<Leave>", lambda e: scroll_canvas.unbind_all("<MouseWheel>"))

        def _on_mousewheel(event):
            scroll_canvas.yview_scroll(-1 * (event.delta // 120), "units")

        # 设置卡片
        settings_card = tk.Frame(scroll_frame, bg="#1C1C1E", highlightbackground="#2C2C2E", highlightthickness=1)
        settings_card.pack(fill="x", pady=(0, 12))

        tk.Label(
            settings_card, text="设置",
            font=("SF Pro Text", 15, "bold"), fg="#FFFFFF", bg="#1C1C1E"
        ).pack(anchor="w", padx=20, pady=(20, 12))

        # 工作时间
        self._create_setting_row(settings_card, "连续工作时间", "work_minutes",
                                 self._config.work_minutes, 5, 120, "分钟")

        tk.Frame(settings_card, bg="#2C2C2E", height=1).pack(fill="x", padx=20, pady=4)

        # 活动时间
        self._create_setting_row(settings_card, "建议活动时间", "break_minutes",
                                 self._config.break_minutes, 1, 30, "分钟")

        tk.Frame(settings_card, bg="#2C2C2E", height=1).pack(fill="x", padx=20, pady=4)

        # 摄像头
        self._create_camera_row(settings_card)

        tk.Frame(settings_card, bg="#2C2C2E", height=1).pack(fill="x", padx=20, pady=4)

        # 开机启动
        self._create_startup_row(settings_card)

        tk.Frame(settings_card, bg="#2C2C2E", height=1).pack(fill="x", padx=20, pady=4)

        # 休眠超时
        self._create_setting_row(settings_card, "休眠超时", "sleep_timeout",
                                 self._config.sleep_timeout_minutes, 5, 120, "分钟\n无人后进入省电模式")

        tk.Frame(settings_card, bg="#1C1C1E", height=16).pack()

        # 保存按钮
        save_btn = tk.Button(
            scroll_frame, text="保存设置",
            font=("SF Pro Text", 15, "bold"), fg="#FFFFFF", bg="#0A84FF",
            activebackground="#409CFF", activeforeground="#FFFFFF",
            relief="flat", padx=16, pady=12, command=self._save, cursor="hand2"
        )
        save_btn.pack(fill="x")

    def _create_setting_row(self, parent, label_text, attr_name, default_value, min_val, max_val, unit=""):
        row = tk.Frame(parent, bg="#1C1C1E")
        row.pack(fill="x", padx=20, pady=12)

        label_frame = tk.Frame(row, bg="#1C1C1E")
        label_frame.pack(side="left")

        tk.Label(
            label_frame, text=label_text,
            font=("SF Pro Text", 15), fg="#FFFFFF", bg="#1C1C1E"
        ).pack(anchor="w")

        if unit:
            tk.Label(
                label_frame, text=unit,
                font=("SF Pro Text", 12), fg="#8E8E93", bg="#1C1C1E"
            ).pack(anchor="w")

        var = tk.IntVar(value=default_value)
        setattr(self, f"_{attr_name}_var", var)

        spinbox = AppleSpinbox(row, from_=min_val, to=max_val, variable=var)
        spinbox.pack(side="right")

    def _create_camera_row(self, parent):
        row = tk.Frame(parent, bg="#1C1C1E")
        row.pack(fill="x", padx=20, pady=12)

        tk.Label(
            row, text="摄像头",
            font=("SF Pro Text", 15), fg="#FFFFFF", bg="#1C1C1E"
        ).pack(side="left")

        self._camera_var = tk.StringVar()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            "Camera.TCombobox",
            fieldbackground="#2C2C2E", background="#2C2C2E",
            foreground="#FFFFFF", selectbackground="#2C2C2E",
            selectforeground="#FFFFFF", bordercolor="#3A3A3C",
            arrowsize=12
        )

        self._camera_combo = ttk.Combobox(
            row, textvariable=self._camera_var,
            values=self._camera_names, state="readonly",
            width=20, style="Camera.TCombobox", font=("SF Pro Text", 13)
        )
        self._camera_combo.pack(side="right")
        if self._cameras:
            self._select_current_camera()

    def _select_current_camera(self):
        for i, cam in enumerate(self._cameras):
            if cam["index"] == self._config.camera_index:
                self._camera_var.set(self._camera_names[i])
                return
        if self._camera_names:
            self._camera_var.set(self._camera_names[0])

    def _create_startup_row(self, parent):
        row = tk.Frame(parent, bg="#1C1C1E")
        row.pack(fill="x", padx=20, pady=12)

        tk.Label(
            row, text="开机启动",
            font=("SF Pro Text", 15), fg="#FFFFFF", bg="#1C1C1E"
        ).pack(side="left")

        self._startup_var = tk.BooleanVar(value=self._config.startup_enabled)
        toggle = AppleToggle(row, variable=self._startup_var, bg="#1C1C1E")
        toggle.pack(side="right")

    def _save(self):
        self._config.work_minutes = self._work_minutes_var.get()
        self._config.break_minutes = self._break_minutes_var.get()
        self._config.sleep_timeout_minutes = self._sleep_timeout_var.get()
        selected_name = self._camera_var.get()
        for cam in self._cameras:
            if cam["name"] == selected_name:
                self._config.camera_index = cam["index"]
                break
        startup = self._startup_var.get()
        if startup != self._config.startup_enabled:
            self._config.startup_enabled = startup
            set_startup(startup)
        self._config.save()
        if self._on_save:
            self._on_save()

    def update_status(self, status: str):
        if self._status_label and self._status_dot:
            if status == "有人":
                self._status_label.config(text="有人", fg="#34C759")
                self._status_dot.delete("all")
                self._status_dot.create_oval(1, 1, 9, 9, fill="#34C759", outline="")
            elif status == "无人":
                self._status_label.config(text="无人", fg="#FF453A")
                self._status_dot.delete("all")
                self._status_dot.create_oval(1, 1, 9, 9, fill="#FF453A", outline="")
            elif status == "暂停":
                self._status_label.config(text="暂停", fg="#FFD60A")
                self._status_dot.delete("all")
                self._status_dot.create_oval(1, 1, 9, 9, fill="#FFD60A", outline="")
            elif status == "休眠":
                self._status_label.config(text="休眠", fg="#5AC8FA")
                self._status_dot.delete("all")
                self._status_dot.create_oval(1, 1, 9, 9, fill="#5AC8FA", outline="")

    def update_countdown(self, seconds: int):
        if self._countdown_label:
            mins = seconds // 60
            secs = seconds % 60
            self._countdown_label.config(text=f"{mins:02d}:{secs:02d}")

    def update_work_countdown(self, elapsed_seconds: int):
        if self._countdown_label:
            remaining = max(0, self._config.work_minutes * 60 - elapsed_seconds)
            mins = remaining // 60
            secs = remaining % 60
            self._countdown_label.config(text=f"{mins:02d}:{secs:02d}")

    def reset_countdown(self):
        if self._countdown_label:
            mins = self._config.work_minutes
            self._countdown_label.config(text=f"{mins:02d}:00")

    def _on_close(self):
        if self._window:
            self._window.destroy()
        self._window = None
        self._camera_combo = None

    def close(self):
        if self._window:
            self._window.destroy()
        self._window = None
        self._camera_combo = None
