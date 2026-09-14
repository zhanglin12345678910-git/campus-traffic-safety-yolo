# 安巡智脑

安巡智脑是一个可独立运行的校园交通安全智能巡检系统。用户上传现场图片后，系统通过真实 LangGraph 工作流调用图片质量检测、TT100K 交通标志 YOLO26、COCO 人员车辆 YOLO26、Qdrant 知识检索、风险研判、报告生成和人工复核模块，并保存完整执行轨迹；视频入口使用 ByteTrack 连续轨迹判断人员聚集与逆行候选。

## 当前模型原则

- 当前主模型：使用 TT100K 45 类完整训练集训练的 YOLO26m，640 像素，第 32 个完整 epoch 的最佳检查点。
- 原计划最多 80 epochs；已于 2026-09-08 按用户要求停止，不再自动续训。第 33 轮未完成，不计入模型选择。
- 已完成 3,992 张独立 test 集评估：Precision 0.86560、Recall 0.76376、mAP50 0.83880、mAP50-95 0.64666。
- 旧项目的 YOLO11 权重只保留为基线，不会改名或冒充 YOLO26。
- 系统主权重为 `models/yolo26-tt100k-best.pt`，SHA-256 为 `0d4ad7756c965bdb5ec2520c7124a195fabc28084cc6039ec02e1aa6a15dd9af`。
- 通用辅助权重为官方 COCO 80 类 `models/yolo26m.pt`；系统只采纳 `person/bicycle/car/motorcycle/bus/truck` 白名单，避免通用模型的交通标志结果干扰 TT100K 专用模型。混合来源巡检样本按 SHA-256 去重后的 10 张唯一图片中，medium 相比 nano 的检出总数由 35 提升至 47（约 +34%），有检出图片由 5 张增至 7 张，因此当前默认使用 medium，同时保留 nano 供低资源环境回退。该样本无人工真值，不能据此宣称准确率或召回率提升。
- 静态图片达到人数阈值时只生成“人员聚集候选”；逆行必须通过视频连续轨迹与用户配置的道路允许方向判断，不使用单张图片伪造方向结论。

## 功能

- GIS 态势总览、真实巡检数据分析、新建巡检、历史记录、任务详情、人工复核、知识库和系统状态页面。
- FastAPI REST API、真实 SSE 执行轨迹和 OpenAPI 文档。
- 11 节点 LangGraph 状态图，包含质量、置信度、知识不足和工具异常分支。
- 双 YOLO 单例延迟加载：专用模型识别交通标志，官方通用模型识别人员与五类车辆，并输出模型来源、置信度、检测框、可视化图片和分模型耗时。
- 静态图片人员聚集阈值规则；MP4/AVI/MOV/MKV/WebM 视频上传、ByteTrack 多目标跟踪、区域人数峰值与逆行轨迹规则，结果视频使用浏览器兼容的 VP8/WebM。
- PDF、DOCX、TXT、Markdown 文档解析、分块、向量化和 Qdrant Top-K 检索。
- 默认接入 DeepSeek V4 Flash；官方地址、模型名和快速模式已预设，只需填写 `LLM_API_KEY`。无密钥时明确进入规则保守模式和人工复核。
- 高德 Web Service 地理编码与静态地图由后端代理，浏览器和构建产物不包含服务 Key；供应商暂不可用时自动回退到随包校园 GIS 图。
- MySQL 生产存储、SQLite 本地测试、Alembic 初始迁移、Docker Compose + Nginx 部署。

2026-09-09 已完成 DeepSeek V4 Flash 官方鉴权与真实全链路验证：`/models` 返回 HTTP 200，巡检任务经 YOLO26、Qdrant、DeepSeek、LangGraph 和报告节点成功完成，结果为 `analysis_mode=llm`。脱敏证据保存在 `outputs/deepseek-e2e.json`。

## 目录

