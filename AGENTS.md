# AGENTS.md

GetUp: Windows 系统托盘久坐提醒应用。检测用户是否在电脑前，连续久坐后弹出遮罩提醒起身活动。

## 常用命令

```bash
pip install -r requirements.txt   # 依赖已含 PySide6
python main.py                    # 运行应用
pytest tests/ -v                  # 运行所有测试
pytest tests/test_timer.py -v     # 运行单个测试
python make_icon.py               # 重新生成 GetUp.ico（改了图标绘制后运行）
python build.py                   # 打包（输出 dist/GetUp/，--onedir 模式）
```

打包前必须关闭 GetUp.exe 进程，否则 dist 目录被占用（`taskkill /F /IM GetUp.exe`）。

## 线程模型（易错点）

- 主线程: PySide6 事件循环 + 所有 UI 更新
- tick 线程: PresenceDetector.tick() → timer.tick() → UI 投递
- PresenceDetector 内聚 pynput 监听 + 摄像头检测 + 休眠超时逻辑，位于 `detectors/` 包
- tick 线程回调通过 `_CallbackSignal.post(fn)` 投递到主线程
- **禁止** `QTimer.singleShot` 从非主线程调用（回调不会执行）
- 所有 UI 更新必须在 Qt 主线程
- 退出/重启时旧 tick 线程与检测器**后台回收**（_reap_worker），不得在主线程同步 join
- 摄像头检测不持锁：tick() 三阶段（锁内判定 → 锁外检测 → 锁内应用），
  摄像头打开失败按 30→60→120s 指数退避，避免被占用时反复阻塞
- cv2 / mediapipe / 人脸模型**懒加载**（首次使用才 import），新代码不得在模块顶层引入重库
- 版本号唯一来源是 `config.VERSION`，发布与打包均从它读取

## 关键依赖与资源

- `blaze_face_short_range.tflite` — MediaPipe 人脸模型，必须在项目根目录
- 依赖统一在 requirements.txt（PySide6 / pynput / opencv-python / mediapipe / pytest）
- 摄像头使用 DSHOW 后端，320×240 分辨率，5秒检测间隔

## 测试

全部依赖都在 requirements.txt 中，`pytest tests/ -v` 可直接全量跑（当前 69 个测试）。

UI 测试用 `__new__()` 绕过 `__init__`，手动注入 mock：
```python
overlay = OverlayWindow.__new__(OverlayWindow)
overlay._ring = MagicMock()
```

## Git 与发布

- 提交前必须先向用户确认
- `GetUp.spec` 在版本控制中，其余 `.spec` 文件被忽略
- `config.json`、`blaze_face_short_range.tflite`、`dist/`、`build/`、`build_v220/`、
  `build_tmp_v220/`、`dist_v220/`、`前端设计/` 均被 gitignore
- GitHub Release 使用 `tag_name=vX.Y.Z` 格式
- 发布前核对构建产物 mtime 晚于 tag 提交时间，避免发出内容过期的包

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


