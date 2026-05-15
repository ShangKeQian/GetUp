# GetUp Rust 版本设计文档

## 概述

用 Rust + Tauri 2.0 重写 GetUp 久坐提醒软件，借鉴 Health-reminder 的 Apple 风格 UI，保留所有核心功能。

## 目标

- 内存占用：~20-30MB（比 Python 版降低 70%+）
- 打包大小：~10-20MB
- UI 风格：Apple 风格（Health-reminder 样式）
- 功能完整：键盘/鼠标检测 + 摄像头检测 + 计时器 + 遮罩 + 托盘

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Rust (Tauri 2.0) |
| 前端 | Vite + TypeScript |
| 样式 | CSS Variables (Apple 风格) |
| 检测 | 键盘/鼠标 + 摄像头人脸检测 |
| 打包 | Tauri bundler → 单个 exe |

## 架构

```
┌─────────────────────────────────────────────────┐
│                  GetUp App                       │
│                                                  │
│  ┌──────────────┐    ┌────────────────────────┐ │
│  │  Tauri Shell │    │   Rust Backend         │ │
│  │  (系统托盘)   │───▶│   - 键盘/鼠标监听      │ │
│  │              │    │   - 摄像头检测          │ │
│  │              │    │   - 计时器状态机        │ │
│  └──────────────┘    └──────────┬─────────────┘ │
│                                 │                │
│                    ┌────────────┴────────────┐   │
│                    ▼                         ▼   │
│  ┌─────────────────────┐  ┌─────────────────────┐│
│  │  TypeScript Frontend│  │  System Tray        ││
│  │  - Dashboard        │  │  - 启动/暂停        ││
│  │  - Settings         │  │  - 退出            ││
│  │  - 状态显示          │  │                    ││
│  └─────────────────────┘  └─────────────────────┘│
│                                                  │
│  ┌──────────────────────────────────────────────┐│
│  │  Overlay Window (Webview)                    ││
│  │  - 全屏半透明遮罩                            ││
│  │  - 倒计时显示                                ││
│  │  - Apple 风格 UI                             ││
│  └──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

## 模块设计

### 1. Rust 后端 (src-tauri/)

#### 键盘/鼠标监听
- 使用 `device_query` 或 `rdev` crate 监听全局输入事件
- 更新 last_input_time 时间戳

#### 摄像头检测
- 使用 `rusty_scrfd` crate（SCRFD 模型 + ONNX Runtime）
- 高性能人脸检测，支持边界框和关键点
- 每次检测打开/释放摄像头（与 Python 版一致）

#### 计时器状态机
- 三状态：IDLE、TIMING、OVERLAY
- 使用 `std::time::Instant` 获取精确时间

#### 系统托盘
- 使用 Tauri 内置的系统托盘 API
- 图标颜色：绿色(有人)、红色(无人)、黄色(暂停)

### 2. TypeScript 前端 (src/)

#### Dashboard
- 显示当前状态（有人/无人/暂停）
- 显示倒计时
- 显示检测模式

#### Settings
- 工作时间配置
- 活动时间配置
- 摄像头选择

#### Overlay
- 全屏半透明遮罩
- 倒计时显示
- 关闭按钮

### 3. 样式 (src/styles/)

使用 CSS Variables 实现 Apple 风格：
- 圆角、阴影
- 渐变色
- 动画效果

## 文件结构

```
GetUp-Rust/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── tray.rs
│   │   ├── hooks.rs
│   │   ├── camera.rs
│   │   ├── timer.rs
│   │   └── commands.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/
│   ├── main.ts
│   ├── App.vue (或 App.tsx)
│   ├── components/
│   │   ├── Dashboard.vue
│   │   ├── Settings.vue
│   │   └── Overlay.vue
│   └── styles/
│       └── main.css
├── package.json
└── vite.config.ts
```

## 依赖

### Rust (Cargo.toml)
- tauri = "2.0"
- rusty_scrfd = "1.2"
- opencv = "0.88" (用于摄像头捕获)
- device_query = "1.0" 或 rdev

### 前端 (package.json)
- vite
- typescript
- @tauri-apps/api

## 验证方案

1. 编译并运行，验证 Dashboard 显示
2. 验证键盘/鼠标监听（状态切换）
3. 验证摄像头人脸检测（rusty_scrfd）
4. 验证遮罩显示和倒计时
5. 验证设置保存和加载
6. 验证系统托盘功能
7. 检查内存占用（目标：~20-30MB）
