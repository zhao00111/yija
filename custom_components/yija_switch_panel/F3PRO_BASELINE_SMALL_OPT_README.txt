F3 Pro 基准线小优化版

改动仅一处：
- quirks/ts0601_switch_screen.py

改动内容：
- 调光组（Light Group 1~4）的 Power / Brightness / Color Temp 改为默认启用
- 窗帘组（Curtain Group 1~4）的 Control / Position 改为默认启用

目的：
- 减少用户手动启用后等待初始化的过程
- 尽量避免 Curtain Group Control 刚启用时动作选项需要等待一段时间才显示

未改动：
- DP 点位
- 名称同步逻辑
- 开关/场景/配置逻辑
- 原始文件夹结构
