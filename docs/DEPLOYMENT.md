# 部署说明

### 2026-09-14 阿里云 2核 / 1.8 GiB 比赛 CPU 包

当前新部署使用独立 `docker-compose.cloud.yml`，不是下面历史四容器方案：预构建Nginx前端 + CPU后端，SQLite/嵌入式Qdrant，保留真实双权重、Qwen旁挂、DeepSeek、地图、视频/复核/报告功能入口。配置仅服务器 `.env.cloud`，不复制本地GPU/Windows代理配置。新空任务库+五来源幂等入库，不自动迁移本地13任务。完整操作见 [deploy/README.md](../deploy/README.md)。

用户服务器Alibaba Cloud Linux 3 / 2核 / 1.8 GiB /声称Docker v4.9.4-rhel inactive；该版本疑似podman-docker，先查真正Engine/Compose，确认存在docker.service才start/enable，不盲目卸载。小内存要求检查至少约2 GB swap与10 GB可用磁盘；不是吞吐/峰值内存保证。只开放80与必要管理端口，网关Basic认证覆盖页面/API/媒体，HTTP非加密，长期/个人信息必须HTTPS。

本地Docker Desktop用户截图已Engine running，但Codex连Linux命名管道报permission denied，无法运行镜像构建/容器验收；阿里云未连接。静态Compose/97pytest/前端构建可验证，不得写作公网部署已成功。保留原四容器方案和隔离验收脚本，原示例夹具不删除/不入云端知识库。新包为源码+权重+dist，不含离线镜像，首次构建仍需网络。

### 2026-09-14 Qwen 本地联网修复

VLM默认继承 `OUTBOUND_HTTP_PROXY`（`VISION_LLM_USE_OUTBOUND_PROXY=true`），与提供商品牌无关；代理为空时直连，也可显式false强制直连。VLM客户端不继承环境代理变量，TLS验证不关闭。VPN Fake-IP DNS可能同样影响百炼；本机已实测百炼域名解析为<FAKE_IP>，强制直连报10013，通过已配置HTTP代理真实回归10/10。不要修改hosts/系统ACL或用猜测的真实IP替换官方域名。

代码修复后必须重启后端。当前8000/PID38816拒绝由本轮执行环境终止，尚运行旧代码；用户需在原后端终端Ctrl+C，然后在项目根运行 `& .\scripts\start-backend.ps1`。保持现有.env密钥与代理配置即可，不需重填。最新实测与运行边界见TEST_REPORT §29；不把隔离回归成功当当前旧进程已更新。

## 2026-09-14 当前交付边界（优先于下方历史说明）

本机 Compose 静态校验通过，但 Docker Engine 未启动/管道不存在，Desktop 日志目录访问拒绝；独立运行态验收实际执行并写出 failed（`outputs/docker-runtime-acceptance.json`）。不能据此称已部署。请在普通用户终端打开 Docker Desktop，确认 `docker info` 有 Server；本轮没有权限修改 Docker 用户配置或日志目录 ACL，不能绕过该限制。Windows Desktop 不是 Linux 服务器必需条件，服务器可直接用 Docker Engine。

正式配置以根 `.env` 为准：DeepSeek `LLM_*`，百炼 `VISION_LLM_BASE_URL/VISION_LLM_MODEL/VISION_LLM_API_KEY`，高德 `AMAP_WEB_SERVICE_KEY`，数据库强密码。不要复制本机 VPN 环回地址到服务器；直连服务器保持 `DOCKER_OUTBOUND_HTTP_PROXY` 为空。样例 `VISION_LLM_ENABLED=false` 只避免无视觉密钥的新部署自动联网；当前生产 `.env` 显式开启 qwen3-vl-plus。本地源码默认 true 的事实不变。

CPU 容器由 `DOCKER_YOLO_DEVICE=cpu` 单独控制，不能使用本机 `YOLO_DEVICE=0` 冒充容器 GPU 支持。Nginx 视频请求 600s；服务器低性能 CPU 下需重新实测，不保证所有视频 600s 内完成。

### 安全隔离验收

在仓库根使用 PowerShell 7：

```powershell
pwsh -NoProfile -File scripts/docker-runtime-acceptance.ps1
```

脚本现在用独立 `campus-safety-acceptance` 项目、`docker-compose.acceptance.yml`、验收命名卷（MySQL/Qdrant/uploads/outputs）、回环端口 8081/6334；不复用正式卷/上传目录。`!override` 需要 Compose ≥2.24.4。脚本优先读取 .env.example，再读取现有 .env，避免示例空 key 覆盖实际配置。示例知识只能存在验收库，不能把脚本目标改为正式地址。验收卷保留，不执行 down -v。

```powershell
docker compose --env-file .env.example -f docker-compose.yml -f docker-compose.acceptance.yml --project-name campus-safety-acceptance config --quiet
```

上面仅检查结构，不证明镜像构建、迁移、数据库连接或真实容器 API 通过。

### 公网上线前必须补齐

- 服务器系统、IP、SSH 登录方式、内存/GPU、域名/证书信息；不要通过聊天发送密码、私钥。
- 传输正式双权重、5 份保留来源，以及按策略迁移 SQLite 历史数据到 MySQL；Git 不携带 .pt/原始校园素材/业务数据，启动空容器不等于已迁移。
- MySQL/Qdrant、上传文件和报告备份与恢复验证；强密码、HTTPS、访问控制、日志脱敏及留存期限。
- 当前 API_KEY 只保护写请求和 SSE，不是完整用户登录体系；部分读接口与素材可公开读取。含校园个人信息的实例不能裸露公网。
- 正式 Compose 将前端8080与Qdrant6333绑定127.0.0.1；通过受控 HTTPS 反向代理开放80/443，并设置认证，不能开放8080绕过认证。现阶段不得宣称公网安全验收完成。

