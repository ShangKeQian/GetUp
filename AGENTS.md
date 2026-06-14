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
- tick 线程: PresenceDetector.tick() → timer.tick() → UI 投递
- PresenceDetector 内聚 pynput 监听 + 摄像头检测 + 休眠超时逻辑
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

## 开发原则

### 1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:

State your assumptions explicitly. If uncertain, ask.
If multiple interpretations exist, present them - don't pick silently.
If a simpler approach exists, say so. Push back when warranted.
If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

No features beyond what was asked.
No abstractions for single-use code.
No "flexibility" or "configurability" that wasn't requested.
No error handling for impossible scenarios.
If you write 200 lines and it could be 50, rewrite it.
Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:

Don't "improve" adjacent code, comments, or formatting.
Don't refactor things that aren't broken.
Match existing style, even if you'd do it differently.
If you notice unrelated dead code, mention it - don't delete it.
When your changes create orphans:

Remove imports/variables/functions that YOUR changes made unused.
Don't remove pre-existing dead code unless asked.
The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution
Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

"Add validation" → "Write tests for invalid inputs, then make them pass"
"Fix the bug" → "Write a test that reproduces it, then make it pass"
"Refactor X" → "Ensure tests pass before and after"
For multi-step tasks, state a brief plan:

1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.


