# 安巡智脑最终测试与验收报告

**验收日期：** 2026-09-08（2026-09-09、2026-09-10 增量再核验）  
**项目：** `campus-safety-agent`  
**最终结论：** **现有功能、高德与 DeepSeek 实时联网通过（PASS）；当前 Docker 守护进程限制见第 12 节**  
**训练完成策略：** 用户明确要求停止继续训练，并接受已完成轮次中的最佳检查点；本报告不把 32/80 轮描述成“完整训练完成”。

## 1. 结论摘要

项目已按“停止训练、使用现有最佳轮次、完成系统”的要求完成收尾：

- YOLO26 训练已停止，自动恢复任务已禁用，训练脚本会识别停止状态并拒绝误启动。
- 计划训练 80 轮，实际完整完成 32 轮；第 33 轮只运行到 `142/2341` batch，没有形成完整轮次检查点，因此不参与最佳模型选择。
- 在 1–32 个完整轮次中，第 32 轮验证集 `mAP50-95=0.62980` 最高，故选择该轮 `best.pt`。
- 已使用独立 test 集 3,992 张图片进行正式评测，得到 `mAP50=0.83880`、`mAP50-95=0.64666`。
- 正式权重已接入项目 `models/yolo26-tt100k-best.pt`，源文件、接入文件和评测记录中的 SHA256 完全一致。
- 本机真实模型 E2E、DeepSeek V4 Flash 真实鉴权与全链路 E2E、Docker 真实运行态 E2E、当前 20 项后端测试、SQLite/MySQL 迁移、前端严格类型检查和生产构建均通过。
- 前端已按用户选定的“高密度 GIS 校园安防指挥台”参考图完成视觉改造，并通过桌面端与移动端真实浏览器检查，控制台 0 错误、0 警告。
- Docker 生产栈在最终验收时保持运行并通过 `http://127.0.0.1:8080/dashboard` 访问；2026-09-09 受管执行环境恢复时改用本地预览栈，当前可访问 `http://127.0.0.1:5173/dashboard`。

## 2. 模型选择与训练状态

### 2.1 训练状态事实

| 项目 | 实际结果 |
|---|---:|
| 模型架构 | YOLO26m |
| 类别数 | 45 |
| 输入尺寸 | 640 |
| 原计划轮次 | 80 |
| 完整完成轮次 | 32 |
| 中断位置 | 第 33 轮，`142/2341` batch |
| 停止原因 | `user_requested` |
| 最终状态 | `completed_partial_by_user` |
| 选择规则 | 完整轮次中验证集 `mAP50-95` 最高 |
| 选中轮次 | 第 32 轮（检查点内部 `epoch_index=31`） |

第 33 轮未完整结束，不能把该轮批次进度当成 epoch 结果。`best.pt` 与 `last.pt` 在停止时内容完全相同，均对应完整完成的第 32 轮。

### 2.2 第 32 轮验证集结果

| 指标 | 数值 |
|---|---:|
| Precision | 0.84572 |
| Recall | 0.76955 |
| mAP50 | 0.82615 |
| mAP50-95 | **0.62980** |

### 2.3 权重身份

| 项目 | 数值 |
|---|---|
| 项目模型路径 | `models/yolo26-tt100k-best.pt` |
| 原始训练权重 | `<LOCAL_PATH>` |
| 文件大小 | 131,630,898 bytes |
| SHA256 | `0d4ad7756c965bdb5ec2520c7124a195fabc28084cc6039ec02e1aa6a15dd9af` |

哈希核验覆盖原始 `best.pt`、原始 `last.pt`、项目正式模型以及 `evaluation-result.json` 记录的被评测权重，结果一致。

## 3. 独立 test 集正式评测

评测使用独立 test split，不使用训练集或验证集指标冒充最终结果。

| 项目 | 实际结果 |
|---|---:|
| Test 图片数 | 3,992 |
| Test 标注实例数 | 10,060 |
| Precision | **0.865597** |
| Recall | **0.763761** |
| mAP50 | **0.838795** |
| mAP50-95 | **0.646661** |
| 平均推理耗时 | 13.1448 ms/image |
| End-to-end 模型 | `true` |
| Ultralytics | 8.4.138 |
| 评测错误 | 无 |

正式评测证据：

- `<LOCAL_PATH>`
- 数据配置 SHA256：`53c86f31b35ad2227943a53188464b4a096b7200cac7728f0c80d2e54f24b40d`
- 训练结果 SHA256：`67f3e7b5aeaf725af102ff969a168e59a77498124a7b31751e736fe744789331`
- 训练参数 SHA256：`e51d2eaa8fa43461aa630a0a2d296dd32c990a90fbab57dd4c04c9fe6f9ef7aa`

## 4. 真实模型与智能体 E2E

### 4.1 本机正式权重 E2E

执行结果：**通过**。

| 项目 | 结果 |
|---|---|
| 正式模型 | `yolo26-tt100k-best.pt` |
| 模型加载次数 | 1 |
| 真实检测数 | 3 |
| 最终状态 | `review` |
| 分析模式 | `rules_only` |
| 报告长度 | 1,397 字符 |
| LangGraph 成功节点 | 9/9 |

成功节点依次为：

1. `validate_input`
2. `check_image_quality`
3. `detect_traffic_signs`
4. `check_detection_result`
5. `retrieve_knowledge`
6. `evaluate_risk`
7. `generate_recommendations`
8. `generate_report`
9. `save_result`

证据文件：`outputs/formal-model-e2e.json`。

说明：该本机测试为了专门核验模型分支，将测试实例的模糊阈值设为 0；这不会修改生产默认规则。生产规则是否能自然通过，由下面的 Docker 运行态测试另行验证。

### 4.2 DeepSeek V4 Flash 真实 E2E

执行结果：**通过**。

2026-09-09 使用项目自带的授权 TT100K 样例完成真实联调；密钥仅从被 Git 忽略的 `.env` 读取，没有写入前端、报告、测试证据或日志。

| 项目 | 结果 |
|---|---|
| DeepSeek `/models` 鉴权 | HTTP 200 |
| 模型 | `deepseek-v4-flash` |
| 结构化输出校验 | 通过 |
| 分析模式 | `llm` |
| YOLO26 真实检测数 | 2 |
| LangGraph 成功节点 | 9/9 |
| 报告生成 | 成功，886 字符 |
| 最终状态 | `review`（预期人工复核安全终态） |

证据文件：`outputs/deepseek-e2e.json`。

### 4.3 Docker 生产规则 E2E

执行结果：**通过**。

Docker 测试使用清晰度 227.46、超过生产阈值 80 的真实 TT100K 道路图片，没有关闭或绕过图片质量护栏。

| 项目 | 结果 |
|---|---|
| Docker Engine | 29.6.1 |
| 运行服务 | mysql、qdrant、backend、frontend |
| 服务状态 | 全部运行，MySQL/Backend 健康 |
| Qdrant Server | 1.15.5 |
| Qdrant Client | 1.15.1（同一 minor 系列） |
| 正式 YOLO26 配置 | 是 |
| 正式 YOLO26 已加载 | 是 |
| 模型加载次数 | 1 |
| 真实检测数 | 2 |
| 知识文档分块 | 1 |
| Qdrant 搜索命中 | 3 |
| LangGraph 节点 | 9/9 |
| 报告长度 | 2,728 字符 |
| 最终状态 | `review`（符合人工复核安全策略） |

证据文件：`outputs/docker-runtime-acceptance.json`。

## 5. 后端、数据库与 API 验收

| 验收项 | 结果 | 证据/说明 |
|---|---|---|
| 后端自动测试 | **通过** | 20 passed，0 failed；包含 DeepSeek V4 Flash 请求地址、模型名、鉴权、JSON 输出与非思考模式契约测试 |
| SQLite 新库迁移 | **通过** | `alembic upgrade head` |
| SQLite 迁移差异检查 | **通过** | `No new upgrade operations detected` |
| MySQL 容器迁移 | **通过** | revision `0001_initial` |
| MySQL 数据库名 | **通过** | `campus_safety` |
| MySQL 表结构 | **通过** | 11 张要求表全部存在 |
| API 健康检查 | **通过** | database/qdrant/yolo 均正常 |
| 知识上传 | **通过** | Markdown 文件成功入库 |
| 知识检索 | **通过** | Qdrant 返回命中 |
| 巡检创建与执行 | **通过** | 201 + 202，任务到达 `review` |
| 工作流轨迹 | **通过** | 检测、检索、研判、报告、保存节点完整 |
| 报告读取 | **通过** | 正式 HTML 报告可读取 |

MySQL 验证表包括：`agent_runs`、`agent_steps`、`alembic_version`、`detection_results`、`inspection_images`、`inspection_tasks`、`knowledge_documents`、`manual_reviews`、`reports`、`risk_assessments`、`users`。

本机迁移证据库：`backend/data/final-acceptance-20260908.db`。

## 6. 前端构建与视觉验收

### 6.1 构建

| 验收项 | 结果 |
|---|---|
| `vue-tsc -b --pretty false` | **通过，0 类型错误** |
| `npm run build` | **通过** |
| Vite 版本 | 7.3.6 |
| 处理模块 | 2,290 |
| Dashboard 产物 | 480.19 kB / gzip 164.97 kB |

### 6.2 真实浏览器

使用 Playwright 在 Docker/Nginx 实际地址上检查，而不是只看源码或静态截图。

| 视口/页面 | 结果 |
|---|---|
| 1492×1072 Dashboard | **通过**；地图、事件队列与底部表格纵向铺满 |
| 1492×1072 新建巡检 | **通过** |
| 巡检档案 | **通过** |
| 人工复核 | **通过** |
| 安全知识库 | **通过** |
| 系统设置 | **通过** |
| 390×844 Dashboard | **通过**；底部导航与两列 KPI 正常 |
| 390×844 新建巡检 | **通过**；表单单列，无横向溢出 |
| 浏览器控制台 | **0 errors / 0 warnings** |

最终截图：

- `frontend/output/playwright/container-dashboard-final.png`
- `frontend/output/playwright/container-new-inspection-final.png`
- `frontend/output/playwright/container-dashboard-mobile-final.png`
- `frontend/output/playwright/container-new-inspection-mobile-final.png`

视觉设计比对与偏差说明见项目根目录 `design-qa.md`。

### 6.3 校园地理基准接入（2026-09-09）

- 新增统一校园配置 `frontend/src/config/campus.ts`，当前部署院校为四川现代职业学院。
- 国内地图默认中心为 GCJ-02 `[103.997424, 30.515862]`，GeoJSON/OSM 备用中心为 WGS84 `[103.995133, 30.518507]`，坐标顺序统一为 `[经度, 纬度]`。
- Dashboard 侧栏、地图图片语义、DOM 地理属性、可点击校园信息卡和“回到校园中心”操作均使用同一份配置。
- `npm run build` 通过：2,291 个模块，Dashboard 产物 480.94 kB / gzip 165.17 kB。
- 本机 Edge Chromium 真实渲染检查通过：1440×1000 下坐标卡未遮挡图层、风险点或缩放控件；390×844 下坐标卡正常收窄；渲染后 DOM 含院校名称、两个坐标属性和复位按钮语义，页面级 `Uncaught` / `TypeError` / `ReferenceError` 计数为 0。

本轮截图：

- `frontend/output/playwright/campus-location-desktop.png`
- `frontend/output/playwright/campus-location-mobile.png`

## 7. Docker 配置与本机环境修复

### 7.1 项目容器配置

- 后端镜像固定使用 CPU 版 `torch==2.2.2+cpu` 与 `torchvision==0.17.2+cpu`，避免误下载数 GB CUDA 依赖。
- `ultralytics==8.4.138` 与正式评测环境保持一致。
- `numpy==1.26.4`、`opencv-python==4.10.0.84` 固定，降低未来自动升级导致的不确定性。
- `qdrant-client==1.15.1` 与 Qdrant Server 1.15.5 保持同系列。
- 前端 `.dockerignore` 排除了 `node_modules`、`dist`、日志和本地验收输出，缩小构建上下文。
- 容器数据卷保留；验收过程中没有执行 `down -v` 或删除数据库卷。

### 7.2 Docker Desktop 修复记录

Docker Desktop 原先因无关的 Docker AI/Inference 本地 socket 损坏而无法启动 Engine。处理方式均为可恢复操作：

- 关闭了当前项目不需要的 `EnableDockerAI` 设置。
- 原设置备份：`<LOCAL_PATH>`。
- 临时运行目录移动备份：
  - `<LOCAL_PATH>`
  - `<LOCAL_PATH>`
  - `<LOCAL_PATH>`

上述目录未删除。修复后 Docker Engine `docker info` 与项目完整运行态验收均通过。

## 8. 最终自动总验收

最终总控脚本 `scripts/final-acceptance.ps1` 执行结果：**PASS**。

它实际核验了：

- 用户停止训练的状态与 `stop_reason`；
- 32/80 轮事实与“部分完成”策略；
- `results.csv` 中完整轮次最高验证 `mAP50-95` 的选择；
- 选中轮次与检查点元数据的一致性；
- 正式模型 SHA256；
- 独立 test 结果；
- 数据库迁移；
- 后端测试；
- 前端类型检查和构建；
- 正式模型本机 E2E；
- Docker Compose 配置；
- Docker 完整运行态 E2E。

总验收证据：`<LOCAL_PATH>`。

## 9. 已知边界（非阻塞）

1. **训练仅完成 32/80 轮。** 这是用户明确停止后的最终交付策略，不代表第 80 轮模型，也不能宣称达到未实际测得的目标指标。
2. **DeepSeek V4 Flash 已真实验证。** 官方 `/models` 鉴权返回 HTTP 200，结构化生成和完整巡检工作流均通过，任务结果保存为 `analysis_mode=llm`。调用异常时系统仍会如实记录并安全降级到 `rules_only`，不会伪造大模型结果。
3. **YOLO26 模型是 45 类 TT100K 交通标志模型。** 它不等于通用人员、车辆、车牌或所有校园违法行为检测模型；界面中的其他事件类型不能被误解为该权重已覆盖的训练类别。
4. **人工复核是预期安全终态。** `review` 不表示系统执行失败，而是低置信度、信息不足或风险规则要求人工确认时的安全设计。
5. **容器默认 CPU 推理。** 这是为了通用部署与可复现性；需要更高吞吐时可另行配置 GPU 容器运行时，但不能因此重新启动训练。

## 10. 运行与停止

### 当前本地预览（2026-09-10）

- 前端：`http://127.0.0.1:5173/dashboard`
- 后端健康：`http://127.0.0.1:8000/api/v1/health`
- 数据库：本地 SQLite
- 向量库：Qdrant embedded
- 正式 YOLO26：已配置，按请求懒加载