### 续工作任务：尚未创建，不绕过额度

本轮可用工具没有定时任务管理接口。请在应用的 Scheduled 中创建项目内任务（机器开机、应用运行），建议每30分钟检查。提示词：

> 读取 HANDOFF 最新轮与 TEST_REPORT 当前轮，仅在有未完成且可行动事项、且本项目没有正在执行的任务时继续工作。全部完成则静默退出；状态未变化或仍受同一外部阻塞时保持安静，只在有实质进展、完成、失败或需要用户处理时通知。不得重启模型训练，不得改生产数据、不上传示例、不绕过额度或权限。Docker/服务器/联网缺权时记录准确边界，等待条件变化。

这只是准备好的提示词，不是已注册任务。无法保证定时任务在额度耗尽时启动新推理；需要额度重置/额外额度或另行配置独立计费的 OpenAI API。系统的 DeepSeek/百炼密钥不授予 Codex 额度。

## 准备

1. 安装 Docker Desktop/Engine 和 Compose 插件。
2. 将 TT100K 正式训练并测试的权重放到 `models/yolo26-tt100k-best.pt`，并将官方 COCO 通用 medium 权重放到 `models/yolo26m.pt`。两个 `*.pt` 均被 Git 忽略，不随源码交付；缺少任一权重会导致对应检测模型无法加载。
3. 将 `.env.example` 复制为 `.env`，修改 MySQL 密码和允许来源；DeepSeek V4 Flash 已预设，只需填写 `LLM_API_KEY`。
4. 在 `.env.amap` 填写 `AMAP_WEB_SERVICE_KEY`。必须使用高德控制台创建的“Web 服务”Key，不是“Web 端（JS API）”Key；该文件已被 Git 忽略。
5. 使用 Clash/Mihomo 等 VPN 且后端无法联网时，在 `.env.proxy` 填写 `OUTBOUND_HTTP_PROXY=http://127.0.0.1:7890`。Docker 内不能使用容器自己的 `127.0.0.1`，应通过 `DOCKER_OUTBOUND_HTTP_PROXY=http://host.docker.internal:7890` 单独配置。
5. 导入经学校审核的知识资料，示例材料只能用于演示。

## 启动

项目根目录 `.env` 中的大模型配置只需这一项：

```dotenv
LLM_API_KEY=你的DeepSeek密钥
```

接口固定为 `https://api.deepseek.com`，模型固定为 `deepseek-v4-flash`。密钥仅由后端读取，不要将它填写到浏览器的“系统接口访问 Key”中，也不要提交 `.env`。

高德地图单独保存在项目根目录 `.env.amap`，等号右侧直接粘贴，不加引号：

```dotenv
AMAP_WEB_SERVICE_KEY=你的高德Web服务Key
```

本机 VPN 出站代理单独保存在根目录 `.env.proxy`：

```dotenv
OUTBOUND_HTTP_PROXY=http://127.0.0.1:7890
```

前端只请求后端 `/api/v1/maps/geocode` 和 `/api/v1/maps/static`；真实 Key 不会进入浏览器请求地址。保存后需要重启后端。

```powershell
docker compose config
docker compose up --build -d
docker compose ps
```

后端容器启动时会先执行 `python -m alembic upgrade head`，迁移成功后才启动 Uvicorn；迁移失败会使容器退出，避免在未知表结构上提供服务。

访问：

- 管理端：`http://localhost:8080`
- Qdrant：`http://localhost:6333`
- 后端由 Nginx 代理，不默认暴露独立宿主机端口。

查看日志：

```powershell
docker compose logs -f backend
```

停止服务：

```powershell
docker compose down
```

不要在需要保留数据时运行 `docker compose down -v`，因为 `-v` 会删除 MySQL 与 Qdrant 卷。

## GPU

默认容器配置使用 CPU，兼容没有 NVIDIA Container Toolkit 的机器。本机 GPU 训练通过 `training/train_yolo26.py` 执行。若生产推理要使用 GPU，先安装与 Docker 兼容的 NVIDIA 驱动/Toolkit，再为 backend 增加受控 GPU 设备映射并把 `YOLO_DEVICE` 改为 `0`。

## 上线检查

正式验收可使用 PowerShell 7 执行：

```powershell
./scripts/docker-runtime-acceptance.ps1
```

该脚本会构建并启动 Compose 服务，核对 MySQL 的 Alembic revision、10 张业务表及 `alembic_version` 迁移表，再通过前端 Nginx 入口执行知识文档入库、Qdrant 检索、样例巡检、正式 YOLO26 加载、LangGraph 检测/报告节点和报告读取。结构化结果写入 `outputs/docker-runtime-acceptance.json`，脚本不会删除数据卷。

- `/api/v1/health` 中数据库和 Qdrant 为 `ok`，YOLO `configured=true`。
- 使用一张授权样例执行完整工作流并核对 SSE 轨迹。
- 检查原图、结果图、报告、知识引用和人工复核记录。
- 备份 MySQL、Qdrant 存储及上传目录。
- 设置 HTTPS、强密码、访问控制、留存期限和个人信息脱敏策略。
- 若配置了 `API_KEY`，在管理端“系统设置”中录入；密钥只保存于当前浏览器会话，并随写请求和 SSE 连接发送。
