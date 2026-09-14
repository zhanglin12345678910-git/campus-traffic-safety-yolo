# 安巡智脑 API 本地运行说明

本次改造新增一个最小 FastAPI 图片检测服务，同时保留原来的 `app.py` 桌面端入口。

当前项目仍使用现有 YOLO11/Ultralytics 权重；后续训练 YOLO26 后，只需要把 `YOLO_MODEL_PATH` 指向新的 `best.pt`，不需要改 API 调用格式。

## 安装 API 依赖

建议在你原本能运行 YOLO 桌面端的 Python 环境里安装：

```powershell
pip install -r requirements_api.txt
```

该环境还需要已有项目依赖，例如 `torch`、`opencv-python`、`ultralytics`。本次新增的 API 依赖只包含 FastAPI 相关包。

## 配置

可以参考 `.env.example`。当前 `scripts/run_api.bat` 不自动加载 `.env` 文件，建议先直接在 PowerShell 中设置：

```powershell
$env:YOLO_MODEL_PATH="<LOCAL_PATH>"
$env:YOLO_DEVICE="0"
$env:YOLO_DEFAULT_IMGSZ="640"
$env:YOLO_DEFAULT_CONF="0.30"
$env:YOLO_DEFAULT_IOU="0.50"
$env:API_KEY="change-me"
```

如果没有设置 `YOLO_MODEL_PATH`，程序会按顺序尝试项目内这些候选权重：

- `runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/weights/best.pt`
- `runs/train/579-pssm-消融/weights/best.pt`
- `runs/train/ASPP-pssm-cctsdb-200e/weights/best.pt`

## 启动

```powershell
scripts\run_api.bat
```

或：

```powershell
python -m uvicorn traffic_api.main:app --host 127.0.0.1 --port 8000
```

如果你的系统里 `python` 指向了错误解释器，可以这样启动：

```powershell
$env:PYTHON_EXE="%USERPROFILE%\.conda\envs\yolo_change\python.exe"
scripts\run_api.bat
```

也可以直接运行：

```powershell
$env:API_KEY="replace-me"
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m uvicorn traffic_api.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

手动图片检测：

```powershell
python scripts\smoke_api_request.py path\to\image.jpg --api-key change-me
```
