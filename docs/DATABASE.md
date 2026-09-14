# 数据库设计

生产环境使用 MySQL 8，字符集为 `utf8mb4`；测试和本地轻量运行可使用 SQLite。初始结构由 Alembic `0001_initial` 迁移创建，`0002_multimodel_vision`（当前 head）为检测记录增加模型角色、模型文件和显示名称，并为巡检任务增加视觉事件 JSON。容器验收探针 `app/docker_probe.py` 从迁移目录读取 head，新增迁移后无需再手改期望版本。

| 表 | 用途 |
|---|---|
| `users` | 用户基本信息预留 |
| `inspection_tasks` | 巡检任务主记录、状态、风险和反馈 |
| `inspection_images` | 原图路径、摘要、尺寸和 MIME 信息 |
| `detection_results` | YOLO 类别、置信度、坐标与耗时 |
| `agent_runs` | 每次工作流运行状态和总耗时 |
| `agent_steps` | 节点级输入/输出摘要、错误和耗时 |
| `knowledge_documents` | 知识文件解析与入库状态 |
| `risk_assessments` | 风险、证据、引用、建议和分析模式 |
| `reports` | 可展示的 HTML 报告 |
| `manual_reviews` | 人工确认、修改或驳回记录 |

数据库保存文件路径和摘要，不把图片二进制直接写入表。删除任务时相关图片元数据、检测、运行、步骤、研判、报告和复核记录通过级联关系清理；文件生命周期应由部署方的归档策略管理。
