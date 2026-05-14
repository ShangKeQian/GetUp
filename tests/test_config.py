import os
import json
import tempfile
from config import Config


def test_default_values():
    cfg = Config()
    assert cfg.work_minutes == 30
    assert cfg.break_minutes == 2
    assert cfg.idle_timeout == 2
    assert cfg.detection_mode == "keyboard_mouse"
    assert cfg.camera_index == 0


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        cfg = Config(path)
        cfg.work_minutes = 45
        cfg.break_minutes = 5
        cfg.save()

        loaded = Config(path)
        assert loaded.work_minutes == 45
        assert loaded.break_minutes == 5


def test_load_missing_file_uses_defaults():
    cfg = Config("/nonexistent/path/config.json")
    assert cfg.work_minutes == 30
