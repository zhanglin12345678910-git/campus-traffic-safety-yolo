# 当前完成进展与后续交接说明

日期：2026-07-10

## 1. 当前项目目标

本项目不是单纯做一个 YOLO 检测脚本，而是要把现有 YOLO11/PyQt5 交通标志识别项目，改造成比赛可用的“安巡智脑”系统。

最终目标是：

```text
用户在 SF-FastGPT / 大赛平台中上传图片
→ 平台调用我们的交通标志识别 API
→ YOLO 模型完成检测
→ API 返回结构化检测结果和结果图
→ 智能体根据结果生成巡检/交通安全相关回答
```

目前模型先使用项目已有 `best.pt`。以后用户会自己训练 YOLO26，只需要替换 `YOLO_MODEL_PATH` 指向新的权重文件。

## 2. 当前已经完成的工作

### 2.1 项目审计与规划

已完成原项目审计，确认：

- 原桌面端入口是 `app.py`
- 桌面端基于 PyQt5
- 当前模型来自项目已有 YOLO/Ultralytics 权重
- 不重新训练模型
- 不推翻原桌面端
- 新增 API 层作为比赛平台调用入口

已生成相关文档：

```text
docs/PROJECT_AUDIT.md
docs/DOCUMENT_CONFLICTS.md
docs/API_MIGRATION_PLAN.md
docs/AI_HANDOFF.md
```

### 2.2 FastAPI 检测服务

已新增 API 包：

```text
traffic_api/
```

主要能力：

- 读取模型路径、设备、阈值等配置
- 自动 fallback 到项目已有 `best.pt`
- OpenCV 解码上传图片
- YOLO 模型懒加载
- 图片推理
- 检测结果结构化
- 结果图保存到 `outputs/detections`
- API Key 鉴权
- FastAPI 路由

主要接口：

```text
GET  /api/v1/health
GET  /api/v1/models/current
POST /api/v1/detect/image
```

### 2.3 SF-FastGPT 友好的返回结构

当前图片检测接口返回字段包括：

```text
success
task_id
image
model
detections
object_count
review_required
review_reasons
result_image_url
timing
location
description
error
```

这套结构更适合智能体读取和组织回答。

### 2.4 桌面端保留

`app.py` 没有被重写。

已做的只是最小兼容改造：

- 模型路径优先读取新配置
- 推理参数优先读取新配置
- 原有 PyQt5 桌面端仍然保留

### 2.5 测试与本地联调

用户当前主要运行环境：

```text
%USERPROFILE%\.conda\envs\yolo_change\python.exe
```

已确认：

```text
Python 3.10.14
fastapi 0.115.14
uvicorn 0.50.2
cv2 4.10.0
torch 2.2.2
ultralytics 8.3.9
CUDA 可用
```

测试结果：

```powershell
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m pytest -q api_tests
```

结果：

```text
34 passed
```

本地 API 已经真实跑通：

```text
http://127.0.0.1:8000
```

健康检查通过：

```text
http://127.0.0.1:8000/api/v1/health
```

真实图片请求返回过 HTTP `200`，并生成了结果图。

## 3. 当前没有完成的部分

目前完成的是“本地 YOLO 检测 API 第一阶段”，不是完整比赛闭环。

尚未完成：

1. 尚未真正接入 SF-FastGPT / 大赛平台
2. 尚未在平台中真实上传图片调用 API
3. 尚未确认平台如何导入工具 JSON
4. 尚未确认所谓 `skill` 的具体格式和导出方式
5. 尚未解决公网访问问题
6. 尚未验证平台能否显示 `result_image_url`
7. 尚未完成最终比赛演示闭环

## 4. SF-FastGPT 平台信息

用户已确认比赛平台地址：

```text
https://fastgpt.sangfor.com.cn/scenarios
```

用户从培训/说明中了解到：

```text
可以直接写代码，然后用某个 skill 导出 JSON
```

当前注意事项：

- 暂时不用额外做独立网页前端
- 优先使用他们提供的 SF-FastGPT 平台
- `skill` 具体是什么、JSON 格式是什么，目前还不清楚
- 后续需要根据平台真实规则生成可导入的 JSON
- 不能假设平台一定支持我们当前的 multipart 文件上传方式，需要实际确认

## 5. 后续工作模式计划

用户计划把后续工作交给：

```text
Hermes Agent
```

预期协作方式：

```text
Hermes Agent 负责统筹任务
→ Hermes 调动 Codex 出方案
→ Claude Code 负责具体写代码
```

建议分工：

### Hermes Agent

负责：

- 读取本交接文档
- 理解最终比赛目标
- 管理阶段任务
- 判断是否需要修改 API
- 统筹 Codex 和 Claude Code
- 根据 SF-FastGPT 平台规则拆解任务

### Codex

负责：

- 读代码和文档
- 出技术方案
- 判断当前 API 是否适合平台
- 设计最小改造方案
- 生成清晰任务说明给 Claude Code
- 审查 Claude Code 改动

### Claude Code

负责：

- 按明确任务写代码
- 生成/修改 JSON、配置文件、脚本
- 补测试
- 跑本地验证
- 不自行推翻架构

## 6. 推荐下一步任务

下一步不要继续盲目写功能，应该围绕 SF-FastGPT 平台规则做适配。

推荐顺序：

### Step 1：确认平台导入方式

进入：