```text
campus-safety-agent/
├─ backend/       FastAPI、LangGraph、数据库、工具和测试
├─ frontend/      Vue 3 管理端
├─ training/      TT100K 审计、YOLO26 训练和评估
├─ models/        本地模型权重（不提交 Git）
├─ knowledge/     演示知识材料
├─ docs/          架构、接口、部署、测试和演示说明
├─ samples/       非敏感测试样例
└─ docker-compose.yml
```

## 本地启动

这台已配置好的电脑可在项目根目录分别打开两个 PowerShell 窗口，运行 `./scripts/start-backend.ps1` 与 `./scripts/start-frontend.ps1`，并保持窗口运行。后端脚本固定使用 `yolo_change` 解释器并切到 `backend/`；前端严格使用 5173 并代理到 8000，端口占用时会明确报错。使用其他后端端口时，两侧对应传入 `start-backend.ps1 -Port 8010` 与 `start-frontend.ps1 -BackendPort 8010`。已有密钥配置无需重新复制或填写。

建议使用独立 Python 3.10 环境。命令均从本项目根目录执行。DeepSeek V4 Flash 只需在根目录 `.env` 中填写 `LLM_API_KEY=你的密钥`；高德地图在根目录 `.env.amap` 中填写 `AMAP_WEB_SERVICE_KEY=你的Web服务Key`。等号右侧直接粘贴，不加中文引号，不要把密钥提交到 Git 或粘贴到前端页面。

如果正在使用 Clash/Mihomo 等 VPN，且其 Fake-IP DNS 已启用、但 Windows 系统代理没有启用，可在被 Git 忽略的根目录 `.env.proxy` 填写 `OUTBOUND_HTTP_PROXY=http://127.0.0.1:7890`。本项目让 DeepSeek、Qwen 等旁挂视觉模型、高德和可选远程 Embedding 的服务端请求使用该代理；浏览器、本地数据库、Qdrant 和 YOLO26 不经过代理。视觉模型默认 `VISION_LLM_USE_OUTBOUND_PROXY=true`，不要因百炼是国内提供方而强制直连 Fake-IP；明确可直连时可设为 false。关闭 VPN 后若代理端口不再监听，清空代理值即可恢复直连。修改配置或调用代码后需重启后端；健康接口“已配置”不等于真实模型调用成功。

```powershell
Copy-Item .env.example .env
Set-Location backend
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

另开终端：

```powershell
Set-Location frontend
npm ci
npm run dev
```

访问 `http://localhost:5173`；接口文档位于 `http://localhost:8000/docs`。

本地开发若没有 MySQL/Qdrant，可在项目根目录 `.env` 使用 `DATABASE_URL=sqlite:///./data/campus_safety.db`，并将 `QDRANT_URL` 留空以使用嵌入式 Qdrant。项目需要 `models/yolo26-tt100k-best.pt` 和 `models/yolo26m.pt` 两份权重；健康检查会分别报告两个模型是否配置。通用模型暂不可用时，交通标志流程仍会继续并明确进入人工复核。

“新建智能巡检”页面提供两个入口：图片模式串联双模型、RAG、DeepSeek 和报告；视频模式要求设置道路允许方向，使用 ByteTrack 分析人员聚集与逆行。视频方向必须与实际摄像头视角对应，所有事件均保留人工复核边界。

## YOLO26 训练

> 当前训练已按用户要求停止并锁定，以下命令只作为未来明确重新开启训练时的参考；现在不要执行。

```powershell
Set-Location training
python audit_tt100k.py --data <LOCAL_PATH> --output audit-report.json
python train_yolo26.py --preset smoke --fraction 0.01 --data <LOCAL_PATH>
python train_yolo26.py --preset baseline --data <LOCAL_PATH>
python train_yolo26.py --preset final --data <LOCAL_PATH> --promote
python evaluate_yolo26.py --weights runs\yolo26l-tt100k-960\weights\best.pt --data <LOCAL_PATH> --imgsz 960
```

