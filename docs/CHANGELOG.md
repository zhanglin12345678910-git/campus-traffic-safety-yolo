# 变更记录

## 2026-07-08

- 新增 `traffic_api` 包，提供配置、图像工具、检测结果序列化、YOLO 结果转换、模型懒加载服务和 FastAPI 入口。
- 新增 `/api/v1/health`、`/api/v1/models/current`、`/api/v1/detect/image`。
- 新增 `requirements_api.txt`、`.env.example`、`scripts/run_api.bat`、`scripts/smoke_api_request.py`。
- 新增 `api_tests/`，覆盖配置、图像工具、序列化、推理核心、模型服务、路由结构和 SF-FastGPT 响应契约。
- 最小修改 `app.py`：桌面端继续保留原入口，但默认模型路径和推理参数优先读取共享 API 配置。
- 新增 API 文档、SF-FastGPT 接入说明和测试报告。
- 调整图片检测响应为更贴近 SF-FastGPT 的扁平契约：`task_id`、`object_count`、`detections`、`result_image_url`、`timing`、`model.weights`。

