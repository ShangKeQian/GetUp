# GetUp Rust 版本实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Rust + Tauri 2.0 重写 GetUp 久坐提醒软件，内存占用降低 70%+

**Architecture:** Tauri 2.0 后端处理系统级操作（键盘/鼠标监听、摄像头检测、系统托盘），TypeScript 前端提供 Apple 风格 UI（Dashboard、设置、遮罩）

**Tech Stack:** Rust, Tauri 2.0, TypeScript, Vite, rusty_scrfd, opencv

---

## 文件结构

```
GetUp-Rust/
├── src-tauri/
│   ├── src/
│   │   ├── main.rs              # 入口
│   │   ├── lib.rs               # 库入口
│   │   ├── tray.rs              # 系统托盘
│   │   ├── hooks.rs             # 键盘/鼠标钩子
│   │   ├── camera.rs            # 摄像头检测
│   │   ├── timer.rs             # 计时器状态机
│   │   └── commands.rs          # Tauri 命令
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/
│   ├── main.ts                  # 前端入口
│   ├── App.vue                  # 主组件
│   ├── components/
│   │   ├── Dashboard.vue        # 仪表盘
│   │   ├── Settings.vue         # 设置
│   │   └── Overlay.vue          # 遮罩
│   └── styles/
│       └── main.css             # Apple 风格样式
├── package.json
└── vite.config.ts
```

---

### Task 1: Tauri 项目初始化

**Files:**
- Create: `GetUp-Rust/` (项目目录)
- Create: `GetUp-Rust/src-tauri/Cargo.toml`
- Create: `GetUp-Rust/src-tauri/tauri.conf.json`
- Create: `GetUp-Rust/package.json`
- Create: `GetUp-Rust/vite.config.ts`

- [ ] **Step 1: 创建 Tauri 项目**

```bash
cd C:\Users\ShangKeQian\OneDrive\Desktop\GetUp
npm create tauri-app@latest GetUp-Rust
cd GetUp-Rust
```

选择：Vanilla + TypeScript

- [ ] **Step 2: 安装依赖**

```bash
npm install
npm install @tauri-apps/api
```

- [ ] **Step 3: 更新 Cargo.toml**

```toml
[package]
name = "getup"
version = "0.1.0"
edition = "2021"

[dependencies]
tauri = { version = "2.0", features = ["tray-icon"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
device_query = "1.0"
opencv = "0.88"
rusty_scrfd = "1.2"
tokio = { version = "1.0", features = ["full"] }

[build-dependencies]
tauri-build = { version = "2.0", features = [] }
```

- [ ] **Step 4: 更新 tauri.conf.json**

```json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:1420",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "GetUp",
        "width": 800,
        "height": 600,
        "resizable": true,
        "fullscreen": false
      }
    ],
    "security": {
      "csp": null
    }
  }
}
```

- [ ] **Step 5: 编译测试**

```bash
cargo build
```

- [ ] **Step 6: Commit**

```bash
git add .
git commit -m "feat: initialize Tauri project"
```

---

### Task 2: 计时器状态机

**Files:**
- Create: `GetUp-Rust/src-tauri/src/timer.rs`
- Test: `GetUp-Rust/src-tauri/src/timer_test.rs`

- [ ] **Step 1: 创建 timer.rs**