2026-09-10 最终标准端口冒烟结果：后端健康接口 HTTP 200，`database=ok`、`qdrant.status=ok`；正式模型为 `yolo26-tt100k-best.pt`，DeepSeek 与高德配置状态均为 `configured=true`。Chromium 依次访问 `/dashboard`、`/reviews`、`/settings`、`/inspections`，4/4 页面 HTTP 200、每页唯一 `h1`、页面脚本错误 0。修复 VPN 出站代理后，高德静态图 HTTP 200，Dashboard 显示“高德底图 · 实时态势”。

之所以使用本地预览，是因为后续受管执行环境不允许 Docker Desktop 写入用户 AppData；这不影响 2026-09-08 已保存的 Docker 完整运行态 PASS 证据。

### Docker 生产栈

Docker Desktop 在普通用户环境启动后，生产入口为：

- 前端：`http://127.0.0.1:8080/dashboard`
- 后端健康：`http://127.0.0.1:8080/api/v1/health`
- Qdrant：`http://127.0.0.1:6333/`

日常启动：

```powershell
docker compose --env-file .env.example up -d
```

停止服务但保留数据：

```powershell
docker compose --env-file .env.example down
```

除非明确需要清空数据，不要增加 `-v`。

## 11. 证据索引

| 证据 | 路径 |
|---|---|
| 训练最终状态 | `<LOCAL_PATH>` |
| 独立 test 评测 | `<LOCAL_PATH>` |
| 最终自动总验收 | `<LOCAL_PATH>` |
| 本机正式模型 E2E | `outputs/formal-model-e2e.json` |
| DeepSeek 真实 E2E | `outputs/deepseek-e2e.json` |
| Docker 运行态 E2E | `outputs/docker-runtime-acceptance.json` |
| 前端视觉验收 | `design-qa.md` |
| 校园坐标桌面端截图 | `frontend/output/playwright/campus-location-desktop.png` |
| 校园坐标移动端截图 | `frontend/output/playwright/campus-location-mobile.png` |
| 正式项目权重 | `models/yolo26-tt100k-best.pt` |

## 12. 2026-09-10 高德接入、复核闭环与现有功能全量回归

### 12.1 本轮交付内容

本轮在不恢复模型训练的前提下，完成了用户指定的“先修复人工复核，再接入高德，然后按通用软件测试流程验收现有功能”。用户提供的密钥均只保存在被 Git 忽略的服务器环境文件中，本报告、前端源码、构建产物和自动化证据不记录密钥明文。

| 交付项 | 最终行为 | 结果 |
|---|---|---|
| 演示复核队列 | 点击“生成并复核”后上传随包现场图、创建真实 UUID 任务、启动 YOLO26/LangGraph 并进入任务详情 | **通过** |
| 人工复核闭环 | 展示原图/检测图、检测表、9 节点轨迹、风险依据和报告；点击“人工确认”后状态变为 `completed` 且 `review_required=false` | **通过** |
| 高德地理编码 | 新增后端 `GET /api/v1/maps/geocode` 代理，浏览器不接触服务 Key | **契约与真实联网均通过** |
| 高德静态地图 | 新增后端 `GET /api/v1/maps/static` 图片代理、参数边界、响应大小与类型校验、5 分钟缓存 | **契约与真实联网均通过** |
| VPN/Fake-IP 兼容 | 后端通过独立 `OUTBOUND_HTTP_PROXY` 显式使用本机 Mihomo HTTP 代理，不依赖关闭状态的 Windows/WinHTTP 系统代理 | **通过** |
| 地图容错 | 高德请求不可用时 Dashboard 自动切换为随包校园 GIS 图，并明确显示“校园 GIS 备用图” | **通过** |
| Ultralytics 运行目录 | 将 Ultralytics 设置目录固定到项目内可写且已忽略的 `backend/data/ultralytics`，避免 Windows Roaming Profile 权限错误 | **通过** |
| DeepSeek 降级文案 | 外部大模型不可用时仍执行 `rules_only` 安全策略；底层传输错误只写服务日志，前端显示可理解的降级说明 | **通过** |
| 基础可访问性 | 为 6 个页面补齐唯一 `h1`、摄像头图标按钮名称、文件输入和筛选器名称；不改变视觉和业务 | **通过** |

