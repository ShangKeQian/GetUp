# AGENTS.md

GetUp: Windows 系统托盘久坐提醒应用。

## 工作流约束

**开发前**: 必须阅读 `doc/DEVELOPMENT.md`，理解架构和模块职责。

**提交前**: 同步更新 `doc/DEVELOPMENT.md` 和 `README.md`。

**Git 提交**: 必须先向用户确认，禁止直接提交。

## 常用命令

```bash
pip install -r requirements.txt   # 安装依赖（PySide6 需单独安装）
python main.py                    # 运行应用
pytest tests/ -v                  # 运行所有测试
pytest tests/test_timer.py -v     # 运行单个测试
python build.py                   # 打包（输出 dist/GetUp/）
```

打包前必须关闭 GetUp.exe 进程，否则 dist 目录被占用。

测试部分模块（camera、overlay、tray）需要 cv2/PySide6，环境未安装时只跑 `test_timer.py` 和 `test_config.py`。

## 关键架构

**线程模型（易错点）**:
- 主线程: PySide6 事件循环 + 所有 UI 更新
- tick 线程: pynput 监听 + 摄像头检测 + timer.tick()

**跨线程通信**:
- tick 线程回调通过 `_CallbackSignal.post(fn)` 投递到主线程
- **禁止** `QTimer.singleShot` 从非主线程调用（回调不会执行）
- 所有 UI 更新必须在 Qt 主线程

**状态机**: IDLE → TIMING → OVERLAY（详见 timer.py）

**摄像头**: MediaPipe 人脸检测，DSHOW 后端，320×240 分辨率，5秒检测间隔

## 文件职责

| 文件 | 职责 |
|------|------|
| main.py | 入口、线程调度、跨线程通信 |
| timer.py | 计时器状态机（纯逻辑，threading.Lock 保护） |
| config.py | JSON 配置 + Windows 注册表开机自启 |
| overlay.py | 休息提醒遮罩（RingProgress + RestTimerWindow） |
| main_window.py | 设置窗口（520×760 固定尺寸） |
| tray.py | 系统托盘图标与状态感知菜单 |
| theme.py | 三套色板 + QSS 样式表 + fmt_mmss() |
| detectors/camera.py | 摄像头人脸检测（懒初始化、release/close 分离） |

## 测试技巧

UI 测试用 `__new__()` 绕过 `__init__`，手动注入 mock：
```python
overlay = OverlayWindow.__new__(OverlayWindow)
overlay._ring = MagicMock()
```

## 编码原则

1. 先想后写，不确定就问
2. 最少代码解决问题
3. 只改必须改的
4. 每次修改后运行测试验证
