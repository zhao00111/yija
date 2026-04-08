# Yija Smart Switch Panel Integration (Home Assistant)

🚀 专为涂鸦 Zigbee 智能面板打造的 Home Assistant 集成  
🚀 A powerful Home Assistant integration for Tuya Zigbee smart panels

---

## 📖 Overview | 项目简介

Yija Switch Panel 是一款面向 Home Assistant 的自定义集成，支持多型号 Zigbee 智能开关面板，实现：

- 多按键控制
- 场景切换
- 灯光调光（亮度 + 色温）
- 窗帘控制
- 屏幕UI显示（天气 / 时间 / 名称）

适用于家庭自动化、酒店、办公、智能空间等场景。

---

## ✨ Core Features | 核心功能

- 🔘 Multi-button control（1~8按键）
- 🎬 Scene switching（场景切换）
- 💡 Dimming control（亮度 + 色温）
- 🪟 Curtain control（开 / 关 / 停 / 位置）
- 📺 Screen UI（天气 / 时间 / 名称显示）
- 🔗 Real-time sync（设备与HA状态同步）
- ⚡ Automation ready（自动化深度支持）

---

## 📦 Supported Devices | 支持设备

### 🔹 Non-screen Panels（无屏设备）

| Model | Description |
|------|-------------|
| M8-1 | 1键场景开关 |
| M8-2 | 2键场景开关 |
| M8-3 | 3键场景开关 |
| M8-4 | 4键场景开关 |
| M8-6 | 4开关 + 2固定场景 |
| M9   | 8键（4场景 + 4固定） |

---

### 🔹 Screen Panels（带屏设备）

| Model | Description |
|------|-------------|
| M8-Pro | 4键 + 屏幕（天气 / 时间） |
| M9-Pro | 4键 + 高级UI |
| F3 Pro | 旗舰款 |

---

## ⚙️ System Requirements | 系统要求

- Home Assistant 2024.6+
- Python 3.11+
- Zigbee Coordinator
- Zigbee Network（ZHA 或 Zigbee2MQTT）

---

## 📥 Installation | 安装方法

### ⭐ HACS（推荐）

1. 打开 HACS
2. 添加自定义仓库：
https://github.com/zhao00111/yija
3. 安装 Integration
4. 重启 HA

---

## 🔌 Device Setup | 设备接入

1. 打开 ZHA 或 Zigbee2MQTT
2. 设备进入配对模式
3. 添加设备
4. 自动生成实体

---

## 💡 Lighting Control | 灯光控制

支持：

- 开关控制
- 亮度控制
- 色温控制

---

## 🪟 Curtain Control | 窗帘控制

支持：

- open_cover
- close_cover
- stop_cover
- set_cover_position

---

## ⚠️ Notes | 注意事项

- Tuya TS0601 在 ZHA 下可能不稳定
- 强烈推荐 Zigbee2MQTT
- 建议设备统一型号

---

## 🚀 Roadmap

- 一键绑定 UI
- Zigbee2MQTT 深度适配
- 自动化优化

---

## 👨‍💻 Author

Yija Smart Home

---

## 📄 License

MIT License