```rust
use std::time::Instant;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum TimerState {
    Idle,
    Timing,
    Overlay,
}

pub struct Timer {
    pub state: TimerState,
    work_seconds: f64,
    break_seconds: f64,
    elapsed: f64,
    pub break_remaining: f64,
    last_tick: Instant,
    overlay_paused: bool,
}

impl Timer {
    pub fn new(work_minutes: u32, break_minutes: u32) -> Self {
        Self {
            state: TimerState::Idle,
            work_seconds: work_minutes as f64 * 60.0,
            break_seconds: break_minutes as f64 * 60.0,
            elapsed: 0.0,
            break_remaining: 0.0,
            last_tick: Instant::now(),
            overlay_paused: false,
        }
    }

    pub fn on_person_detected(&mut self) {
        match self.state {
            TimerState::Idle => {
                self.state = TimerState::Timing;
                self.elapsed = 1.0;
            }
            TimerState::Overlay => {
                self.overlay_paused = true;
            }
            _ => {}
        }
    }

    pub fn on_person_absent(&mut self) {
        if self.state == TimerState::Overlay {
            self.overlay_paused = false;
        }
    }

    pub fn on_overlay_dismissed(&mut self) {
        self.state = TimerState::Timing;
        self.elapsed = 0.0;
        self.overlay_paused = false;
    }

    pub fn tick(&mut self) -> Option<TimerEvent> {
        let now = Instant::now();
        let dt = now.duration_since(self.last_tick).as_secs_f64();
        self.last_tick = now;

        match self.state {
            TimerState::Timing => {
                self.elapsed += dt;
                if self.elapsed >= self.work_seconds {
                    self.state = TimerState::Overlay;
                    self.break_remaining = self.break_seconds;
                    self.overlay_paused = false;
                    return Some(TimerEvent::ShowOverlay);
                }
            }
            TimerState::Overlay => {
                if !self.overlay_paused {
                    self.break_remaining -= dt;
                    if self.break_remaining <= 0.0 {
                        self.state = TimerState::Timing;
                        self.elapsed = 0.0;
                        return Some(TimerEvent::CloseOverlay);
                    }
                    return Some(TimerEvent::UpdateCountdown(self.break_remaining as i32));
                }
            }
            _ => {}
        }
        None
    }
}

pub enum TimerEvent {
    ShowOverlay,
    UpdateCountdown(i32),
    CloseOverlay,
}
```

- [ ] **Step 2: 编译测试**

```bash
cargo build
```

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/timer.rs
git commit -m "feat: add timer state machine"
```

---

### Task 3: 键盘/鼠标钩子

**Files:**
- Create: `GetUp-Rust/src-tauri/src/hooks.rs`

- [ ] **Step 1: 创建 hooks.rs**

```rust
use device_query::{DeviceQuery, DeviceState, Key, MouseButton};
use std::sync::{Arc, Mutex};
use std::time::Instant;

pub struct InputHooks {
    last_input_time: Arc<Mutex<Instant>>,
    running: bool,
}

impl InputHooks {
    pub fn new() -> Self {
        Self {
            last_input_time: Arc::new(Mutex::new(Instant::now())),
            running: false,
        }
    }

    pub fn start(&mut self) {
        self.running = true;
        let last_input = self.last_input_time.clone();

        std::thread::spawn(move || {
            let device_state = DeviceState::new();
            let mut last_keys = Vec::new();
            let mut last_mouse = Vec::new();

            while {
                let keys = device_state.get_keys();
                let mouse = device_state.get_mouse();

                if keys != last_keys || mouse.buttons != last_mouse {
                    if let Ok(mut t) = last_input.lock() {
                        *t = Instant::now();
                    }
                    last_keys = keys;
                    last_mouse = mouse.buttons;
                }

                std::thread::sleep(std::time::Duration::from_millis(100));
                true
            } {}
        });
    }

    pub fn stop(&mut self) {
        self.running = false;
    }

    pub fn get_last_input_time(&self) -> Instant {
        self.last_input_time.lock().copied().unwrap_or_else(|| Instant::now())
    }

    pub fn idle_seconds(&self) -> f64 {
        self.get_last_input_time().elapsed().as_secs_f64()
    }
}
```

- [ ] **Step 2: 编译测试**

```bash
cargo build
```

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/hooks.rs
git commit -m "feat: add keyboard/mouse hooks"
```

---

### Task 4: 摄像头检测

**Files:**
- Create: `GetUp-Rust/src-tauri/src/camera.rs`

- [ ] **Step 1: 创建 camera.rs**

```rust
use opencv::{core, imgproc, objdetect, videoio};
use std::path::Path;

pub struct CameraDetector {
    camera_index: i32,
    cascade: objdetect::CascadeClassifier,
}

impl CameraDetector {
    pub fn new(camera_index: i32, cascade_path: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let mut cascade = objdetect::CascadeClassifier::default();
        if Path::new(cascade_path).exists() {
            cascade.load(cascade_path)?;
        }
        Ok(Self {
            camera_index,
            cascade,
        })
    }

    pub fn check_once(&self) -> bool {
        let mut cap = match videoio::VideoCapture::new(self::camera_index, videoio::CAP_ANY) {
            Ok(cap) => cap,
            Err(_) => return false,
        };

        if !cap.is_opened().unwrap_or(false) {
            return false;
        }

        // Warm up
        std::thread::sleep(std::time::Duration::from_millis(500));

        // Discard stale frames
        let mut frame = core::Mat::default();
        for _ in 0..3 {
            let _ = cap.read(&mut frame);
        }

        // Read frame
        if !cap.read(&mut frame).unwrap_or(false) {
            return false;
        }

        // Convert to grayscale
        let mut gray = core::Mat::default();
        imgproc::cvt_color(&frame, &mut gray, imgproc::COLOR_BGR2GRAY, 0).unwrap_or_default();

        // Detect faces
        let mut faces = core::Vector::<core::Rect>::new();
        self.cascade
            .detect_multi_scale(
                &gray,
                &mut faces,
                1.1,
                3,
                objdetect::CASCADE_SCALE_IMAGE,
                core::Size::new(50, 50),
                core::Size::new(0, 0),
            )
            .unwrap_or_default();

        !faces.is_empty()
    }
}
```

