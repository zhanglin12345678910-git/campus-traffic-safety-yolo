# 单机容器配置

`docker-compose.cloud.yml` 是可选的两容器配置：Nginx 前端、CPU 后端，以及持久化的 SQLite 和嵌入式 Qdrant。不要与根目录标准 Compose 配置合并使用。

## 准备

- Linux x86_64、Docker Engine 和 Compose。
- 足够的内存与磁盘空间，资源检查脚本会检查当前可用条件。
- 在 `models/` 放入 `yolo26-tt100k-best.pt` 与 `yolo26m.pt`。
- 在 `frontend/` 执行 `npm ci` 和 `npm run build`，此配置使用预构建的 `dist/`。
- 将 `deploy/cloud.env.example` 复制为根目录 `.env.cloud`，设置 `DEMO_USER`、独立的 `DEMO_PASSWORD` 和所需服务配置。密码至少 12 个字符，真实配置不得提交。

## 启动与检查

在项目根目录执行：

```bash
sh deploy/cloud-preflight.sh
sh deploy/cloud-deploy.sh
docker compose --env-file .env.cloud -f docker-compose.cloud.yml ps
```

默认用户名为 `operator`，监听地址与端口由 `CLOUD_BIND_IP`、`CLOUD_HTTP_PORT` 配置。默认仅监听本机回环地址。认证配置只提供基础访问控制，加密传输和其他访问策略需另外配置。

健康检查验证基础配置与存储状态，不证明模型已完成推理。

## 功能验证

准备一张授权且已脱敏的测试图片，保存为 `test-data/acceptance.jpg`，随后执行：

```bash
sh deploy/cloud-verify.sh
```

脚本会创建一条明确标记的测试任务，检查检测、报告和复核持久化。需要对应服务已配置；结果只代表该测试样本，不代表视频性能、全部外部服务或检测准确率。

## 日志与停止

```bash
docker compose --env-file .env.cloud -f docker-compose.cloud.yml logs --tail=80 backend frontend
docker compose --env-file .env.cloud -f docker-compose.cloud.yml stop
```

`cloud-data/`、`uploads/`、`outputs/` 和 `.cloud-runtime/` 是运行数据，不提交到仓库。停止不会删除这些数据，分享日志前应脱敏。通用配置要求见 [安全说明](../SECURITY.md)。
