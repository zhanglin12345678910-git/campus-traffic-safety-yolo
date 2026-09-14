# 阿里云轻量服务器部署（比赛 CPU Demo）

目标：Alibaba Cloud Linux 3、x86_64、2核、1.8 GiB内存。保持全部现有页面、双YOLO、图片/RAG/DeepSeek、Qwen旁挂证据、人工复核/报告、地图与视频入口；不承诺这台机器能达到本地GPU的视频速度。训练停在32/80，不改称完整训练。

本目录对应独立 `docker-compose.cloud.yml`，**不要与根目录四容器 Compose 合并**。两容器：Nginx预编译前端 + CPU后端，后端SQLite/嵌入式Qdrant。它是比赛轻量部署方案，不代替原MySQL部署拓扑。本地 `.env` 和GPU设置不变。

## 1. 先确认真正的 Docker Engine

```sh
cat /etc/os-release
uname -m
docker --version
podman --version
rpm -q docker-ce podman-docker
systemctl status docker --no-pager
docker compose version
```

`v4.9.4-rhel` **疑似Podman**，需要上述真实输出确认。若是podman-docker兼容命令，不能仅靠 `systemctl start docker` 修好。本方案要求真正Docker Engine和Compose插件；不要盲目卸载Podman/删除其数据。按阿里云官方Alibaba Cloud Linux 3安装步骤核对包冲突后安装Docker CE：<https://help.aliyun.com/zh/ecs/user-guide/install-and-use-docker>；官方也解释了podman-docker没有systemd守护进程：<https://help.aliyun.com/zh/document_detail/2842585.html>。

**确认存在Docker Engine后**执行：

```sh
sudo systemctl start docker
sudo systemctl enable docker
sudo docker info
sudo docker compose version
```

后续命令统一在有Docker权限的服务器终端运行（例如root终端；普通用户按需加sudo）。不能用Codex本地权限错误当作服务器失败证据。

## 2. 小内存与磁盘检查

```sh
free -h
swapon --show
df -h
```

低于3 GB物理内存时，部署脚本要求至少约2 GB交换空间；保留10 GB可用磁盘。交换空间只降低OOM风险，不增加CPU速度，也不保证双模型/视频一定能跑完。**若已有足够swap，不重复创建。** 若未满足且磁盘足够，在root终端执行下面的受保护命令（已存在同名文件就停止，不覆盖）：

```sh
if [ -e /swapfile-campus ]; then
    echo '/swapfile-campus already exists; inspect it, do not overwrite it'
else
    fallocate -l 2G /swapfile-campus &&
    chmod 600 /swapfile-campus &&
    mkswap /swapfile-campus &&
    swapon /swapfile-campus
fi
```

上述仅当前启动生效。需要开机自动启用时，先确认该swap已正常启用且fstab没有此条，再由管理员加入 `/swapfile-campus none swap sw 0 0`；脚本不会擅自改fstab。注意服务器磁盘空间/账单，不能自动扩容。

## 3. 上传解压与配置

上传生成的 `campus-safety-cloud-*.zip`，在**新目录**解压，不覆盖已有部署。ZIP内顶层目录为 `campus-safety-agent`。

```sh
unzip campus-safety-cloud-20260914-r1.zip -d release-20260914
cd release-20260914/campus-safety-agent
cp deploy/cloud.env.example .env.cloud
chmod 600 .env.cloud
vi .env.cloud
```

只需填写四项：`DEMO_PASSWORD`（至少12字符）、`LLM_API_KEY`（DeepSeek）、`VISION_LLM_API_KEY`（百炼Qwen）、`AMAP_WEB_SERVICE_KEY`（高德Web服务Key）。默认用户 `judge`。不要把密钥发回聊天，不复制Windows `.env/.env.proxy`，不要在服务器配置 `127.0.0.1:7890`。密码若有 `$`、`#` 或空格，用dotenv **ASCII单引号**包起来避免插值，不能用中文引号。`API_KEY` 保持空：本方案已通过Nginx统一认证保护页面、读写API、媒体和报告，不再让评委另填系统访问Key。