- [ ] **Step 2: 编译测试**

```bash
cargo build
```

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/camera.rs
git commit -m "feat: add camera face detection"
```

---

### Task 5: 系统托盘

**Files:**
- Create: `GetUp-Rust/src-tauri/src/tray.rs`

- [ ] **Step 1: 创建 tray.rs**

```rust
use tauri::{
    tray::{TrayIconBuilder, TrayIconEvent, MouseButton, MouseButtonState},
    Manager, Runtime,
};

pub fn create_tray(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let _tray = TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .tooltip("GetUp - 久坐提醒")
        .on_tray_icon_event(|tray_icon, event| {
            match event {
                TrayIconEvent::Click {
                    button: MouseButton::Left,
                    button_state: MouseButtonState::Up,
                    ..
                } => {
                    // Double click to toggle
                }
                TrayIconEvent::Click {
                    button: MouseButton::Right,
                    button_state: MouseButtonState::Up,
                    ..
                } => {
                    // Show menu
                }
                _ => {}
            }
        })
        .build(app)?;

    Ok(())
}
```

- [ ] **Step 2: 编译测试**

```bash
cargo build
```

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/tray.rs
git commit -m "feat: add system tray"
```

---

### Task 6: Tauri 命令

**Files:**
- Create: `GetUp-Rust/src-tauri/src/commands.rs`

- [ ] **Step 1: 创建 commands.rs**

```rust
use tauri::State;
use std::sync::Mutex;
use crate::timer::{Timer, TimerState};
use crate::hooks::InputHooks;

pub struct AppState {
    pub timer: Mutex<Timer>,
    pub hooks: Mutex<InputHooks>,
    pub running: Mutex<bool>,
}

#[tauri::command]
pub fn get_status(state: State<'_, AppState>) -> String {
    let timer = state.timer.lock().unwrap();
    match timer.state {
        TimerState::Idle => "idle".to_string(),
        TimerState::Timing => "timing".to_string(),
        TimerState::Overlay => "overlay".to_string(),
    }
}

#[tauri::command]
pub fn get_countdown(state: State<'_, AppState>) -> f64 {
    let timer = state.timer.lock().unwrap();
    timer.break_remaining
}

#[tauri::command]
pub fn toggle_detection(state: State<'_, AppState>) -> bool {
    let mut running = state.running.lock().unwrap();
    *running = !*running;
    *running
}

#[tauri::command]
pub fn dismiss_overlay(state: State<'_, AppState>) {
    let mut timer = state.timer.lock().unwrap();
    timer.on_overlay_dismissed();
}
```

- [ ] **Step 2: 编译测试**

