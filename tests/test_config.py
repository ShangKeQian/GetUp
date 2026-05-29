import os
import json
import tempfile
from config import Config


def test_default_values():
    cfg = Config()
    assert cfg.work_minutes == 30
    assert cfg.break_minutes == 2
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


def test_reject_unknown_attribute():
    cfg = Config()
    try:
        cfg.unknown_field = 123
        assert False, "Should have raised AttributeError"
    except AttributeError as e:
        assert "unknown_field" in str(e)


def test_to_dict_returns_defensive_copy():
    cfg = Config()
    d = cfg.to_dict()
    d["work_minutes"] = 999
    assert cfg.work_minutes == 30, "Modifying to_dict() result should not affect config"


def test_corrupt_file_uses_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{{{this is not json!!!")
        cfg = Config(path)
        assert cfg.work_minutes == 30


def test_set_startup_closes_key_on_exception():
    from unittest.mock import patch, MagicMock
    import config as config_module

    mock_key = MagicMock()
    mock_key.__enter__ = MagicMock(return_value=mock_key)
    mock_key.__exit__ = MagicMock(return_value=False)

    with patch("config.winreg.OpenKey", return_value=mock_key), \
         patch("config.winreg.SetValueEx", side_effect=OSError("test error")):
        result = config_module.set_startup(True)
        assert result is False
        mock_key.__exit__.assert_called_once()


def test_corrupt_config_values_use_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"work_minutes": "not_a_number", "break_minutes": 5}, f)
        cfg = Config(path)
        assert cfg.work_minutes == 30
        assert cfg.break_minutes == 5
