# GetUp 开发文档

> GetUp 是一个 Windows 系统托盘应用，通过键盘鼠标活动和摄像头人脸检测判断用户是否在电脑前，连续久坐后弹出全屏遮罩提醒起身活动。
>
> **本项目完全由 AI 编写**，使用 OpenCode 作为开发工具。

---

## 目录

1. [项目架构](#项目架构)
2. [线程模型](#线程模型)
3. [模块说明](#模块说明)
4. [UI 系统](#ui-系统)
5. [计时器状态机](#计时器状态机)
6. [在位检测逻辑](#在位检测逻辑)
7. [配置系统](#配置系统)
8. [测试](#测试)
9. [构建与分发](#构建与分发)
10. [开发指南](#开发指南)
11. [更新日志](#更新日志)

---

## 项目架构

### 整体结构

```
GetUp/
├── main.py              # 入口：应用生命周期、线程调度、跨线程通信
├── timer.py             # 计时器状态机（IDLE → TIMING → OVERLAY）
├── config.py            # 配置管理（JSON 文件 + Windows 注册表开机自启）
├── overlay.py           # 遮罩窗口（提醒模式 + 休息计时模式）
├── main_window.py       # 设置窗口（状态卡片 + 分组设置面板）
├── tray.py              # 系统托盘图标与状态感知右键菜单
├── theme.py             # 全局主题常量与 QSS 样式表
├── camera_utils.py      # 摄像头枚举工具
├── detectors/
│   └── camera.py        # 摄像头人脸检测（MediaPipe BlazeFace）
├── tests/               # 单元测试
├── build.py             # PyInstaller 打包脚本
├── requirements.txt     # Python 依赖
├── blaze_face_short_range.tflite  # MediaPipe 人脸检测模型（gitignore）
├── config.json          # 运行时配置（自动生成，gitignore）
└── GetUp.spec           # PyInstaller spec 文件（版本控制中）
```

### 数据流

```
┌─────────────────────────────────────────────────────────┐
│                     tick 线程 (1Hz)                      │
│  pynput 键鼠监听 → idle_time                            │
│  CameraDetector.check_once() → face_detected            │
│         ↓                                               │
│  TimerEngine.tick() / on_person_detected() / absent()   │
│         ↓ 回调                                           │
│  _CallbackSignal.post(fn) ──→ Qt 信号槽 ──→ 主线程      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                     Qt 主线程                            │
│  OverlayWindow.update_countdown()                       │
│  MainWindow.update_work_countdown() / update_status()   │
│  SystemTray.update_presence() / update_work_elapsed()   │
└─────────────────────────────────────────────────────────┘
```

---

## 线程模型

本项目有两个线程，**所有 UI 操作必须在 Qt 主线程执行**。

| 线程 | 职责 | 运行方式 |
|------|------|----------|
| **主线程** | PySide6 事件循环、所有 UI 更新、窗口管理 | `QApplication.exec()` |
| **tick 线程** | pynput 键鼠监听、摄像头检测、`TimerEngine.tick()` | `threading.Thread(daemon=True)` |

### 跨线程通信：`_CallbackSignal`

tick 线程的回调（`on_show_overlay`、`on_update_work_time` 等）在 tick 线程触发，但 UI 更新必须在 Qt 主线程执行。解决方案：

```python
class _CallbackSignal(QObject):
    fired = Signal()

    def __init__(self):
        super().__init__()
        self._callbacks = deque()
        self.fired.connect(self._drain, type=Qt.ConnectionType.QueuedConnection)

    def post(self, fn):
        self._callbacks.append(fn)
        self.fired.emit()  # 触发信号，通过 QueuedConnection 投递到主线程
```

**关键点：**
- `QueuedConnection` 确保 `_drain` 在主线程事件循环中执行
- tick 线程调用 `self._ui_cb.post(lambda: widget.update())` 安全更新 UI
- **禁止**从非主线程调用 `QTimer.singleShot`——它是静态方法，从 tick 线程调用时回调不会投递到主线程

### 线程安全的 tick 循环

```python
def _tick_loop(self, generation):
    # generation 参数用于检测是否应退出（暂停/重启时 generation 递增）
    while self._running and self._tick_generation == generation:
        # 1. 检测在位状态
        # 2. 调用 timer.on_person_detected() / on_person_absent()
        # 3. 调用 timer.tick()
        # 4. 检查是否需要进入休眠
        # 5. 更新 UI（通过 _ui_cb.post）
        time.sleep(1)
```

暂停/重启时：
1. `_running = False` + `_tick_generation += 1` → 旧线程自然退出
2. `old_thread.join(timeout=3)` → 等待旧线程结束
3. 启动新线程

---

## 模块说明

### `main.py` — 应用入口

`GetUpApp` 类管理整个应用生命周期：

| 方法 | 说明 |
|------|------|
| `__init__()` | 创建 QApplication、Config、TimerEngine、CameraDetector、OverlayWindow、MainWindow、SystemTray |
| `_toggle_detection()` | 启动/暂停检测（线程安全） |
| `_tick_loop(generation)` | tick 线程主循环 |
| `_bind_timer_callbacks()` | 将 TimerEngine 回调绑定到 UI 更新方法 |
| `_restart_detection()` | 设置保存后重启检测（重建 TimerEngine 和 CameraDetector） |
| `_quit()` | 停止线程、释放摄像头、退出应用 |

### `timer.py` — 计时器状态机

纯逻辑模块，不依赖任何 UI 库。线程安全（内部使用 `threading.Lock`）。

```python
class State(Enum):
    IDLE = "idle"       # 空闲，等待有人出现
    TIMING = "timing"   # 计时中，累计工作时间
    OVERLAY = "overlay" # 遮罩已弹出，休息倒计时中
```

**回调接口（由 main.py 绑定）：**

| 回调 | 触发时机 |
|------|----------|
| `on_show_overlay` | 工作时间达到阈值，需要弹出遮罩 |
| `on_update_countdown(seconds)` | 遮罩倒计时更新（每秒） |
| `on_update_work_time(elapsed)` | 工作时间更新（每秒） |
| `on_close_overlay` | 休息倒计时结束 |
| `on_reset_work_time` | 工作计时重置（回到 IDLE 时） |

### `config.py` — 配置管理

```python
DEFAULTS = {
    "work_minutes": 30,          # 连续工作提醒阈值（分钟）
    "break_minutes": 2,          # 休息倒计时时长（分钟）
    "camera_index": 0,           # 摄像头设备索引
    "startup_enabled": False,    # 开机自启
    "sleep_timeout_minutes": 15, # 无人休眠阈值（分钟）
}
```

- `Config` 类通过 `__getattr__`/`__setattr__` 暴露配置为属性
- 类型检查：赋值时验证类型与默认值一致
- `set_startup()` 通过 Windows 注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 实现

### `detectors/camera.py` — 摄像头人脸检测

```python
class CameraDetector:
    check_once() -> Optional[bool]  # True=检测到人脸, False=未检测到, None=摄像头错误
    release()                        # 释放摄像头（休眠时调用）
    close()                          # 释放摄像头 + 释放人脸检测器
```

- 使用 OpenCV DSHOW 后端打开摄像头（加速）
- 分辨率设为 320×240（够用即可，减少计算量）
- `threading.Lock` 保护，支持从 tick 线程安全调用
- 懒初始化：首次 `check_once()` 时才打开摄像头

### `camera_utils.py` — 摄像头枚举

```python
enumerate_cameras(max_index=10) -> list[dict]
# 返回: [{"index": 0, "name": "Camera 0 (1920x1080, DSHOW)"}, ...]
```

在设置窗口的后台线程中调用，通过 `Signal` 将结果传回主线程填充下拉框。

---

## UI 系统

### 主题体系 (`theme.py`)

定义三套色板和对应的 QSS 样式表：

| 色板 | 用途 | 主要颜色 |
|------|------|----------|
| **主色板** | 设置窗口、状态卡片 | `#f8faf9` 背景、`#22c55e` 绿色强调 |
| **遮罩色板** | 久提提醒遮罩 | `#0f172a` 深蓝灰背景、`#22c55e` 绿色环 |
| **休息色板** | 休息计时窗口 | `#f0fdf4` 浅绿背景、`#14532d` 深绿文字 |

**状态色：**

| 状态 | 颜色 | 用途 |
|------|------|------|
| 有人 | `#22c55e` (绿) | 托盘图标、状态指示器 |
| 无人 | `#f59e0b` (琥珀) | 托盘图标、状态指示器 |
| 暂停 | `#6366f1` (靛蓝) | 托盘图标、状态指示器 |
| 休眠 | `#6b7280` (灰) | 托盘图标、状态指示器 |

**QSS 样式表：**

| 样式表 | 应用对象 | 说明 |
|--------|----------|------|
| `MAIN_WINDOW_STYLE` | MainWindow | 浅色主题、白色卡片、绿色按钮 |
| `OVERLAY_STYLE` | OverlayWindow | 深色主题、半透明按钮 |
| `REST_STYLE` | RestTimerWindow | 浅绿主题、绿色强调 |

### 设置窗口 (`main_window.py`)

**窗口尺寸：** 520×760 固定

**布局结构：**
```
┌─────────────────────────────┐
│ ☕  GetUp 设置              │  ← 标题栏（logo + 标题 + 版本号）
│     v1.2.0                  │
├─────────────────────────────┤
│ [状态药丸]  有人             │  ← 状态卡片
│ 距休息还有                   │
│      30:00                  │  ← 大字倒计时
├─────────────────────────────┤
│ ┌─ 计时器 ────────────────┐ │
│ │ ⏱ 工作时长    [− 30 +] 分│ │  ← 分组设置卡片
│ │ ☕ 休息时长    [−  2 +] 分│ │     每组有标题、图标、描述
│ └─────────────────────────┘ │
│ ┌─ 在位检测 ──────────────┐ │
│ │ 📷 摄像头索引   [▼ 选择] │ │
│ └─────────────────────────┘ │
│ ┌─ 智能休眠 ──────────────┐ │
│ │ 🌙 自动休眠        [开关] │ │
│ │ ⏱ 休眠阈值    [− 15 +] 分│ │
│ └─────────────────────────┘ │
│ ┌─ 系统 ──────────────────┐ │
│ │ 💻 开机自启动      [开关] │ │
│ │ 🔔 通知声音        [开关] │ │
│ └─────────────────────────┘ │
├─────────────────────────────┤
│  [恢复默认]  [保存设置]     │  ← 底部按钮
└─────────────────────────────┘
```

**自定义控件：**

| 控件 | 类 | 说明 |
|------|-----|------|
| 数字调节器 | `FluentSpinbox` | 水平 −/+ 按钮 + 数值显示，支持 `step` 参数 |
| 开关 | `FluentToggle` | 44×24 滑块开关，绿色选中态 |
| 状态药丸 | `StatusPill` | 圆角药丸形标签，自动根据文字映射颜色 |

### 遮罩窗口 (`overlay.py`)

#### 提醒模式 (`OverlayWindow`)

全屏深色遮罩，连续工作超时后弹出。

**布局结构：**
```
┌─────────────────────────────────────────────┐
│                            [✕ 关闭]         │  ← 右上角关闭按钮
│                                             │
│            该起身活动了                      │  ← 标题 (32px)
│         站起来伸展一下吧                     │  ← 副标题 (16px)
│                                             │
│           ╭─────────────╮                   │
│          │   ╭───────╮   │                  │
│          │  │  5:00  │   │  ← 260×260 环形进度条
│          │  │休息倒计时│   │     带绿色辉光效果
│          │   ╰───────╯   │                  │
│           ╰─────────────╯                   │
│                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │  ← 三张提示卡片
│  │☕ 站立伸展│ │🚶 走动一下│ │👀 远眺放松│    │     彩色图标 + 文字
│  └──────────┘ └──────────┘ └──────────┘    │
│                                             │
│            [跳过本次提醒]                    │  ← 跳过按钮
│                                             │
│     按 Esc 关闭 · Space 暂停计时            │  ← 键盘提示
└─────────────────────────────────────────────┘
```

**关键实现：**
- `RingProgress`：260×260 自绘环形进度条，带半透明辉光层
- 首次显示时全屏覆盖 + 300ms 淡入动画
- `showOverlay()` / `updateCountdown(seconds)` / `destroyOverlay()` API

#### 休息计时模式 (`RestTimerWindow`)

全屏浅绿遮罩，休息期间显示。

**布局结构：**
```
┌─────────────────────────────────────────────┐
│                   [提前结束休息]             │
│                                             │
│            ╭ · · · · · · · ╮               │
│           │  ╭───────────╮  │               │  ← 220×220 呼吸动画环
│           │ │    3:12    │  │               │     三层同心圆脉冲动画
│           │ │   休息中    │  │               │
│           │  ╰───────────╯  │               │
│            ╰ · · · · · · · ╮               │
│                                             │
│           做得好，休息一下                   │
│     起身走动、喝水、看看窗外...              │
│                                             │
│     ┌──────────────────────────────┐        │  ← 进度条
│     │████████████████░░░░░░░░░░░░░░│        │     已耗时 / 总时长
│     └──────────────────────────────┘        │
│              1:48              5:00          │
│                                             │
│      3            4h 12m         15m        │  ← 统计行
│  今日休息次数   今日工作时长   今日休息时长  │
│                                             │
│          休息结束后自动返回工作计时           │
└─────────────────────────────────────────────┘
```

**关键实现：**
- `BreathingRing`：220×220 三层同心圆，`sin()` 驱动脉冲动画（~20fps）
- 进度条实时更新（已耗时/总时长）
- 统计数据通过 `show_rest(rest_count, today_work_seconds, today_rest_seconds)` 传入

### 系统托盘 (`tray.py`)

**图标绘制：** 64×64 彩色圆 + 白色图形（人形/双人/暂停/月亮），颜色随状态变化。

**悬停提示（tooltip）：** 鼠标悬停时显示状态和下次休息倒计时（如 "GetUp · 工作中\n下次休息: 25:30"）。

**右键菜单（状态感知）：**

| 状态 | 菜单内容 |
|------|----------|
| **工作中** | 标题 "GetUp · 工作中"、在位检测状态、摄像头状态、暂停监控、设置、退出 |
| **无人** | 标题 "GetUp · 无人"、摄像头待机、设置、退出 |
| **已暂停** | 标题 "GetUp · 已暂停"、监控已暂停、恢复监控、设置、退出 |
| **休眠中** | 标题 "GetUp · 休眠"、智能休眠中、摄像头已释放、唤醒、设置、退出 |

**API：**
- `update_work_elapsed(seconds, remaining=0)` — 更新工作时间和剩余时间，触发 tooltip 更新
- `update_presence(present)` — 更新在位状态
- `update_running(running)` — 更新运行状态
- `update_sleeping(sleeping)` — 更新休眠状态

---

## 计时器状态机

```
              有人出现
    IDLE ─────────────→ TIMING
     ↑                    │
     │  无人超过            │ 达到 work_minutes
     │  break_minutes      ↓
     │                  OVERLAY
     │                    │
     └────────────────────┘
       倒计时结束/被关闭
       (elapsed 重置为 0)
```

### 状态转换规则

| 当前状态 | 事件 | 下一状态 | 说明 |
|----------|------|----------|------|
| IDLE | `on_person_detected()` | TIMING | 有人出现，开始计时，重置 elapsed |
| TIMING | `tick()` 累计 ≥ work_seconds | OVERLAY | 触发 `on_show_overlay` 回调 |
| TIMING | 无人 ≥ break_seconds | IDLE | 重置 elapsed，触发 `on_reset_work_time` |
| OVERLAY | `tick()` 倒计时 ≤ 0 | TIMING | 触发 `on_close_overlay`，重置 elapsed |
| OVERLAY | `on_overlay_dismissed()` | TIMING | 用户手动关闭，重置 elapsed |
| OVERLAY | `on_person_detected()` | OVERLAY | 暂停倒计时（`_overlay_paused = True`） |
| OVERLAY | `on_person_absent()` | OVERLAY | 恢复倒计时（`_overlay_paused = False`） |

### 无人计时逻辑

TIMING 状态下有人离开时：
1. 记录 `_absence_start = time.monotonic()`
2. 每次 `tick()` 检查 `absence_duration >= break_seconds`
3. 如果超时 → 回到 IDLE，重置 elapsed
4. 如果人在超时前回来 → 取消离开状态，继续累计工作时间

---

## 在位检测逻辑

每秒执行一次（在 tick 线程中）：

```
1. idle_time = 当前时间 - 最后一次键鼠操作时间

2. 如果处于休眠状态：
   └── idle_time < 5秒 → 唤醒，标记为有人

3. 如果非休眠状态：
   ├── idle_time < 5秒 → 有人（键鼠活动）
   ├── 最后一次摄像头检测到人 < 5秒 → 有人（跳过重复检测）
   └── 距上次摄像头检测 ≥ 5秒 → 调用 camera.check_once()
       ├── 检测到人脸 → 有人，更新 last_camera_found_time
       └── 未检测到 → 无人

4. 更新 timer 状态

5. 如果无人且 timer 状态为 IDLE：
   └── 累计无人时间 ≥ sleep_timeout → 进入休眠，释放摄像头
```

### 摄像头检测优化

- **DSHOW 后端**：Windows 下比默认后端快很多
- **320×240 分辨率**：降低计算量，人脸检测不需要高分辨率
- **缓冲区大小 1**：`CAP_PROP_BUFFERSIZE = 1`，避免读到旧帧
- **5 秒检测间隔**：避免频繁调用摄像头
- **5 秒缓存**：检测到人后 5 秒内直接认为有人，跳过重复检测

---

## 配置系统

### 配置文件 (`config.json`)

```json
{
  "work_minutes": 30,
  "break_minutes": 2,
  "camera_index": 0,
  "startup_enabled": false,
  "sleep_timeout_minutes": 15
}
```

### 配置热更新流程

用户在设置窗口点击"保存设置"后：

1. `MainWindow._save()` → 更新 `Config` 对象属性
2. `Config.save()` → 写入 `config.json`
3. 调用 `on_save` 回调 → `GetUpApp._on_settings_saved()`
4. `_restart_detection()` → 停止旧线程 → 重建 TimerEngine + CameraDetector → 重启线程

---

## 测试

### 运行测试

```bash
pytest tests/                    # 运行所有测试
pytest tests/test_timer.py -v    # 运行单个测试文件
pytest tests/ -k "overlay"       # 按名称过滤
```

### 测试文件

| 文件 | 覆盖范围 |
|------|----------|
| `test_timer.py` | TimerEngine 状态转换、计时逻辑 |
| `test_overlay.py` | OverlayWindow 回调调用、倒计时更新 |
| `test_negative_countdown.py` | 负数倒计时边界处理 |
| `test_tray_state.py` | SystemTray 状态更新逻辑 |
| `test_config.py` | Config 读写、类型检查、默认值 |
| `test_detectors.py` | CameraDetector 懒初始化、释放、重开 |
| `test_camera_error.py` | 摄像头错误处理 |
| `test_camera_utils.py` | 摄像头枚举 |
| `test_thread_sync.py` | 并发 tick 和 dismiss 的线程安全 |

### 测试技巧

UI 组件测试使用 `__new__()` 绕过 `__init__`，手动注入 mock 属性：

```python
def test_overlay_destroy_calls_callback():
    overlay = OverlayWindow.__new__(OverlayWindow)
    overlay._is_shown = True
    overlay._on_close_callback = MagicMock()
    overlay._ring = MagicMock()  # 替换 UI 组件为 mock
    overlay.hide = MagicMock()
    overlay.destroy_overlay()
    overlay._on_close_callback.assert_called_once()
```

---

## 构建与分发

### 打包命令

```bash
python build.py
```

### 打包配置

- **模式：** `--onedir --windowed`（目录模式，无控制台）
- **输出：** `dist/GetUp/`
- **捆绑资源：**
  - `blaze_face_short_range.tflite` — MediaPipe 人脸检测模型
  - MediaPipe 原生库（`libmediapipe.dll`、`modules/`、`metadata/`）
- **隐藏导入：** `pynput.keyboard._win32`、`pynput.mouse._win32`、`mediapipe.*`

### 注意事项

- 打包前必须关闭已运行的 `GetUp.exe`，否则 `dist/` 目录被占用（`taskkill /F /IM GetUp.exe`）
- PySide6 需要手动安装（不在 `requirements.txt` 中）
- 打包后首次运行可能较慢（MediaPipe 模型加载）
- `config.json`、`blaze_face_short_range.tflite`、`dist/`、`build/` 均被 gitignore

### GitHub Release

```bash
# 1. 打包
python build.py

# 2. 压缩
Compress-Archive -Path "dist\GetUp\*" -DestinationPath "dist\GetUp-vX.Y.Z.zip" -Force

# 3. 创建标签并推送
git tag -a vX.Y.Z -m "GetUp vX.Y.Z"
git push origin vX.Y.Z

# 4. 通过 GitHub API 创建 Release 并上传 zip（或手动在网页操作）
```

---

## 开发指南

### 编码原则

1. **先想后写** — 明确假设，不确定就问
2. **简单优先** — 最少代码解决问题，不做投机性抽象
3. **精确修改** — 只改必须改的，不顺手"改进"无关代码
4. **目标驱动** — 定义验证标准，循环直到通过

### 添加新设置项

1. 在 `config.py` 的 `DEFAULTS` 中添加默认值
2. 在 `main_window.py` 的 `_init_ui()` 中添加 UI 控件
3. 在 `MainWindow._save()` 中读取控件值写入 config
4. 如果需要运行时生效，在 `GetUpApp._restart_detection()` 中处理

### 修改 UI 主题

1. 编辑 `theme.py` 中的色板常量
2. QSS 样式表会自动引用这些常量
3. 自定义绘制的控件（`FluentToggle`、`StatusPill`、`RingProgress` 等）需要单独更新 paintEvent

### 修改检测逻辑

检测逻辑在 `main.py` 的 `_tick_loop()` 中。修改时注意：
- 所有 UI 更新必须通过 `_ui_cb.post()` 投递到主线程
- 摄像头操作有 `threading.Lock` 保护
- `generation` 参数确保暂停/重启时旧线程正确退出

---

## 更新日志

### v2.1.2 — 托盘 tooltip 优化 (2026-06-04)

#### 功能增强

- **托盘悬停提示**：鼠标悬停时显示下次休息倒计时（如 "GetUp · 工作中\n下次休息: 25:30"）
- **菜单精简**：移除右键菜单中的"已工作时间"和"下次休息倒计时"项，时间信息已通过 tooltip 展示

#### API 变更

- `update_work_elapsed(seconds)` → `update_work_elapsed(seconds, remaining=0)`：新增 `remaining` 参数，自动更新 tooltip

### v2.1.0 — UI 全面重设计 (2026-06-02)

基于 `前端设计/` 目录中的 HTML 设计稿，对所有 UI 组件进行全面重设计。

#### 主题系统重构 (`theme.py`)

- **色板切换**：深色主题 → 浅色主题（`#f8faf9` 背景、`#ffffff` 卡片）
- **强调色**：Windows 蓝 `#0078D4` → 绿色 `#22c55e`
- **新增色板**：遮罩深色（`#0f172a`）、休息浅绿（`#f0fdf4`）、四种状态色
- **新增样式表**：`REST_STYLE`（休息窗口专用）
- **QSS 改进**：圆角增大至 10px、按钮 8px 圆角、新增 `#secondary` 按钮样式

#### 遮罩窗口重设计 (`overlay.py`)

- **全屏覆盖**：从 1/3 屏幕高度 → 真正全屏
- **环形进度条**：`CircularProgress`(160px) → `RingProgress`(260px)，带绿色辉光效果
- **新增元素**：
  - 副标题 "站起来伸展一下吧"
  - 三张提示卡片（站立伸展/走动一下/远眺放松）
  - "跳过本次提醒" 按钮
  - 底部键盘快捷键提示（Esc/Space）
- **新增 `RestTimerWindow`**：
  - 浅绿主题休息计时窗口
  - `BreathingRing` 呼吸动画（三层同心圆脉冲）
  - 水平进度条（已耗时/总时长）
  - 每日统计行（休息次数、工作时长、休息时长）
  - "提前结束休息" 按钮

#### 设置窗口重设计 (`main_window.py`)

- **窗口尺寸**：400×760 → 520×760
- **标题栏**：新增绿色 logo + 版本号
- **分组布局**：设置项按"计时器/在位检测/智能休眠/系统"分组，每组有标题和白色卡片
- **设置行**：新增彩色图标 + 标签 + 描述 + 控件的行布局
- **新增控件**：
  - `FluentSpinbox` 支持 `step` 参数（工作时长步进 5 分钟）
  - "恢复默认" 次要按钮
- **状态药丸**：`StatusPill` 现在根据文字自动映射颜色

#### 系统托盘增强 (`tray.py`)

- **状态感知菜单**：根据当前状态（工作中/无人/暂停/休眠）显示不同菜单内容
- **实时信息**：显示已工作时间、下次休息倒计时、检测状态、摄像头状态
- **菜单样式**：白色背景、圆角、emoji 图标
- **新增 API**：
  - `update_work_elapsed(seconds)` — 更新工作时间显示
  - `update_camera_status(active)` — 更新摄像头状态

#### 测试更新

- overlay 测试：`_progress` → `_ring`（适配新的 RingProgress 控件）
- tray 测试：新增 `_build_menu` mock 和新属性初始化

### v2.1.1 — Bug 修复与代码质量 (2026-06-02)

基于 `/code-review` 和 `/simplify` 工作流的发现，修复 12 项问题并清理代码。

#### Bug 修复

- **Lambda 闭包竞争** (`main.py:230`)：`lambda: self._last_presence` → `lambda p=self._last_presence:`，修复 tick 线程与 Qt 主线程之间的值竞争
- **Timer 竞争** (`main.py:165`)：`_tick_loop` 中 `self._timer` 改为本地引用 `timer`，避免 `_restart_detection` 替换 timer 时旧线程操作新 timer
- **唤醒操作逻辑错误** (`tray.py:202`)：新增 `on_wake` 回调，唤醒不再错误地停止检测
- **休眠状态泄漏** (`main.py:91,254`)：`_toggle_detection` 和 `_restart_detection` 中重置 `_sleeping` 和 `_idle_start_time`
- **FaceDetector 泄漏** (`main.py:191`)：tick 线程 finally 中 `camera.release()` → `camera.close()`，确保释放 face_detector
- **遮罩窗口设置不同步** (`main.py:265`)：`_restart_detection` 中重建 OverlayWindow，修复 `_total_seconds` 不随 break_minutes 更新
- **Config float 拒绝** (`config.py:53`)：接受 JSON float 类型的整数值（如 `30.0` → `30`）

#### 代码清理

- **共享工具函数**：`theme.py` 新增 `fmt_mmss()` 和 `STATUS_MAP`，消除 5 处重复的 MM:SS 格式化和 3 文件各自维护的状态映射
- **死代码移除**：6 个未使用导入（`QFont`, `QBrush`, `QRadialGradient`, `QTimer`, `QWidgetAction`, `REST_BG`）、2 个死字段（`_work_minutes`, `_break_remaining`）、1 个冗余字段（`_camera_active`）、1 个死方法（`StatusPill.setColor`）
- **内联样式统一**：`tray.py` QMenu 样式改用 `SURFACE`/`BORDER`/`FG`/`MUTED` 常量
- **格式化统一**：`main_window.py` 的 `update_work_countdown` 和 `reset_countdown` 改用 `fmt_mmss()`
- **移除无功能 UI**：设置窗口中从未读取的"自动休眠"开关
- **`import math` 位置修正**：从 `paintEvent` 内部移至文件顶部

### v2.0.0 — 代码质量改进 (2026-06-01)

- 全面 bug 修复和代码质量改进
- 移除 GetUp-Rust 目录和构建产物
- 添加构建配置用于分发