```bash
cargo build
```

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/commands.rs
git commit -m "feat: add Tauri commands"
```

---

### Task 7: 主程序集成

**Files:**
- Create: `GetUp-Rust/src-tauri/src/main.rs`
- Create: `GetUp-Rust/src-tauri/src/lib.rs`

- [ ] **Step 1: 创建 lib.rs**

```rust
pub mod timer;
pub mod hooks;
pub mod camera;
pub mod tray;
pub mod commands;
```

- [ ] **Step 2: 创建 main.rs**

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::sync::Mutex;
use getup::timer::Timer;
use getup::hooks::InputHooks;
use getup::commands::AppState;

fn main() {
    let timer = Timer::new(30, 2);
    let hooks = InputHooks::new();

    tauri::Builder::default()
        .manage(AppState {
            timer: Mutex::new(timer),
            hooks: Mutex::new(hooks),
            running: Mutex::new(false),
        })
        .invoke_handler(tauri::generate_handler![
            getup::commands::get_status,
            getup::commands::get_countdown,
            getup::commands::toggle_detection,
            getup::commands::dismiss_overlay,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

- [ ] **Step 3: 编译测试**

```bash
cargo build
```

- [ ] **Step 4: Commit**

```bash
git add src-tauri/src/main.rs src-tauri/src/lib.rs
git commit -m "feat: integrate all backend modules"
```

---

### Task 8: 前端 Dashboard

**Files:**
- Create: `GetUp-Rust/src/App.vue`
- Create: `GetUp-Rust/src/components/Dashboard.vue`
- Create: `GetUp-Rust/src/styles/main.css`

- [ ] **Step 1: 创建 main.css (Apple 风格)**

```css
:root {
  --bg-primary: #f5f5f7;
  --bg-card: #ffffff;
  --text-primary: #1d1d1f;
  --text-secondary: #86868b;
  --accent-green: #34c759;
  --accent-red: #ff3b30;
  --accent-yellow: #ffcc00;
  --border-radius: 12px;
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.card {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  padding: 24px;
  margin: 16px;
}

.status-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
}

.status-present {
  background: rgba(52, 199, 89, 0.15);
  color: var(--accent-green);
}

.status-absent {
  background: rgba(255, 59, 48, 0.15);
  color: var(--accent-red);
}

