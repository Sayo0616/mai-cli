# Changelog

## v1.1.0 (2026-04-19)
- 配置外部化：所有协作规则移至 config.json
- 深度合并 fallback：支持老配置平滑迁移
- 兼容旧格式（owner→handler，sla_hours→sla_minutes）

## v1.0.0 (2026-04-19)
- 初始版本：26 个命令，flock 原子锁，事件驱动每日汇总
