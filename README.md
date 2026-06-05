# GetUp

Windows 系统托盘应用 — 久坐提醒，起身活动。

GetUp 通过键盘鼠标操作和摄像头人脸检测判断你是否在电脑前，连续工作超过设定时长后弹出遮罩提醒你起身休息。

> **本项目完全由 AI 编写**，使用 [OpenCode](https://opencode.ai/) 作为开发工具。

## 功能

- **智能在位检测** — 键盘/鼠标操作 + 摄像头人脸检测，双重判断是否有人
- **久坐提醒** — 连续工作超时后弹出全屏遮罩，显示倒计时环形进度条
- **休息计时** — 遮罩倒计时结束后自动关闭，重新开始工作计时
- **智能休眠** — 离开电脑超过 15 分钟自动释放摄像头，回来后自动恢复
- **系统托盘常驻** — 四种状态图标（有人 / 无人 / 暂停 / 休眠），悬停显示倒计时，右键菜单控制
- **开机自启** — 可选通过 Windows 注册表设置开机自动启动
- **可配置** — 支持自定义工作时长、休息时长、摄像头索引等参数

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.10+
- 摄像头（用于人脸检测）

### 安装依赖

```bash
pip install -r requirements.txt
```

> **注意：** `requirements.txt` 中可能未包含 `PySide6`，需手动安装：
> ```bash
> pip install PySide6
> ```

### 运行

```bash
python main.py
```

### 打包为可执行文件

```bash
python build.py
```

输出到 `dist/GetUp/` 目录。打包前需关闭已运行的 GetUp.exe 进程。

## 配置

运行后在项目目录下生成 `config.json`：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `work_minutes` | 30 | 连续工作多少分钟后弹出提醒 |
| `break_minutes` | 2 | 休息倒计时时长（分钟） |
| `camera_index` | 0 | 摄像头设备索引 |
| `startup_enabled` | false | 是否开机自启 |
| `sleep_timeout_minutes` | 15 | 无人多久后进入休眠释放摄像头 |

## 工作原理

```
在位检测（每秒）
├── 键盘/鼠标 5 秒内有操作 → 有人
├── 5 秒无操作 → 摄像头检测人脸
│   ├── 检测到人脸 → 有人（5 秒内跳过重复检测）
│   └── 未检测到 → 无人
└── 无人 + 摄像头未检测到 → 无人

计时器状态机
├── IDLE（空闲）→ 有人出现 → 开始计时
├── TIMING（计时中）→ 累计工作时间
│   ├── 无人超过 break_minutes → 回到 IDLE
│   └── 达到 work_minutes → 弹出遮罩
└── OVERLAY（遮罩中）→ 休息倒计时
    ├── 人回来 → 暂停倒计时
    ├── 人离开 → 恢复倒计时
    └── 倒计时结束 → 回到 TIMING
```

## 项目结构

```
GetUp/
├── main.py              # 入口，线程调度与跨线程通信
├── timer.py             # 计时器状态机
├── config.py            # 配置管理（JSON + 开机自启）
├── overlay.py           # 休息提醒遮罩窗口
├── main_window.py       # 主设置窗口
├── tray.py              # 系统托盘图标与菜单
├── theme.py             # UI 主题样式
├── camera_utils.py      # 摄像头枚举工具
├── detectors/
│   └── camera.py        # 摄像头人脸检测（MediaPipe）
├── tests/               # 单元测试
├── build.py             # PyInstaller 打包脚本
├── requirements.txt     # Python 依赖
└── config.json          # 运行时配置（自动生成）
```

## 测试

```bash
pytest tests/
```

## 技术栈

- **PySide6** — GUI 框架
- **pynput** — 全局键盘/鼠标监听
- **OpenCV** — 摄像头捕获
- **MediaPipe** — 人脸检测（BlazeFace 模型）
- **PyInstaller** — 打包分发

## 许可证

MIT
