# 安巡智脑 · 校园交通安全巡检系统

面向校园交通安全管理的巡检项目，提供图片检测、视频轨迹分析、规范检索、风险评估、人工复核和报告管理。前端展示巡检任务、校园地图、检测结果与统计数据，后端负责检测、工作流执行和数据持久化。

## 功能

- 图片巡检：检查图片质量，识别交通标志、人员和车辆，展示检测框与置信度。
- 视频分析：使用 ByteTrack 跟踪目标，根据配置识别人员聚集和逆行候选事件。
- 规范检索：导入 Markdown、TXT、PDF、DOCX 资料，通过 Qdrant 检索相关条款并保留引用。
- 风险评估：结合检测结果、现场说明和规范依据形成结构化结论与整改建议。
- 人工复核：对证据不足、低置信度或执行异常的任务保留复核入口和处理记录。
- 档案与报告：查询任务、查看执行轨迹、导出报告，并汇总风险和检测统计。

## 技术栈

后端使用 Python、FastAPI、SQLAlchemy、Alembic、LangGraph 和 Ultralytics；前端使用 Vue 3、TypeScript、Vite、Element Plus 和 ECharts。支持 SQLite 或 MySQL，知识检索使用 Qdrant。视频跟踪使用 ByteTrack。

## 项目结构

```text
backend/       接口、工作流、检测服务、数据库迁移与测试
frontend/      页面、组件、样式与前端测试脚本
knowledge/     规范资料与开发测试示例
models/        模型文件说明（权重单独配置）
training/      数据检查、训练与评估脚本
scripts/       开发启动、检查与测试脚本
deploy/        可选容器部署配置
docs/          架构、接口、数据、测试与部署文档
```

## 本地运行

需要 Python 3.10 或更高版本，以及满足 Vite 7 要求的 Node.js（20.19+ 或 22.12+）。以下命令在项目根目录执行。

1. 创建独立 Python 环境，安装依赖并复制配置模板：

```bash
python -m venv .venv
# 激活 .venv 后执行：
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

将 `.env.example` 复制为 `.env`，本地运行至少调整以下配置：

```dotenv
ENVIRONMENT=development
DATABASE_URL=sqlite:///./data/campus_safety.db
YOLO_MODEL_PATH=../models/yolo26-tt100k-best.pt
GENERAL_YOLO_MODEL_PATH=../models/yolo26m.pt
YOLO_DEVICE=cpu
QDRANT_URL=
QDRANT_PATH=./data/qdrant
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

2. 将有权使用的权重放入 `models/`，文件说明见 [模型说明](models/README.md)。权重与训练数据不随仓库提供。

3. 启动后端：

```bash
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4. 在另一个终端启动前端：

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

浏览器访问 `http://127.0.0.1:5173`。接口文档位于 `http://127.0.0.1:8000/docs`。

检测模型、规范资料和外部服务应按实际需求配置。未配置文本评估服务或检索依据不足时，任务使用保守处理并进入人工复核；地图与视觉证据服务为可选配置。密钥只保存在本地环境文件或服务端，不写入前端代码。

## 测试与构建

```bash
cd backend
python -m pytest
```

```bash
cd frontend
npm run typecheck
npm run build
```

完整测试范围见 [测试说明](docs/TEST_REPORT.md)。容器运行方式见 [部署说明](docs/DEPLOYMENT.md)。

## 使用边界与资料保护

单帧图片不能证明运动方向；视频事件和风险结论需要结合现场证据复核。系统输出不替代学校制度、现场核实或管理人员的最终决定。

仓库仅提供源码、依赖清单、配置模板和项目文档，不包含真实密钥、数据库、上传素材、运行结果、原始校园照片、模型权重或构建缓存。使用现场资料前应取得授权，并按需处理人脸、车牌、姓名、联系方式和定位信息。素材来源见 [资源说明](frontend/src/assets/SOURCES.md)，安全配置见 [安全说明](SECURITY.md)。

## 文档

- [系统架构](docs/ARCHITECTURE.md)
- [工作流设计](docs/AGENT_DESIGN.md)
- [接口说明](docs/API.md)
- [数据库设计](docs/DATABASE.md)
- [知识检索设计](docs/RAG_DESIGN.md)
- [部署说明](docs/DEPLOYMENT.md)
- [测试说明](docs/TEST_REPORT.md)
- [现场验证记录模板](docs/REAL_WORLD_VALIDATION_TEMPLATE.md)
