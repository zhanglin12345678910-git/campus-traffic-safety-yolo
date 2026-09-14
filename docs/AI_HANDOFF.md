# AI Handoff: 安巡智脑 YOLO 检测 API 改造交接文档

## 1. 项目背景

当前项目路径：

```text
<PROJECT_ROOT>
```

用户目标不是简单做一个 YOLO 接口，而是把现有 YOLO11/PyQt5 交通标志识别项目，改造成面向比赛的“安巡智脑”系统：

- 保留原有桌面端 `app.py`
- 新增可被大赛工具 / SF-FastGPT 调用的检测 API
- 最终形成完整闭环：

```text
用户上传图片
→ 智能体调用 API
→ YOLO 检测
→ 返回结构化结果和结果图
→ 智能体解释检测结果
```

用户说明：后续会自己训练并替换成 YOLO26，目前先使用项目已有的 `best.pt`。

## 2. 当前分支

已创建并切换到功能分支：

```text
feat/agent-detection-api
```

## 3. 已完成内容

### 3.1 新增 API 包

新增目录：

```text
traffic_api/
```

主要文件：

```text
traffic_api/__init__.py
traffic_api/config.py
traffic_api/main.py
traffic_api/inference_service.py
traffic_api/inference_core.py
traffic_api/serialization.py
traffic_api/image_utils.py
traffic_api/image_quality.py
traffic_api/security.py
traffic_api/storage.py
traffic_api/exceptions.py
```

已经实现：

- FastAPI 服务入口
- `/api/v1/health`
- `/api/v1/models/current`
- `/api/v1/detect/image`
- `X-API-Key` 鉴权
- 图片上传
- OpenCV 图片解码
- YOLO 模型懒加载
- 调用现有 `best.pt`
- 结果图保存到 `outputs/detections`
- SF-FastGPT 友好的扁平 JSON 返回结构

### 3.2 API 返回契约

`POST /api/v1/detect/image` 返回结构包含：

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

其中 `detections` 包含：

```text
class_id
class_name
confidence
box_xyxy
```

### 3.3 新增测试

新增目录：

```text
api_tests/
```

测试覆盖：

- 配置读取
- 模型路径 fallback
- 图像 shape 校验
- 序列化
- SF-FastGPT 响应契约
- YOLO fake 结果转换
- 模型懒加载服务
- FastAPI 路由

### 3.4 修改桌面端

修改文件：

```text
app.py
```

只做了最小兼容改造：

- 桌面端入口仍保留
- UI 和主流程未重写
- 模型路径和推理参数优先从 `traffic_api.config.get_settings()` 读取
- 没有推翻原 PyQt5 桌面端

### 3.5 新增脚本

```text
scripts/run_api.bat
scripts/smoke_api_request.py
```

`scripts/run_api.bat` 支持通过 `PYTHON_EXE` 指定解释器：

```powershell
$env:PYTHON_EXE="%USERPROFILE%\.conda\envs\yolo_change\python.exe"
scripts\run_api.bat
```

### 3.6 新增/更新依赖

新增文件：

```text
requirements_api.txt
```

当前内容：

```text
fastapi>=0.115,<0.116
uvicorn[standard]>=0.30,<1
python-multipart>=0.0.9
httpx>=0.27,<0.29
pydantic>=2,<3
requests>=2.28.2,<2.29
```

说明：

- 曾尝试安装最新版 FastAPI，发现 2026 年新版 Starlette 需要 `httpx2`，并会引入与现有环境冲突的 `idna` 版本。
- 后来将 FastAPI 锁定在 `0.115.x`，与 `yolo_change` 环境更稳定。
- `requests` 限制为 `<2.29`，避免和 `openxlab` 要求冲突。

### 3.7 更新 `.gitignore`

新增忽略：

```text
outputs/
```

避免 API 运行后生成的结果图进入 Git 变更。

## 4. 已生成文档

审计/计划类：

```text
docs/PROJECT_AUDIT.md
docs/DOCUMENT_CONFLICTS.md
docs/API_MIGRATION_PLAN.md
docs/superpowers/plans/2026-07-08-agent-detection-api.md
```

API/接入类：

```text
docs/API_README.md
docs/API_CONTRACT.md
docs/SF_FASTGPT_INTEGRATION.md
docs/TEST_REPORT.md
docs/CHANGELOG.md
```

当前交接文档：

```text
docs/AI_HANDOFF.md
```

## 5. `yolo_change` 环境验证情况

用户指定环境：

```text
%USERPROFILE%\.conda\envs\yolo_change\python.exe
```

已确认：

```text
Python 3.10.14
fastapi 0.115.14
starlette 0.46.2
httpx 0.28.1
uvicorn 0.50.2
cv2 4.10.0
torch 2.2.2
ultralytics 8.3.9
CUDA 可用，识别到 1 张 GPU
```

默认模型路径已自动找到：

```text
runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/weights/best.pt
```

## 6. 测试结果

在 `yolo_change` 环境中执行：

```powershell
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m pytest -q api_tests
```

结果：

