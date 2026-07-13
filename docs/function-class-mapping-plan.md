# Function Class Mapping Plan

这份文档记录 `function_call/function.py` 和 `config/class.txt` 的剩余映射缺口。这里不直接补 class id，是因为 `class.txt` 通常和训练标签、模型输出维度、benchmark 标注绑定，贸然新增会让推理链路和训练链路不一致。

## 当前缺口

以下 function 已存在于 schema，但还没有出现在 `config/class.txt`：

| Function | Domain | Suggested action |
| --- | --- | --- |
| `Close_Cruise_Broadcast` | driving_assistance | 检查训练集是否已有巡航播报关闭样本 |
| `Open_Cruise_Broadcast` | driving_assistance | 检查训练集是否已有巡航播报打开样本 |
| `Nav_To_Home` | navigation_map | 确认是否复用通用导航 intent，避免新增重复导航类 |
| `Nav_To_Company` | navigation_map | 确认是否复用通用导航 intent，避免新增重复导航类 |
| `Cancel_High_Way_First` | navigation_map | 检查和高速优先、路线偏好类 intent 的关系 |
| `Avoid_Fee` | navigation_map | 检查和路线偏好类 intent 的关系 |
| `Set_Meeting_Place` | navigation_map | 检查是否需要新增社交/组队导航类 intent |
| `Radio_Am` | media | 检查是否并入 `Search_Radio` 或 `Play_Local_Radio` |
| `Radio_Fm` | media | 检查是否并入 `Search_Radio` 或 `Play_Local_Radio` |
| `Query_Destination_Weather` | weather_info | 检查是否复用天气查询 intent，并通过 slot 区分目的地 |

## 收敛步骤

1. 先在 `test/data/` 和真实样本里确认每个 function 是否有独立标注。
2. 如果已有标注，再给 `config/class.txt` 增加稳定 class id。
3. 如果没有独立标注，不急着加 class id，先在 schema 报告里保留债务。
4. 修改 class 后同步更新 benchmark，并重跑 `python scripts/check_project.py`。

## 当前策略

短期保留这些缺口，不影响本地 demo 和 schema 基础校验；中期通过训练样本和 benchmark 决定是新增 intent，还是合并到已有 intent。