评估脚本只接受训练目录里的 `best.pt`（需要同目录上一级的 `args.yaml` 与 `results.csv` 证明来源），`--imgsz` 必须与训练一致：`baseline` 预设为 640，`final` 预设为 960（脚本默认值）。不要把 `models/yolo26-tt100k-best.pt` 直接传给评估脚本，它会因文件名和缺少训练记录被拒绝。

Windows 长时间训练可运行 `scripts/run-yolo26-baseline.ps1`；它会自动恢复 `last.pt`、训练完成后复制正式权重、执行独立测试集评估并写入状态文件。默认使用 batch 12、workers 0，避免 Windows 多进程数据加载在长时间验证时耗尽主机内存；也可显式传入 `-Batch` 与 `-Workers`。用 `scripts/training-status.ps1` 查看最新进度。

当前项目已经按用户决定在第 32 个完整 epoch 结束并完成模型晋升与独立测试集评估。状态值 `completed_partial_by_user` 表示“用户明确接受提前停止的最佳完整检查点”，不是 80 轮训练已完成。启动器与看门狗都会识别该状态并拒绝自动恢复训练。

`status.json` 会记录 `training`、`evaluation`、`promotion` 或 `completed` 阶段；失败记录同时保留发生故障的阶段、attempt 与是否存在可恢复检查点。独立测试集评估期间不会被守护程序误判为训练消失。

未来若用户明确重新开启无人值守训练，可使用 PowerShell 7 执行 `scripts/start-yolo26-watchdog.ps1`。守护程序每分钟核对训练、验证或独立评估进程，连续两次缺失后才从 `last.pt` 恢复；启动器和守护程序均使用命名互斥锁避免重复训练。状态与事件分别保存在训练目录的 `watchdog-status.json` 和 `watchdog.jsonl`。

普通后台进程仍可能随启动它的终端生命周期结束。正式长时任务使用 `scripts/install-yolo26-watchdog-task.ps1` 注册当前用户的 Windows 登录任务；任务设置为无执行时限、忽略重复实例、异常后一分钟重启，并由命名互斥锁继续防止双重训练。训练完成后可在任务计划程序中禁用或删除 `CampusSafetyYolo26Watchdog`。

正式训练和独立测试集评估结束后运行 `scripts/final-acceptance.ps1`。它会核对三份权重哈希、45 类与 3,992 张测试图记录，然后依次执行数据库迁移、后端测试、前端构建、正式模型端到端巡检、Compose 配置解析和容器运行态验收。运行态验收会构建并启动 MySQL、Qdrant、后端和前端，核对 Alembic revision、10 张业务表及 `alembic_version` 迁移表，并通过 Nginx 真实执行知识入库/检索、正式 YOLO26 巡检、LangGraph 轨迹和报告生成；不会删除数据卷。

训练报告必须以生成的 `results.csv`、`best.pt` 和测试集评估 JSON 为准，计划目标不能写成真实结果。正式评估会在推理前拒绝冒烟权重、非 `best.pt`、非 3,992 张测试集、非 45 类或类别顺序不一致、`fraction` 非 1.0、训练/评估数据配置不一致以及缺少 `args.yaml`/`results.csv` 的情况，并在结果中保存所有关键文件的 SHA-256。

## 容器部署

将正式权重放入 `models/yolo26-tt100k-best.pt`，复制并修改 `.env` 后：

```powershell
docker compose config
docker compose up --build -d
```

访问 `http://localhost:8080`。详细说明见 `docs/DEPLOYMENT.md`。

## 验证

```powershell
Set-Location backend
python -m pytest
Set-Location ..\frontend
npm run typecheck
npm run build
Set-Location ..
docker compose config
```

真实校园验证时应使用经授权、已脱敏的现场图片，避免上传清晰人脸、车牌等个人信息。

已验证的桌面端与移动端截图保存在 `frontend/output/playwright/`，视觉比对见 `design-qa.md`，模型与项目最终验收结果见 `docs/TEST_REPORT.md`。
