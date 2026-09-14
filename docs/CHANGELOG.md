# 变更记录

## 未发布 - 2026-09-12（Codex 判定链路与数据分析轮）

- 修复：图片清晰度按 1024px 长边归一化后计算，能解码的质量告警图片继续分析，仅无法解码时短路。
- 修复：人工复核采用后端确定性策略 B，DeepSeek 不再直接决定 `review_required`；低置信度规则改为全部检测均低于各模型阈值才触发。
- 升级：人员/车辆通用模型默认从 `yolo26n.pt` 切换为 `yolo26m.pt`；15 个文件按 SHA-256 去重为 10 张唯一图片后，同口径检出 35 → 47（约 +34%），有检出图片 5 → 7，低于复核阈值 0.35 的框 12 → 11。样本为混合来源且无人工真值，不据此宣称准确率或召回率提升。
- 新增：`GET /api/v1/analytics/overview` 与 `/analytics` 真实数据分析工作台，包含 4 项 KPI、7 个 ECharts 决策面板和响应式移动布局。
- 新增：浏览器视觉验收脚本与 1489×1070 参考图同屏对照；最新验收后端 44/44、前端严格构建、浏览器 6/6 均通过。
- 文档：更新 API、设计系统、Design QA、滚动交接和最终测试报告。

## 未发布 - 2026-09-11（Claude 交接修复轮，详见 `docs/HANDOFF.md`）

- 修复：视频跟踪改用独立的通用模型实例。此前 `model.track()` 在共享单例上留下 ByteTrack 回调，视频分析后的图片巡检人数会被过滤（真实权重实测 13 人 → 6 人，漏报人员聚集候选）；同时消除了图片与视频并发共用一个预测器的线程安全问题。
- 修复：`app/docker_probe.py` 从 Alembic 迁移目录读取 head，不再写死 `0001_initial`（此前下次 Docker 运行态验收必然在表结构探针处失败）；新增真实迁移测试。
- 修复：Nginx `client_max_body_size` 由 20m 调到 110m，与 100 MB 视频上限一致。
- 修复：Dashboard 真实模式不再显示写死或推算的数据；新增 `/dashboard` 的 `today_tasks`、`daily_trend`，任务对象的 `detection_count`、`max_confidence`，以及 `APP_TIMEZONE` 配置。
- 新增：`GET /api/v1/maps/weather` 高德实况天气代理（10 分钟缓存），替换顶栏写死的“22°C 多云”；复核角标只取接口值。
- 修复：知识库检索失败时提示错误，不再用演示结果顶替。
- 新增依赖 `tzdata`，保证 Windows 与精简容器都能解析 IANA 时区。
- 文档：修正评估命令、迁移版本、API 列表；`frontend/DESIGN.md` 写入真实模式的数据规则。

## 0.1.0 - 2026-09-04

- 创建独立的 Vue 3 + FastAPI 项目。
- 实现 LangGraph 巡检状态图、节点持久化和 SSE 轨迹。
- 实现图片质量、YOLO26、Qdrant RAG、风险研判、报告和人工复核。
- 实现 MySQL/SQLite 数据层和 Alembic 初始迁移。
- 实现 TT100K 数据审计、YOLO26m/l 训练预设与测试集评估脚本。
- 添加 Docker Compose、Nginx、健康检查、文档和自动化测试。
- 明确旧 YOLO11 仅为对照，最终模型必须是 TT100K 重新训练的 YOLO26。
