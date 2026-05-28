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
python build.py                   # 打包为 exe (输出到 dist/GetUp/)
```

打包后需手动关闭 GetUp.exe 进程再重新编译，否则 dist 目录会被占用。

## 架构

**线程模型：**
- 主线程：tkinter 事件循环 + UI 更新
- tick 线程：pynput 键盘/鼠标监听 + 每秒调用 timer.tick() + 摄像头检测
- 摄像头线程：后台持续抓图（~10 FPS），主线程从内存读取帧做人脸检测（~2.5ms）

**检测逻辑（main.py _tick_loop）：**
- 键盘/鼠标 5 秒内有操作 → 有人
- 5 秒无操作 → 从摄像头内存帧检测人脸
- 摄像头检测到人 → 5 秒内直接认为有人（跳过重复检测）
- 无人且摄像头也未检测到 → 无人

**计时器状态机（timer.py）：**
- IDLE → TIMING → OVERLAY
- 有人时累计工作时间，无人时不累计
- 无人超过 break_seconds 重置为 IDLE
- 遮罩显示时：人回来暂停倒计时，人离开恢复倒计时

**摄像头（detectors/camera.py）：**
- 异步方案：启动时打开摄像头（DSHOW 后端），后台线程持续抓图
- check_once() 从内存获取最新帧，用 MediaPipe BlazeFace 检测人脸
- 停止时才释放摄像头，避免频繁开关的 ~1.8s 延迟

**配置（config.py）：**
- JSON 配置文件（config.json），支持 work_minutes / break_minutes / camera_index / startup_enabled
- startup_enabled 通过 Windows 注册表 HKCU\...\Run 实现开机启动

**关键依赖：**
- pynput - 全局键盘/鼠标监听
- opencv-python - 摄像头捕获（使用 DSHOW 后端加速）
- mediapipe - 人脸检测（blaze_face_short_range.tflite 模型文件需在项目根目录）
- pystray - 系统托盘（双击打开主窗口通过 menu item 的 default=True 实现）
- tkinter - GUI 界面
