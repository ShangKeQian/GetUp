import json
import os
import sys
import winreg

APP_NAME = "GetUp"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _default_config_path() -> str:
    """配置文件默认路径：优先使用 %APPDATA%/GetUp/，避免重打包后丢失。"""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        config_dir = os.path.join(base, APP_NAME)
        try:
            os.makedirs(config_dir, exist_ok=True)
        except OSError:
            # 回退到程序所在目录
            return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.json")
        return os.path.join(config_dir, "config.json")
    return os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "config.json")

DEFAULTS = {
    "work_minutes": 25,
    "break_minutes": 2,
    "camera_index": 0,
    "startup_enabled": False,
    "sleep_timeout_minutes": 15,
}

CONSTRAINTS = {
    "work_minutes": {"min": 5, "max": 120},
    "break_minutes": {"min": 1, "max": 30},
    "camera_index": {"min": 0, "max": 9},
    "sleep_timeout_minutes": {"min": 5, "max": 120},
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
        self._path = path or _default_config_path()
        self._data = dict(DEFAULTS)
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except (json.JSONDecodeError, ValueError):
                saved = {}
            for key in DEFAULTS:
                if key in saved:
                    expected = type(DEFAULTS[key])
                    val = saved[key]
                    # 接受 float 类型的整数值（JSON 无 int/float 区分）
                    if expected is int and isinstance(val, float) and val == int(val):
                        val = int(val)
                    if isinstance(val, expected):
                        if key in CONSTRAINTS:
                            c = CONSTRAINTS[key]
                            if not (c["min"] <= val <= c["max"]):
                                print(
                                    f"[Config] '{key}' value {val} out of range [{c['min']}, {c['max']}], "
                                    f"using default {DEFAULTS[key]}",
                                    file=sys.stderr,
                                )
                                continue
                        self._data[key] = val

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
                if name in CONSTRAINTS:
                    c = CONSTRAINTS[name]
                    if not (c["min"] <= value <= c["max"]):
                        print(
                            f"[Config] '{name}' value {value} out of range [{c['min']}, {c['max']}]",
                            file=sys.stderr,
                        )
                        raise ValueError(
                            f"Attribute '{name}' value {value} out of range [{c['min']}, {c['max']}]"
                        )
                data[name] = value
            else:
                raise AttributeError(f"Config has no attribute '{name}'")

    def save(self) -> bool:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except OSError as e:
            print(f"[Config] 保存失败: {e}", file=sys.stderr)
            return False

    def to_dict(self) -> dict:
        return dict(self._data)
