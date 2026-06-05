# AGENTS.md

GetUp: Windows 系统托盘久坐提醒应用。检测用户是否在电脑前，连续久坐后弹出遮罩提醒起身活动。

## 常用命令

```bash
pip install -r requirements.txt   # PySide6 不在 requirements.txt，需单独 pip install PySide6
python main.py                    # 运行应用
pytest tests/ -v                  # 运行所有测试
pytest tests/test_timer.py -v     # 运行单个测试
python build.py                   # 打包（输出 dist/GetUp/，--onedir 模式）
```

打包前必须关闭 GetUp.exe 进程，否则 dist 目录被占用（`taskkill /F /IM GetUp.exe`）。

## 线程模型（易错点）

- 主线程: PySide6 事件循环 + 所有 UI 更新
- tick 线程: pynput 监听 + 摄像头检测 + timer.tick()
- tick 线程回调通过 `_CallbackSignal.post(fn)` 投递到主线程
- **禁止** `QTimer.singleShot` 从非主线程调用（回调不会执行）
- 所有 UI 更新必须在 Qt 主线程

## 关键依赖与资源

- `blaze_face_short_range.tflite` — MediaPipe 人脸模型，必须在项目根目录
- PySide6 — 不在 requirements.txt，需手动安装
- 摄像头使用 DSHOW 后端，320×240 分辨率，5秒检测间隔

## 测试

部分测试（test_overlay.py、test_detectors.py、test_tray_state.py）需要 cv2/PySide6。环境未安装时只跑：
```bash
pytest tests/test_timer.py tests/test_config.py -v
```

UI 测试用 `__new__()` 绕过 `__init__`，手动注入 mock：
```python
overlay = OverlayWindow.__new__(OverlayWindow)
overlay._ring = MagicMock()
```

## Git 与发布

- 提交前必须先向用户确认
- `GetUp.spec` 在版本控制中，其余 `.spec` 文件被忽略
- `config.json`、`blaze_face_short_range.tflite`、`dist/`、`build/` 均被 gitignore
- GitHub Release 使用 `tag_name=vX.Y.Z` 格式
