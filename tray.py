import sys
import threading
import pystray
from PIL import Image, ImageDraw
from config import Config


def create_icon_image(present: bool = True):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if present:
        fill, outline = "#00CC66", "#009944"
    else:
        fill, outline = "#CC3333", "#992222"
    draw.ellipse([8, 8, 56, 56], fill=fill, outline=outline, width=2)
    draw.text((20, 16), "G", fill="white")
    return img


class SystemTray:
    def __init__(self, config: Config, on_start, on_stop, on_quit, on_settings=None):
        self._config = config
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._icon = None
        self._running = False

    def _build_menu(self):
        modes = [
            pystray.MenuItem(
                "键盘鼠标", lambda icon, item: self._set_mode("keyboard_mouse"),
                radio=True, checked=lambda item: self._config.detection_mode == "keyboard_mouse"
            ),
            pystray.MenuItem(
                "摄像头", lambda icon, item: self._set_mode("camera"),
                radio=True, checked=lambda item: self._config.detection_mode == "camera"
            ),
            pystray.MenuItem(
                "同时启用", lambda icon, item: self._set_mode("both"),
                radio=True, checked=lambda item: self._config.detection_mode == "both"
            ),
        ]

        return pystray.Menu(
            pystray.MenuItem("启动", self._on_start, default=True),
            pystray.MenuItem("停止", self._on_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("检测模式", pystray.Menu(*modes)),
            pystray.MenuItem("设置", self._on_settings) if self._on_settings else pystray.Menu.SEPARATOR,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    def _set_mode(self, mode: str):
        self._config.detection_mode = mode
        self._config.save()
        if self._icon:
            self._icon.update_menu()

    def update_presence(self, present: bool):
        if self._icon:
            self._icon.icon = create_icon_image(present)

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