```text
34 passed
```

## 7. 真实 API 联调结果

启动 API：

```powershell
$env:API_KEY="dev-secret"
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m uvicorn traffic_api.main:app --host 127.0.0.1 --port 8000
```

健康检查已通过：

```text
GET http://127.0.0.1:8000/api/v1/health
```

真实图片请求已通过：

```powershell
%USERPROFILE%\.conda\envs\yolo_change\python.exe scripts\smoke_api_request.py results\result_3483169a-8c6f-40e8-bd18-e13c946ce59b_1766858993.jpg --api-key dev-secret
```

结果：

- HTTP `200`
- 返回 SF-FastGPT 契约字段
- 生成结果图

示例结果图 URL：

```text
/outputs/detections/result_3483169a-8c6f-40e8-bd18-e13c946ce59b_1766858993-052026700245.jpg
```

说明：测试图片返回 `object_count: 0`，但 API 链路已验证通过，包括上传、解码、模型加载、推理、返回 JSON、保存结果图。

## 8. 当前 API 使用方式

本地启动：

```powershell
$env:API_KEY="dev-secret"
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m uvicorn traffic_api.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/v1/health
```

图片检测接口：

```text
POST http://127.0.0.1:8000/api/v1/detect/image
```

Header：

```text
X-API-Key: replace-me
```

Body：

```text
multipart/form-data
file: 图片文件
location: 可选
description: 可选
```

## 9. 用户对话重点

用户最开始要求：

- 先不要写代码
- 先读 `agent` 文档和聊天文档
- 审计现有项目
- 不要推翻桌面端
- 不要重新训练模型

用户说明：

```text
模型以后会换成 YOLO26，我会自己训练；现在先用现有 best.pt。
```

用户后来确认：

- 最终前端主要应该在大赛提供的工具 / SF-FastGPT 里配置
- 本项目主要负责 YOLO 检测 API
- 单独网页前端不是当前第一优先级
- 桌面端保留用于本地演示和调试

用户指出：

```text
不是这么快就结束吧？最终功能不是很复杂吗？
```

因此需要明确：当前不是整个比赛项目完成，只是后端检测 API 第一阶段完成并本地联调通过。

## 10. 还没完成的工作

下一阶段要做的是完整比赛闭环：

```text
大赛平台 / SF-FastGPT
→ 上传图片
→ 调用公网 API
→ YOLO 检测
→ 返回检测结果和结果图
→ 智能体解释结果
```

具体待办：

1. 大赛工具 / SF-FastGPT 真实接入
2. 解决公网访问问题
   - `127.0.0.1:8000` 只能本机访问
   - 大赛平台若在云端，需要服务器部署或内网穿透
3. 在 SF-FastGPT 中配置工具
   - Method: `POST`
   - URL: `http://公网地址/api/v1/detect/image`
   - Header: `X-API-Key: replace-me
   - Body: `multipart/form-data`
   - 文件字段名：`file`
   - 可选字段：`location`、`description`
4. 用大赛平台真实上传图片调用 API
5. 让智能体根据返回字段组织自然语言回答
6. 验证大赛平台是否支持：
   - multipart 文件上传
   - Header 鉴权
   - 展示 `result_image_url`
7. 如果平台需要公网图片 URL，要让 `/outputs/detections/...` 也能公网访问
8. 最后做完整演示闭环

## 11. 注意事项

### 11.1 不要误判“已经全部完成”

当前准确状态：

```text
后端检测 API 第一阶段已完成，并在 yolo_change 环境本地联调通过。
完整比赛闭环尚未完成。
```

### 11.2 不要随便回滚用户已有改动

当前 Git 状态中存在一些不是本次 API 改造产生的变更/未跟踪文件，例如：

```text
M claude-修改/generate_dataset.py
?? .git_commit_msg.txt
?? .ultralytics_tmp/
?? agent/
?? detect copy.py
```

这些不要误删、不要回滚。

### 11.3 API 进程可能仍在运行

之前曾启动过本地 API 到：

```text
http://127.0.0.1:8000
```

如果端口被占用，先检查已有 `uvicorn` / Python 进程，或换端口启动。

### 11.4 pip 镜像问题

用户环境的 pip 全局源是清华镜像，之前安装 FastAPI 时遇到过 403。

成功安装时使用了官方 PyPI：

```powershell
%USERPROFILE%\.conda\envs\yolo_change\python.exe -m pip install -r requirements_api.txt --index-url https://pypi.org/simple --trusted-host pypi.org --trusted-host files.pythonhosted.org
```

### 11.5 pip check 残留提示

`pip check` 曾提示：

```text
openxlab 0.1.2 has requirement pytz~=2023.3, but you have pytz 2025.2.
```

该问题不是本次 API 依赖引起，当前 API 测试和运行不受影响。

## 12. 一句话总结

当前项目已经完成“本地 YOLO 检测 API 第一阶段”，并在 `yolo_change` 环境真实跑通；下一步应继续做“大赛工具 / SF-FastGPT 平台接入、公网访问、完整智能体工作流联调”。

