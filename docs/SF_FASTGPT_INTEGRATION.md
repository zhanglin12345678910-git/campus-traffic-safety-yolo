# SF-FastGPT 工具接入说明

建议把本服务作为 HTTP 工具接入 SF-FastGPT。

## 工具配置

- Method: `POST`
- URL: `http://<你的服务器地址>:8000/api/v1/detect/image`
- Headers:
  - `X-API-Key: <你的 API_KEY>`
- Body 类型：`multipart/form-data`
- 文件字段名：`file`
- 可选文本字段：`location`、`description`

## 返回字段建议

SF-FastGPT 可以重点读取：

- `success`
- `task_id`
- `object_count`
- `detections`
- `result_image_url`
- `timing.elapsed_ms`
- `location`
- `description`

## 备注

当前 API 只做图片检测。视频、摄像头、风险评分、报告生成、数据库记录等能力没有纳入第一阶段，避免影响桌面端稳定性。

未来替换 YOLO26 时，保持接口不变，只更新：

```powershell
$env:YOLO_MODEL_PATH="<LOCAL_PATH>"
```

