# 部署说明

项目支持直接运行后端与前端，也提供容器配置。本地开发步骤见 [README](../README.md)。

## 标准容器配置

根目录 `docker-compose.yml` 包含前端、后端、MySQL 和 Qdrant。前端负责页面与接口反向代理，数据库和模型文件持久化存储。

准备 Docker Engine 与 Compose，将 `.env.example` 复制为 `.env`，设置独立的数据库密码、接口访问密钥和所需外部服务配置。将权重放入 `models/`。

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

默认访问地址为 `http://127.0.0.1:8080`，默认检测设备为 CPU。模型按需加载，健康检查通过不等于真实推理已完成；应使用授权测试资料验证检测、检索、复核和报告流程。

## 运行维护

```bash
docker compose logs --tail=80 backend frontend
docker compose stop
```

停止容器不会删除持久化数据。数据库卷、上传目录和结果目录应按需备份；不要通过删除数据目录排查故障。分享日志前应移除密钥、账号和个人信息。

## 可选单机配置

`docker-compose.cloud.yml` 使用前端与 CPU 后端两个容器，后端使用 SQLite 和嵌入式 Qdrant。它与标准配置独立使用，准备步骤见 [单机容器配置](../deploy/README.md)。

容器配置不代表访问控制、加密传输或容量验证已经完成。配置要求见 [安全说明](../SECURITY.md)。
