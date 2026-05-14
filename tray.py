import sys
import threading
import pystray
from PIL import Image, ImageDraw
from config import Config


def create_icon_image(present: bool = True, paused: bool = False):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if paused:
        fill, outline = "#FFCC00", "#CC9900"
    elif present:
        fill, outline = "#00CC66", "#009944"
    else:
        fill, outline = "#CC3333", "#992222"
    draw.ellipse([8, 8, 56, 56], fill=fill, outline=outline, width=2)
    draw.text((20, 16), "G", fill="white")
    return img


class SystemTray:
    def __init__(self, config: Config, on_toggle, on_quit, on_settings=None):
        self._config = config
        self._on_toggle = on_toggle
        self._on_quit = on_quit
        self._on_settings = on_settings
        self._icon = None
        self._running = False

    def _build_menu(self):
        label = "暂停" if self._running else "启动"
        return pystray.Menu(
            pystray.MenuItem(label, self._on_toggle, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("设置", self._on_settings) if self._on_settings else pystray.Menu.SEPARATOR,
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_quit),
        )

    def update_presence(self, present: bool):
        if self._icon:
            self._icon.icon = create_icon_image(present)

    def update_paused(self):
        if self._icon:
            self._icon.icon = create_icon_image(paused=True)

    def start(self):
        self._running = True
        self._icon = pystray.Icon(
            "GetUp",
            create_icon_image(),
            "GetUp - 久坐提醒",
            self._build_menu(),
        )
        self._icon.run()

    def update_running(self, running: bool):
        self._running = running
        if self._icon:
            self._icon.menu = self._build_menu()
            self._icon.update_menu()

    def stop(self):
        self._running = False
        if self._icon:
            self._icon.stop()
