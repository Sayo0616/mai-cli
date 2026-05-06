# [dev] mai-cli - 移除 Async 镜像功能 (v1.12.0)

## 变更描述
根据 v1.12.0 需求，本项目已完全移除 `async/` 文件夹及其相关的自动同步机制。该机制原用于在项目根目录下维护一份 `.mai/` 内部文件的可读镜像，现已废弃。

## 主要变更点

### 1. 核心模块移除
- **删除** `src/mai/sync.py`: 移除所有文件同步逻辑。
- **清理** `src/mai/config.py`: 移除 `get_async_dir` 路径辅助函数。

### 2. 业务逻辑解耦
移除了以下模块中对 `sync_to_async` 的所有调用和引用：
- `src/mai/issue.py`: 工单创建、状态更新、迁移逻辑、结论生成等。
- `src/mai/daily_summary.py`: 每日日报状态更新、写入和汇总报告生成。
- `src/mai/lock.py`: 锁定工单时的处理记录同步。
- `src/mai/log.py`: 审计日志的同步。
- `src/mai/mai.py`: 基础命令分发清理。

### 3. 项目生命周期调整
- `src/mai/project.py`: 
    - `ensure_mai_structure` 不再创建 `async/` 及其子目录。
    - `cmd_project_delete` 不再尝试删除 `async/` 目录。

### 4. 测试套件更新
更新了以下测试文件，移除了对 `async/` 文件夹存在性的断言：
- `tests/test_mai.py`
- `tests/test_v1_10_4_delete_fix.py`

## 验证结论
执行 `pytest`，所有 58 项测试全部通过，确认移除镜像功能后系统核心逻辑（工单流转、锁定、权限、日报等）正常运行。
