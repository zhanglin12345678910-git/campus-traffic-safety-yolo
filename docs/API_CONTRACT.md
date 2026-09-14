# API 接口契约

Base URL: `http://127.0.0.1:8000`

## GET `/api/v1/health`

用途：健康检查和当前模型配置摘要。

示例响应：

```json
{
  "status": "ok",
  "app_name": "安巡智脑",
  "model_path": "runs/train/.../weights/best.pt",
  "model_exists": true,
  "device": "0",
  "load_count": 0
}
```

## GET `/api/v1/models/current`

用途：查看当前模型路径和默认推理参数。

## POST `/api/v1/detect/image`

用途：上传一张图片并返回交通标志检测结果。

请求：

- Header: `X-API-Key: <API_KEY>`，仅当环境变量配置了 `API_KEY` 时需要。
- Body: `multipart/form-data`
- 文件字段名：`file`
- 可选字段：`location`、`description`

示例响应结构：

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
      "box_xyxy": [1.0, 2.0, 30.0, 40.0]
    }
  ],
  "object_count": 1,
  "review_required": false,
  "review_reasons": [],
  "result_image_url": "/outputs/detections/road-xxxx.jpg",
  "timing": {
    "elapsed_ms": 12.34
  },
  "location": "north gate",
  "description": "morning inspection",
  "error": null
}
```

错误响应：

```json
{
  "success": false,
  "message": "Invalid image upload: Failed to decode image bytes",
  "error": {
    "code": "invalid_image"
  }
}
```

