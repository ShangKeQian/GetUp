"""回归测试：detectors.camera 重库懒加载，降低开机自启影响。

用子进程确保干净的 sys.modules，验证：
- 导入 detectors.camera 与构造 CameraDetector 都不加载 cv2/mediapipe；
- 调用 _init_face_detector() 后才加载 mediapipe（按需加载）。
"""
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(code: str) -> str:
    return subprocess.check_output(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, text=True
    ).strip()


def test_heavy_libs_not_loaded_at_import_or_construction():
    code = (
        "import sys; from detectors.camera import CameraDetector; "
        "CameraDetector(0); "
        "print('cv2' in sys.modules, 'mediapipe' in sys.modules)"
    )
    assert _run(code) == "False False", (
        "导入/构造时应延迟加载 cv2/mediapipe，实际已加载"
    )


def test_mediapipe_loaded_on_demand_after_init_face_detector():
    code = (
        "import sys; from detectors.camera import CameraDetector; "
        "d = CameraDetector(0); d._init_face_detector(); "
        "print('mediapipe' in sys.modules)"
    )
    assert _run(code) == "True", "_init_face_detector() 应按需加载 mediapipe"
