# SF-FastGPT 工具接入参考（培训前材料）

> 本文档整理当前 API 的通用接入信息，供培训时对照平台要求使用。
> 具体配置方式以培训时确认的平台实际能力为准。

## 1. 接口总览

| 项目 | 值 |
|------|------|
| 接口名称 | 交通标志检测 |
| 用途 | 上传一张图片，返回交通标志检测结果和标注结果图 |
| Method | `POST` |
| Content-Type | `multipart/form-data` |
| 本地 URL | `http://127.0.0.1:8000/api/v1/detect/image` |
| 公网 URL | 待培训后确定（需内网穿透或服务器部署） |
| 鉴权方式 | Header `X-API-Key`（值由环境变量 `API_KEY` 配置） |

## 2. 请求参数

### 2.1 Header

| Header | 必填 | 说明 |
|--------|------|------|
| `X-API-Key` | 视配置而定 | 如果服务端启动时设置了 `API_KEY` 环境变量，则必填；否则不需要 |

### 2.2 Body（multipart/form-data）

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `file` | 文件 | ✅ 是 | 图片文件，支持 jpg/jpeg/png/bmp/webp |
| `location` | 文本 | ❌ 否 | 拍摄地点描述，如"北门入口" |
| `description` | 文本 | ❌ 否 | 备注信息，如"早班巡检" |

## 3. 返回字段说明

成功响应（HTTP 200）：

```json
{
  "success": true,
  "task_id": "f1f6b68fd9f94420a39c67c58c9a3f2a",
  "image": {
    "filename": "road.jpg",
    "width": 640,
    "height": 480,
    "channels": 3
  },
  "model": {
    "weights": "best.pt",
    "device": "0",
    "img_size": 640,
    "conf_threshold": 0.3,
    "iou_threshold": 0.5
  },
  "detections": [
    {
      "class_id": 1,
      "class_name": "stop",
      "confidence": 0.94,
      "box_xyxy": [100.0, 200.0, 300.0, 400.0]
    }
  ],
  "object_count": 1,
  "review_required": false,
  "review_reasons": [],
  "result_image_url": "/outputs/detections/road-a1b2c3d4.jpg",
  "timing": {
    "elapsed_ms": 45.67
  },
  "location": "北门入口",
  "description": "早班巡检",
  "error": null
}
```

### 3.1 字段详解

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | bool | 是否检测成功 |
| `task_id` | string | 本次请求的唯一 ID（UUID hex） |
| `image.filename` | string | 原始上传文件名 |
| `image.width` | int | 图片宽度（像素） |
| `image.height` | int | 图片高度（像素） |
| `image.channels` | int | 图片通道数（通常为 3） |
| `model.weights` | string | 模型权重文件名（仅文件名，不含路径） |
| `model.device` | string | 推理设备（"0"=GPU，"cpu"=CPU） |
| `model.img_size` | int | 推理输入尺寸 |
| `model.conf_threshold` | float | 置信度阈值 |
| `model.iou_threshold` | float | IoU 阈值 |
| `detections` | array | 检测到的目标列表 |
| `detections[].class_id` | int | 类别 ID |
| `detections[].class_name` | string | 类别名称（如 stop, speed_limit_30 等） |
| `detections[].confidence` | float | 置信度（0~1） |
| `detections[].box_xyxy` | array[4] | 边界框坐标 [x1, y1, x2, y2] |
| `object_count` | int | 检测到的目标总数 |
| `review_required` | bool | 是否需要人工复核（图片质量差或无检测结果时为 true） |
| `review_reasons` | array[string] | 需要复核的原因列表 |
| `result_image_url` | string | 标注结果图的相对 URL（需拼接服务器地址） |
| `timing.elapsed_ms` | float | 推理耗时（毫秒） |
| `location` | string | 用户传入的拍摄地点（原样返回） |
| `description` | string | 用户传入的备注（原样返回） |
| `error` | object/null | 错误信息（成功时为 null） |

### 3.2 错误响应

所有错误均返回 JSON，格式统一：

```json
{
  "success": false,
  "message": "具体错误描述",
  "error": {
    "code": "错误代码"
  }
}
```

常见错误代码：

| HTTP 状态码 | error.code | 含义 |
|-------------|------------|------|
| 400 | `invalid_image` | 图片无效（解码失败、格式不对、尺寸太小等） |
| 401 | `invalid_api_key` | API Key 错误或缺失 |
| 413 | `payload_too_large` | 文件超过大小限制 |
| 500 | `model_not_configured` | 模型路径未配置或文件不存在 |
| 500 | `model_load_failed` | 模型加载失败 |
| 500 | `prediction_failed` | 推理过程出错 |

## 4. 示例 curl 命令

### 4.1 健康检查（无需鉴权）

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 4.2 图片检测

```bash
curl -X POST http://127.0.0.1:8000/api/v1/detect/image \
  -H "X-API-Key: replace-me" \
  -F "file=@/path/to/traffic_sign.jpg" \
  -F "location=北门入口" \
  -F "description=早班巡检"
```

### 4.3 最简请求（仅上传文件）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/detect/image \
  -H "X-API-Key: replace-me" \
  -F "file=@test.jpg"
```

## 5. 结果图访问

API 返回的 `result_image_url` 是相对路径，例如：

```
/outputs/detections/road-a1b2c3d4.jpg
```

拼接服务器地址后可直接访问：

```
http://127.0.0.1:8000/outputs/detections/road-a1b2c3d4.jpg
```

> ⚠️ 公网场景下，需要确保该 URL 可被大赛平台访问到。

## 6. 本地启动方式

```powershell
# 设置 API Key
$env:API_KEY="dev-secret"

# 启动服务
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m uvicorn traffic_api.main:app --host 127.0.0.1 --port 8000
```

启动后可访问：
- Swagger 文档：http://127.0.0.1:8000/docs
- ReDoc 文档：http://127.0.0.1:8000/redoc
- OpenAPI JSON：http://127.0.0.1:8000/openapi.json

## 7. 智能体可读取的关键字段

如果平台智能体需要根据检测结果组织自然语言回答，建议重点读取：

| 字段 | 用途 |
|------|------|
| `success` | 判断检测是否成功 |
| `object_count` | 告诉用户检测到几个目标 |
| `detections[].class_name` | 告诉用户检测到了什么类型的标志 |
| `detections[].confidence` | 告诉用户检测的置信度 |
| `result_image_url` | 展示标注后的结果图 |
| `review_required` | 提示用户是否需要人工复核 |
| `timing.elapsed_ms` | 告诉用户检测耗时 |
| `location` | 在回答中引用拍摄地点 |

## 8. OpenAPI 规范文件

已导出完整的 OpenAPI 3.1 规范文件：

```
docs/openapi.json
```

可用于：
- 导入 Postman 测试
- 平台导入 API 定义（如果平台支持 OpenAPI 导入）
- 自动生成接口文档
