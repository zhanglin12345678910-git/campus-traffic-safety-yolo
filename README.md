# 安巡智脑：校园交通安全智能巡检

基于 Ultralytics YOLO11 的校园交通标志检测与安全巡检项目，包含桌面端、FastAPI 检测接口、模型结构扩展、数据分析脚本和实验工具。

## 主要内容

- `app.py`：现有桌面端入口。
- `traffic_api/`：图片检测 FastAPI 服务。
- `api_tests/`：API 合约与序列化测试。
- `scripts/`：API 启动和冒烟测试脚本。
- `ultralytics/`：项目使用的 Ultralytics/YOLO 扩展代码。
- `docs/API_README.md`：API 本地运行说明。
- `docs/API_CONTRACT.md`：接口契约。

## 快速开始

建议在能够运行 PyTorch 和 YOLO 的 Python 环境中安装项目与 API 依赖：

```powershell
pip install -e .
pip install -r requirements_api.txt
```

复制环境变量模板，并把占位值替换为仅保存在本机的配置：

```powershell
Copy-Item .env.example .env
```

不要把真实 API Key 写回 `.env.example`，也不要提交 `.env`。

启动 API：

```powershell
$env:API_KEY="replace-me"
python -m uvicorn traffic_api.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

完整说明见 [`docs/API_README.md`](docs/API_README.md)。

## 模型与数据

本仓库不包含以下内容：

- 训练/验证数据集与现场采集照片；
- 用户上传的图片、视频和录屏；
- 模型权重与导出文件；
- 训练结果、日志和缓存；
- `.env`、令牌、账号配置和本机绝对路径；
- 比赛提交材料及可能含个人信息的 Office/PDF 文件。

请在本机通过 `YOLO_MODEL_PATH` 指定模型权重，并遵循数据授权、隐私和许可证要求。

## 安全说明

提交前请阅读 [`SECURITY.md`](SECURITY.md)。如果密钥曾进入 Git 历史，仅删除最新文件并不安全，必须立即撤销并轮换密钥，同时清理历史。

## 上游项目与许可证

项目基于 Ultralytics。上游说明保留在 [`README.ultralytics.md`](README.ultralytics.md)，许可证见 [`LICENSE`](LICENSE)。使用、修改或部署前请确认符合对应许可证条款。

