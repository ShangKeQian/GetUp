# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

GetUp 是一个 Windows 系统托盘应用，检测用户是否在电脑前，连续久坐后弹出遮罩提醒起身活动。

## 常用命令

```bash
pip install -r requirements.txt   # 安装依赖
python main.py                    # 运行应用
pytest tests/                     # 运行测试
pytest tests/test_timer.py -v     # 运行单个测试
python make_icon.py               # 重新生成 GetUp.ico（改了图标绘制后运行）
python build.py                   # 打包为 exe (输出到 dist/GetUp/)
```

打包后需手动关闭 GetUp.exe 进程再重新编译，否则 dist 目录会被占用。

## 架构

**线程模型：**

- 主线程：PySide6 (Qt) 事件循环 + 所有 UI 更新
- tick 线程：`main.py _tick_loop` 每秒调用 `PresenceDetector.tick()` → `timer.tick()`，回调经 `_CallbackSignal` 投递主线程
- 旧 tick 线程与检测器由 `_reap_worker` **后台回收**，不在主线程 join（避免 UI 冻结最长 3s）

**跨线程通信（关键）：**

TimerEngine 的回调（on_show_overlay、on_update_work_time 等）在 tick 线程触发，但 UI 更新必须在 Qt 主线程执行。通过 `_CallbackSignal` 类实现：tick 线程调用 `self._ui_cb.post(fn)` 将回调投入队列，Qt 信号槽的 `QueuedConnection` 自动将回调投递到主线程事件循环执行。**不得使用 `QTimer.singleShot` 从非主线程调度 UI 更新**——它是静态方法，从 tick 线程调用时回调不会投递到主线程。

**检测逻辑（detectors/presence.py — PresenceDetector.tick() 三阶段）：**

- Phase 1（锁内）：判定是否需要摄像头检测——键鼠 5 秒内有操作、或 5 秒内摄像头见过人 → 直接用缓存判定，跳过检测
- Phase 2（锁外）：需要时执行 `camera.check_once()`（打开/读帧可达数百毫秒至数秒，**不持锁**，不阻塞 `wake()`/`is_sleeping()`）
- Phase 3（锁内）：应用检测结果、更新在位/休眠状态
- 摄像头打开失败按 30→60→120s 指数退避（上限 `_BACKOFF_MAX=120`），被占用时不再每 5 秒阻塞一次

**计时器状态机（timer.py）：**

- IDLE → TIMING → OVERLAY
- 有人时累计工作时间，无人时不累计
- 无人超过 break_seconds 重置为 IDLE
- 遮罩显示时：人回来暂停倒计时，人离开恢复倒计时

**遮罩窗口（overlay.py）：**

- 横向全屏、纵向 1/3 居中区域
- 240px 环形进度条（RingProgress）+ 倒计时文字
- 底部三张提示卡片（站立伸展/走动一下/远眺放松，纯文字+边框）
- 300ms 淡入动画

**摄像头（detectors/camera.py）：**

- 启动时打开摄像头（DSHOW 后端），check_once() 抓一帧做人脸检测
- 内部有 threading.Lock 保护，支持从 tick 线程安全调用
- 休眠时释放摄像头节省资源，唤醒时自动重新打开
- tick 线程 finally 中调用 `presence.close()`（而非直接 `camera.close()`），由 PresenceDetector 统一管理资源

**懒加载（性能关键约束）：**

- cv2、mediapipe 与 blaze_face 模型均**首次使用时才 import/加载**（实测省约 2.4s 导入 + 57MB 常驻内存）
- 新代码不得在模块顶层 import 重库；`tests/test_lazy_imports.py` 守护此约束
- 打包需显式 `--hidden-import cv2`（build.py / GetUp.spec 已配置），新增懒加载模块时同样要补

**在位检测（detectors/presence.py — PresenceDetector）：**

- 内聚键鼠空闲轮询 + CameraDetector + 5 秒节流 + 休眠超时
- `tick() -> bool`：一次检测周期，内部持有 `threading.Lock` 与 `wake()` 互斥
- 空闲时长由模块级 `get_idle_seconds()` 提供（Win32 `GetLastInputInfo` 轮询，无键盘钩子）；
  无监听器可启停，`close()` 幂等释放摄像头（`_closed` 守卫）

**配置（config.py）：**

- JSON 配置文件（config.json），支持 work_minutes / break_minutes / camera_index / startup_enabled / sleep_timeout_minutes
- 范围校验（CONSTRAINTS）：越界值拒绝并打印 stderr 警告，JSON 加载时越界回退默认值
- startup_enabled 通过 Windows 注册表 HKCU\...\Run 实现开机启动
- 类型检查时接受 float 类型的整数值（如 `30.0` → `30`）

**UI 主题（theme.py）：**

- Fluent Design QSS 样式表定义（颜色、字体、控件样式）
- 共享工具函数：`fmt_mmss()` 时间格式化、`STATUS_MAP` 状态→(标签, 颜色) 映射
- 三套色板：主色板（浅色设置窗口）、遮罩色板（深蓝灰）、休息色板（浅绿）

**系统托盘（tray.py）：**

- 基于 PySide6 QSystemTrayIcon 的托盘图标和右键菜单
- 状态图标绘制（有人=人形/无人=双人/暂停=双竖条/休眠=月亮，彩色圆底白色图形）
- 状态感知菜单：工作中显示已工作时间+下次休息、无人显示离开状态、暂停显示恢复操作、休眠显示唤醒操作
- `on_wake` 回调：唤醒操作独立于暂停/恢复操作

**摄像头工具（camera_utils.py）：**

- 摄像头枚举辅助函数

**关键依赖：**

- PySide6 - GUI 框架（主窗口、遮罩、系统托盘）
- opencv-python - 摄像头捕获（使用 DSHOW 后端加速）
- mediapipe - 人脸检测（blaze_face_short_range.tflite 模型文件需在项目根目录）

> `requirements.txt` 已包含全部依赖（含 PySide6），`pip install -r requirements.txt` 即可。
> 版本号唯一来源是 `config.VERSION`，发布打 tag / 打包均从它读取。

## Coding Guidelines

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

### 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

Define success criteria. Loop until verified.

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```
