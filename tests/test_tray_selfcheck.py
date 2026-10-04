"""回归测试：托盘可用性启动自检（main.GetUpApp._check_tray）。

窗口模式（console=False）下 stderr 不可见，故未注册成功时追加写入配置文件同目录的
getup.log；正常注册时不产生任何输出，避免日志噪音。
"""
from unittest.mock import MagicMock, patch

from config import Config
from main import GetUpApp


def _make_app(tmp_path, tray_visible):
    app = GetUpApp.__new__(GetUpApp)
    app._tray = MagicMock()
    app._tray.isVisible.return_value = tray_visible
    app._config = Config(path=str(tmp_path / "config.json"))
    return app


def test_check_tray_logs_when_not_registered(tmp_path):
    app = _make_app(tmp_path, tray_visible=False)

    with patch("main.QSystemTrayIcon") as tray_cls:
        tray_cls.isSystemTrayAvailable.return_value = True
        app._check_tray()

    log = tmp_path / "getup.log"
    assert log.exists()
    assert "托盘图标未注册" in log.read_text(encoding="utf-8")


def test_check_tray_logs_when_system_tray_unavailable(tmp_path):
    app = _make_app(tmp_path, tray_visible=True)

    with patch("main.QSystemTrayIcon") as tray_cls:
        tray_cls.isSystemTrayAvailable.return_value = False
        app._check_tray()

    assert "托盘图标未注册" in (tmp_path / "getup.log").read_text(encoding="utf-8")


def test_check_tray_silent_when_registered(tmp_path):
    app = _make_app(tmp_path, tray_visible=True)

    with patch("main.QSystemTrayIcon") as tray_cls:
        tray_cls.isSystemTrayAvailable.return_value = True
        app._check_tray()

    assert not (tmp_path / "getup.log").exists()