包中含本轮真实双权重（约176 MB未压缩）与已构建dist，不含密钥、原始校园照片、训练目录、生产数据库/上传记录。因此首次部署启动**新的空任务库**，再入库五份保留知识来源；本地13条历史任务不会自动出现在服务器上，原文件全部保留。若要迁移历史数据需另做一致性备份与路径转换，不要直接复制正在使用的SQLite/Qdrant目录。

## 4. 部署与验收

```sh
sh deploy/cloud-preflight.sh
sh deploy/cloud-deploy.sh
sh deploy/cloud-verify.sh
docker compose --env-file .env.cloud -f docker-compose.cloud.yml ps
docker stats --no-stream
```

部署：资源检查 → 构建CPU后端/直接复制dist的前端 → 校验配置并生成密码哈希 → SQLite迁移到当前head → 等健康 → 幂等入库五来源 → 检查schema/知识与匿名401。默认只公开80端口；后端/向量库/数据库没有宿主机映射。不上传源目录第六份 `校园交通巡检示例规范.md`，原仓库夹具不删除。

`cloud-verify.sh` 会在**这次新云库**创建一条明确标记“云端CPU部署验收（TT100K夹具，非校园实拍）”的任务，实际CPU双模型→RAG/DeepSeek→HTML报告/媒体→脚本确认并持久化。确认仅验证功能，不是人工事实核验。它可能产生模型调用费用，不影响本地库，不自动删除验收记录。执行结果存 `.cloud-runtime/acceptance-result.json`。

健康/配置成功 **不表示Qwen或高德真实联网通过**。此夹具可能检出person，按隐私闸门跳过Qwen；必须另外用已授权且无person的停车图片验证Qwen真实证据与DeepSeek引用，地图在浏览器真实加载/检索验证。视频需用已授权短视频实测CPU耗时和实际播放；移动镜头不能当真实逆行真值。脚本不会声称这些未测项目通过。

## 5. 让评委通过公网访问

阿里云轻量服务器防火墙开放TCP80（SSH22保留用于管理，**不开放8000/3306/6333**）。本机浏览器访问 `http://服务器公网IP/`，输入 `judge` 和设置的演示密码。使用真实校园素材前授权/脱敏，优先短视频、普通分辨率，CPU可能比本地GPU慢很多。

基础认证不是HTTPS：HTTP下密码/内容可能被网络监听。比赛无敏感资料的临时演示至少使用一次性独立密码，并可在云防火墙限制评委来源IP；要传个人信息或用于长期开放，先配置HTTPS。不能用这个包宣称企业级或公网安全认证已完成。防火墙说明：<https://help.aliyun.com/zh/simple-application-server/user-guide/manage-the-firewall-of-a-server>。

## 6. 排查与停止（不删除数据）

```sh
docker compose --env-file .env.cloud -f docker-compose.cloud.yml logs --tail=80 backend frontend
docker inspect --format '{{.State.OOMKilled}}' campus-safety-cloud-backend-1
free -h
docker stats --no-stream
docker compose --env-file .env.cloud -f docker-compose.cloud.yml stop
```

日志先脱敏再分享。模型默认按需加载，启动healthy时可能仍loaded=false；必须完成真实推理后检查双loaded=true。1.8 GiB若发生OOM/超时，不强称功能完成；先检查swap、磁盘、输入尺寸，必要时增配或保留本地GPU演示。切勿 `down -v`、清空cloud-data或删除uploads/outputs来“修复”。

## 当前交付边界

部署包是**源码 + 真实权重 + 预构建网页**，不是Docker镜像离线包。首次需服务器下载基础镜像/Python依赖；若国内网络下载失败，保留具体错误，再考虑已验证的镜像仓库/本地导出，不能擅自关闭TLS或使用来源不明镜像。ZIP附RELEASE_MANIFEST及每文件SHA-256/CRC验证。

2026-09-14本地Docker Desktop截图显示Engine running，但当前Codex访问Linux Engine命名管道被拒绝。因此本轮不能执行构建/容器运行测试，也尚未连接阿里云；本地与服务器容器启动、1.8 GiB峰值内存、CPU视频/Qwen/高德、公网IP浏览器可达仍需真实验收。不把静态Compose校验当部署成功。
