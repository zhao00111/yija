# Yija Switch Panel

This package is structured for use as a Home Assistant HACS custom repository.

---

## 仓库结构 / Repository Structure

- `custom_components/yija_switch_panel/` — 集成文件（保持原始功能）  
- `hacs.json` — HACS 自定义仓库元数据 / HACS metadata  
- `README.md` — 使用说明 / User Guide

---

## 安装方式 / Installation

### 方式一：通过 HACS 自定义仓库安装 / Install with HACS custom repository

1. 打开 Home Assistant → **HACS** / Open Home Assistant → HACS → Integrations  
2. 点击右上角菜单 → **Custom repositories** / Top-right menu → Custom repositories  
3. 添加仓库 URL / Add this repository URL:
4. 类型选择 **Integration** / Select Integration as type  
5. 安装 **Yija Switch Panel** / Install Yija Switch Panel  
6. 重启 Home Assistant / Restart Home Assistant

### 方式二：手动安装 / Manual Installation

1. 下载仓库 ZIP / Download the repository ZIP  
2. 将 `custom_components/yija_switch_panel/` 复制到 Home Assistant 配置目录 / Copy `custom_components/yija_switch_panel/` into:
3. 重启 Home Assistant / Restart Home Assistant

---

## 功能说明 / Features

- 支持多路开关控制 / Multi-switch control  
- 支持场景触发 / Scene triggers  
- 支持 DP 触发 / DP (Data Point) triggers  
- 天气信息显示 / Weather information display  
- 保留原始设备功能 / Preserves original switch functionality

---

## 注意事项 / Notes

- 安装完成后必须重启 Home Assistant / Restart Home Assistant after installation  
- 更新插件时请确保版本号正确，以便 HACS 自动更新 / Ensure version numbers are correct for HACS updates  
- 如果 HACS 无法识别，请检查仓库结构是否符合标准 / If HACS does not detect the integration, verify repository structure

---

## 电商/用户说明建议 / E-commerce / User Guide Tips

- 提示客户可通过 HACS 一键安装 / Highlight one-click installation via HACS  
- 可在产品详情页加入“无需编程，5分钟完成配置” / Include “No programming required, configure in 5 minutes”  
- 推荐在说明书中附带仓库 URL / Recommend providing repository URL in user manual

