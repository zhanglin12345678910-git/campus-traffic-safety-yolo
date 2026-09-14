# API 概览

基础路径：`/api/v1`。交互式文档：`/docs`。配置 `API_KEY` 后，写接口要求 `X-API-Key`；SSE 使用 `?api_key=`。管理端可在“系统设置”中把密钥保存到当前标签页的 `sessionStorage`，关闭标签页后不会长期保留。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 数据库、Qdrant、两个 YOLO26 模型、LLM、高德和出站代理状态 |
| GET | `/dashboard` | 仪表盘汇总、今日任务数、近 7 日趋势与近期任务 |
| GET | `/analytics/overview` | 真实任务、风险、区域、复核原因、双模型检出和 Agent 耗时分析 |
| GET | `/maps/geocode` | 高德地理编码代理（服务 Key 不下发浏览器） |
| GET | `/maps/static` | 高德静态地图图片代理 |
| GET | `/maps/weather` | 高德实况天气代理，`adcode` 为 6 位行政区划代码 |
| POST | `/inspections` | 多段表单创建任务并上传图片 |
| POST | `/inspections/{id}/execute` | 后台执行工作流 |
| GET | `/inspections` | 分页并按状态/风险/复核筛选 |
| GET | `/inspections/{id}` | 任务、检测、研判、报告和复核详情 |
| GET | `/inspections/{id}/trace` | 节点执行轨迹 |
| GET | `/inspections/{id}/stream` | SSE 实时步骤与完成事件 |
| POST | `/inspections/{id}/review` | 人工确认、修改或驳回 |
| POST | `/inspections/{id}/feedback` | 保存 1–5 分评价和意见 |
| POST | `/video-analytics` | 上传视频并按道路允许方向做 ByteTrack 聚集/逆行分析（同步返回） |
| GET | `/reports/{id}` | 报告 JSON |
| GET | `/reports/{id}/view` | 报告 HTML 页面 |
| POST | `/knowledge/documents` | 上传并入库知识文档 |
| GET | `/knowledge/documents` | 文档列表 |
| DELETE | `/knowledge/documents/{id}` | 删除知识文档（同时清除向量库分块、数据库记录与上传源文件） |
| POST | `/knowledge/search` | 知识检索测试 |

`DELETE /knowledge/documents/{id}` 返回 `{"deleted": true, "id", "name", "removed_chunks", "file_removed"}`；文档不存在返回 404，向量库删除失败返回 503。源文件删除失败不阻断接口，仅在 `file_removed` 中返回 `false`。向量库为 embedded 模式时目录被后端进程独占，**删除必须经由后端接口执行，外部脚本无法改写**。

上传图片允许 JPG/JPEG、PNG、BMP、WebP，默认上限 20 MB，且会执行真实解码校验；视频允许 MP4/AVI/MOV/MKV/WebM，默认上限 100 MB（Nginx `client_max_body_size` 为 110 MB）。错误统一使用 FastAPI 的 `detail` 字段，不返回伪成功。

## 字段补充

- 任务对象（列表、仪表盘、详情）包含 `detection_count` 与 `max_confidence`；没有检测结果时 `max_confidence` 为 `null`，前端显示“—”，不得用默认值代替。
- `/dashboard` 的 `today_tasks` 与 `daily_trend` 按 `APP_TIMEZONE`（默认 `Asia/Shanghai`）划分自然日；`daily_trend` 固定 7 项，每项含 `date`、`total`、`review_required`（当天创建且仍待复核）、`high_risk`。
- `/analytics/overview` 为只读汇总接口；返回累计任务/闭环率/复核率/平均耗时、30 日趋势、风险和状态构成、区域分布、按任务去重的复核原因分类、模型检出贡献、高频类别与 Agent 节点平均耗时。所有值均由当前数据库记录聚合，不生成演示数据。
- `/maps/weather` 在未配置 Key 或供应商失败时仍返回 HTTP 200，内容为 `{"available": false, "message": ...}`，避免顶栏在每个页面制造控制台错误；可用时返回 `available: true` 与 `weather`、`temperature`、`report_time` 等字段，服务端缓存 10 分钟。
- `/health` 的 `general_yolo` 额外给出 `tracking_loaded` 与 `tracking_load_count`：视频跟踪使用独立模型实例，不与图片推理共享（见 `docs/HANDOFF.md` 第 2.1 节）。