.status-paused {
  background: rgba(255, 204, 0, 0.15);
  color: var(--accent-yellow);
}
```

- [ ] **Step 2: 创建 Dashboard.vue**

```vue
<template>
  <div class="dashboard">
    <div class="card">
      <h1>GetUp</h1>
      <p class="subtitle">久坐提醒</p>
      
      <div class="status-section">
        <span :class="['status-badge', statusClass]">{{ statusText }}</span>
      </div>

      <div class="countdown-section" v-if="status === 'overlay'">
        <div class="countdown">{{ formatCountdown(countdown) }}</div>
        <p>请起身活动</p>
      </div>

      <div class="timer-section" v-else-if="status === 'timing'">
        <div class="timer">{{ formatTimer(elapsed) }}</div>
        <p>已工作时间</p>
      </div>

      <button class="toggle-btn" @click="toggle">
        {{ running ? '暂停' : '启动' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { invoke } from '@tauri-apps/api/tauri';

const status = ref('idle');
const countdown = ref(0);
const elapsed = ref(0);
const running = ref(false);

const statusText = computed(() => {
  switch (status.value) {
    case 'idle': return '等待中';
    case 'timing': return '计时中';
    case 'overlay': return '休息提醒';
    default: return '未知';
  }
});

const statusClass = computed(() => {
  if (status.value === 'overlay') return 'status-absent';
  if (status.value === 'timing') return 'status-present';
  return 'status-paused';
});

function formatCountdown(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function formatTimer(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

async function toggle() {
  running.value = await invoke('toggle_detection');
}

onMounted(async () => {
  status.value = await invoke('get_status');
  countdown.value = await invoke('get_countdown');
});
</script>

<style scoped>
.dashboard {
  padding: 20px;
  max-width: 400px;
  margin: 0 auto;
}

h1 {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 4px;
}

.subtitle {
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.status-section {
  margin-bottom: 24px;
}

.countdown-section {
  text-align: center;
  margin-bottom: 24px;
}

.countdown {
  font-size: 64px;
  font-weight: 700;
  color: var(--accent-red);
}

.timer-section {
  text-align: center;
  margin-bottom: 24px;
}

.timer {
  font-size: 48px;
  font-weight: 600;
  color: var(--accent-green);
}

.toggle-btn {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: var(--border-radius);
  background: var(--accent-green);
  color: white;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.toggle-btn:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(52, 199, 89, 0.3);
}
</style>
```

- [ ] **Step 3: 创建 App.vue**

```vue
<template>
  <Dashboard />
</template>

<script setup lang="ts">
import Dashboard from './components/Dashboard.vue';
</script>

<style>
@import './styles/main.css';
</style>
```

- [ ] **Step 4: 编译测试**

```bash
npm run build
cargo build
```

- [ ] **Step 5: Commit**

```bash
git add src/
git commit -m "feat: add Dashboard with Apple-style UI"
```

---

### Task 9: 设置界面

**Files:**
- Create: `GetUp-Rust/src/components/Settings.vue`

- [ ] **Step 1: 创建 Settings.vue**

```vue
<template>
  <div class="settings">
    <div class="card">
      <h2>设置</h2>
      
      <div class="form-group">
        <label>连续工作时间（分钟）</label>
        <input type="number" v-model.number="workMinutes" min="5" max="120">
      </div>

      <div class="form-group">
        <label>建议活动时间（分钟）</label>
        <input type="number" v-model.number="breakMinutes" min="1" max="30">
      </div>

      <div class="form-group">
        <label>摄像头</label>
        <select v-model="cameraIndex">
          <option v-for="i in 10" :key="i" :value="i-1">Camera {{ i-1 }}</option>
        </select>
      </div>

      <div class="button-group">
        <button class="save-btn" @click="save">保存</button>
        <button class="cancel-btn" @click="cancel">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { invoke } from '@tauri-apps/api/tauri';

const workMinutes = ref(30);
const breakMinutes = ref(2);
const cameraIndex = ref(1);

async function save() {
  await invoke('save_config', {
    workMinutes: workMinutes.value,
    breakMinutes: breakMinutes.value,
    cameraIndex: cameraIndex.value,
  });
}

function cancel() {
  // Emit close event
}
</script>

<style scoped>
.settings {
  padding: 20px;
  max-width: 400px;
  margin: 0 auto;
}

h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 20px;
}

label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

input, select {
  width: 100%;
  padding: 12px;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  font-size: 16px;
  background: var(--bg-primary);
}

.button-group {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.save-btn, .cancel-btn {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.save-btn {
  background: var(--accent-green);
  color: white;
}

.cancel-btn {
  background: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid #d2d2d7;
}
</style>
```

- [ ] **Step 2: 编译测试**

```bash
npm run build
cargo build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/Settings.vue
git commit -m "feat: add Settings component"
```

---

### Task 10: 遮罩界面

**Files:**
- Create: `GetUp-Rust/src/components/Overlay.vue`

- [ ] **Step 1: 创建 Overlay.vue**

```vue
<template>
  <div class="overlay" v-if="visible">
    <div class="overlay-content">
      <h1>请起身活动</h1>
      <div class="countdown">{{ formatCountdown(countdown) }}</div>
      <p class="hint">点击右上角关闭</p>
      <button class="close-btn" @click="close">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { invoke } from '@tauri-apps/api/tauri';

const props = defineProps<{
  visible: boolean;
  countdown: number;
}>();

const emit = defineEmits<{
  close: [];
}>();

function formatCountdown(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

async function close() {
  await invoke('dismiss_overlay');
  emit('close');
}
</script>

<style scoped>
.overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.overlay-content {
  text-align: center;
  color: white;
}

h1 {
  font-size: 48px;
  font-weight: 700;
  margin-bottom: 24px;
}

.countdown {
  font-size: 96px;
  font-weight: 700;
  color: #00ff88;
  margin-bottom: 24px;
}

.hint {
  font-size: 18px;
  color: #888;
  margin-bottom: 24px;
}

.close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  font-size: 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
```

- [ ] **Step 2: 编译测试**

```bash
npm run build
cargo build
```

- [ ] **Step 3: Commit**

```bash
git add src/components/Overlay.vue
git commit -m "feat: add Overlay component"
```

---

### Task 11: 集成测试

- [ ] **Step 1: 编译完整项目**

```bash
cargo build --release
```

- [ ] **Step 2: 运行测试**

```bash
cargo run
```

- [ ] **Step 3: 验证功能**
- Dashboard 显示正常
- 键盘/鼠标监听工作
- 系统托盘显示
- 设置界面可用
- 遮罩显示正常

- [ ] **Step 4: 检查内存占用**

在任务管理器中查看 GetUp.exe 内存占用，目标：~20-30MB

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "feat: complete Rust implementation with testing"
```

---

### Task 12: 打包发布

- [ ] **Step 1: 配置 Tauri 打包**

在 `tauri.conf.json` 中添加：

```json
{
  "bundle": {
    "active": true,
    "targets": "all",
    "identifier": "com.getup.app",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

- [ ] **Step 2: 构建安装包**

```bash
cargo tauri build
```

- [ ] **Step 3: 测试安装包**

运行生成的安装程序，验证功能正常

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat: add build configuration for distribution"
```