高德 Key 类型与接口用法依据官方 [静态地图 Web Service 文档](https://lbs.amap.com/api/webservice/guide/api/staticmaps) 和 [地理编码 Web Service 文档](https://lbs.amap.com/api/webservice/guide/api/georegeo/)。DeepSeek 配置经官方 [Chat Completions API 文档](https://api-docs.deepseek.com/api/create-chat-completion/) 复核：`deepseek-v4-flash` 是有效模型标识，`thinking.type=disabled` 是有效的非思考模式参数，JSON Output 受支持。

### 12.2 自动化测试矩阵

| 测试层 | 方法与范围 | 2026-09-10 实测结果 |
|---|---|---|
| 后端单元/服务/API 集成 | 图片质量、YOLO 单例与 Unicode 路径、RAG、DeepSeek 请求契约与降级、AMap 地理编码/静态图、鉴权、上传校验、执行冲突、SSE、完整工作流、报告、复核、反馈、分页 | **24 passed，0 failed；代理修复后最终回归 11.99 s** |
| Python 语法/字节码 | `python -m compileall -q app tests` | **通过** |
| 前端严格类型与生产构建 | `vue-tsc -b && vite build` | **通过；2,291 modules；代理状态展示加入后最终构建 19.52 s** |
| 真实浏览器 E2E | Chromium 149，桌面 1492×1072；API、Dashboard、全部路由、空表单、复核全链路、档案、知识上传检索、设置 | **9/9 通过；0 个页面脚本错误；33.104 s** |
| 真实 YOLO26 | 正式 `yolo26-tt100k-best.pt`，真实现场图，要求检测节点 success、无错误节点、模型仅加载一次 | **通过；1 个 `pl60`；置信度 95.9213%；9/9 节点成功** |
| 移动端兼容 | Chromium，390×844 Dashboard | **通过；viewport/document/body 均 390 px，无文档级横向溢出** |
| 基础可访问性 | 6 个现有页面：语言、唯一 H1、图片 alt、按钮/链接/输入控件可读名称 | **全部通过，0 缺失** |
| API 并发冒烟 | `/api/v1/health`，100 请求、10 并发 | **100/100 成功；P50 50.78 ms；P95 93.56 ms；最大 109.38 ms** |
| OpenAPI 完整性 | schema 读取、Operation ID 唯一、地图接口存在、敏感串不进入 schema | **通过；15 paths / 17 operations** |
| Alembic 迁移 | 全新 SQLite：upgrade head → check → downgrade base → upgrade head → 表/版本核验 | **通过；revision `0001_initial`；11 张表** |
| 密钥与构建产物扫描 | 前端源码、`dist`、后端源码/测试、文档、脚本、Compose；同时检查 `.env.amap` 是否被 Git 忽略 | **通过；0 泄露；环境文件已忽略** |
| Docker Compose 静态验收 | Docker Compose 5.3.0，`docker compose config --quiet` | **通过** |
| Ruff 代码风格 | `python -m ruff` | **未执行：当前 Python 环境未安装 Ruff** |

首次浏览器回归曾单独记录代理修复前高德请求的受控 HTTP 503，以及页面跳转时主动终止的旧 SSE/GET 请求。代理修复后的最终复测中，高德静态图 HTTP 200，Dashboard 页面 HTTP 200、页面级 JavaScript 错误 0。

可重复测试脚本与证据：

- `frontend/scripts/e2e_existing_features.py`
- `frontend/output/playwright/standard-test/e2e-result.json`
- `frontend/output/playwright/standard-test/01-dashboard-desktop.png`
- `frontend/output/playwright/standard-test/02-review-queue-before.png`
- `frontend/output/playwright/standard-test/03-inspection-before-confirm.png`
- `frontend/output/playwright/standard-test/04-inspection-confirmed.png`
- `frontend/output/playwright/standard-test/05-knowledge-search.png`
- `frontend/output/playwright/standard-test/06-dashboard-mobile.png`

### 12.3 VPN 根因、真实联网复测与结论边界

1. **根因已经定位并修复。** 本机 Mihomo 在 `127.0.0.1:7890` 正常监听，但 Windows 系统代理为关闭状态，WinHTTP 为 Direct，进程环境也没有 `HTTP_PROXY`/`HTTPS_PROXY`。与此同时 Fake-IP DNS 把 `restapi.amap.com` 和 `api.deepseek.com` 解析为 `198.18.x.x`；Python/httpx 原先直连这些 Fake-IP，因而两个供应商同时出现 `WinError 10013`。后端现通过被 Git 忽略的 `.env.proxy` 显式使用 Mihomo HTTP 代理。
2. **高德真实联网通过。** `GET /api/v1/maps/geocode` 成功把“四川现代职业学院”解析为 `103.997424,30.515862`；`GET /api/v1/maps/static` 返回 HTTP 200、`image/png`、47,768 字节，响应头 `X-Map-Provider=amap`。Chromium 最终复测地图请求 HTTP 200，页面显示“高德底图 · 实时态势”，页面脚本错误 0。证据截图为 `frontend/output/playwright/standard-test/07-dashboard-amap-live.png`。
3. **DeepSeek 真实联网通过。** `/models` 鉴权 HTTP 200；直接结构化风险调用返回 `analysis_mode=llm`。随后经正在运行的 FastAPI 创建真实图片巡检任务，正式 YOLO26 检出 1 个目标，DeepSeek 分析模式为 `llm`，LangGraph 9/9 节点成功、0 错误、报告生成成功，测试任务人工确认完成。
4. **当前 Docker 运行态未重复判为通过。** Docker 29.6.1 客户端和 Compose 5.3.0 可用，最新 Compose 配置通过；但本轮受管会话无权打开/启动 `com.docker.service`，Docker Engine 未就绪。第 4.3 节保留的是 2026-09-08 的历史运行态证据，不能替代对本轮镜像的重新启动验证。容器如需走本机 Mihomo，应设置 `DOCKER_OUTBOUND_HTTP_PROXY=http://host.docker.internal:7890`，而不是容器自己的 `127.0.0.1`。
5. **当前可交付范围。** 本地 FastAPI + Vue + SQLite + embedded Qdrant + 正式 YOLO26、人工复核、高德与 DeepSeek 真实调用均已通过。即使将来代理临时不可用，系统仍保留高德 GIS 备用图与 DeepSeek `rules_only` 安全降级，不会伪造外部服务结果。

---

## 13. 2026-09-10 四川现代职业学院真实校园照片验证

### 13.1 素材审计

- 用户提供目录：`校园照片/`。
- 可读取真实图片共 68 张：`含标志/` 35 张，普通校园场景 33 张。
- 原图主体分辨率主要为 3024×4032、3072×4096、4096×3072、4284×5712，满足项目 320×240 的最低输入要求。
- 另有约 64 个名称以 `._` 开头的 macOS 元数据侧车文件，它们不是图片损坏；验收时已排除，原始文件未删除、未移动、未覆盖。

### 13.2 正式 YOLO26 批量筛选

使用项目正式 `models/yolo26-tt100k-best.pt`、`imgsz=640`、CPU、筛选阈值 0.20 对 35 张“含标志”照片逐张推理。结果表明当前 TT100K 45 类权重适合识别国标道路交通标志，不覆盖消防通道文字、应急避难场所、禁止滑板、人员聚集、路面积水或标线磨损等自定义校园安全类别。

| 校园原图 | 视觉事实 | 模型结果 | 采用策略 |
|---|---|---|---|
| `IMG_9781.JPG` | 限速 5、禁止鸣笛 | `p11=0.9420`，禁止鸣笛定位正确 | 作为第一真实校园 YOLO 演示 |
| `IMG_9769.JPG` | 连续减速带、限速 5 | `w57=0.8636`，连续减速带警告定位正确 | 作为第二真实校园 YOLO 演示 |
| `IMG_9759.JPG` | 连续减速带、限速 5 | `w57=0.8571` 正确，但同时把数字 5 低置信误判为 `pl50=0.3633` | 不作为主演示，避免夸大准确性 |
| `IMG_9756.JPG` | 限速 5 | `pl50=0.3208`，数字类别错误 | 不作为主演示 |
| `1684.JPG` | 禁止滑板 | `ph4=0.7075`，超出训练类别后语义错误 | 不作为 YOLO 能力证据 |
| 消防/避难/人流等照片 | 校园安全管理场景 | 多数无 TT100K 检测 | 作为“证据不足→人工复核”的安全闭环演示 |

### 13.3 前端接入与真实浏览器闭环

原始照片保持不动，仅将 5 张选定素材复制到 `frontend/public/campus/`：禁止鸣笛、连续减速带、消防通道、应急避难区和宿舍区人员密集场景。人工复核页的 5 条演示队列已改成四川现代职业学院真实地点与真实图片，不再使用此前的通用道路素材。

Chromium 149 真实执行第一条“图书馆北侧道路”任务：

- 校园素材 HTTP 200；复核页 HTTP 200。
- 页面成功上传 6.51 MB 校园原图并创建真实 UUID 巡检任务。
- 正式 YOLO26 输出 `p11`，置信度 94.2%，检测框正确落在禁止鸣笛标志上。
- DeepSeek 返回 `analysis_mode=llm`。
- LangGraph 9/9 节点成功、0 错误。
- 正式巡检报告生成成功，人工确认成功。
- 页面级 JavaScript 错误为 0。
- `vue-tsc -b && vite build` 通过，2,291 modules，最终构建 30.89 秒；5 张真实校园素材全部进入 `dist/campus/`。

增量验收截图：

- `frontend/output/playwright/standard-test/08-real-campus-review-queue.png`
- `frontend/output/playwright/standard-test/09-real-campus-inspection-detail.png`

**最终判定：项目在“用户接受第 32 轮最佳检查点、不再继续训练”的明确前提下，当前本地现有功能、正式 YOLO26、四川现代职业学院真实照片验证、人工复核、数据库、知识库、前端、高德实时地图、DeepSeek 实时研判和外部服务降级路径均已通过，可用于本地演示与材料提交；只有当前 Docker 守护进程运行态仍须按第 12.3 节如实标注。**

---

## 14. 2026-09-10 多模型校园安防与视频轨迹增量验收

### 14.1 实现范围与结论边界

本轮在不恢复 TT100K 训练的前提下，新增官方 COCO 预训练 `yolo26n.pt` 作为人员车辆辅助模型。文件位于 `models/yolo26n.pt`，大小 5,544,453 bytes，SHA-256 为 `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef`。系统采用明确的模型职责隔离：

- `yolo26-tt100k-best.pt` 只负责 TT100K 45 类交通标志。
- `yolo26n.pt` 只采纳 `person`、`bicycle`、`car`、`motorcycle`、`bus`、`truck` 六类；COCO 的通用交通标志预测会被丢弃，不能覆盖专用模型。
- 静态图片达到 8 人阈值时生成“人员聚集候选”，同时标记需要人工复核和连续视频确认，不把单帧人数直接表述为持续聚集。
- 逆行只由视频中同一 `track_id` 的连续轨迹、最小位移和道路允许方向共同判断；单张图片不会产生逆行事件。
- 视频分析接受 MP4/AVI/MOV/MKV/WebM，最大 100 MB，默认隔帧处理并限制最多 900 个分析帧；输出为浏览器可直接播放的 VP8/WebM。

数据库迁移升级为 `0002_multimodel_vision`，为检测记录增加模型角色、模型文件和显示名称，为巡检任务增加结构化视觉事件 JSON。迁移同时兼容旧的 `create_all()` 数据库和全新数据库。

### 14.2 四川现代职业学院真实图片双模型验证

使用 `frontend/public/campus/dormitory-crowd.png` 创建真实巡检任务 `a225dd08-29f8-4d10-ac2d-e6c61a9579ed`，依次执行图片质量、TT100K 模型、COCO 通用模型、事件规则、知识检索、DeepSeek、建议、报告和持久化：

| 检查项 | 实测结果 |
|---|---|
| 人员检测 | 13 个 `person`，全部来自 `yolo26n.pt` |
| 交通标志/车辆 | 该图均为 0，未伪造无关类别 |
| 视觉事件 | 1 个“人员聚集候选”，人数 13，阈值 8 |
| DeepSeek | `analysis_mode=llm` |
| 工作流 | 9 个实际经过节点全部成功 |
| 任务状态 | `review`，保留人工确认边界 |
| 报告 | 成功生成，报告 ID `7aab8a53-62da-4d08-b3c2-d45e5f2393fc` |

检测结果图使用不同颜色区分交通标志和人员车辆；详情页展示四项视觉统计、每个检测的模型来源、原始类别代码、事件阈值和静态图片限制说明。Chromium 桌面与 390×844 移动端均验证通过，无页面脚本错误或失败请求。

### 14.3 ByteTrack 视频功能与浏览器播放验证

为避免把合成移动伪装成真实逆行，视频冒烟使用真实宿舍区照片生成 2 秒静止测试视频，只验证解码、真实 YOLO26 推理、ByteTrack、人员聚集、输出编码和页面播放；预期逆行必须为 0：

| 检查项 | 实测结果 |
|---|---|
| 检测模型/跟踪器 | `yolo26n.pt` / ByteTrack |
| 分析帧 | 5 |
| 最大同帧人数 | 9 |
| 唯一人员轨迹 | 9 |
| 视觉事件 | 人员聚集 1 个 |
| 逆行轨迹 | 0，符合静止画面预期 |
| 后端分析耗时 | 881.79 ms |
| 输出格式 | VP8/WebM |
| Chromium 媒体状态 | `readyState=4`、时长 2 秒、无媒体错误 |

首次视频冒烟如实暴露 ByteTrack 缺少 `lap` 的 422 错误。项目已在 `backend/requirements.txt` 固定 `lap>=0.5.12,<0.6`；当前受控 Windows 环境通过 Mihomo `127.0.0.1:7890` 下载到项目忽略的 `.runtime/python-packages`，Docker 构建则按 requirements 正常安装。修复后同一视频接口和前端上传流程均通过。

逆行规则另以确定性轨迹单元测试覆盖：连续向允许方向相反移动会触发，顺向移动与低位移抖动均不触发。真实校园逆行准确性仍需用户提供固定机位视频、正确的道路允许方向和人工标注样本后才能评估，本报告不以合成视频宣称真实逆行准确率。

### 14.4 增量回归结果

| 测试层 | 最终结果 |
|---|---|
| 后端语法与全量 pytest | **27 passed，0 failed** |
| 多模型单元测试 | 通用类别白名单、模型来源、人员聚集事件通过 |
| 视频规则单元测试 | 反向/顺向/抖动三种轨迹通过 |
| 视频 API 集成 | 上传、允许方向校验、结果结构通过 |
| Alembic | `0002_multimodel_vision (head)`；新增列和索引存在 |
| 前端严格类型与生产构建 | **通过；2,291 modules** |
| 真实图片浏览器 E2E | 桌面与移动端通过；0 console error，0 request failure |
| 视频上传浏览器 E2E | 上传、分析、聚集事件、WebM 播放通过；0 console error，0 request failure |

增量证据截图：

- `frontend/output/playwright/multimodel/10-new-inspection-image-mode.png`
- `frontend/output/playwright/multimodel/11-new-inspection-video-mode.png`
- `frontend/output/playwright/multimodel/12-real-campus-crowd-detail.png`
- `frontend/output/playwright/multimodel/13-real-campus-crowd-mobile.png`
- `frontend/output/playwright/multimodel/14-video-analytics-end-to-end.png`

**增量最终判定：系统现已从单一交通标志模型扩展为“交通标志专用 YOLO26 + 官方人员车辆 YOLO26 + 静态事件规则 + ByteTrack 视频轨迹”的多模型视觉系统。四川现代职业学院真实照片上的人员聚集候选已通过完整工作流；视频聚集和逆行功能可用，但逆行准确率必须等待真实固定机位视频再评估。**

---

## 15. 2026-09-11 最终运行态复验

在后端改为从项目自包含路径 `models/yolo26n.pt` 加载通用模型后，重新启动 FastAPI，并对当前代码和实际运行服务执行最终验收：

| 验收项 | 最终实测结果 |
|---|---|
| 后端语法、单元、服务与 API 集成 | `python -m compileall -q app tests` 通过；`pytest` **27 passed，0 failed，10.82 s** |
| 数据库迁移 | `0002_multimodel_vision (head)`；`alembic check` 返回 `No new upgrade operations detected` |
| 前端严格类型与生产构建 | `vue-tsc -b && vite build` 通过；2,291 modules；33.63 s |
| Docker Compose 静态配置 | `docker compose config --quiet` 通过；Docker 用户配置权限仅产生警告，不影响 Compose 解析结果 |
| 代码差异格式 | `git diff --check -- campus-safety-agent` 通过 |
| 运行态健康 | `status=ok`，SQLite 与 embedded Qdrant 均为 `ok`，DeepSeek、高德和显式出站代理均已配置 |
| 模型进程内加载 | `yolo26-tt100k-best.pt` 与 `yolo26n.pt` 均 `loaded=true`、`load_count=1` |
| 自包含模型真实图片复验 | 四川现代职业学院宿舍区照片检出 13 人、0 个交通标志，生成 1 个“人员聚集候选”，DeepSeek 使用 `analysis_mode=llm`，任务按边界进入人工复核 |
| 标准浏览器 E2E | Chromium **9/9 passed，0 failed，23.332 s** |

浏览器 E2E 覆盖健康和错误边界、Dashboard、高德实时态势、全部当前路由、空表单校验、人工复核闭环、归档持久化、知识文档入库和检索、设置状态、390×844 移动端布局，以及浏览器页面/控制台/网络异常收集。最终 `page_errors=0`、`console_errors=0`；1 个 `ERR_ABORTED` 是页面导航主动取消上一页尚未完成的旧请求，已作为预期导航信号分类，不属于接口失败。高德真实地图返回可用，Dashboard 显示“高德底图 · 实时态势”。

标准 E2E 脚本同时修复了两个可重复性问题：数据库为空时使用“生成并复核”，已有真实待复核任务时使用“进入复核”；进入归档页后等待异步表格出现本次任务编号再断言。该修复只影响自动测试，不改变产品业务功能。

最终浏览器证据与结构化结果：

- `frontend/output/playwright/standard-test/e2e-result.json`
- `frontend/output/playwright/standard-test/01-dashboard-desktop.png`
- `frontend/output/playwright/standard-test/02-review-queue-before.png`
- `frontend/output/playwright/standard-test/03-inspection-before-confirm.png`
- `frontend/output/playwright/standard-test/04-inspection-confirmed.png`
- `frontend/output/playwright/standard-test/05-knowledge-search.png`
- `frontend/output/playwright/standard-test/06-dashboard-mobile.png`

**最终判定：在“不继续训练、采用已接受的 TT100K 最佳检查点”的前提下，当前本地运行态的双 YOLO26、四川现代职业学院真实图片、人员聚集候选、视频上传与 ByteTrack、人工复核、归档、知识库、DeepSeek、高德地图、前端桌面/移动端均通过现有功能范围内的验收。真实逆行准确率仍必须等待固定机位真实视频和人工标注，不能由静态图或静止冒烟视频推断。**

---

## 16. 2026-09-11 前端高密度工作台与响应式复验

### 16.1 本轮视觉改造

本轮严格限定为现有前端信息架构和交互的视觉重排，没有新增后端能力、修改 API 语义或恢复模型训练。视觉真值继续采用用户选定的深色校园 GIS 指挥中心参考图，重点修复业务页左右留白过多、卡片被强制撑高、关键信息缺乏层次的问题：

- 新建巡检：改为“表单 + 上传证据 + 提交准备度/Agent 执行链/识别范围”工作台；准备度和识别范围根据真实输入与图片/视频模式变化。
- 巡检档案：保留真实任务表，新增真实闭环率、平均耗时、状态分布和区域覆盖侧栏；移动端由宽表切换为可读任务卡片。
- 人工复核：写死的等待时长和区域数量已删除，改用真实高风险数、复核原因数和区域数；补充复核质量检查、标准流程和人工覆盖原则。
- 知识库：增加文档数、就绪数、片段数和本次命中数，形成来源、检索、治理三栏工作台；无命中时提供可点击的真实检索建议。
- 系统设置：完整展示数据库、Qdrant、交通标志 YOLO26、人员车辆 YOLO26、DeepSeek 和高德状态，并明确服务端密钥边界、失败降级与运行链路。
- 巡检详情：Agent 轨迹卡改为自然高度的粘性上下文面板，增加节点进度、耗时、复核状态、知识依据和报告状态，消除与长检测表等高造成的空白。
- 全局：业务页改为满宽流式容器，移除 `calc(100vh - ...)` 强制空高度；Dashboard 地图使用更深的低饱和蓝灰滤镜贴近参考图。

### 16.2 视觉与响应式矩阵

自动截图脚本 `frontend/scripts/capture_ui_density.py` 共覆盖 17 个页面/视口状态：

| 视口 | 覆盖页面 | 结果 |
|---|---|---|
| 1440×1000 | Dashboard、新建巡检、档案、复核、知识库、设置、真实巡检详情 | **7/7 通过** |
| 1920×1080 | 新建巡检、档案、复核、知识库、设置 | **5/5 通过；页面使用完整可用宽度** |
| 390×844 | 新建巡检、档案、复核、知识库、设置 | **5/5 通过；文档宽度 390px，无横向撑宽** |

最终采集信号为 `page_errors=0`、`console_errors=0`、`failed_requests=0`。参考图与 Dashboard 最终实现放在同一张对照板中复核：`frontend/output/playwright/ui-density-audit/reference-vs-dashboard.png`。全部截图和结构化采集报告位于 `frontend/output/playwright/ui-density-audit/`。

### 16.3 标准回归

| 测试层 | 最终实测结果 |
|---|---|
| 后端全量 pytest | **27 passed，0 failed，9.64 s** |
| 前端严格类型与生产构建 | **通过；2,291 modules，14.21 s** |
| 标准 Chromium E2E | **9/9 passed，0 failed，36.098 s** |
| 数据库迁移 | `0002_multimodel_vision (head)`，current 与 heads 一致 |
| Docker Compose 静态配置 | `docker compose config --quiet` 通过；Docker 用户配置读取权限仅产生环境警告 |

标准 E2E 继续覆盖健康接口和错误边界、高德实时地图、全部当前路由、空表单校验、正式双 YOLO26 重新执行、人工确认、归档持久化、知识入库和检索、设置状态及 390px 移动布局。为保证重复运行仍真实加载模型，测试在队列已有持久化任务时调用产品现有“重新执行”接口，再验证两个 YOLO26 均在进程内加载；这只增强测试可重复性，不改变产品流程。

**本轮最终判定：主要业务页已从“顶部少量内容 + 大块空白卡片”统一为与 GIS 指挥中心同一视觉语言的高密度操作工作台；桌面、宽屏和移动端均通过真实浏览器采集与现有功能回归。**

---

## 17. 2026-09-11 Claude 交接修复轮复验

本轮修复内容与原因见 `docs/HANDOFF.md`。验证全部在独立端口（后端 8010、前端 5176）和临时 SQLite/Qdrant 目录上进行，没有改动正在运行的 8000/5173 本地预览及其数据。

### 17.1 自动化测试

| 测试层 | 实测结果 |
|---|---|
| 后端全量 pytest | **35 passed，0 failed，10.21 s**（原 27 项 + 新增 8 项） |
| 新增后端测试 | 视频跟踪不使用图片单例并复用独立实例；单例与跟踪实例互不相同；真实 `alembic upgrade head` 后探针通过；高德天气解析与缓存；空天气报错；天气接口未配置/可用/参数校验；仪表盘按本地自然日统计趋势与真实置信度；健康接口跟踪模型字段 |
| 前端严格类型与生产构建 | `vue-tsc -b && vite build` **通过**，12.64 s |

### 17.2 真实权重复现与修复验证

使用正式 `yolo26n.pt` 与四川现代职业学院宿舍区照片（`frontend/public/campus/dormitory-crowd.png`），并用同一张照片生成 12 帧测试视频：

| 场景 | 结果 |
|---|---|
| 修复前的 Ultralytics 行为：同一模型对象先 `track(persist=True)` 再 `predict` | 人员检测 **13 → 6**，结果带上跟踪 ID；人员聚集阈值为 8，候选事件会漏报 |
| 修复后：`TrafficSignDetectionTool.detect` → `VideoAnalyticsTool.analyze` → 再次 `detect` | **13 → 13**，检测结果逐项一致；聚集候选前后均为 13 人；图片预测器没有 `trackers` 属性；两个模型实例不同，加载次数各 1 |
| Docker 探针 | 迁移到 head 的数据库：新探针 `passed`；同一数据库用旧常量 `0001_initial`：`failed`（证明旧代码会让 Docker 验收失败） |

测试视频写出 VP8/WebM 时 OpenCV 会打印 `tag 0x30385056/'VP80' is not supported with codec id 139` 警告，文件仍正常生成；这是修复前就存在的提示，第 14.3 节已验证 Chromium 可播放。

### 17.3 标准浏览器 E2E 与真实数据仪表盘

- 项目原版 `frontend/scripts/e2e_existing_features.py` 未改动，经启动器以系统 Chrome 运行（本机没有安装 Python Playwright，Playwright 1.62 期望的浏览器版本与缓存不一致）：**9/9 passed，0 failed，36.945 s**；`page_errors=0`、`console_errors=0`、`failed_requests=0`；DeepSeek `analysis_mode=llm`；高德静态图可用；移动端文档宽 390px。
- E2E 运行时数据库为空，Dashboard 处于演示态势。之后通过 HTTP 依次执行视频分析和图片巡检再检查真实模式：视频之后的图片巡检仍检出 13 人并生成“人员聚集候选”；`/health` 显示 `load_count=1`、`tracking_loaded=true`、`tracking_load_count=1`（两次视频分析后仍为 1）。
- 真实模式 Dashboard：KPI 为“今日巡检 3 次 / 较昨日 +3”“待复核 2 条 / 近 7 日 2 条”“高风险 0 起”“在线摄像头 — / 摄像头接口未接入”；顶栏显示高德实况“21°C 阴”；地图只剩 3 个门岗点位；演示标记 0 个；页面错误 0。
- 证据：`frontend/output/playwright/claude-handoff-2026-09-11/`（`e2e-result.json`、01–06 标准截图、`10-dashboard-real-data-desktop.png`、`11-dashboard-real-data-mobile.png`、`real-data-dashboard-check.json`）。Codex 此前的 `standard-test/` 证据未被覆盖。

### 17.4 未验证项

- **Docker 运行态没有重跑。** 本轮修复了必然导致失败的探针和 Nginx 上传上限，但尚未用新镜像执行 `scripts/docker-runtime-acceptance.ps1`。
- 用户要手动验收，8000 端口本地预览后端已按原命令重启为新代码，数据库和知识库未变。重启后复查：`/health` 正常且含跟踪模型字段；`/dashboard` 返回 7 日趋势（共 5 个任务、今日 2 个）；高德实况天气可用。5173 的 Vite 已热更新到新前端。
- Ruff 仍未执行（环境未安装）。

---

## 18. 2026-09-12 判定链路、YOLO26m 与真实数据分析最终验收

本轮遵循用户“停止训练、采用现有最佳检查点”的决定，没有恢复任何训练进程。验收范围为当前已有功能、已接受的 TT100K 权重、通用 YOLO26m、DeepSeek/高德配置、图片质量与复核策略修复，以及新增的真实数据分析工作台。

### 18.1 缺陷修复验证

| 检查项 | 实测结果 |
|---|---|
| 图片清晰度口径 | 长边统一到 1024px 后计算拉普拉斯方差，阈值 500；15 张审计样本 14 张通过、1 张已知柔焦样本告警 |
| 低纹理清晰图误报 | `IMG_9794` 归一化分数 1010.3，已不再被误判为模糊；旧柔焦样本 152.6，仍能触发告警 |
| 质量告警路由 | 能解码的图片继续执行双 YOLO、RAG、风险研判和报告，质量问题作为复核原因保留；无法解码才短路 |
| 低置信度规则 | 仅当全部检测都低于各自模型复核阈值时强制复核；图内高置信证据不再被一个低分框覆盖 |
| 复核策略 B | 明确原因、视觉事件或 medium/high/review 风险均复核；仅无原因、无事件的 low 自动完成 |
| 非确定性复验 | 同一任务当次 3 次均为 `review / score 30 / review_required=true`；`review_required` 不再由模型直接输出，但 `risk_level`/`risk_score` 仍是 LLM 研判，温度 0 不构成跨供应商版本的确定性证明 |

### 18.2 YOLO26m 真实图片对比

对 15 个混合来源巡检文件先按 SHA-256 内容去重，得到 10 张唯一图片，再以 `imgsz=640`、`conf=0.2` 对比官方通用模型。样本并非全部本校实拍且没有人工真值，本节只描述候选框数量与置信度，不宣称准确率或召回率提升：

| 指标 | YOLO26n | YOLO26m | 结论 |
|---|---:|---:|---|
| 总检出数 | 35 | 47 | **约 +34%** |
| 有检出的图片 | 5 / 10 | 7 / 10 | 增加 2 张 |
| 低于复核阈值 0.35 的检出数 | 12 | 11 | 小幅减少 |
| 平均置信度 | 0.5365 | 0.5638 | 提升 |
| 最高置信度 | 0.9088 | 0.9540 | 提升 |
| 汽车检出 / 平均置信度 | 11 / 0.4867 | 15 / 0.5928 | 数量和平均置信度均提升 |

当前默认通用权重为 `models/yolo26m.pt`，大小 44,255,705 bytes，SHA-256：`401CEA9AB23AD19246FF7744859816BC599F350E93C9DD30367B6F0A0745D0B7`。TT100K 专用权重仍为用户接受的 `models/yolo26-tt100k-best.pt`，训练状态不变。

结构化证据：`outputs/general_model_comparison_unique_20260913.json`（含 15→10 去重清单、权重哈希、运行设备和耗时）。旧文件 `outputs/general_model_comparison.json` 仅保留为未去重历史证据，不再作为模型收益口径。正式 TT100K 图像 E2E 证据：`outputs/formal-model-e2e-current.json`（4 个检测、`analysis_mode=llm`、9 个工作流节点、报告成功、任务进入复核）。

### 18.3 真实数据分析接口与前端

新增只读 `/api/v1/analytics/overview` 和 `/analytics` 页面。运行态使用当前生产 SQLite 的完整副本（完整性 `ok`、初始 11 项任务）验收，不写入 8000 服务的数据：

- 4 项 KPI：累计巡检、闭环完成率、人工复核率、平均链路耗时。
- 7 个真实数据面板：30 日任务/复核/高风险趋势、风险构成、区域分布、复核原因、模型贡献、高频类别、Agent 节点耗时。
- 当前副本返回 11 项任务、10 项待复核、5 个区域；复核原因按任务内类别去重，历史模型文件名如实保留。
- 前端使用可复用 `DataChart.vue`，ECharts 按需注册，监听 ResizeObserver；空数据展示原因与下一步，不填充演示指标。

### 18.4 最终测试矩阵

| 测试层 | 最终结果 |
|---|---|
| 后端全量 pytest | **44 passed，0 failed，18.46 s**（2026-09-12 最终重跑） |
| 前端严格类型与生产构建 | **通过；2295 modules，22.24 s**（2026-09-12 最终重跑） |
| 数据库全新迁移 | `0001_initial → 0002_multimodel_vision (head)` 成功 |
| Alembic 模型一致性 | `No new upgrade operations detected` |
| Docker Compose 静态配置 | `docker compose config --quiet` **通过** |
| Docker 运行态 | CLI 29.6.1 可用；守护进程未启动，故本轮没有伪报容器运行态通过 |
| git 差异格式 | `git diff --check` **通过** |
| 浏览器桌面与移动验收 | **6/6 passed，0 failed** |
| 浏览器异常收集 | `page_errors=0`、`console_errors=0`、`failed_requests=0`、404=0 |

浏览器验收使用 1489×1070 与用户参考图同尺寸，并检查 390×844 移动端。覆盖：健康/分析 API 和 404 边界、GIS Dashboard、七项导航、七个 ECharts 面板、刷新交互、新建巡检空表单校验、档案、复核队列进入真实详情、知识库、系统设置，以及桌面/移动文档宽度。Dashboard 与参考图已左右拼接后复核，主区域层级和比例一致。

证据目录：

- `frontend/output/playwright/visual-audit/visual-acceptance-report.json`
- `frontend/output/playwright/visual-audit/dashboard-reference-comparison.png`
- `frontend/output/playwright/visual-audit/dashboard-1489x1070.png`
- `frontend/output/playwright/visual-audit/analytics-1489x1070.png`
- `frontend/output/playwright/visual-audit/dashboard-mobile-390x844.png`
- `frontend/output/playwright/visual-audit/analytics-mobile-390x844.png`

**本轮判定：当前源码范围内的判定链路修复、正式 TT100K 权重、通用 YOLO26m、真实数据分析、前端桌面/移动布局、迁移与 Compose 静态配置均通过。Docker 守护进程未启动仍是唯一未执行的环境级运行态验收；这不等同于应用测试失败，但提交材料时应保持该边界说明。**

### 18.5 22:51 收口复验与环境边界

- 本地预览进程退出导致首次续跑收到 `ECONNREFUSED`，该次失败是服务未运行；恢复 8010 后端和 5173 前端后重新执行验收，最新结果时间为 `2026-09-12T14:51:20.960Z`（北京时间 22:51）。
- 浏览器验收脚本补齐移动端错误监听，将所有浏览器 HTTP 4xx/5xx 计为失败；不再忽略供应商 503，不再允许缺少真实复核按钮时跳过检查，刷新操作须收到分析 API 的 HTTP 200。加严后仍 **6/6 通过**，页面错误、控制台错误、失败请求、HTTP 错误均为 0。
- 修正启动脚本：后端使用指定 `yolo_change` 解释器和正确 CWD；前端支持后端端口参数并启用严格端口检查；组合预览启动器将代理目标同步到参数端口。三个 PowerShell 脚本与浏览器脚本均通过语法检查，前端启动脚本已在 5173 → 8010 组合下实际使用。
- 已尝试启动 Docker Desktop，其进程存在，但默认 `docker_engine` 和明确的 `dockerDesktopLinuxEngine` 管道均不存在，Docker 配置读取同时报 `Access is denied`。因此不能把剩余问题简单表述为“尚未尝试打开 Desktop”；当前是 **Desktop 启动尝试后，执行环境仍无法连接 Engine**。没有运行会写入容器知识库的验收步骤，没有上传演示夹具。
- 当前 5173 使用的是 8010 隔离数据库副本，Qdrant 为内存实例；这用于 UI 与回归预览，不代表正式知识库已复制或正式服务已完成部署。正式环境仍使用原来的 SQLite 和 embedded Qdrant 数据目录。

---

## 19. 2026-09-13 专家审核整改与灰黑表面主题复验

### 19.1 数据与判定链路整改

- 通用模型对比脚本改为按文件内容 SHA-256 去重、显式记录运行设备与两份权重哈希，并拒绝覆盖已有证据文件。15 个输入文件对应 10 张唯一图片；nano/medium 为 35/47 个候选框、5/7 张有检出、12/11 个低于 0.35 的框。
- 该集合是混合来源巡检样本且没有人工真值，结论只用于资源选型，不表述为准确率或召回率提升。旧的 61→91/+49% 是包含重复别名的文件口径，已在当前文档修正、在历史交接段加勘误。
- 人工复核布尔值与理由由后端策略层单次计算；LLM schema 不接受 `review_required`/`policy_reasons`。内部策略理由经工作流保存到任务 `review_reasons_json`，模型服务异常的降级证据可在后续 GET 和分析聚合中读取。
- 质量路由采用 fail-closed：只有 `image_quality.analyzable is True` 才进入检测；字段缺失、`None`、`False` 均进入人工复核，无法解码不会越过护栏继续分析。
- 决策边界记录在 `docs/audit/REMEDIATION_2026-09-13.md`。本轮不在 10 张无真值样本上调整 0.35，不自动放行 medium，不覆盖生产库历史任务，也不把 LLM 风险等级描述为完全确定。

### 19.2 仅背景表面色调整

按用户确认方案，仅替换 `frontend/src/styles.css` 的 8 个表面 token：

| Token | 当前值 |
|---|---|
| `--canvas` | `#0d1117` |
| `--canvas-deep` | `#010409` |
| `--sidebar` | `#0d1117` |
| `--panel` | `#161b22` |
| `--panel-2` | `#21262d` |
| `--panel-3` | `#2d333b` |
| `--line` | `#30363d` |
| `--line-soft` | `#21262d` |

文字色、蓝/青/绿/黄/红/紫强调色、字体、字号、布局与 GIS 地图配色未调整。桌面 1489×1070 的总览、数据分析、创建巡检，以及 390×844 移动端均已实际截图检查；灰黑表面层次生效，主蓝继续只承担主要操作和选中态。

### 19.3 测试矩阵

| 测试层 | 结果 |
|---|---|
| 审计专项回归 | **20 passed，0 failed，2.36 s** |
| 后端全量 pytest | **64 passed，0 failed，24.17 s**；使用全新 `--basetemp` |
| 当前代码隔离 HTTP 冒烟 | **通过**；8020 临时服务 `status/database/qdrant=ok`，双模型配置名正确，30 日分析接口正常；完成后已停止该临时进程 |
| 前端强制类型检查 | `npx vue-tsc -b --force` **通过** |
| 前端生产构建 | **通过**；2295 modules，24.71 s |
| 真实浏览器 | **6/6 passed**；桌面/移动、全部当前路由、7 个图表、刷新、复核详情、空表单校验均通过 |
| 浏览器错误采集 | `pageErrors=0`、`consoleErrors=0`、`failedRequests=0`、`httpErrors=0` |
| Docker Compose 静态配置 | `docker compose config --quiet` **通过** |
| Docker 运行态 | **未执行**；当前 Docker Engine 不可连接，不能记为通过 |
| 相关差异格式 | `git diff --check` **通过**；全工作树另有既存 `.workbuddy/memory/2026-09-12.md` EOF 空行告警，不属于本轮改动 |

浏览器报告：`frontend/output/playwright/visual-audit/visual-acceptance-report.json`，生成时间 `2026-09-13T03:45:43.912Z`。新增桌面创建巡检截图：`frontend/output/playwright/visual-audit/new-inspection-1489x1070-gray-surface.png`。

**本轮判定：审核 P0 数据口径、复核理由单一来源、保守质量路由、回归缺口与部署说明已按决策完成；灰黑表面色改造在不改变文字、强调色、字体、布局和业务功能的前提下通过构建与浏览器验收。Docker 守护进程不可用仍是唯一未执行的环境级运行态边界。**

---

## 20. 2026-09-13 六张 UI 参考图实施与真实数据边界验收

### 20.1 实施结果

本轮把六张 1680×945 参考图的视觉层级迁移到现有系统，而不是制作脱离后端的静态模板。态势总览、数据分析、新建图片/视频巡检、人工复核详情、知识库和系统设置均保留真实 API 调用；前端内置演示任务、演示知识文档和演示检索命中已经移除。

| 页面 | 数据来源与缺失处理 |
|---|---|
| 态势总览 | `/dashboard`；任务、风险、趋势和置信度来自数据库。摄像头与任务坐标无接口，显示“—/未接入”并禁用图层 |
| 数据分析 | `/analytics/overview`；4 项 KPI、7 个 ECharts 和统计口径均由当前 11 项持久化任务聚合 |
| 新建巡检 | `/health` + 巡检列表 + 用户真实选择的文件；图片/视频提交继续调用原分析接口 |
| 人工复核 | 真实待复核列表、任务详情、原图/结果图、检测表、风险结果与 Agent 轨迹 |
| 知识库 | 文档列表、Qdrant 状态和在线检索；当前 5 份文档、63 块，无正文接口时明确显示边界 |
| 系统设置 | `/health`；分别表达已连接、已配置、按需加载，密钥存在不等于外网调用成功 |

### 20.2 视觉对照结果

- 在与参考图一致的 1680×945 视口逐页采集首屏，并检查 1489×1070 桌面和 390×844 移动端。
- 总览的地图高度继承曾在地图下产生空白带，已通过取消面板强制拉伸修复。
- 复核详情首屏将真实风险研判放到右侧 Agent 轨迹上方，保持原图和结果图完整比例，不为无目标任务绘制假框。
- 视频模式只呈现上传入口、允许方向和真实能力边界；没有上传视频时不显示参考图中的轨迹数量、FPS 或事件列表。
- 六项服务卡不再把“密钥存在/权重存在”统一写成服务可用。

### 20.3 最终测试矩阵

| 测试层 | 结果 |
|---|---|
| 后端全量 pytest | **64 passed，0 failed，27.93 s** |
| 前端强制类型检查 | `vue-tsc -b --force` **通过** |
| 前端生产构建 | **通过；2291 modules transformed** |
| Playwright 综合验收 | **7/7 passed，0 failed** |
| 同尺寸参考图首屏 | Dashboard、Analytics、图片巡检、视频模式、Knowledge、Settings、Reviews、Review Detail 均完成 1680×945 截图 |
| 移动端 | Dashboard、Analytics、新建巡检、Reviews 在 390×844 无文档横向溢出 |
| 浏览器异常 | `pageErrors=0`、`consoleErrors=0`、`failedRequests=0`、`httpErrors=0` |
| 相关代码差异格式 | 本轮相关文件无新增 whitespace 错误；全工作树仍有前序 `.workbuddy/memory/2026-09-12.md` EOF 空行告警 |

证据：`frontend/output/playwright/visual-audit/visual-acceptance-report.json`、`*-reference-1680x945.png`、`video-mode-reference-1680x945.png`、`review-detail-reference-1680x945.png` 及四张移动端截图。

**本轮判定：六张参考图的布局、密度与视觉语言已接入现有真实业务系统；现有功能测试、类型检查、构建和浏览器回归通过。实时摄像头、任务地理坐标与视频直播不是当前后端功能，本轮没有伪造实现；Docker Engine 运行态也没有伪报通过。**

---

## 21. 2026-09-13 用户截图差异整改与超宽屏复验

### 21.1 截图反馈对应整改

- 新建巡检页的大段空白已确认由 CSS Grid 行高产生：近期任务原位于完整左右网格之后，右侧四张说明卡较高时把下方内容整体推迟。现将近期任务移入主操作列，紧跟表单与上传区。
- 侧栏加入透明校园建筑线稿和“厚德 精技 / 笃行 创新”校训；该元素明确是学校品牌装饰，不是实时校园数据。
- 主文字令牌调整为冷白 `#edf6ff`，二级文字为 `#b6c9dc`，辅助文字为钢蓝 `#86a0b8`；页面 kicker 统一为亮蓝，业务状态色未改变。
- 人工复核详情改为参考图的信息拓扑：顶部“人工复核 / 证据审查”与六项任务元数据；首层为原图/识别图和右侧风险、知识、不确定性、模型来源；第二层为横向 Agent 轨迹与结构化检测表。
- 对 `AX-20260910-B01B59` 真实任务的 5 条检测和 27 个真实 Agent 节点做专项验收。轨迹只改变呈现方式，全部节点仍可横向浏览，没有截断或替换数据。

### 21.2 最终测试矩阵

| 测试层 | 结果 |
|---|---|
| 后端全量 pytest | **64 passed，0 failed，30.79 s**；指定 `yolo_change` 解释器与 `backend/` CWD |
| 前端严格类型与生产构建 | **通过；2292 modules transformed，52.05 s** |
| Playwright 综合验收 | **8/8 passed，0 failed**；报告时间 `2026-09-13T09:49:23.448Z` |
| 参考图视口 | 1680×945 的 8 张页面/模式截图均重新采集 |
| 用户截图视口 | 2353×1156 新建巡检和含真实检测的复核详情专项通过；近期任务间距硬断言为 `0–20px` |
| 移动端 | 390×844 的 Dashboard、Analytics、新建巡检和 Reviews 无文档级横向溢出 |
| 浏览器异常 | `pageErrors=0`、`consoleErrors=0`、`failedRequests=0`、`httpErrors=0` |

证据：`frontend/output/playwright/visual-audit/visual-acceptance-report.json`、`new-inspection-wide-2353x1156.png`、`review-detail-detected-wide-2353x1156.png`、`*-reference-1680x945.png` 与移动端截图。

### 21.3 不能一比一复制的边界

- 参考图里的实时摄像头流、逐帧缩略带、SLA 倒计时、真实风险经纬度、视频 FPS 和直播轨迹没有当前后端接口；实现保留现有上传式图片/视频分析和诚实的“未接入/等待上传”，不绘制假数据。
- 真实现场证据的横竖比例、真实目标数量与 Agent 节点数量由任务决定，不能为了像静态参考图而裁切图片、删除节点或补检测框。
- 地图继续使用真实高德/校园 GIS 资产；不会把生成参考图中的虚构校园平面替换为生产底图。

**本轮判定：用户指出的巡检空白、侧栏校园品牌、文字层级和人工复核结构均已整改并通过超宽屏、参考尺寸、移动端、构建和回归测试。视觉差异仅保留在缺少真实后端能力或真实数据形态不同的区域。**

---

## 22. 2026-09-13 v7 字体、语义色块与连续布局终验

### 22.1 本轮针对问题

- 字体链改为为当前 Windows 实际安装的 `Noto Sans SC / Microsoft YaHei UI / Segoe UI Variable`，任务号和模型名使用 `Cascadia Code / Consolas`；浏览器计算样式断言确认 `Noto Sans SC` 生效。
- 全局字体层级按页面标题、卡片标题、正文、辅助信息重新收口；2353 宽屏下不再把常用标签压到 8–10px。
- 新增蓝、青、绿、黄、红、紫半透明语义表面，用于 KPI、检测统计、复核原因、服务状态和证据分区；Dashboard KPI 与检测统计各自动断言至少 4 种独立颜色。
- Dashboard 地图高度同时考虑下方任务表，修复 1489×1070 下地图内容向父卡片溢出 18px并裁切底部控件的问题；终验父子底边误差不超过 2px。
- 人工复核详情采用左侧独立内容栈，视觉证据后 10px 即接 Agent 轨迹与结构化检测，不再被右侧证据栏高度推迟。

### 22.2 测试矩阵

| 测试层 | 结果 |
|---|---|
| 后端全量 pytest | **64 passed，0 failed，30.00 s**；使用 `yolo_change` 解释器和 `backend/` CWD |
| 前端类型检查与生产构建 | **通过**；`vue-tsc -b` 零错误，2292 modules，35.36 s |
| Playwright 综合验收 | **8/8 passed，0 failed**；报告时间 `2026-09-13T14:11:23.443Z` |
| 真实接口与交互 | `/health`、分析聚合、现有页面、刷新、表单校验、复核进入详情均通过 |
| 参考尺寸 | 1680×945 的总览、分析、图片/视频巡检、知识库、设置、复核队列与详情通过 |
| 超宽屏 | 2353×1156 创建页和 5 条真实检测详情通过；两处内容中断几何断言通过 |
| 移动端 | 390×844 的 Dashboard、Analytics、新建巡检、Reviews 无文档级横向溢出 |
| 浏览器异常 | `pageErrors=0`、`consoleErrors=0`、`failedRequests=0`、`httpErrors=0` |

### 22.3 视觉取证

- 六张同画布参考/实现对照：`frontend/output/playwright/design-qa/01-dashboard-combined.png` 至 `06-settings-combined.png`。
- 最新运行报告：`frontend/output/playwright/visual-audit/visual-acceptance-report.json`。
- 专项截图：`dashboard-reference-1680x945.png`、`new-inspection-wide-2353x1156.png`、`review-detail-detected-reference-1680x945.png`、`review-detail-detected-wide-2353x1156.png` 及四张移动端截图。

### 22.4 真实性边界

参考图中的实时摄像头、逐帧视频缩略、FPS、直播轨迹、虚构热力波动和额外配置日志没有当前后端数据。本轮只复刻它们的视觉系统与信息拓扑；未上传视频时显示真实上传态，设置页只显示实际接入服务，内容自然结束后的页面底色不以假图表填充。

**本轮判定：字体、语义色块、Dashboard 地图裁切、巡检创建连续布局和人工复核详情连续布局均已修复；后端、构建、桌面/超宽屏/移动端真实浏览器回归全部通过。**

---

## 23. 2026-09-13 4K 高帧率视频卡顿与超时修复

### 23.1 根因与修复

- 现场视频为 2160×3840、约 60.13 FPS、271 帧；旧流程每隔 2 帧执行一次检测并以原始 4K 分辨率进行 VP8 软件编码，单次需处理 136 帧，超过前端原 60 秒请求超时。
- 视频分析现在按 10 FPS 目标分析帧率自适应采样，高帧率源视频的实际步长为 6；25 FPS 等常规视频仍采用配置步长 2。
- 分析与结果视频最长边限制为 960 像素，4K 竖屏等比处理为 540×960；原始宽高、分析宽高、配置步长和实际步长均进入真实接口响应。
- 单视频分析锁改为立即拒绝并返回明确错误，避免重复点击后无提示地排队；前端视频请求上限调整为 600 秒，并显示持续递增的实际等待秒数。
- 本机后端以 `YOLO_DEVICE=0` 使用 RTX 4060 Ti，训练任务未重启。

### 23.2 真实视频与回归结果

| 测试层 | 结果 |
|---|---|
| 用户现场 51.03 MB MP4 | **HTTP 200**；总请求 103.00 s，后端分析约 88 s |
| 采样与尺寸 | 271 源帧 → **46 分析帧**；步长 6；2160×3840 → **540×960** |
| 真实识别结果 | 峰值人员 12；人员轨迹 27；车辆轨迹 1；逆行候选轨迹 7 |
| 结果视频 | WebM 成功生成，OpenCV 可重新打开；540×960，3,347,569 bytes |
| 后端全量 pytest | **65 passed，0 failed，34.96 s**；使用 `yolo_change` 解释器与 `backend/` CWD |
| 前端类型检查与生产构建 | **通过**；2292 modules transformed，46.22 s |

**本轮判定：截图中的视频请求并非模型崩溃，而是同步分析超过旧前端超时；现在真实视频可完整返回结果、浏览器等待状态可见、重复提交会明确拒绝，后端与前端回归通过。**

---

## 24. 2026-09-13 知识库缺口整改与双维度检索审计

### 24.1 决策与实施

按 `docs/KNOWLEDGE_GAP_ASSESSMENT_2026-09-13.md` 完成三项决策（A1 视觉可验证边界 / B1 逆行闭环保持现状并如实标注 / C3 本轮 hash 重写、语义嵌入单独立项），改写两份知识文档并经生产 API「删旧→传新」：

| 文档 | 块数变化 | 新增内容 |
|---|---|---|
| 校园交通安全巡检判定规范.md | 13 → 17 | 逆行能力边界纪律；逆行条文嵌入真实类别代号（pne/p5/i5/bicycle/motorcycle）；共享单车与外卖配送判定条目；恶劣天气专项（道交法 42 条、实施条例 46/58 条，均经官方网站核实） |
| 校园交通隐患整改建议库.md | 12 → 15 | 逆行条目区域名+代号逐句嵌入与能力边界；共享单车/外卖配送整改模板；恶劣天气整改条目 |

线上库：5 份 / 70 块（原 63），其余 3 份未动；`uploads/knowledge/` 零孤儿。法条引用全部经官方网站交叉验证，未凭记忆填写。

### 24.2 双维度检索审计（改前/改后）

| 维度 | 零命中 | 分数区间 | 管理实践席位 | 判定规范 | 建议库 |
|---|---|---|---|---|---|
| 区域 16 查询 | 0 → 0 | 0.2777~0.5558 → 0.2819~0.6045 | 51 → 47 | 19 → 20 | 10 → 13 |
| 隐患 12 查询 | 0 → 0 | 0.2362~0.5435 → 0.2750~0.5435 | 41 → 27 | 15 → 24 | 4 → 9 |

改前基线与 2026-09-11 审计逐位一致。通用词块霸榜被稀释（管理实践 92 → 74 席）；非机动车乱停、共享单车、外卖配送、违停等目标场景的业务文档席位显著增加。

### 24.3 如实记录的边界

- 恶劣天气专项块即使把「雨天/湿滑/雾」塞进查询词也进不了 top5（hash 排序噪声的硬边界），其激活需语义嵌入（C2）或后端天气注入，本轮未解决、已立项。
- 逆行知识对真实格式查询仍结构性不可召回，与诊断结论一致。
- 隔离库真实任务回归（AX-20260913-ACA61A，IMG_9781/p11 0.942）：`analysis_mode=llm`、p11 正确译为禁止鸣喇叭、知识引用与审计预测逐位一致；单次重跑不作 A/B 判断。临时隔离环境（8030）已停止并删除，未写入生产库任务表。

### 24.4 测试矩阵

| 测试层 | 结果 |
|---|---|
| 分块自检（`scripts/check_knowledge_chunks.py`） | 源目录 6 文件 / 71 块，0 个需要关注；线上 70 块与自检一致 |
| 离线召回模拟（新增 `scripts/simulate_knowledge_recall.py`） | 分数与线上逐位吻合，动库前预检通过 |
| 双维度检索审计（改后线上库实测） | 零命中 0/28；证据 `outputs/kb_audit_{before,after}_20260913.json` |
| 后端全量 pytest | **65 passed，0 failed，28.85 s**（全新 `--basetemp`） |
| 前端 | 本轮未改前端，无需回归 |

**本轮判定：知识库三项决策已定案并记录；两份文档按 hash 口径完成重写与生产替换，零退化且目标场景席位提升；天气与逆行的结构性检索边界经实测再次确认并如实记录，语义嵌入（C2）取得立项依据。**

## 25. 2026-09-13 VLM 旁挂视觉研判（模式乙）接入与端到端回归

### 25.1 选型实验（接入前零风险验证，`scripts/test_vlm_parking.py`）

对 3 张违停预期样例（含 IMG_9752/IMG_9759）双轮对照两个候选视觉模型：

| 模型 | 端点 | 方向判断 | 确定性 |
|---|---|---|---|
| 阿里百炼 qwen3.7-flash | 百炼 compatible-mode | **偏宽松**：违停预期图被判「合规」（9752/9759 高置信合规） | 两轮一致 |
| DeepSeek deepseek-v4-flash-vision-exp | api.deepseek.com（复用 LLM_API_KEY） | **保守诚实**：9759 判 uncertain（0.4），承认未见车位线无法定论 | 两轮一致 |

**结论：默认采用 deepseek-v4-flash-vision-exp**（config 默认值；qwen 保留 `.env` 注释掉的切换行 + DASHSCOPE_API_KEY，可随时改回）。

### 25.2 接入实现（模式乙：旁挂证据侧车，DeepSeek 仍是唯一决策者）

- `config.py`：`vision_llm_enabled`（默认 False，回退时与改造前逐字节等价）+ base_url/api_key/model/timeout/`vision_image_max_side`/`vision_skip_images_with_person`。
- `tools/privacy_mask.py`（新增）：haar 人脸模糊 + 长边归一 1024 + JPEG 重编码；person 图由闸门在上游直接拦截，打码仅兜底。
- `services/llm.py`：`VisionLLMService`（白名单 7 键收敛、置信度夹紧 0~1、HTTP 错误重试；DeepSeek 用 `thinking` 字段、百炼用 `enable_thinking`；DeepSeek 走代理、其他直连）。
- `services/risk.py`：`evaluate()` 接收 `vision_assessment`，转证据文本并入 evidence，payload 附 `vision_assessment_role`（声明仅作证据、不得直接采用）；不产生任何策略字段。
- `agents/graph.py`：`_run_vision_assessment()`——服务不可用/未启用 → None（等价旧路径）；person 闸门静默跳过（隐私）；任何异常降级纯文本并追加复核原因（fail-closed）。
- `main.py` 装配、`router.py` health 暴露 `vision_llm` 状态块（enabled/configured/model/person_gate）。

### 25.3 隔离端到端回归（真实 API + 真实权重，隔离 DB/Qdrant/上传目录）

`scripts/e2e_vlm_regression.py`，证据 `outputs/vlm_e2e_regression_20260913.json`，**全部检查通过**：

| 用例 | 结果 |
|---|---|
| A：IMG_9759（违停、无人物） | 视觉服务恰好调用 1 次；返回仅含白名单字段；`vision_assessment` 与并入 DeepSeek payload 的内容逐字节一致；payload 含模式乙角色声明；研判结论 uncertain 0.4 并列出可见证据与已排除的合法情形 |
| B：IMG_9760（YOLO 检出 2 名 person） | 隐私闸门生效，视觉服务**零调用**，图片未上送云端；巡检正常完成 |
| health | `vision_llm.enabled/configured=true`，模型与闸门状态正确暴露 |

首轮回归曾因脚本未显式指定权重绝对路径（默认相对 `backend/`）导致检测静默为空、断言假性通过；已修正脚本并强化断言（`vision_result is not None` 为前置），第二轮真实通过。

### 25.4 测试矩阵

| 测试层 | 结果 |
|---|---|
| 后端全量 pytest（含新增 `tests/test_vision_llm.py` 15 例） | **80 passed，0 failed，30.77 s**（全新 `--basetemp`） |
| 隔离端到端回归（真实 DeepSeek + 真实视觉模型） | 全部检查通过，证据 JSON 留存 |
| 生产启用状态 | **已启用（2026-09-14 00:40 用户拍板）**：config 默认值 False→True，`.env` 显式 `VISION_LLM_ENABLED=true`；默认值翻转后全量 pytest 复跑 **80 passed，28.07 s**；生产后端已重启，health 实测 `enabled:true / configured:true / model:deepseek-v4-flash-vision-exp / person_gate:true`。回退：`.env` 改 false + 重启 |
| 前端 | 本轮未改前端，无需回归 |

**本轮判定：VLM 模式乙接入完成并经真实 API 端到端验证；隐私闸门与降级路径行为符合设计；功能默认关闭，随时可通过单一开关启用或回退。**

### 25.5 提供方切换复验（2026-09-14 01:05，DeepSeek 视觉 → qwen3-vl-plus）

用户拍板改用 qwen 系最强视觉模型。实测与验证：

| 项 | 结果 |
|---|---|
| 该 key 可用视觉模型盘点 | 标准百炼端点 `/models` 可见 250 个模型，视觉类最强为 **qwen3-vl-plus**（235B 旗舰未开放，`qwen-vl-max` 为上一代；原配置的 qwen3.7-flash 为轻量档） |
| 6 样例方向实测（`outputs/vlm_qwen3vl_plus_test_20260914.json`） | **5/6 吻合、两轮确定**：9752/9759 疑似违停 ✓、9773 合规 0.95 ✓、9781/宿舍路不确定 ✓；偏差 1 例：9769 倒置图判疑似违停（转正后识别出边缘车辆），优于 qwen3.7-flash（违停全判合规） |
| 端到端回归（qwen 提供方） | 全过（`outputs/vlm_e2e_regression_qwen_20260914.json`）：A 视觉恰调 1 次并入一致、B person 闸门零调用 |
| 生产 health | `vision_llm={enabled:true, configured:true, model:qwen3-vl-plus, person_gate:true}` |
| 全量 pytest | **80 passed，0 failed，25.31 s**（含 conftest 密闭性修复：夹具钉死 `vision_llm_*` 四字段，套件对 .env/默认值变化免疫；修复前 2 例因 .env 泄漏失败） |
| 如实记录 | 提示词敏感性：9759 在实验提示词下判疑似违停 0.75、生产提示词下判 compliant 0.95——模式乙下仅为证据，DeepSeek 最终判 review 未误放行；演示口径不得称「视觉结论=最终结论」 |

## 26. 2026-09-14 宽屏布局、模型职责与交付回归

### 26.1 测试计划与范围

按“范围/环境确认 → 用例与预期 → 执行取证 → 缺陷定位/修复 → 回归 → 准出判断”组织。仅测试现有能力：图片上传/质量/双YOLO/RAG/LLM/报告/复核、视频轨迹、统计、知识库、设置、地图代理与布局。没有发明摄像头流、用户权限系统、视频归档或实时坐标功能，也不声称 ISO/国标认证。

Windows PowerShell、conda yolo_change；生产8000只读，UI指向5173。生产库保持历史基线，不上传例文、不生成生产演示任务。真实媒体用隔离SQLite/Qdrant/上传/输出；套件80条主要是单元/集成契约，不冒充80次真实云端推理。

### 26.2 用例与实测矩阵

| 层级/用例 | 预期与实测 | 判定/证据 |
|---|---|---|
| 后端回归 | 健康/地图代理隐藏key、损坏与不支持上传、质量告警继续、低置信度策略、重复执行拒绝、SSE回放、报告、复核、反馈、真实统计与分页等；首次80 passed /28.11s，最终复跑80 passed /25.15s | 通过；conda解释器、backend CWD，pytest -q -p no:cacheprovider |
| 前端静态/类型 | vue-tsc与Vite构建 | 通过；新增耗时图曾漏传必填ariaLabel，被构建阻断，已修复后重跑 |
| 浏览器9组 | API真实状态/404、7图与刷新、7路由与空态、真实复核详情、1680参考尺寸、2353宽屏几何、用户2560五页、390移动端、无页面/控制台/HTTP/请求错误 | 9/9通过；frontend/output/playwright/visual-audit/visual-acceptance-report.json |
| 五页2560×1440 | 无横向溢出；模型名与实时health一致；知识卡align=start/命中列表独立滚动；档案≤10行且下一页切换真实记录 | 通过；*-user-2560x1440.png，主agent已目视对比 |
| 新图184554 | 保持生产阈值，上传执行/报告读取 | 3目标、1person；DeepSeek llm、medium、review，报告可读 |
| 新图191815 | 聚集候选/转人工，不伪造风险 | 13目标、12person；达8人阈值、review，报告可读，DeepSeek llm |
| 新视频185218 | 4K/60fps真实上传与ByteTrack，等比缩放采样 | 271源帧→46分析帧，stride6，540×960，76,592.17ms；max_people12/人员轨迹27；接口成功 |
| VLM独立回归 | 无人物图取得白名单证据且并入DeepSeek；有人图零视觉调用 | 7/10通过、3条失败；无人物调用WinError10013，证据未生成/未并入/无角色字段；人物检出12且闸门通过 |
| Docker结构 | 正式/独立验收Compose校验，CPU设备不继承本机0、验收独立卷与端口 | config --quiet通过，不打印密钥；独立卷替换仅只读models保留宿主机绑定 |
| Docker运行态/迁移 | Engine/构建/MySQL迁移/Qdrant/Nginx/巡检/报告 | 失败于Engine探针；构建、迁移、容器API均未进入，不能记为通过；outputs/docker-runtime-acceptance.json |

### 26.3 本轮整改与定位

- 原5173代理旧后端，health没有vision_llm且知识63块；5174/8000有qwen3-vl-plus且70块。已确认并替换旧Vite PID9700，用启动脚本把5173接到8000；后端未重启。
- Knowledge三列stretch和530px最小高度制造内部空白，已改start/自然高度；命中列表独立560px滚动，不截断正文。
- NewInspection/Settings加共享真实模型职责面板，字段缺失显示未知而非关闭。视频工作流改为视频实际链路，不暗示视频调用RAG/qwen/DeepSeek或自动归档。
- Archive当前获取列表本地10条分页，补近期真实耗时图；不是后端全库分页。历史任务不能据图证明新版本性能提升。
- Docker CPU镜像不继承本机YOLO_DEVICE=0，新增DOCKER_YOLO_DEVICE；正式前端8080/Qdrant6333仅回环绑定，需受控HTTPS认证代理上线；Nginx视频读/发超时600s。
- 验收脚本改独立campus-safety-acceptance项目，独立验收卷、8081/6334；示例知识只进验收库。无卷删除。
- npm在线取Playwright CLI被EACCES阻断；复用已安装D:/ClaudeCode/npm-cache/_npx/9833c18b2d85bc59/node_modules，通过NODE_PATH及已有Chromium1228显式路径运行既有浏览器验收，不安装插件。

### 26.4 限制与剩余缺陷

- qwen当前配置正确不等于本轮联网成功。直接探针明确WinError10013套接字访问权限拒绝，未擅改VPN、ACL或提供方。DeepSeek在新媒体隔离链路实际llm成功。生产qwen历史成功不能替代本轮失败证据。
- 视频7条反向轨迹来自left_to_right配置测试/移动镜头，不是7个真实逆行；视频聚集/轨迹属于既有规则能力，不是带真值数据集准确率测试。OpenCV给出VP80/WebM标签兼容警告，接口成功不等于所有浏览器播放兼容性均过。
- 78新图/13视频仅首选2图和1视频实际跑过，其余视频没有全部筛完。素材清单见DEMO_MEDIA_SELECTION_2026-09-14.md。
- Docker默认管道与LinuxEngine管道不存在；Desktop工具无法写用户日志目录，运行态受环境权限阻塞。服务器信息/HTTPS认证/备份恢复、SQLite→MySQL历史迁移和公网验收均未完成。
- 定时任务工具本轮未提供，未创建任务；提示词已放DEPLOYMENT。额度耗尽不能绕过，DeepSeek/百炼key不能给Codex续额度。
- 未做系统性渗透测试、并发负载/压力/浸泡测试、服务器性能SLA、所有浏览器兼容、真实校园方向真值验证；不称“所有测试全过”。
- git diff --check全仓发现既有.workbuddy/memory/2026-09-12.md尾部空行警告，未顺手覆盖他人改动。

### 26.5 准出结论

本地现有功能与UI回归可继续受控演示；不准出为“已完成公网生产部署/全部任务完成”。准出前需恢复合法Docker Engine访问、服务器部署/数据迁移与安全验收、qwen联网复验。自然内容末尾保留适量画布，不用虚构数字/图表填满每个像素。训练仍32/80锁定。

## 27. 2026-09-14 官方校徽、可读性与本地全流程回归

### 27.1 计划、环境与准入

流程为“确认范围/风险与准入 → 用例和预期 → 执行取证 → 缺陷分类 → 修正与重测 → 准出结论”，不声称获得任何测试标准认证。范围只包括现有功能，不加入摄像头、账号权限、视频归档或新知识系统。最新版用户要求本地GPU优先、云CPU部署延后，训练32/80锁定。

环境：Windows/conda yolo_change，后端CWD=backend，正式权重绝对路径；生产8000与5173/5174只读且未重启。修改型联调使用新脚本local_functional_acceptance.py的临时SQLite/Qdrant/uploads/outputs，临时后端8002/前端5176，空白数据库先迁移再启动；完成后仅清理脚本自己的临时目录与子进程。现有校园原始素材保留。

本轮Python解释器缺playwright，第一次脚本被ImportError阻断；只在`<LOCAL_PATH>`安装playwright1.58.0及其依赖，不改业务conda环境。设PYTHONPATH使用该目录，显式使用已有Chromium1228。Node视觉测试复用此前安装的Playwright；未安装插件。

### 27.2 用例、预期、结果与证据

| 层级 | 用例/预期 | 实测与判定 |
|---|---|---|
| 后端单元/集成契约 | 现有API、上传/质量/模型/规则/RAG/LLM/隐私闸门/报告/复核/反馈/统计/地图/错误与边界 | **80 passed /27.79s**；不是80次云调用，也不是渗透或压力认证 |
| 类型/生产构建 | vue-tsc零错误、Vite产物构建成功 | **通过**，最终Vite40.80s，含新校徽资产 |
| 浏览器视觉/交互 | 七路由/七图、多桌面尺寸与390移动；真实复核入口/字体色块/连续布局；校徽实际解码/顶栏≥36px/校训≥13px/任务标题≥15px/原因≥12px/按钮≥40px；Enter进入详情、折叠隐藏校训；无页面/控制台/请求/HTTP错误 | **10/10通过**，visual-audit/visual-acceptance-report.json；新增reviews-identity-2560x1392.png，最终桌面/移动复核截图已目视检查 |
| 隔离迁移 | 从空白SQLite升级当前head并查alembic_version | **通过**，0002_multimodel_vision；不代表MySQL生产迁移通过 |
| 隔离知识 | 空库→当前5份来源入库→ready/70块→真实检索有命中 | **通过**；没有向生产上传演示文档 |
| 真实网页图片闭环 | 必填校验→真实校园图片上传/执行→双YOLO/RAG/DeepSeek→可读报告/无错误轨迹 | **通过**，13目标/12人，DeepSeek analysis_mode=llm；nvidia-smi观察到隔离推理进程，确认GPU实际使用 |
| 真实网页复核闭环 | 队列按钮→详情→人工确认→completed/review_required=false→报告HTML可读→反馈持久化→档案/统计一致 | **通过**，隔离库总任务1/完成1/待复核0；不是修改历史生产基线的结果 |
| 网页空态/负例 | 1440×1000与390×844七页面；复核清空后真实空态；不存在资源404、无效检索/反馈422、损坏图片400 | **通过**，上述隔离测试共**6/6**；local-release/functional-acceptance-20260914.json，无页面/控制台错误 |
| 视频真实API | 4K原始MP4→等比降采样→ByteTrack→统计/产物返回 | **通过**，271源帧→46处理帧、540×960、55,067.97ms，峰值12人/27人员轨迹；outputs/video-ui-regression-20260914.json |
| 高德真实接口 | 只读天气/学校地理编码返回正常，不泄露key | **通过**，天气200且available=true，地理编码200/GCJ-02 103.997424,30.515862；静态地图资源在浏览器请求验收无HTTP错误 |
| Qwen真实证据回归 | 无person视觉白名单结果并入文字模型，角色声明保留；有人图零额外调用 | **未通过整体准出：7/10**；3条无person证据/并入/角色断言失败，person12/零额外调用通过；outputs/vlm-ui-regression-20260914.json；新直接探针为WinError10013套接字拒绝 |
| 数据保护/服务清理 | 生产知识不污染，测试子进程退出，不恢复训练/不改密钥 | **通过**，线上仍5份/70块全部ready，8002/5176不再监听，正式服务保留 |

### 27.3 本轮缺陷与回归

- UI已修：校训10px与线稿透明留白/低亮度导致不可辨识；顶栏通用Tickets不是校徽；复核任务13px标题/10px原因/长ISO串难读。官网原图CSS取左端校徽、字号与亮度提升、结构拆层、真实缩略图/风险徽章与键盘入口，最终构建及浏览器重测通过。
- 测试脚本已修：首轮`**/inspection/*`错误匹配`/inspection/new`导致404及KeyError，不是后端功能失败；改UUID严格匹配并对响应raise_for_status，重跑6/6，另加GPU进程真实断言。
- 仍未闭环（影响完整VLM演示）：Qwen健康已启用/配置不代表实际调用成功。直接探针在服务调用处WinError10013，当前执行环境拒绝直连套接字且不提供提升权限路径；这是运行权限边界，不是用户未授权。未改VPN/ACL/供应商或密钥。继续由既有fail-closed进入人工复核，不能用旧成功记录覆盖本轮失败。
- 视频仍有VP80/WebM兼容警告，接口成功不是所有浏览器播放通过；移动镜头的7条反向轨迹不是逆行真值；不得把此次55.1s与上次76.6s单样本差异称为性能优化。

### 27.4 复跑入口与准出

后端：backend目录下conda解释器`-m pytest -q -p no:cacheprovider`；前端：`npm run build`。浏览器视觉：设NODE_PATH为既有Node Playwright目录、PLAYWRIGHT_CHROMIUM_EXECUTABLE为已有浏览器，运行`node frontend/scripts/visual_acceptance.cjs`。

隔离真实闭环：设PYTHONPATH为上述独立Python依赖目录，在项目根用conda解释器运行`scripts/local_functional_acceptance.py --image "校园照片/新增照片和视频/MVIMG_20260913_190642_2等91项文件/MVIMG_20260913_191815.jpg" --output frontend/output/playwright/local-release/functional-acceptance-20260914.json`。该用例需GPU/真实提供方连接，可产生现有API费用，切勿把BASE_URL改为生产执行老的写入型验收脚本。输出中的任务URL属于已清理隔离库，不是持久演示入口。

**结论：本轮UI整改与本地图片完整闭环、视频API回归通过，可继续受控演示；Qwen完整联网证据未通过，不宣称全部功能全通过。** Docker运行态/公网服务器/HTTPS访问控制按用户最新优先级延后，本轮未运行也不记通过。未执行系统性渗透、压力/浸泡、全部浏览器/操作系统兼容、服务器SLA或模型真值准确率测试，不以“完整测试流程”冒充这些测试已完成。

## 28. 2026-09-14 07:52 前端运行恢复与只读复验

准入检查发现8000/PID38816仍在监听，但5173/5174均未监听。仅运行现有 `scripts/start-frontend.ps1 -BackendPort 8000 -Port 5173`，Vite严格端口启动成功（会话86745、PID24216）。后端没有重启，没有修改业务代码、生产数据库、知识库、模型或密钥；未重复启动5174。开发会话退出后可能停止，不等同服务器常驻部署。

复验顺序：端口检查 → 恢复既有前端 → 页面和代理健康 → 浏览器实际渲染/交互 → 取证与准出。`/reviews`与经5173代理的`/api/v1/health`均200，status=ok，双YOLO loaded；生产知识仍5份/70块，全部ready。CIM进程枚举权限拒绝，仅据netstat确认监听PID，不据此猜测训练或其他执行状态。

Playwright CLI因离线缓存缺失未启动，复用现有Node Playwright脚本与已安装Chromium。只读 `visual_acceptance.cjs` **10/10通过**，报告UTC时间 `2026-09-13T23:51:53.955Z`，零页面/控制台/请求/HTTP错误，涵盖校徽加载、字号与按钮尺寸、真实复核/键盘入口、七图、桌面及移动布局。最新 `reviews-identity-2560x1392.png` 已目视检查。证据仍位于frontend/output/playwright/visual-audit/。

准出：本地页面恢复可访问，统一使用 http://127.0.0.1:5173/reviews 。本轮不重复有费用的完整提供方回归；后端80 passed、构建、隔离真实GPU闭环6/6与媒体结果引用§27，不标成本次重跑。Qwen真实联网仍未闭环，Docker/公网按用户优先级延后，不能宣称所有功能/所有测试均通过。

## 29. 2026-09-14 11:17 Qwen实际联网修复与隔离回归

### 29.1 范围与诊断

仅修Qwen联网；不改UI/训练/供应商/密钥/Windows ACL/VPN设置，不写生产任务或知识库。先查运行配置（不输出密钥），再做DNS/TCP与匿名HTTP探针，定位代码路由，补边界测试，真实隔离回归，最后尝试加载到正式服务。

本轮DNS实测 `dashscope.aliyuncs.com` 为 **198.18.4.38**；直连TCP报WinError10013，既有应用代理127.0.0.1:7890可连接。通过该代理访问相同官方端点的/models（不带密钥）返回HTTP401，证明是实际百炼HTTP响应而非配置检查。`llm.py`原逻辑将所有非DeepSeek VLM的proxy设为None，国内提供方同样受到VPN Fake-IP DNS影响。

**更正历史结论：§26–28只根据10013把问题归为执行环境套接字限制，证据不充分；本轮对照探针确认可修复的Fake-IP与强制直连路由问题。** 本轮稍后的进程终止“拒绝访问”是另一项真实权限限制，不能混为一谈。

### 29.2 修复与测试矩阵

Settings新增 `vision_llm_use_outbound_proxy=True`；VLM默认继承配置好的outbound_http_proxy，空代理即直连，false明确直连；trust_env=False不让环境代理/NO_PROXY覆盖路由。保留TLS验证，不修改提供方参数、模型、密钥、白名单、人员闸门、重试与风险策略。配置说明同步README/DEPLOYMENT/.env.example，实际.env不改。

| 测试 | 预期 | 实测 |
|---|---|---|
| 路由边界 | 百炼/DeepSeek继承代理、显式直连、代理空值；不信任环境代理；TLS不关闭 | 新增4项通过 |
| 后端现有单元/集成 | 所有旧用例与新增用例通过 | **84 passed /28.95s**，不是84次云调用 |
| 前端类型/生产构建 | 交付构建无错误 | **通过**，Vite26.41s，未修改UI |
| 隔离真实Qwen | 无person图真实调用1次、返回白名单视觉证据 | **通过**，qwen3-vl-plus实际返回scene_description/parking_assessment/confidence/证据等 |
| 隔离风险链路 | 视觉证据一致并入DeepSeek payload、仅证据角色声明保留、risk_result生成 | **通过**，修复此前3个失败断言 |
| 隔离隐私闸门 | 真实YOLO检出person，图片不上送视觉云模型 | **通过**，person=12，视觉零新增调用 |
| 正式进程加载 | 重启8000使修复生效 | **未完成**，已确认PID38816/python/本项目health，Stop-Process拒绝访问；旧进程仍在运行 |

真实隔离回归 **10/10通过**，证据 `outputs/vlm-proxy-fix-20260914.json`，UTC时间2026-09-14T03:14:55.489078+00:00。临时SQLite/Qdrant/uploads/outputs与生产分离；只向隔离知识库导入正式规范，没有污染线上库。样本A模型输出compliant/0.88是此次输出，不是人工真值、准确率或稳定性承诺；最终任务review仍可能来自低置信度/策略，不应为证明联网成功强制完成。

复跑：项目根下conda yolo_change解释器运行 `scripts/e2e_vlm_regression.py --image "校园照片/新增照片/车/IMG_9759.JPG" --image-person "校园照片/新增照片和视频/MVIMG_20260913_190642_2等91项文件/MVIMG_20260913_191815.jpg" --output outputs/vlm-proxy-fix-20260914.json`。使用真实提供方，可产生已有API费用；不要改成生产写入测试。

### 29.3 准出与用户动作

**代码与隔离真实调用修复通过；正式8000仍运行旧代码，尚不能宣称网页已生效。** 尝试重启前生产列表为1completed/11review，无执行中；Get-NetTCPConnection访问拒绝，改用既有netstat核验精确监听PID，再检查python进程与本项目health；Stop-Process明确拒绝访问后未再绕过权限或使用替代终止路径。

用户需在原后端终端按Ctrl+C，再在项目根 `& .\scripts\start-backend.ps1`（脚本自动切backend CWD并使用正确conda解释器）。无需重填密钥/改VPN。后续核对重启服务与必要隔离调用即可，健康configured仍不能独立充当模型调用成功证据。

## 30. 2026-09-14 完整校名、知识库独立列与详情连续布局回归

### 30.1 范围、缺陷与修正

范围仅为用户本轮三张截图：侧栏校名缩写、知识库短卡与底部说明之间空洞、详情轨迹下方空档及整改建议过小。先检查设计规范与截图，再调整布局、补浏览器断言、执行回归并目视复查；不引入新业务或演示数字。

- AppLayout副标题由shortName改用campusProfile.name，完整显示“四川现代职业学院”，不改学校坐标。
- 知识库旧全宽底部说明必须等待最长主卡，造成短列下方空洞。改为三个独立knowledge-column，每列主卡与说明自身间距12px；来源/流水线、元数据/索引状态、检索/资料说明分别连续排布，中屏两列、手机单列。保留真实上传、文档选择与检索；空库不再因0=0显示“全部文档可检索”。
- 详情将整改建议放入detail-action-stack，紧跟真实Agent轨迹；建议逐条面板展示，正文14px、1900px以上16px，内容直接取后端数组，空数组明确提示。检测表可见上限310→590px，仍保留全部行与内部滚动；视觉卡恢复内边距。

### 30.2 执行与证据

| 层级 | 预期 | 本轮实测 |
|---|---|---|
| 后端现有单元/集成 | 不破坏既有契约 | **84 passed /29.27s**，conda yolo_change、backend CWD、关闭pytest缓存；不是84次云调用 |
| 前端类型/生产构建 | vue-tsc与Vite通过 | **通过**，最终Vite38.78s，包含手机按钮修正 |
| 浏览器现有回归与新增布局 | 七路由/七图/多屏、真实入口、校徽、无异常；完整校名与列连续 | **11/11通过**，最终报告UTC2026-09-14T03:47:57.502Z；页面/控制台/请求/HTTP错误均0 |
| 知识库真实交互 | Enter切文档、问题建议发起真实检索、结果与响应一致 | **通过**，真实检索200，显示命中数与响应一致；三列各两卡，列内间距≤16px，空态与命中态截图均复查 |
| 详情真实数据与排布 | 建议不造数、文字清晰、轨迹后连续展示 | **通过**，建议全文与后端数组一致，2560px下字体≥16px，轨迹/建议间距≤16px且宽度一致；390px无横向溢出 |
| 手机按钮边界 | 操作按钮实际可见而非仅文档无溢出 | **通过**，最终断言每个任务操作按钮left≥0、right≤视口宽度+1 |
| 运行态只读 | 页面可达、线上知识不变 | **通过**，5173知识页面200；线上5份/70块、全部ready；8000监听PID23712，5173 PID24216 |

复用已有Node Playwright与Chromium，未安装插件。CLI离线缓存缺失时改用现有脚本，不把CLI失败计为网页失败。证据目录 `frontend/output/playwright/visual-audit/`，报告 `visual-acceptance-report.json`；新增最终截图 `knowledge-continuity-empty-2560x1440.png`、`knowledge-continuity-hits-2560x1440.png`、`detail-continuity-2560x1440.png`、`detail-continuity-mobile-390x844.png`。

### 30.3 缺陷重测与准出边界

首轮新增浏览器断言虽通过，目视手机截图仍发现人工确认按钮被裁切：文档无横向溢出不能证明子元素完整可见。task-actions改flex-wrap、去掉按钮叠加margin，并增加实际按钮边界断言；随后重跑最终构建与11组浏览器验收，桌面及手机截图复查通过。

本轮没有改后端、生产任务/知识、密钥或训练，没有上传执行、人工确认写入或有费用VLM/媒体回归。完整图片闭环和视频结果引用§27，Qwen隔离实际联网结果引用§29，均不标作本轮重跑。8000已由上一轮PID38816更换为23712，本轮未重启服务，不以PID变化或健康“已配置”代替新的真实Qwen调用证据。

**准出：本轮校名与所指布局/可读性整改通过。** 通过独立列和建议重新编排消除人为区块间空洞；内容结束后的自然留白仍允许保留，不添加假数字、不强行把所有短列拉到同高。Docker/公网、全平台兼容、系统性压力/安全测试不在本轮范围，不宣称项目全部任务已完成。

## 31. 2026-09-14 最终 UI 审查、可读性整改与验收

### 31.1 范围与流程

用户授权自主确定最后一次UI优化。本轮按设计规范→八页现状截图→逐页审查→有限实现→自动回归→目视复查→缺陷重测→准出/交接执行。使用Product Design audit与Playwright方法，复用现有依赖、不安装插件、不导入模板。逐页结论/有序截图见[UI最终验收](UI_POLISH_AUDIT_2026-09-14.md)。

保留灰黑背景、字体令牌、强调色、官方校徽、地图和真实七图；主要修复辅助文字过小、服务状态省略、复核标题被缩略图挤窄、风险全文误作粗体标题、知识依据两行裁切及手机摘要竖排。真实接口、任务状态和生产数据不改，不为自然留白造数。

### 31.2 最终测试矩阵

| 层级 | 预期 | 最终实测 |
|---|---|---|
| 后端单元/集成 | 现有契约无回归 | **84 passed /28.45s**，conda yolo_change、backend CWD、关闭缓存；不是云模型调用次数 |
| 前端类型/生产构建 | vue-tsc和Vite通过 | **通过，Vite31.67s**，包含最后手机摘要修正 |
| 原有浏览器回归 | 多屏/七图/真实入口/校徽/列连续/校名无回归 | **11/11**，UTC2026-09-14T04:23:05.178Z；页面/控制台/请求/HTTP错误0，导航中止0 |
| 新增桌面/手机验收 | 八页1440×1000和390×844、稳定资源、控件/字体/真实内容 | **20/20**，UTC2026-09-14T04:22:15.490Z；errors=[] |
| 知识文件与键盘 | 中文提示/实际文件名、Space切换元数据 | **通过**；仅选择现有本地文件，无上传操作/生产写入 |
| 服务卡与真实模型 | 普通桌面四列、2560七列；状态12px可换行、Qwen来自接口 | **通过**；不以configured当作联网成功 |
| 风险摘要/知识全文 | ≥14px常规字重、全文与API一致、键盘折叠展开 | **通过**，原始textContent全文一致，无两行裁切 |
| 手机可读性/触摸 | 关键目标≥40px且未裁切、摘要标签不竖排、值不溢出 | **通过**，标签≥80px且最多两行；最终设置/知识截图再次目视检查 |
| 运行态只读 | 现有服务健康、生产知识不变 | **通过**，8000/PID23712、5173/PID24216监听；health=ok、5份70块ready；本轮未重启 |

新增脚本 `frontend/scripts/ui_polish_acceptance.cjs`，使用已有Node Playwright/Chromium；执行参数与既有visual_acceptance一致，另设UI_POLISH_PHASE=before/after。before稳定性9/9只是整改前基线。证据 `frontend/output/playwright/ui-polish/before/` 和 `after/report.json`、八页桌面/手机截图、文件键盘/设置超宽/引用展开截图；既有最终报告 `frontend/output/playwright/visual-audit/visual-acceptance-report.json`。

### 31.3 缺陷记录与准出边界

第一次新增回归19/20：innerText折叠空白使全文一致性断言失败，原始textContent与API全文实测相同，改原始文本比较，保留after/report.first-pass.json。自动20/20后目视仍发现手机设置摘要竖排，修成三行单列并增加实际宽度/行数/数值裁切检查，随后最终构建与两套浏览器重新通过。一次启动因执行器路径漏win64目录失败，纠正已有路径后重跑，不掩盖为网页通过。

**准出：本轮有限UI优化通过。** 未做生产媒体提交/人工确认、付费Qwen或DeepSeek复跑、模型准确率、所有浏览器/辅助技术、压力/安全/Docker公网验收，不声称WCAG全合规或整个项目所有功能均完成。真实媒体/联网结果沿用§27/§29并明确不是本轮重跑。训练锁定32/80、密钥和生产知识不动。

## 32. 2026-09-14 比赛 Demo 现有功能全流程测试

### 32.1 最新范围与测试流程

用户明确“不再改UI、比赛小Demo给评委看、完整测试现有功能，不考虑企业级安全与并发，仅保障基本安全”。本轮将本地GPU功能演示作为准出目标，Docker/公网、CPU性能、压力/浸泡、渗透审计与全设备认证排除在外，不因此卡住Demo交付。

按“范围/准入→用例与预期→执行取证→异常定位→重测→准出/交接”执行；完整覆盖及演示说明见[Demo测试报告](DEMO_TEST_REPORT_2026-09-14.md)。原84后端用例含单元/模拟/集成，真实云和真实网页在独立套件再次验证，绝不拿测试数量冒充准确率、云调用次数或用户人数。

正式8000/5173只读，不重启、不写任务/知识；所有提交、确认、反馈和知识导入走隔离SQLite/Qdrant/uploads/outputs。RTX4060Ti/16GB，GPU0请求+对应Python PID实测，正式交通与人员车辆权重绝对路径；conda yolo_change，backend CWD。训练32/80不恢复。没有改业务/UI源码，只新增测试与文档。

### 32.2 最终执行矩阵

| 测试 | 预期 | 最终实测 |
|---|---|---|
| 后端单元/集成/基础输入 | 原有流程与新增空图/超限图/空视频均正确 | **87 passed /31.92s**；首次原84项另跑27.75s通过，最终含新增3项 |
| 前端类型/生产构建 | vue-tsc和Vite通过 | **通过，Vite31.00s** |
| 原浏览器回归 | 多屏/七图/真实入口/校徽/独立列/空态无回归 | **11/11**，UTC04:52:14.996Z；零页面/控制台/请求/HTTP错误 |
| 八页桌面/手机/关键交互 | 稳定资源、布局、控件、全文/键盘一致 | **20/20**，UTC04:55:20.326Z；errors=[] |
| 隔离完整图片网页闭环 | 从迁移、知识到上传/分析/复核/报告/反馈/统计 | **6/6**；13检测/12person、双模型实际loaded/GPU PID可见、DeepSeek analysis_mode=llm，人工确认completed/review_required=false，反馈5，统计1总/1完成/0待复核；HTML报告可读 |
| Qwen真实隔离回归 | 无人图视觉证据并入DeepSeek、有人图闸门 | **10/10**，UTC04:51:53.773764Z；qwen3-vl-plus实际白名单字段/仅证据角色，person12/零新增视觉调用；无10013 |
| 正式Chrome视频网页闭环 | 原预览→上传/进度→GPU轨迹→数据一致→结果播放 | **4/4**，UTC04:59:39.939328Z；原2160×3840可播放，271→46帧、stride6、540×960结果可播放及OpenCV解码；最大12人/27轨迹、81,048.24ms分析，网页上传与处理92.56s；无浏览器错误 |
| 视频预览发行版对照 | 区分真实视频画面与只有音轨 | **Chrome通过，精简headless-shell不兼容（1/2）**；相同源文件Chrome2160×3840/时间推进，shell0×0但音轨推进；限制保留，不能说全浏览器通过 |
| 正式只读/地图/基本密钥卫生 | 实际地图可用、密钥不下发、正式数据不变 | **6/6**，最终UTC05:01:10.621879Z；天气available、GCJ-02 103.997424/30.515862、1024×640底图可解码；32个前端文本产物/当前公开JSON无已配置密钥，真实.env未跟踪；13任务/5文档70块ready，前后列表指纹一致 |

基本输入额外覆盖空文件/超限、损坏/不支持图片、非法方向、非法反馈/检索、404；既有套件验证API_KEY开启时写/SSE拒绝无效Key，质量/低置信度/云失败降级、重复执行与实时步骤回放。未攻击正式服务，也未声称公网匿名读接口或全部静态文件已有企业级访问控制。

### 32.3 异常分类与缺陷重测

- 超限新测试最初直接用1MB bytes做pytest参数，用例ID导致Windows临时目录超长，出现86 passed/2个setup errors。改整数size、短ids，在测试内生成相同超限数据；最终87通过。不是产品功能失败，没有改业务逻辑。
- 首次精简浏览器视频4/4只检查readyState/时长，原视频实际0×0，没有画面，因此预览断言不充分。保留report.headless-first-pass.json并补源/结果videoWidth/Height与播放推进检查；只读正式Chrome对照成功，再用正式Chrome重新跑隔离视频4/4，不能覆盖掉发行版兼容失败事实。
- 实拍视频移动镜头且方向只是left_to_right配置，7反向轨迹只验证规则，不是7个实际逆行。人员聚集需人工核对；本轮成功不是准确率真值认证。

### 32.4 证据、准出与后续使用

新增 `scripts/demo_readiness_checks.py`、`scripts/demo_video_acceptance.py`、`frontend/scripts/demo_video_preview.cjs`、`backend/tests/test_demo_boundaries.py`；无业务/UI改动。证据 `outputs/demo-functional-20260914/report.json`及图片详情截图、`outputs/demo-vlm-20260914.json`、`outputs/demo-video-20260914/report.json`及桌面/手机截图、`outputs/demo-checks-before-20260914.json`与after、`frontend/output/playwright/demo-video-preview/report.json`及两浏览器截图；原visual-audit与ui-polish报告已本轮重跑。主Agent已打开图片详情、源视频Chrome、最终结果桌面/手机截图检查。

临时8002/5176/8003/5177均已退出，脚本只回收自己临时目录；原校园素材和正式库保留。正式8000/PID23712、5173/PID24216继续监听。隔离任务/媒体URL不是演示持久地址，评委演示须重新上传留存原文件。

**准出：本地GPU版现有比赛Demo功能通过，可进入演示彩排；没有发现未解决的主链路演示阻断。** 使用本机正式Google Chrome与已验证191815人车图、9759停车图、185218视频；4K视频预留1–2分钟，图片转人工是正确流程不是失败。公开演示素材先授权/脱敏。云服务和耗时动态变化不承诺长期稳定；精简浏览器源视频兼容限制仍保留。本结论不等于所有图片/视频、所有浏览器或Docker/公网版已验收，不再要求本轮做企业级安全或并发压测。

## 33. 阿里云小内存 CPU 部署包检查（2026-09-14 13:36）

### 33.1 范围与环境事实

用户要求准备阿里云轻量部署包，服务器由用户提供Alibaba Cloud Linux3/2核/1.8 GiB/v4.9.4-rhel inactive。不是本轮SSH探测结果；版本疑似Podman兼容CLI，官方说明见deploy/README，需先验证Docker Engine/Compose/docker.service。没有服务器连接，不能声称已在服务器start/enable。

本地CLI29.6.1/Compose5.3.0；最初Engine管道不存在。用户手动打开Desktop后截图Engine running/已有campus-safety组，随后Codex对npipe dockerDesktopLinuxEngine真实请求变为permission denied，config.json亦Access denied。不能绕过ACL，不执行现有容器stop/down或清卷。**当前阻塞为会话Docker访问权限，非Desktop未安装。**

### 33.2 检查矩阵

| 项目 | 实际执行/断言 | 结果与边界 |
| --- | --- | --- |
| 后端回归 | conda yolo_change，backend CWD，唯一basetemp；本轮新增12项云部署/打包测试 | 首次97 passed/39.95s；最终99 passed/46.14s |
| 前端构建 | npm.cmd run build：vue-tsc -b + Vite | 通过，Vite43.34s；UI源码未改 |
| 云Compose结构 | docker compose --env-file deploy/cloud.env.example -f docker-compose.cloud.yml config --no-env-resolution --quiet | exit0；跳过.env.cloud加载，仅结构/变量检查，不是联网/启动 |
| shell语法 | Git Bash bash -n：cloud-deploy/preflight/verify与backend entrypoint | exit0；包内所有.sh归一LF，无改源文件内容 |
| 登录/guard/来源/错误卫生 | 合法/非法用户名密码、禁止本地guard、真实五来源/排除示例、响应错误不回显私密正文、Basic客户端auth=None确实匿名 | pytest通过；不冒充Nginx实际运行 |
| 轻量部署契约 | CPU固定、无MySQL/公开后端向量端口、frontend直接COPY dist且context允许dist、网关认证/600s请求、真实验收夹具路径存在 | pytest通过；镜像内兼容性待运行 |
| 打包负例 | campus原图（public与Vite dist副本）、backend/data/.runtime/.env均排除，LF仅改变打包字节不改源 | 2新增pytest通过 |
| ZIP完整性 | 最终r1全140文件CRC及SHA256、已配置四类密钥文本扫描 | 通过；不是历史Git/企业安全审计 |
| 包清单复核 | 精确2真实.pt、5知识、前端index存在；无.env/业务库/校园原图/示例路径；全部.sh LF | 通过 |
| 本地镜像构建/容器验收 | Engine命名管道拒绝，不能执行 | **未执行，不记通过** |
| 阿里云迁移/启动/CPU推理 | 未连接服务器 | **未执行**，已提供cloud_admin与脚本 |
| 云Qwen/高德/CPU视频/公网浏览器 | 未连接服务器/未实际模型调用 | **未执行**；健康和密钥配置不是调用成功，person闸门仍保留 |

### 33.3 实施与包核对

独立docker-compose.cloud.yml使用Nginx + CPU后端，SQLite与embedded Qdrant在cloud-data持久化，不合并原MySQL四容器。强制linuxamd64/cpu、两线程、空outbound代理，本机GPU/.env不改。frontend/Dockerfile.cloud从本轮编译dist复制，服务器不跑Node；VIDEO_MAX_DIMENSION640/TARGET_FPS5仅CPU资源参数，不保证吞吐或准确率不变。资源预检小内存要求约2GBswap/10GB空盘；不自动改swap/fstab、扩容或卸载Podman。

网关Basic认证覆盖页面/API读写/媒体/报告，/health例外；用户名与至少12字符密码校验，Linux容器生成SHA512哈希，不在包/日志打印密码。HTTP不加密：比赛无敏感素材短期临时密码，长期/个人信息需HTTPS。密钥只在服务器.env.cloud填三provider，不复制本地Windows代理、业务数据库/上传目录。新空任务库不是13条本地任务已迁移。

cloud_admin seed只处理五保留来源，重复运行不重复上传；遇意外/重复/错误来源停止而不删，不上传示例。check验证SQLite当前migration head/表、认证匿名401/授权SPA/health/知识。verify创建明确标记TT100K云CPU验收任务，实际图片双模型/DeepSeek llm/报告媒体/双loaded/确认持久化；自动确认仅功能检查非真实现场判断，可能产生模型费用。它不证明Qwen/highde/video，仍需真实云端无人物授权素材/浏览器/CPU视频验收。

首次初版149文件/221018045bytes误包含Vite复制到dist的五张未引用campus原图及public副本；清单审查发现后通过源码引用搜索核对，没有当前运行源码引用，追加打包排除与两测试。没有删源图或初版，未带r1的初版**不发布/不要上传**，旁边加DO-NOT-UPLOAD提示。

最终包：`<LOCAL_PATH>`，140文件、163081090字节（约155.5 MiB），SHA256：`f2413f1c82335bc371db279a1ad81ad8e58001db1654db5a06313fe74a67e09e`。包内RELEASE_MANIFEST记录逐文件字节/哈希、训练32/80、history_migrated=false、container_runtime_verified=false。源码含有效未提交改动，不能用git archive代替。包为源码+真实权重+预编译网页，**不是离线Docker镜像包**，首次构建仍需网络拉取基础镜像/依赖。

### 33.4 准出与下一步

本轮准出仅为“CPU部署包已生成且结构/回归/完整性检查通过”，**不等于Docker容器/1.8GiB性能/公网部署已验收**。下一步服务器核对真正Engine→start/enable→swap磁盘→上传最终r1→填.env.cloud→cloud-deploy→cloud-verify→真实Qwen/高德/短视频/公网浏览器测试与内存观测。必须保留失败实际输出，不用本地GPU测试冒充CPU版。原运行态、原文件与训练32/80保留；HANDOFF/本节/日记/PROJECT_NOTES同步，不改全球记忆文件。

## 34. 负责人显示数据清理（2026-09-14）

用户最终要求目标负责人统一改为“张林”，界面不能出现此前两种旧名称。以backend为CWD直连正式SQLite并先分组核对：13条中目标记录6、系统验收3、安保值班员2、空值2。单事务精确更新6条后，数据库为张林6、两种旧名称均0；运行中8000 `GET /api/v1/inspections?page_size=100` 返回total13/张林6/Claude前缀0。未把另外7条负责人改为张林，未修改代码，因此本轮不重复模型、构建或全量回归；页面刷新后从真实接口读取新值。
