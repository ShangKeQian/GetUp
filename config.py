import json
import os

DEFAULTS = {
    "work_minutes": 30,
    "break_minutes": 2,
    "detection_mode": "camera",
    "camera_index": 1,
}


class Config:
    def __init__(self, path: str | None = None):
        self._path = path or os.path.join(
            os.getcwd(), "config.json"
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
