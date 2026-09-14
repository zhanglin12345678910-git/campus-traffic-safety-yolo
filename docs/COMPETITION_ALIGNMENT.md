# 项目要求对应关系

| 要求 | 实现位置 | 可验证证据 |
|---|---|---|
| 独立新项目 | 项目根目录 | 未直接改造旧桌面 UI |
| YOLO26 + TT100K | `training/`、`models/` | 审计报告、训练日志、权重、测试集指标 |
| 真实智能体编排 | `backend/app/agents/graph.py` | `StateGraph` 节点、条件边、轨迹 API |
| 工具调用 | `backend/app/tools/` | 图片质量与 YOLO 工具真实执行 |
| RAG | `backend/app/services/rag.py` | 文档解析、Qdrant 入库、Top-K 引用 |
| 大模型可替换 | `backend/app/services/llm.py` | OpenAI 兼容配置、超时与重试 |
| 风险兜底 | Agent 条件分支 | 人工复核、异常保护报告、不确定性字段 |
| 前后端 | `frontend/`、`backend/` | 页面构建、API 和 SSE 测试 |
| 数据持久化 | SQLAlchemy/Alembic | 10 张业务表，迁移 `0001_initial` → `0002_multimodel_vision` |
| 部署 | Docker Compose/Nginx | 配置解析、服务健康检查 |
| 真实性 | `docs/TEST_REPORT.md` | 已验证结果与待验证项分开记录 |

SF-FastGPT/深信服路线只作为旧文档背景，不属于最终运行依赖。最终系统由 Vue、FastAPI、LangGraph、Qdrant、MySQL、YOLO26 和可配置 LLM API 组成。
