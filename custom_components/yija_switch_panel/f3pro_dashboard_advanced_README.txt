F3 Pro 高级仪表板说明

1. 这是基于基准线版本制作的专用 Lovelace 仪表板。
2. 分为五块：
   - 开关面板
   - 调光面板
   - 窗帘面板
   - 面板设置
   - 场景触发
3. 导入方法：
   - 新建一个空白仪表板
   - 打开原始配置编辑器
   - 把本 YAML 全部粘贴进去
4. 如果保存时报错，说明 entity_id 与你本机不一致。
   请在开发者工具 -> 状态 中搜索以下关键词并替换：
   - switch_1
   - light_group_1
   - curtain_group_1
   - scene_1_last_triggered
5. 这份 YAML 默认按当前设备名 _TZE284_idn2htgu TS0601 的常见实体 ID 编写。
