import json
import os
import sys
import winreg

APP_NAME = "GetUp"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

DEFAULTS = {
    "work_minutes": 30,
    "break_minutes": 2,
    "camera_index": 0,
    "startup_enabled": False,
    "sleep_timeout_minutes": 15,
}


def _get_exe_path():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'


def set_startup(enabled: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_exe_path())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


class Config:
    def __init__(self, path: str | None = None):
        self._path = path or os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])), "config.json"
        )
        self._data = dict(DEFAULTS)
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except (json.JSONDecodeError, ValueError):
                saved = {}
            for key in DEFAULTS:
                if key in saved:
                    if isinstance(saved[key], type(DEFAULTS[key])):
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
                expected_type = type(DEFAULTS[name])
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Attribute '{name}' expects {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )
                data[name] = value
            else:
                raise AttributeError(f"Config has no attribute '{name}'")

    def save(self):
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> dict:
        return dict(self._data)
