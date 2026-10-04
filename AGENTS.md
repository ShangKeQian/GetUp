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
python build.py --deploy          # 打包并部署到 %LOCALAPPDATA%\Programs\GetUp（正式使用用这个）
```

打包前必须关闭 GetUp.exe 进程，否则 dist 目录被占用（`taskkill /F /IM GetUp.exe`）。

## ⚠️ 禁止从项目目录内运行 dist 产物（本项目位于 OneDrive 同步范围内）

直接双击 `dist/GetUp/GetUp.exe` 会启动失败：PyInstaller 引导程序读不到自身内嵌的
PKG 归档，弹出标题为 `Error` 的对话框，正文为
`Could not load PyInstaller's embedded PKG archive from the executable`。
此时进程会因阻塞在该对话框上而留在任务管理器，但 Qt 从未初始化 →
**没有托盘图标、getup.log 也不会生成**，极易误判为托盘 bug。

- 正式使用一律用 `python build.py --deploy`：它把产物复制到
  `%LOCALAPPDATA%\Programs\GetUp`，同步更新 `HKCU\...\Run` 自启动项，并把
  `NotifyIconSettings` 中对应该 exe 的 `IsPromoted` 置 1（Win11 新条目默认落进
  「隐藏的图标」溢出区，看起来同样是"没有托盘图标"）。
- exe 归档本身是好的（cookie 在 `size-88`，`CArchiveReader` 可读），
  换到同步目录之外即可正常运行——同一份字节，仅位置不同。

## 线程模型（易错点）

- 主线程: PySide6 事件循环 + 所有 UI 更新
- tick 线程: PresenceDetector.tick() → timer.tick() → UI 投递
- PresenceDetector 内聚键鼠空闲轮询（Win32 GetLastInputInfo）+ 摄像头检测 + 休眠超时逻辑，位于 `detectors/` 包
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
- 依赖统一在 requirements.txt（PySide6 / opencv-python / mediapipe / pytest）
- 摄像头使用 DSHOW 后端，320×240 分辨率，5秒检测间隔
- **不得在模块顶层安装全局键盘钩子**：键鼠空闲一律走 `detectors.presence.get_idle_seconds()`
  （Win32 `GetLastInputInfo` 轮询）。全局键盘钩子（如 pynput 的 `WH_KEYBOARD_LL`）是键记录器
  特征 API，会显著抬高 Defender / SmartScreen 的启发式误报面
- `version_info.txt` 由 build.py 从 `config.VERSION` 生成（勿手工编辑），供
  `--version-file` 给 exe 打 RT_VERSION；exe 缺版本元数据是安全软件误报的常见诱因
- `GetUp.ico` 由 `make_icon.py` 生成：256×256 用 PNG 载荷，小尺寸用 DIB
  （PNG 压缩项在 ICO 规范里只定义用于 256×256）

## 测试

全部依赖都在 requirements.txt 中，`pytest tests/ -v` 可直接全量跑（当前 95 个测试）。

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


