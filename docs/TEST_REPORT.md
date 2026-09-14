# 测试报告

日期：2026-07-08

## 已执行

```powershell
<LOCAL_PATH> -m pytest -q api_tests
```

结果：

基础 Anaconda 环境结果：

```text
31 passed, 3 skipped in 0.10s
```

跳过原因：基础 Anaconda 环境未安装 `fastapi`，路由集成测试按预期跳过。

`yolo_change` 环境结果：

```powershell
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m pytest -q api_tests
```

```text
34 passed in 10.54s
```

静态编译：

```powershell
<LOCAL_PATH> -m py_compile app.py
<LOCAL_PATH> -m py_compile traffic_api\__init__.py traffic_api\config.py traffic_api\exceptions.py traffic_api\image_utils.py traffic_api\serialization.py
<LOCAL_PATH> -m py_compile traffic_api\inference_core.py traffic_api\inference_service.py traffic_api\security.py traffic_api\storage.py traffic_api\image_quality.py traffic_api\main.py
<LOCAL_PATH> -c "import py_compile; py_compile.compile(r'scripts\smoke_api_request.py', doraise=True); print('ok')"
```

结果：通过，无语法错误。

## 环境限制

当前被检测的 Anaconda 环境缺少：

- `fastapi`
- `uvicorn`
- `cv2`
- `torch`

因此本轮验证了不依赖重型运行库的配置、序列化、图像 shape 校验、YOLO 结果转换、模型懒加载逻辑、SF-FastGPT 响应契约和静态语法。真实 API 服务需要在安装上述依赖或切换到已有 YOLO 环境后运行。

## `yolo_change` 联调记录

已确认：

- Python: `3.10.14`
- `fastapi`: `0.115.14`
- `starlette`: `0.46.2`
- `httpx`: `0.28.1`
- `uvicorn`: `0.50.2`
- `opencv-python`: `4.10.0`
- `torch`: `2.2.2`
- CUDA: 可用，识别到 1 张 GPU
- `ultralytics`: `8.3.9`
- 默认模型路径存在：`runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/weights/best.pt`

API 启动：

```powershell
$env:API_KEY="dev-secret"
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m uvicorn traffic_api.main:app --host 127.0.0.1 --port 8000
```

健康检查通过：

```text
GET http://127.0.0.1:8000/api/v1/health
```

真实图片请求通过：

```powershell
%USERPROFILE%\.conda\envs\yolo_change\python.exe scripts\smoke_api_request.py results\result_3483169a-8c6f-40e8-bd18-e13c946ce59b_1766858993.jpg --api-key dev-secret
```

结果：HTTP `200`，返回 SF-FastGPT 契约字段，生成结果图 URL：`/outputs/detections/result_3483169a-8c6f-40e8-bd18-e13c946ce59b_1766858993-052026700245.jpg`。

备注：`pip check` 仍提示 `openxlab 0.1.2` 要求 `pytz~=2023.3`，当前环境为 `pytz 2025.2`。这不是本次 API 依赖造成的，当前 API 测试和启动联调不受影响。