```text
https://fastgpt.sangfor.com.cn/scenarios
```

确认：

- `skill` 是什么
- JSON 格式是什么
- 是否有示例
- 是否支持 OpenAPI 导入
- 是否支持 HTTP 工具
- 是否支持文件上传
- 是否支持请求 Header
- 是否支持返回图片 URL 展示

### Step 2：导出当前 API 的 OpenAPI

当前 FastAPI 本身可以提供：

```text
http://127.0.0.1:8000/openapi.json
```

可保存为：

```text
docs/openapi.json
```

如果平台支持 OpenAPI 导入，可以优先尝试。

### Step 3：生成 SF-FastGPT 工具配置材料

建议生成：

```text
docs/SF_FASTGPT_TOOL_CONFIG.md
```

内容包括：

- 工具名称
- 接口用途
- Method
- URL
- Header
- Body 类型
- 文件字段名
- 可选字段
- 返回字段说明
- 示例请求
- 示例响应

### Step 4：根据平台要求生成 JSON

如果平台要求导入 JSON，则需要新增类似：

```text
docs/sf_fastgpt_skill.json
```

或平台指定格式的 JSON 文件。

注意：JSON 格式必须以后续平台真实示例为准，不要凭空猜。

### Step 5：公网访问或平台可访问地址

当前本地地址：

```text
http://127.0.0.1:8000
```

只能在本机访问。

如果 SF-FastGPT 平台在云端，则需要：

- 服务器部署，或
- 内网穿透，或
- 平台提供的本地调试方案

## 7. 给 Hermes Agent 的提示词

可以直接把下面这段给 Hermes Agent：

```text
你现在接手“安巡智脑”YOLO 交通标志识别比赛项目。

请先不要写代码。

项目路径：
<PROJECT_ROOT>

请先阅读：

1. docs/CURRENT_PROGRESS_AND_HANDOFF.md
2. docs/AI_HANDOFF.md
3. docs/API_MIGRATION_PLAN.md
4. docs/API_CONTRACT.md
5. docs/SF_FASTGPT_INTEGRATION.md
6. docs/TEST_REPORT.md
7. traffic_api/main.py
8. traffic_api/config.py

当前状态：

- 本地 YOLO 检测 API 第一阶段已经完成
- yolo_change 环境测试通过，api_tests 为 34 passed
- 本地 FastAPI 服务能跑
- 图片上传 API 能调用 best.pt 并返回结构化结果
- 桌面端 app.py 保留
- 完整比赛闭环尚未完成

接下来目标：

使用 SF-FastGPT 平台：
https://fastgpt.sangfor.com.cn/scenarios

用户听说平台可以“直接写代码，然后用 skill 导出 JSON”，但还不知道 skill 的具体格式。

请你先完成：

1. 理解当前 API 能力
2. 判断 SF-FastGPT 平台需要什么工具配置
3. 如果需要 Codex 出方案，请先让 Codex 设计方案
4. 如果需要 Claude Code 写代码，请给 Claude Code 明确、最小、可验证的任务
5. 不要训练模型
6. 不要重写 app.py
7. 不要做独立网页前端，优先使用 SF-FastGPT 平台
8. 不要删除用户已有未提交文件

请先总结当前项目状态，并列出下一步计划，等用户确认后再执行。
```

## 8. 给 Claude Code 的任务模板

如果 Hermes 确认需要 Claude Code 写代码，可以用这个模板：

```text
请按以下要求修改项目：

1. 只做本次指定任务，不要重写 app.py。
2. 不要训练模型。
3. 不要修改 ultralytics 源码。
4. 不要删除已有未提交文件。
5. 当前 API 包在 traffic_api/。
6. 当前测试在 api_tests/。
7. 修改前先说明要改哪些文件。
8. 修改后必须运行：
   %USERPROFILE%\.conda\envs\yolo_change\python.exe -m pytest -q api_tests
9. 如果涉及 FastAPI 接口，必须同步更新 docs/API_CONTRACT.md。
10. 如果涉及 SF-FastGPT 工具配置，必须同步更新 docs/SF_FASTGPT_INTEGRATION.md 或新增对应 JSON/Markdown 文档。
```

## 9. 风险提醒

### 9.1 不要把本地 API 完成误认为项目完成

准确状态：

```text
本地后端 API 完成
完整比赛平台闭环未完成
```

### 9.2 不要假设平台一定支持 multipart 文件上传

当前 API 使用：

```text
multipart/form-data
file: 图片文件
```

如果 SF-FastGPT 不支持文件上传，可能需要新增：

```text
POST /api/v1/detect/image-url
```

让平台传图片 URL，API 再下载图片检测。

这个改造要等确认平台规则后再做。

### 9.3 不要假设 `result_image_url` 能直接显示

当前返回：

```text
/outputs/detections/xxx.jpg
```

这是相对 URL。

如果平台在云端，需要公网可访问的完整 URL，例如：

```text
https://your-domain.com/outputs/detections/xxx.jpg
```

### 9.4 不要随便改模型

当前使用项目已有 `best.pt`。

用户以后会自己训练 YOLO26。

现在不要训练、不要换模型结构。

## 10. 当前最重要的结论

当前阶段已经完成：

```text
本地 YOLO 检测 API
```

下一阶段重点是：

```text
SF-FastGPT 平台适配
skill / JSON 导出
公网访问
完整演示闭环
```

