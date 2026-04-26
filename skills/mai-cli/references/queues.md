# 队列配置参考

## 配置文件

配置文件位置：`.mai/config.json`（相对于共享工作区根目录）。

## 完整配置结构

```json
{
  "root": ["<user>", ...],
  "queues": {
    "<queue-name>": {
      "owner": "<agent-name>",
      "sla_minutes": <number>,
      "id_prefix": "<prefix>"
    }
  },
  "agents": {
    "<agent-name>": {
      "heartbeat_minutes": <number>
    }
  },
  "daily_summary_order": ["<agent>", ...]
}
```

## 顶层字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `root` | string\|array | 超级管理员列表。未配置时默认取操作系统用户名。 |

## queues 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `owner` | string | 负责该队列的 Agent 名称（管理 Issue 生命周期） |
| `sla_minutes` | int | SLA 超时时间（分钟），超时后 issue 标记为 overdue |
| `id_prefix` | string | issue ID 前缀，例如 `"ARC"` 生成 `ARC-001` |

## agents 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `heartbeat_minutes` | int | Agent 心跳间隔（分钟），锁在 `heartbeat × 1.5` 分钟后自动释放 |

## daily_summary_order

数组，定义每日摘要的参与者列表。触发 trigger 后，每个 Agent 独立调用 `daily-summary write` 写入摘要。

## 兼容性别名字段

| 旧字段 | 新字段 | 说明 |
|------|------|------|
| `handler` | `owner` | v1.9.0 后建议改用 `owner`，`handler` 继续有效 |
| `sla_hours` | `sla_minutes` | 同义，按分钟计算 |

## 标准五队列配置

```json
{
  "root": ["admin"],
  "queues": {
    "architect-questions":  { "owner": "architect",  "sla_minutes": 120, "id_prefix": "ARC" },
    "programmer-questions": { "owner": "programmer", "sla_minutes": 120, "id_prefix": "PRG" },
    "designer-questions":   { "owner": "designer",   "sla_minutes": 120, "id_prefix": "DSN" },
    "narrative-questions":  { "owner": "narrative",  "sla_minutes": 120, "id_prefix": "NAR" },
    "techartist-questions": { "owner": "techartist", "sla_minutes": 120, "id_prefix": "TAT" }
  },
  "agents": {
    "architect":  { "heartbeat_minutes": 17 },
    "programmer": { "heartbeat_minutes": 17 },
    "designer":   { "heartbeat_minutes": 29 },
    "narrative":  { "heartbeat_minutes": 29 },
    "techartist": { "heartbeat_minutes": 29 }
  },
  "daily_summary_order": ["architect", "programmer", "designer", "narrative", "techartist"]
}
```
