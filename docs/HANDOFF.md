# 安巡智脑交接文档（滚动交接，最新一轮在最上面）

## 最新一轮：Codex → 接手方（2026-09-14 · 负责人显示清理）

- 用户最终要求这批负责人统一显示“张林”，不能出现“Claude”或“Claude 代上传”。正式 SQLite 库实查13条任务，其中目标记录6条，其余为系统验收3、安保值班员2、空值2。
- 仅在单事务中把这6条目标记录的 `inspection_tasks.inspector_name` 精确更新为“张林”；未改系统验收、安保值班员或空值，未改前后端源码、知识、媒体、模型或训练。
- 数据库复查：updated=6、两种旧名称均剩余0、张林=6；运行中8000接口复查total=13、张林=6、Claude前缀=0，立即生效，前端刷新页面即可看到。

## 最新一轮：Codex → 接手方（2026-09-14 13:36 · 阿里云小内存 CPU 部署包）

- 用户要求打包供阿里云轻量服务器部署，补充Alibaba Cloud Linux 3 / 2核 / 1.8 GiB / v4.9.4-rhel inactive。该版本疑似Podman兼容Docker命令，尚无服务器真实输出；先查docker-ce/podman-docker/Compose/docker.service，不盲目卸载或声称start就行。官方说明见deploy/README.md。
- 用户手动打开本地Docker Desktop，截图Engine running且已有campus-safety组；当前Codex CLI连npipe dockerDesktopLinuxEngine仍permission denied，config.json也拒绝读取。不是Desktop未安装/未起，而是会话访问限制；不绕过ACL、不动已有容器，没有真正执行镜像构建/容器验收，阿里云未连接。
- 新增独立docker-compose.cloud.yml：Nginx + CPU后端，SQLite/嵌入式Qdrant，固定Linuxamd64，强制cpu/清空Windows代理/两线程，视频640px/5fps参数保留功能但需重新实测。前端Dockerfile.cloud直接复制本机dist，不在1.8 GiB服务器编译Vue；原MySQL四容器Compose/验收脚本保留。
- 新增deploy/cloud.env.example/nginx.cloud.conf/cloud-preflight.sh/cloud-deploy.sh/cloud-verify.sh及操作README；只公开80，NginxBasic认证保护所有页面/读写API/媒体/报告，最简/health例外。三provider密钥+至少12字符演示密码只在服务器.env.cloud；HTTP非加密，长期/个人信息需HTTPS。低于3GB要求至少约2GBswap和10GB空闲盘，仅资源门槛非运行保证。
- 新增app.cloud_admin：云端运行guard，生成SHA512密码哈希，五保留来源幂等seed（遇意外/重复/错误来源停止不删），SQLitehead/schema与网关匿名401检查；verify实际CPU图片/DeepSeek llm/HTML/媒体/双loaded/脚本确认持久化。只在新云库产生标记TT100K验收任务，不是真实现场人工判断；此夹具不能认证Qwen/高德/CPU视频。
- 新增package-cloud-release.py从当前有效未提交源码打包（不能git archive丢改动），含真实两个pt+dist+五知识，不含.env/数据库/上传输出/原校园照片/训练。首次初版误带Vite复制的未引用public/campus原图，未发布；追加排除规则和2测试，原文件未删除。**只用campus-safety-cloud-20260914-r1.zip，未带r1初版不要上传。** 本地13任务不会随新库迁移，迁移历史需另行授权/一致性备份。
- 最终交付C:\Users\project_user\Desktop\codex-workspace\campus-safety-cloud-20260914-r1.zip：140文件、163081090字节、SHA256 f2413f1c82335bc371db279a1ad81ad8e58001db1654db5a06313fe74a67e09e；CRC/140文件哈希与已配置密钥文本扫描通过；壳脚本LF、精确2权重/5来源、无示例/运行态/原图路径复核。附RELEASE_MANIFEST明确runtime_verified=false。
- 最终后端99 passed/46.14s（本轮12新增），前端vue-tsc+Vite通过/Vite43.34s，云Compose --no-env-resolution --quiet结构通过、四shell bash -n通过。不是容器运行通过；Qwen/高德、服务器双模型峰值内存、CPU视频/公网浏览器尚未实测。本地UI/.env/GPU/生产库/训练32/80未改，未安装插件、删除文件或停止任何已有容器。TEST_REPORT §33及日记/长期约定同步。

## 最新一轮：Codex → 接手方（2026-09-14 13:03 · 比赛 Demo 全流程测试）

- 用户最新定位：不再改UI，本地GPU版小Demo给评委看，完整测试现有功能，排除企业级安全审计、并发/压力及公网部署；只保障基础输入与密钥卫生。本轮只新增测试脚本/3项测试及记录，没有修改业务/UI源码，训练32/80不恢复。
- 真正重新执行：后端最终87 passed/31.92s（原84+新增空图/超限图/空视频3项）、vue-tsc+Vite通过/31.00s、现有浏览器11/11 UTC04:52:14.996Z、新增页面/交互20/20 UTC04:55:20.326Z，零错误。
- scripts/local_functional_acceptance.py隔离真实网页闭环6/6：空SQLite迁移0002、多知识70块、必填/上传、GPU双YOLO13目标12人、RAG/DeepSeek实际llm、HTML报告、复核入口/确认持久化、反馈5、档案统计一致及负例/空队列。脚本临时8002/5176已退出。
- Qwen实际隔离回归10/10 UTC04:51:53.773764Z：无person图真实白名单证据、真实并入DeepSeek和仅证据角色；12person图零新增视觉调用。本轮无10013，不以配置或输出合规当准确率/长期可达保证。证据outputs/demo-vlm-20260914.json。
- 视频先精简Chromium有音轨无画面（0×0），最初预览断言不足；同文件正式Chrome2160×3840实际播放成功，对照1/2保留。新增demo_video_acceptance.py补画面/播放断言，正式Chrome完整隔离4/4 UTC04:59:39.939328Z：GPU ByteTrack、46/271帧、540×960、最大12人/27轨迹、81.05s分析/92.56s网页等待，结果视频实际播放/OpenCV解码。7反向轨迹是移动镜头+配置测试，不是真实逆行；临时8003/5177已退出。
- 新增demo_readiness_checks.py正式只读最终6/6：高德真实天气/学校坐标/1024×640底图、已配置密钥不在32前端产物/公开JSON/真实.env索引、生产任务知识前后指纹一致（13任务、5份70块ready）。API_KEY写/SSE契约在后端套件验证；不做渗透/历史Git全扫描。
- 新增超限pytest最初bytes参数导致用例ID/Windows临时目录过长而setup错误（86 passed/2 errors），改整数size+短ids重跑87通过，是测试代码问题不是业务修复。主证据docs/DEMO_TEST_REPORT_2026-09-14.md、TEST_REPORT §32、outputs/demo-functional-20260914/、demo-video-20260914/、demo-checks前后、frontend/output/playwright/demo-video-preview/。隔离URL随回收失效，演示须从原素材重新上传。
- 准出为本地比赛Demo现有功能通过，可彩排；正式Chrome+已验证素材，4K视频留1–2分钟，公开素材先授权/脱敏。不是所有素材/设备兼容或Docker公网完成。8000/PID23712、5173/PID24216继续监听；本轮未重启/写正式任务/知识/改密钥或安装插件。

## 最新一轮：Codex → 接手方（2026-09-14 12:26 · 最终 UI 可读性收口）

- 用户授权自行选择最终UI优化，不扩大后端/模型/部署范围。先按Product Design audit截图审查八页，再用已有Node Playwright验收；没有安装插件或模板。保留v7灰黑/字体链/官方校徽/GIS/七图，内容自然结束留白不造数填充。
- 本轮仅页面KnowledgePage/InspectionDetailPage、全局styles、DESIGN、新增只读ui_polish_acceptance.cjs及记录。知识原生文件输入加中文label/真实文件名、18px图标、Enter/Space/aria-pressed，ready才绿勾；详情风险摘要14px/400正文、知识原生details全文/键盘展开、现有轨迹图标与12px文件/元数据/坐标。常规桌面复核原因分行，服务卡四列/1900以上七列/中屏三列/手机两列，状态说明不省略。
- 目视发现手机设置长模型名挤成逐字竖排：设置/知识摘要改标签/数值/说明三行，补标签≥80px、最多两行和数值未裁切断言。前一次引用全文innerText比较因空白折叠失败，原始textContent与API一致，改原始全文断言；首次19/20报告保留。一次执行器路径缺少win64段导致启动失败，纠正到已有浏览器后重跑。
- 最终：84 pytest/28.45s；vue-tsc+Vite通过/31.67s；既有浏览器11/11 UTC04:23:05.178Z；新增20/20 UTC04:22:15.490Z，零页面/控制台/请求/HTTP错误。八页桌面1440/手机390及设置2560，最终截图目视确认；完整逐页报告docs/UI_POLISH_AUDIT_2026-09-14.md、TEST_REPORT §31。before/after截图和新增报告在frontend/output/playwright/ui-polish/。
- 8000/PID23712与5173/PID24216监听，health=ok，线上5份70块ready。未重启服务、写生产数据/知识、改密钥或恢复32/80训练；未再次付费跑Qwen/媒体，不以“已配置”声称联网成功。本轮UI准出，不宣称Docker/公网或全项目所有测试已完成。

## 最新一轮：Codex → 接手方（2026-09-14 11:48 · 完整校名与知识/详情连续布局）

- 用户新增范围：侧栏完整校名、知识库短卡下方空洞、详情轨迹下方空档/整改建议太小。AppLayout品牌副标题改用campusProfile.name完整“四川现代职业学院”，不改学校坐标或后端数据。
- KnowledgePage将原全宽knowledge-pipeline拆入三列knowledge-column：来源/流水线、元数据/索引状态、检索/资料说明，各列自身12px间距独立排布。删除本轮废弃pipeline/跨行CSS，保留原真实上传、键盘文档选择与检索接口。空库索引提示不再显示“全部文档可检索”。
- InspectionDetailPage新增detail-action-stack，整改建议紧跟轨迹卡，正文14px/1900px以上16px、逐条面板、真实数组/空态；检测表310→590px可见上限，仍保留全部检测行/内部滚动。视觉卡恢复内边距。目视发现手机按钮被裁切，修为flex-wrap并去掉叠加按钮margin，补实际按钮边界断言。
- 测试：84 pytest passed/29.27s；最终构建通过/Vite38.78s；最终浏览器11/11、UTC2026-09-14T03:47:57.502Z，零页面/控制台/请求/HTTP错误。新增独立列间距≤16px、完整校名、真实检索/切文档、建议16px/内容与后端一致、手机按钮不裁切检查。最终空/命中知识、详情桌面/手机截图已目视检查，TEST_REPORT §30。
- 本轮未改后端/密钥/生产任务/知识/训练，不重跑有费用VLM或媒体链路；生产知识仍5份70块ready。8000已换PID23712（上一轮38816已不监听），本轮未重启；仅据PID变化记录用户已更换进程，不据健康配置声称再次真实Qwen联网验证。5173/PID24216运行正常。自然内容结束仍允许留白，不造数填满画布。

## 最新一轮：Codex → 接手方（2026-09-14 11:17 · Qwen Fake-IP 联网修复）

- 唯一范围为Qwen实际联网，不改UI/训练/生产数据/密钥/系统VPN或ACL。更正§26–28的根因判断：10013本身不足以证明沙箱限制；本轮DNS实测dashscope.aliyuncs.com=198.18.4.38。旧llm.py将非DeepSeek VLM强制proxy=None，导致直连Fake-IP失败；通过现有127.0.0.1:7890代理匿名请求百炼/models真实401，证明链路可达。
- 最小修复：Settings新增 `vision_llm_use_outbound_proxy=True`；VLM默认继承既有outbound_http_proxy（空值即直连，false显式直连），trust_env=False避免隐式环境路由。提供方思维开关/模型/密钥/证据白名单/person闸门/风险策略不变，TLS验证开启。README/DEPLOYMENT/.env.example已同步。
- 实测：新增4路由边界测试，全量pytest84 passed/28.95s；前端构建通过/Vite26.41s。隔离真实回归 `outputs/vlm-proxy-fix-20260914.json` **10/10通过**（UTC2026-09-14T03:14:55.489078）：Qwen真实白名单证据、DeepSeek payload并入一致/角色声明通过；人物12/视觉零新增调用通过。不把模型合规输出当准确率真值。
- 尚需用户动作：生产8000仍旧PID38816/python，任务1completed/11review、无执行中；经netstat与health确认后Stop-Process明确拒绝访问。未绕过权限，未停止任何其他进程。请用户在原终端Ctrl+C，再从项目根 `& .\scripts\start-backend.ps1`。修复代码与隔离真实调用已验证，但当前8000旧进程尚未加载。后续只核验重启与必要隔离调用，不向生产库上传测试文档。详见TEST_REPORT §29。

## 最新一轮：Codex → 接手方（2026-09-14 07:52 · 前端运行恢复与复验）

- 发现8000仍监听（PID38816），但5173/5174未监听。仅通过现有 `scripts/start-frontend.ps1 -BackendPort 8000 -Port 5173` 恢复前端，当前会话86745、监听PID24216；后端未重启，5174未重复启动。请使用 http://127.0.0.1:5173/reviews 。这是本地开发会话，不保证关闭会话后仍常驻。
- 页面与代理健康接口200，双YOLO均loaded；生产知识5份70块ready。只读浏览器复验10/10，UTC证据时间2026-09-13T23:51:53.955Z，零页面/控制台/请求/HTTP错误；最新复核截图已目视检查。CLI离线缓存缺失，复用已有Node Playwright脚本，无插件安装。
- 本增量没有改业务代码/生产数据/模型或密钥；后端80 passed、构建、隔离GPU闭环6/6与视频等结果仍引用上一轮§27，不伪称本次全部重跑。Qwen联网失败仍未闭环，云部署继续延后。详见TEST_REPORT §28。

## 最新一轮：Codex → 接手方（2026-09-14 · 官方校徽、可读性与本地完整回归）

- 最新优先级：先本地 GPU 完整版，阿里云轻量 CPU 公网版延后；训练32/80不恢复。额度不足不能执行定时任务用户已接受；本轮仍无定时管理工具，未注册任务。
- 官方标识：官网首页引用的 `Content/NewIndex2/images/logo.png` 下载为 `frontend/src/assets/scmvc-official-logo.png`，原图保留、CSS显示左端校徽；侧栏48×46px、顶栏38×36px，不改色、不宣称学校授权。来源见assets/SOURCES.md。
- UI：校训10px→13–16px、建筑94px容器/亮度提升，保持灰黑令牌与字体链；复核标题15–18px、原因/元数据12px、按钮≥40px，编号/区域/时间拆层，只格式化后端墙钟时间不擅自转换时区。增加真实风险徽章/原图缩略图，缺失原因明确提示；设置/说明栏若干小号正文提升12px，知识检索不再误称语义检索。
- 实测：后端80 passed /27.79s，最终构建通过（Vite40.80s），浏览器10/10（字体尺寸/校徽解码/键盘入口/折叠/七图/多屏/无页面或请求错误）；最终截图已目视检查，见TEST_REPORT §27。
- `scripts/local_functional_acceptance.py` 新增：空白隔离SQLite迁移到0002_multimodel_vision、5份70块隔离知识、真实浏览器校验/上传/GPU双模型/DeepSeek/报告/人工确认/反馈/档案/统计/负例，6/6通过。nvidia-smi观察到测试进程，13目标12人、analysis_mode=llm；测试8002/5176已退出，无生产写入或服务重启。
- Python浏览器依赖原来缺失，仅在Desktop/codex-workspace/campus-test-deps安装playwright1.58.0，通过PYTHONPATH引用，不改变业务conda依赖，使用已有Chromium；CLI因Bash权限/缓存不可用，视觉测试复用现有Node Playwright，未安装插件。
- 视频隔离复跑：271→46帧、540×960、55,067.97ms，12人峰值/27人员轨迹，接口成功；7条反向轨迹仅配置测试不是逆行真值，VP80警告仍在。
- 地图真实只读探针：天气200/available=true，学校地理编码200，GCJ-02中心103.997424,30.515862；线上知识仍5份70块ready。
- Qwen独立回归仍7/10，3条视觉证据/并入/角色断言失败，人物闸门正确。新直接探针明确WinError10013套接字拒绝，不将configured或UI展示当联网成功。不报全部功能全过/可公网发布；Docker/服务器延后，未改VPN/ACL/密钥。

## 最新一轮：Codex → 接手方（2026-09-14 03:15 · 宽屏布局与交付验收）

当前有效增量，以下历史不代表本轮测试结果。用户授权继续实现：续工作监控、五页留白、qwen 展示、Docker、公网部署准备、新照片/视频与现有功能测试。

- UI：知识库取消三列等高/530px 空卡片；搜索结果独立滚动。Dashboard 去掉地图 620px 宽屏高度上限，使地图/下方任务表利用现有视口；不添加假点位。新建和设置复用 `ModelEvidencePanel.vue`，真实展示 /health 的 VLM、DeepSeek 与服务端策略职责。设置页把该面板放在左/中卡片下，不再等右栏结束。档案加入当前获取记录的本地 10 条分页与真实近期任务耗时柱状图；未实现后端全库分页，统计仍以列表接口当前获取范围为准。字体、灰黑色系与原强调色不改。
- 运行态：原 5173 连的是旧后端（无 vision_llm、知识库 63 块），5174 连当前 8000（有 qwen、70 块）。已确认 9700 为 node 并替换其 Vite 服务，使用 `scripts/start-frontend.ps1 -BackendPort 8000 -Port 5173`；当前本轮启动会话 11796，不应当作服务器常驻部署。8000 后端未重启，生产任务/知识库未写入。
- 验证：pytest 80 passed / 28.11s；前端最终构建通过（曾修复耗时图必填ariaLabel类型错误）；浏览器实测 9/9，通过真实复核入口、七图、五页 2560×1440、移动端及无请求/控制台错误。证据 `frontend/output/playwright/visual-audit/visual-acceptance-report.json`，新截图 `*-user-2560x1440.png`，含档案耗时图最终回归；见 TEST_REPORT §26。
- 新媒体：78 JPG /13 MP4；2 张新图与 1 个视频用新脚本 `scripts/verify_delivery_media.py` 跑真实 API/权重/生产质量阈值，但 SQLite、Qdrant、上传/输出全部隔离。结果 `outputs/delivery-media-20260914.json`；两图 DeepSeek llm 分析、报告可读、真实进入 review；4K/60fps 视频 46/271 帧，76.6s。7 条反向轨迹只是配置测试，不是真实逆行。素材首选/边界见 `docs/DEMO_MEDIA_SELECTION_2026-09-14.md`；其余 12 视频未全部筛选。
- 联网缺陷：独立 VLM 回归本轮 7/10 条通过，3 条云端视觉证据断言失败；探针明确 `VisionLLMServiceError ... WinError 10013`。人物闸门正确，DeepSeek 在媒体回归中实际 llm 成功。不能把历史 qwen 联网通过或当前 configured=true 当本轮联网成功；当前受执行环境套接字权限限制，不改密钥、不擅自换供应商。
- Docker：CPU 镜像改为独立 `DOCKER_YOLO_DEVICE=cpu`，不继承本机 YOLO_DEVICE=0；Qdrant 只绑定 127.0.0.1；Nginx 600s 与前端视频超时一致。验收脚本改用独立 `campus-safety-acceptance` 项目，`docker-compose.acceptance.yml` 替换挂载与端口（8081/6334），示例知识仅写验收卷。Compose 静态检查通过，运行态仍阻塞：两个 Docker Engine 管道不存在，Docker Desktop 日志目录权限拒绝。未改 Windows ACL、未删卷。服务器地址/系统/SSH/域名待用户提供，公网验收未完成。
- 续工作自动化：已穷尽当前可用工具发现，没有 automation_update 或等效定时管理接口；未创建定时任务，也未伪造成功。额度耗尽不支持绕过继续推理；可用额度恢复/购买额度/API 独立计费，均需真实账户条件。未恢复历史训练监控。后续只能在有产品定时工具的任务中设置或由用户在应用 Scheduled 创建，提示词见 DEPLOYMENT 增补。
- 不在本轮扩展：C2 语义 embedding、天气注入、视频异步与报告/复核闭环、真实事件坐标、服务器 HTTPS/访问权限验收继续为未完成项；不对外称全项目全部完成。


> **交接约定**：每完成一轮工作，把新内容加在「最新一轮」下面，**不要删除历史轮次**。
> 本项目由多个 AI 工具交替接手（Codex 开发 ↔ Claude Code 修复 ↔ WorkBuddy），
> 接手方读完本文件 + `README.md` + `PROJECT_PLAN.md` 就能开工，不需要上一任再讲一遍。

**项目路径：** `<LOCAL_PATH>`

---

## 项目速览（接手先读，30 秒）

**产品**：安巡智脑 —— 校园交通安全巡检 AI 数字员工，服务四川现代职业学院。

**主链路**：上传图片/视频 → 双 YOLO26 检测 → 图片质量护栏 → RAG 检索校园知识库 →
DeepSeek 风险研判 → 整改建议/报告 → 人工复核。

**技术栈**：

- 后端：FastAPI + LangGraph（11 节点工作流）+ SQLAlchemy/Alembic（迁移 head 为 `0002_multimodel_vision`）
  + SQLite/MySQL + Qdrant（当前为 embedded 模式）
- 前端：Vue 3.5 + TS 5.9（strict）+ Vite 7 + Element Plus 2.11 + Pinia + vue-router 4，完整 Admin Console
- 视觉：`yolo26-tt100k-best.pt`（TT100K 训练，45 类交通标志，mAP50 0.839）
  \+ `yolo26m.pt`（官方权重，类别被限制为 person/bicycle/car/motorcycle/bus/truck）
- 大模型：DeepSeek（经 Rainbow Gate 中转）

**关键约定（踩过坑，务必先读）**：

- 区域类型固定 8 个：校门口 / 停车场 / 校园主干道 / 宿舍区 / 食堂周边 / 教学楼路口 / 消防通道 / 其他
- 改前端样式前**必读** `frontend/DESIGN.md`（当前为 v6「真实数据驱动的精密科技感 GIS 校园安防指挥台」）
- `frontend/src/styles.css` 是**全局唯一、无 scoped** 的样式表，改 class 前先确认影响范围
- 侧边栏菜单有**两处独立定义**（`router.ts` 路由表 + `AppLayout.vue` 的 `menu` 数组），增删必须同步
- RAG 检索查询格式 = `{区域类型} {地点} {YOLO 类别} 校园交通安全巡检`
- `EMBEDDING_PROVIDER=hash`：靠**字面重合度**打分，**不是语义嵌入**，知识文档用词必须贴合检索词
- 分块为 `chunk_size=500` / `chunk_overlap=80`：**Markdown 表格必被从中间切碎**，知识文档一律用条目式
- 分块器**不认识 `##` 章节边界**，每个分块必然横跨两节、标题与正文错位，
  所以知识文档里**每条规则都要自带区域名称**，不能依赖章节标题归属
- 知识文档管理走 `POST / GET / DELETE /api/v1/knowledge/documents`
  （删除接口是本轮新增；向量库为 embedded 模式，目录被后端进程独占，**只能由后端删除**）
- **线上知识库 = 5 份真实制度/法规文档 / 63 块**（学校实践 21 / 判定规范 13 / 整改建议库 12 /
  法规摘录 10 / TT100K 释义 7）；`uploads/knowledge/` 与之**一一对应，零孤儿**。
  演示材料《校园交通巡检示例规范》只保留源文件作验收夹具，**已从线上库移除，不要再上传**
- 视频跟踪模型与图片推理模型**必须隔离**，视频跟踪永远不要调用 `get_general_model()`（详见下一轮 2.1）

**启动方式**：开发 → `frontend/` 下 `npm run dev`（5173，代理 `/api` `/uploads` `/outputs` → 8000）；
生产 → `docker-compose up`。
后端必须**以 `backend/` 为 CWD** 启动，否则 `data/campus_safety.db`、`data/qdrant`、`../uploads`
这些相对路径会指错地方。

**Python 环境（重要，踩过坑）**：本项目后端与测试都跑在 conda 环境 **`yolo_change`**：

```
<LOCAL_PATH>
```

后端当前的实际启动命令就是
`<LOCAL_PATH> -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
跑测试用 `cd backend && <上面那个解释器> -m pytest -q`。

> ⚠️ **在 Git Bash 里直接敲 `python` 会解析到 WorkBuddy 的托管 Python 3.13，那里没装 pytest**，
> 会报 `No module named pytest`（`backend/*.pyc` 是 `cpython-310`，一眼能看出解释器不对）。
> 必须写完整路径，或先 `conda activate yolo_change`。

**Docker**：CLI 已安装（**v29.6.1**），但**守护进程未启动**（`docker info` 报
`failed to connect ... dockerDesktopLinuxEngine`）。所以 `docker-compose` 运行态验收
至今未执行——**不是环境缺失，只是没起 Docker Desktop**，Codex 起来后可直接跑。

**版本控制**：`campus-safety-agent/` 是**独立 git 仓库**（分支 `main`，基线提交 `c464cc4`），
不是父仓库 `ultralytics-yolo11-main` 的一部分——父仓库的 `.gitignore` 已排除该目录。
直接在 `campus-safety-agent/` 里 `git add / commit / diff` 即可，**不要**去父仓库操作它。

---

## 当前最新交接：WorkBuddy（阿克）→ 下一个接手方（2026-09-13 深夜 · VLM 接入轮）

> **本节是当前有效状态。** 下方 2026-09-14 凌晨节（知识库轮）仍是其所述内容的有效记录；
> 本节在其之上叠加 VLM 旁挂视觉研判（模式乙）的接入完成态。

**本轮主题**：按 `docs/VLM_INTEGRATION_PROPOSAL.md` 第 7 节评审结论（修改后接入、模式乙）
执行 VLM 识图研判层接入：先零风险实验选型，再改代码，再真实 API 端到端回归。
未恢复训练、未动生产库历史任务、未提交 git。
**2026-09-14 00:40 用户拍板启用并改为默认开启，生产后端已重启生效（见 E 节）。**

### A. 选型实验结论（先于代码，证据充分）

- `scripts/test_vlm_parking.py`（新建，零风险，支持 `--model/--base-url/--key-env/--proxy` 双模型对照）。
- **阿里百炼 qwen3.7-flash：方向判断偏宽松**——3 张违停预期图全判合规（9752/9759 高置信合规）。
- **DeepSeek deepseek-v4-flash-vision-exp：保守诚实**——9759 判 uncertain（0.4），明言「未见车位线无法定论」。
- 两模型两轮结果均一致（确定性好）。**默认采用 DeepSeek 视觉实验模型**（config 默认值），
  qwen 保留 `.env` 中注释掉的切换行 + `DASHSCOPE_API_KEY`，一行取消注释即可切换。

### B. 接入设计（模式乙，三条铁律全部落地）

1. **DeepSeek 文字模型仍是唯一风险决策者**：视觉研判只转成证据文本进 evidence +
   payload 附 `vision_assessment_role`（「仅作证据参考…不得直接采用其结论」），不产生策略字段。
2. **隐私闸门**：YOLO 检出 person 的图片**绝不上送云端**（静默跳过，不追加复核原因）；
   haar 人脸模糊（`tools/privacy_mask.py`）仅作非 person 图的兜底。
3. **回退逐字节等价**：`VISION_LLM_ENABLED` 单开关控制（接入时默认 False；
   **2026-09-14 用户拍板后默认改为 True，见 E 节**），关闭时链路行为与改造前完全一致；
   视觉服务任何异常 → 降级纯文本研判 + 追加复核原因（fail-closed，进人工复核）。

### C. 改动清单

| 文件 | 内容 |
|---|---|
| `backend/app/config.py` | `vision_llm_*` 7 项配置（enabled **默认 True**（09-14 拍板，原 False）；base_url 默认 `https://api.deepseek.com/v1`；model 默认 `deepseek-v4-flash-vision-exp`；api_key 缺省复用 `LLM_API_KEY`） |
| `backend/app/tools/privacy_mask.py` | **新建**：`mask_and_resize()`（haar 人脸模糊 + 长边 1024 + JPEG） |
| `backend/app/services/llm.py` | `VisionLLMService` + `VisionLLMServiceError` + `vision_person_gate()`；白名单 7 键收敛、置信度夹紧、HTTP 错误重试；DeepSeek 走代理/其他直连，`thinking` vs `enable_thinking` 字段分家 |
| `backend/app/services/risk.py` | `evaluate()` 加 `vision_assessment` 参数；`_vision_evidence_line()` 转证据文本；payload 加 `vision_assessment` + `vision_assessment_role` |
| `backend/app/agents/graph.py` | `InspectionWorkflow` 加 `vision_llm`；`evaluate_risk` 调 `_run_vision_assessment()`（闸门+降级） |
| `backend/app/main.py` / `api/router.py` | 装配 `app.state.vision_llm_service`；health 加 `vision_llm` 状态块 |
| `backend/tests/test_vision_llm.py` | **新建 15 例**：门控、请求体纪律、白名单、置信度夹紧、重试、person 闸门、证据并入、graph 降级 |
| `scripts/test_vlm_parking.py` / `scripts/e2e_vlm_regression.py` | **新建**：选型实验脚本 / 隔离端到端回归脚本 |
| `.env` | `DASHSCOPE_API_KEY`（qwen）；**2026-09-14 已加 `VISION_LLM_ENABLED=true`，并在 E2 拍板后指向 qwen3-vl-plus（BASE_URL/MODEL/API_KEY 三行显式）** |

### D. 验证汇总

- 后端全量 pytest：**80 passed，0 failed，30.77 s**（65 → 80，新增 15 例全过，全新 `--basetemp`）。
- 隔离端到端回归（`outputs/vlm_e2e_regression_20260913.json`，真实 API+真实权重，隔离库）**全部通过**：
  - 用例 A（IMG_9759 违停无人物）：视觉恰调 1 次，返回白名单字段，与 DeepSeek payload 并入内容逐字节一致，
    角色声明到位；视觉结论 uncertain 0.4（诚实）。
  - 用例 B（IMG_9760，YOLO 检出 2 名 person）：闸门生效**零调用**，图片未上送，巡检正常完成。
  - 教训记录：回归脚本首轮因权重默认路径相对 `backend/` 而检测静默为空、断言假性通过——
    已在脚本内显式绝对路径 + 断言加非 None 前置。**凡从仓库根跑 backend 代码，YOLO 权重路径必须显式给绝对路径。**
- 前端未改，无需回归。

### E. 启用决策（2026-09-14 00:40 用户已拍板：**启用，且改为默认开启**）

1. `backend/app/config.py`：`vision_llm_enabled` 默认值 False → **True**（注释注明回退方式）。
2. `.env`：显式 `VISION_LLM_ENABLED=true`。
3. 全量 pytest 复跑：**80 passed，0 failed，28.07 s**（默认翻转零破坏）。
4. 生产后端已重启（旧 PID 38888 → 新进程，8000 端口），health 实测：
   `vision_llm = {enabled:true, configured:true, model:deepseek-v4-flash-vision-exp, person_gate:true}`。
5. **回退方式不变**：`.env` 改 `VISION_LLM_ENABLED=false` + 重启，即与改造前逐字节等价。
6. 演示讲点：模式乙证据侧车（DeepSeek 仍是唯一决策者）、person 隐私闸门（检出人即不上送）、
   单开关逐字节回退。注意：每张无 person 巡检图会多一次云端视觉调用（时延 + 费用）。

### E2. 提供方切换（2026-09-14 01:05 用户拍板：**改用 qwen 最强视觉模型**）

- 用户质疑「为什么不用千问」后的实测回答：qwen3.7-flash 是**轻量档**所以判得宽松，不是 qwen 不行。
  该 key 在标准百炼端点下可见 250 个模型，视觉类最强可用为 **qwen3-vl-plus**（Qwen3-VL 代；
  235B 旗舰未对该 key 开放，`qwen-vl-max` 为上一代）。
- **6 样例实测（`outputs/vlm_qwen3vl_plus_test_20260914.json`）：5/6 与预期方向吻合、两轮确定**
  （9752/9759 疑似违停 ✓、9773 合规 0.95 ✓、9781/宿舍路不确定 ✓；唯一偏差：9769 倒置图
  判了疑似违停而非不确定——它把画面转正后识别出了边缘车辆）。明显优于 qwen3.7-flash（全判合规）。
- **切换落点（`.env`）**：`VISION_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`、
  `VISION_LLM_MODEL=qwen3-vl-plus`、`VISION_LLM_API_KEY=<DASHSCOPE key>`（**必须显式设**，
  否则复用 DeepSeek 的 LLM_API_KEY 会 401）。回落 DeepSeek 视觉：注释这三行即可。
- **切换后验证**：生产后端重启，health 实测 `model:qwen3-vl-plus, enabled/configured:true`；
  端到端回归全过（`outputs/vlm_e2e_regression_qwen_20260914.json`）；全量 pytest **80 passed / 25.31s**。
- **如实记录的两点**：
  1. **提示词敏感性**：同一张 9759，实验脚本提示词下 qwen3-vl-plus 判「疑似违停 0.75」，
     生产服务提示词下判「compliant 0.95」（声称看见白色车位线，与实验描述矛盾）——模式乙下它只是证据，
     最终结论仍由 DeepSeek 综合判定（该任务最终 risk_level=review，未造成错误放行），
     但演示时别说「视觉结论就是最终结论」。
  2. **测试密闭性修复**：`tests/conftest.py` 的 settings 夹具原来不钉 `vision_llm_*`，
     `.env` 一切换就漏进真实提供方配置导致 2 例失败；已把 4 个字段钉死为 disabled/None/默认值，
     套件对 `.env` 与默认值变化从此免疫。

### F. 下一步（优先级不变，叠加本轮）

1. 比赛冻结线 9/14 12:00 前停止一切代码改动（VLM 启用已于 00:40 完成并验证，不占用冻结窗口）。
2. C2 语义嵌入立项、视频异步化、Docker 运行态验收、版本收口——同前节。

### G. 运行态快照（2026-09-14 00:55，交给 Codex 时实测）

- **8000 后端**：在跑，VLM 已启用且提供方为 **qwen3-vl-plus**（E2 节；health `vision_llm.enabled/configured=true, model=qwen3-vl-plus`）。
  ⚠️ 它是以 **WorkBuddy 后台任务**方式拉起的，**WorkBuddy 会话一关进程就没了**——
  接手后先 `netstat -ano | findstr :8000` 确认；不在就用 `scripts\start-backend.ps1`
  （或 `cd backend && <yolo_change解释器> -m uvicorn app.main:app --port 8000`）在独立终端重启。
  另：`Start-Process` 拉起的 uvicorn 会随发起会话被杀，别用。
- **5173 前端**：在跑（主界面）。**5174** 还有一个历史多开的 Vite 实例，不用管。
- **生产库任务表仍是修复前数据**（10/11 转人工＝基线），别拿它评估整改效果；
  VLM/知识库效果一律用隔离库验证（`scripts/e2e_vlm_regression.py` 是现成模板）。
- **未提交 git**：本轮全部改动（VLM 代码+测试+脚本+文档）仍在工作区。`.env` 已被
  `.gitignore` 第 1 行忽略（含真实密钥，安全），但 `git add -f` 之类强加时务必避开它。

---

## 当前最新交接：WorkBuddy（阿克）→ 下一个接手方（2026-09-14 凌晨）

> **本节是当前有效状态**（取代下方 2026-09-13 23:30 Codex 节的「G. 下一步真实遗留」第 1 条：
> 知识检索结构性缺口已按 `docs/KNOWLEDGE_GAP_ASSESSMENT_2026-09-13.md` 决策并实施完毕）。

**本轮主题**：知识库三项决策 + 缺口补齐 + 生产库「删旧→传新」+ 双维度审计 + 隔离库真实任务回归。
未恢复训练、未动生产库历史任务、未提交 git。

### A. 三项决策（依据 KNOWLEDGE_GAP_ASSESSMENT，接手方拍板、用户不参与）

1. **决策 A = A1：知识库只收「视觉可验证」的隐患。** 理由：证据来源是图片/视频，
   反诈、食品安全等检不出证据，补进库只会变成第二个「逆行」——躺着、引不到、还挤占席位。
   共享单车（`bicycle` 可检出）、外卖/快递配送（`motorcycle` 可检出）属视觉可验证，本轮已补；
   治安/门禁类不补（无证据来源）；校车/班车不补（未确认学校是否有班车，避免编造）。
   **放弃了**：治安门禁类知识的覆盖广度；**代价**：这些主题的研判永远没有知识依据（可接受，
   因为本来也检不出证据）。
2. **决策 B = B1（现状 + 如实标注），不打通逆行闭环。** 理由：逆行判定已实现但只在视频路径
   （ByteTrack 轨迹 + 调用方手传 `allowed_direction`）且结果不入任务库；打通属开发工作量
   （数据模型/前端展示/复核流），应与「视频异步化」同属工程改造单独立项，不混进知识库轮。
   本轮已在两份文档中**如实标注能力边界**：单帧图片无法确认行驶方向，图片路径检出
   `pne`/`p5`/`i5` 只能作「逆行风险关注点」线索。**B3（VLM）单独评估，见 `docs/VLM_INTEGRATION_PROPOSAL.md`。
   **放弃了**：视频逆行事件的自动闭环处置；**代价**：逆行能力停留在演示级。
3. **决策 C = C3 分两步：本轮 C1（hash 口径内重写），C2（换语义嵌入）单独立项。** 理由：
   C2 动检索底座，影响所有历史结论可比性（需重新入库全部文档、重标 `rag_score_threshold`、
   全量零退化验证），不应夹在知识补充里做。**本轮实测再次证明 C2 必要性**（见 D 节）。

### B. 本轮改动

| 对象 | 内容 |
|---|---|
| `knowledge/校园交通安全巡检判定规范.md` | 13 → **17 块**。①通用判定纪律新增第 5 条（逆行能力边界 + 道交法 35 条）；②校门口/主干道逆行条文改写：嵌入 `bicycle`/`motorcycle`/`pne`/`p5`/`i5` 真实类别代号，改为「逆行线索」表述；③「九、电动自行车专项」扩为含共享单车、外卖配送条目；④新增「十、恶劣天气与不良路况专项」（判定要点+整改要求+法定依据）；⑤依据清单补道交法 35/42 条、实施条例 46/58 条 |
| `knowledge/校园交通隐患整改建议库.md` | 12 → **15 块**。①「六、逆行」隐患特征逐句嵌入区域名+代号，新增「能力边界」段与道交法 35 条依据；②「七、非机动车」扩共享单车/外卖配送整改模板；③新增「十一、恶劣天气下的通行与停放风险」 |
| `scripts/verify_knowledge_recall.py` | 扩展「隐患类型」维度（12 查询，含塞词诊断项）+ 指纹词归属标注 + `--json` 证据输出；区域维度口径与旧版逐位兼容 |
| `scripts/simulate_knowledge_recall.py` | **新增**：离线复现 chunk+hash嵌入+余弦打分全链路，动库前对比 git HEAD vs 磁盘版本（分数与线上逐位吻合，可作以后的标准预检工具） |

法条核实（全部经官方网站交叉验证，非记忆引用）：道交法第 35 条（右侧通行）、第 42 条第 2 款
（恶劣气象降低速度）；实施条例第 46 条（能见度 50 米内/冰雪泥泞 ≤30km/h）、第 58 条
（低能见度灯光）。

生产库替换（走 API「删旧→传新」，不碰任务表）：判定规范 `ac258e0b` → `d827ac61`（17 块）、
建议库 `925ef2ad` → `32f177b5`（15 块）。线上库现为 **5 份 / 70 块**（63−13−12+17+15），
其余 3 份（管理实践 21 / 法规摘录 10 / TT100K 7）未动；`uploads/knowledge/` 与线上库一一对应、零孤儿。

### C. 双维度检索审计（改前/改后，证据 `outputs/kb_audit_{before,after}_20260913.json`）

| 维度 | 零命中 | 分数区间 | 管理实践席位 | 判定规范席位 | 建议库席位 |
|---|---|---|---|---|---|
| 区域 16 查询 | 0 → 0 | 0.2777~0.5558 → **0.2819~0.6045** | 51 → **47** | 19 → 20 | 10 → **13** |
| 隐患 12 查询 | 0 → 0 | 0.2362~0.5435 → **0.2750~0.5435** | 41 → **27** | 15 → **24** | 4 → **9** |

改前基线与 2026-09-11 审计**逐位一致**（0.2777~0.5558、51/19/10），证明脚本口径可信。
「通用词块霸榜」被实质稀释：管理实践席位两维度共 92 → 74，判定规范+建议库从 48 → 66。
目标场景改善：非机动车乱停（宿舍区查询 5 席全为业务文档）、共享单车（校门口 3/5 席含新条目）、
外卖配送（食堂 2/5 席含新条目）、违停（建议库违停整改 3 席）。

### D. 如实记录的未解决项（重要，别误判为漏改）

1. **恶劣天气块在 hash 检索下结构性唤不醒。** 即使把「雨天/湿滑/雾」手动塞进查询词，
   天气专项块仍进不了 top5（被管理实践的长块用字面密度压住）。这是哈希嵌入排序噪声的
   硬边界，**调措辞解决不了**——这正是 C2（换 `openai_compatible` 语义嵌入）立项的实测依据。
   天气规则已在库中（带核实过的法条），其真正激活路径：① C2 语义嵌入；② 后端把实时天气
   注入 RAG 查询词/研判证据链（工程改造，未做）。在 C2 落地前，天气规则只在检索碰巧命中时生效。
2. **逆行知识对「真实格式查询」（不含「逆行」二字）仍基本检不到**——与诊断一致，属结构性
   不可召回；本轮 C1 的收益是把逆行边界纪律挂到了 `bicycle`/`motorcycle`/`pne` 等可产出词上
   （实测：逆行-非机动车查询 top5 已含新边界条文与共享/外卖条目）。
3. 隔离库真实任务回归（`AX-20260913-ACA61A`，IMG_9781/p11 0.942）：链路端到端正常，
   `analysis_mode=llm`，知识引用 top5 与审计预测逐位一致，LLM 正确翻译 p11 为禁止鸣喇叭；
   但其引用的 5 块仍被管理实践主导，LLM 如实指出「p11 对应关系未在片段中明确」——
   再次指向排序噪声（C2），非内容缺陷。结果存 `outputs/kbreg_task_result_20260913.json`。
   单次重跑不作 A/B 判断（判定链路残余非确定性，见历史轮次）。

### E. 验证汇总

- 分块自检：源目录 6 文件 / 71 块（含未入库夹具 1 块），**0 个需要关注**；线上 5 份 / 70 块与自检一致。
- 后端全量 pytest：**65 passed，0 failed，28.85 s**（`--basetemp` 全新路径）。
- 隔离回归临时环境（8030、独立 DB/Qdrant/上传目录）已停止并删除；未写入生产库任务表。
- 本轮未改前后端业务代码；前端无需回归。

### F. 下一步（更新后的优先级）

1. **C2 语义嵌入立项**（本轮实测的硬依据见 D-1）：换 `EMBEDDING_PROVIDER=openai_compatible`，
   重新入库全部文档、重标阈值、用本轮两个 JSON 基线做零退化对照。
2. **视频异步化**（job + 真实进度轮询，替代 600 秒超时等待）——若做，可与逆行闭环（B2）同轮评估。
3. 用户逐页 UI 终验、Docker 运行态验收、版本收口（未提交改动分批提交）——同 2026-09-13 23:30 节 G。

---

## 当前最新交接：Codex → 下一个接手方（2026-09-13 23:30）

> **本节是当前有效状态。** 后面的“知识库覆盖诊断”“UI 参考图实施”和更早轮次是形成当前状态的历史依据；
> 遇到冲突时，以本节、`docs/TEST_REPORT.md` 第 23 节和真实运行结果为准。

### A. 接手后先读什么

按以下顺序完整阅读，再动代码：

1. 本文件的“项目速览”与本节 A–H；
2. `docs/TEST_REPORT.md` 第 18–23 节（重点是第 22 节 UI v7、第 23 节视频修复）；
3. `frontend/DESIGN.md`（全局样式、真实数据和参考图边界）；
4. `docs/audit/REMEDIATION_2026-09-13.md`；如要复核决策，再读 `docs/audit/EXPERT_PANEL_SYNTHESIS_2026-09-12.md` 及四份分报告；
5. `docs/KNOWLEDGE_GAP_ASSESSMENT_2026-09-13.md`（知识检索遗留，尚未实施）。

不要从历史章节抄旧端口、旧测试数量或旧知识库建议。历史中“上传示例规范到生产库”的建议已经明确作废。

### B. 刚完成的代码与 UI 状态

- 专家审核 Q1–Q6 已由工程方自主决策，结果写在 `docs/audit/REMEDIATION_2026-09-13.md`。已执行
  T1、T2、T4、T5、T6、T7、T8、T11、T12；T3/T9 是必须保留的产品边界，T10/T13 有意不做，不能把它们当漏改。
- 图片质量改成按长边 1024 归一化后评分；可解码但有质量告警的图片继续进入 YOLO/RAG/风险分析，只有不可分析图片才短路。
- 人工复核布尔值由后端确定性策略统一决定，DeepSeek 不能直接注入 `review_required`；LLM 的风险分数和风险等级仍可能随供应商输出变化，不能宣称整个判定链机械确定。
- 通用人员车辆模型已改为 `models/yolo26m.pt`；TT100K 专用模型仍是用户接受的 `models/yolo26-tt100k-best.pt`。
- 前端已按六张参考图完成 v7：灰黑表面色、Noto Sans SC / Microsoft YaHei UI 字体链、语义色块、连续布局、
  GIS 总览、真实数据分析页、巡检创建页、人工复核详情、知识库和设置页。参考图里的摄像头、直播 FPS、SLA、虚构热力和假坐标没有后端数据，因此没有伪造。
- 用户最后一次 UI 反馈要求继续检查字体、语义色块和中段空白。对应整改已进入 `styles.css` 和各页面，并在
  1680×945、2353×1156、390×844 通过 Playwright；若用户仍指出某页差异，必须先用真实浏览器截图逐页几何对照，
  不要继续盲目堆 CSS。`frontend/src/styles.css` 无 scoped，修改前先查全仓 class 使用范围。

### C. 最新故障：51.03 MB 4K 视频“卡住后报错”（已修复）

用户视频 `VID_20260913_185218.mp4` 的真实规格为 2160×3840、约 60.13 FPS、271 帧。旧逻辑每隔 2 帧分析并以
原始 4K 分辨率进行 VP8 软件编码，共处理 136 帧；后端仍在运行时，前端 60 秒 Axios 超时先中断，因此看起来像模型卡死。

本轮改动：

- `backend/app/config.py`：新增 `video_target_fps=10`、`video_max_dimension=960`；
- `backend/app/tools/video_analytics.py`：高帧率视频自适应抽帧、等比缩放、响应返回源/分析尺寸和实际步长；
- 同文件的视频锁改为非阻塞，重复提交立即返回“已有视频正在分析”，不再静默排队；
- `frontend/src/pages/NewInspectionPage.vue`：单次视频请求超时改为 600 秒，按钮显示真实等待秒数；
- `.env.example`、单元测试和 `docs/TEST_REPORT.md` 第 23 节已同步。

真实同文件 API 复测：HTTP 200；271 源帧 → 46 分析帧；步长 6；2160×3840 → 540×960；总请求约
103 秒、后端分析约 88 秒；峰值 12 人、27 条人员轨迹、1 条车辆轨迹、7 条逆行候选轨迹。结果 WebM 为
3,347,569 bytes，OpenCV 可重新打开。**这仍是同步长任务，不是秒级接口**；当前修复目标是“不再错误超时并让等待可见”。
如要进一步改善体验，应把 `/video-analytics` 改为异步任务（提交返回 job id + 轮询进度），不要再次单纯放宽超时。

### D. 当前验证基线

- 后端全量测试：**65 passed，0 failed，34.96 s**；
- 前端 `npm run build`：**通过**，2292 modules，46.22 s；
- 最新真实视频接口：HTTP 200；结果视频可读取；
- `git diff --check`（本轮相关文件）：通过；
- 最新累计证据：`docs/TEST_REPORT.md` 第 23 节；UI 证据在 `frontend/output/playwright/visual-audit/`。

标准复跑命令：

```powershell
Set-Location <LOCAL_PATH>
<LOCAL_PATH> -m pytest -q

Set-Location ..\frontend
npm run build
```

### E. 当前运行态（写交接时已实测）

- 后端：`127.0.0.1:8000`，PID 38888，`/api/v1/health` 返回 `status=ok`；必须以 `backend/` 为 CWD。
- 前端：`127.0.0.1:5173`，PID 9700，HTTP 200；另有一份旧 Vite 在 5174（PID 41852）。接手时以端口和进程为准，
  不要再启动第三份前端；需要清理重复进程时先确认用户正在看的端口。
- 视频跟踪模型已按需加载；健康接口中图片模型 `loaded=false` 仅表示当前进程尚未调用图片推理，不等于权重缺失。
- `.env` 中 DeepSeek、高德和代理配置存在，但密钥绝不能写入代码、日志、截图或交接文档。
- 训练保持停止。不得恢复 YOLO 训练、watchdog、计划任务或 heartbeat；不得把 32/80 轮写成完整训练。

### F. 工作树与版本控制警告

- 当前 HEAD：`63df367`；但从专家整改、UI v7 到视频修复有大量**未提交**修改和新增文件。
- 这些改动来自连续多轮协作，全部视为用户现有工作；**禁止 reset、checkout、clean 或覆盖**。
- 当前存在未跟踪的测试、审核文档、UI 参考图、图表组件和运行日志。运行日志不应直接提交，但也不要未经核验删除。
- 只在 `campus-safety-agent/` 独立仓库执行 git；提交前必须先逐项审查 `git diff`、确认 `.env` 未进入索引，并把逻辑改动与
  生成证据/日志区分开。不要在父仓库 `ultralytics-yolo11-main` 添加本目录。

### G. 下一步真实遗留（建议优先级）

1. **知识检索结构性缺口（最高优先级未实施）**：按 `docs/KNOWLEDGE_GAP_ASSESSMENT_2026-09-13.md` 决策并实施。
   “逆行”在图片模型类别中不存在，视频结果又不入任务/RAG；哈希检索还有通用长块霸榜。继续无目的补知识文档不能单独解决。
2. **视频异步化（体验优先）**：当前 4K60 真实视频成功但约 103 秒。若继续做，新增持久化 job 状态与进度接口，前端轮询；
   必须保留真实结果和错误，不要做假进度条。
3. **用户逐页 UI 终验**：现有自动验收已过，但用户审美反馈优先。以用户实际浏览器尺寸逐页截图，对照六张参考图；只改有证据的字体、
   间距、色块和布局问题，真实数据不足的位置允许自然留白，不能填假统计。
4. **Docker 运行态验收**：历史上 Docker CLI 可用但守护进程未启动。Docker Desktop 可用后执行
   `scripts/docker-runtime-acceptance.ps1`，不能用 Compose 静态校验冒充运行通过。
5. **版本收口**：确认哪些未跟踪日志/视觉证据需要保留，完整复测后再分批提交；不要替用户擅自删除历史材料。
6. **次要技术债**：巡检档案服务端分页、地图地标真实经纬度校准、人工确认时选择最终风险等级、报告链接统一 API base、
   视频事件状态类型对齐、脚本移除本机硬编码路径。

### H. 不可违反的边界

- 生产知识库保持 5 份真实文档 / 63 块；`knowledge/校园交通巡检示例规范.md` 只作验收夹具，禁止上传生产库。
- 删除任何文件前执行：全仓路径引用检索 → DB 引用检查 → 确认可从留存副本恢复，并先报告结论。
- 用户给过 DeepSeek 与高德密钥；交接文档只记录“已配置”，不得复制密钥明文。
- 参考图是假数据构图，只能复刻设计系统和拓扑；所有业务数字、检测框、任务、知识命中和服务状态必须来自真实接口。
- 视频“逆行候选”取决于调用方提供的允许方向与 ByteTrack 轨迹，不代表已完成固定机位真实准确率标注验收。

---

## 最新一轮：知识库覆盖诊断与交接决策（2026-09-13 深夜）

**本轮主题**：只读诊断知识库覆盖情况，产出交给 Codex 的决策文档与提示词。
**未改任何知识库文件、未改任何代码、未提交 git。**

### A. 诊断结论

- **内容覆盖是完整的**：8 个区域类型全覆盖；逆行、违停都有专节且写法合规。
- **但「逆行」这条知识在链路上彻底失效**：实测 **0/5 进 top5** ——
  **即使手动把「逆行」两个字写进查询词也检不到**；对照组违停章节 **3/5 命中**。
- 三处断裂叠加：
  ① **检索层** 0/5；
  ② **检测层** —— **「逆行」不是模型的输出类别**（TT100K 45 类、COCO 6 类都没有），
  图片路径完全没有逆行判定（单帧无方向），只有 `video_analytics.py:173` `_is_wrong_way()`
  在**视频**路径判、且要求调用方手传 `allowed_direction`；
  ③ **闭环层** —— `POST /video-analytics`（`router.py:487`）结果**不入库** → 不触发 RAG。
  **根因在检测层**：模型产不出「逆行」这个词 → 查询词里永远没有它 → 检索注定命中不了。
- **新发现「通用词块霸榜」（首次量化）**：《管理实践》「6. 安全教育宣传渠道」块堆叠
  「交通安全、消防安全、食品安全、防溺水」等跨主题通用词，在 **5 个查询里 4 次拿第 1 名**，
  与查询主题无关。哈希嵌入 + 长块堆词的结构性问题。
- **有接口、无知识**：系统已接高德天气（`/api/v1/maps/weather`，前端顶栏在显示），
  但知识库「雨天 / 湿滑 / 雾」**命中 0 份文档**。
- 缺口扫描（grep 命中文档份数）：共享单车 0、校车 0、雨天/湿滑/雾 0、超载 0、
  骑手/快递 0（外卖仅 1 处）、限时停车 0、停车秩序 0。

### B. 本轮产出（三份文档）

| 文件 | 用途 |
|---|---|
| `docs/KNOWLEDGE_GAP_ASSESSMENT_2026-09-13.md` | 诊断报告 + 可复现实测数据 + 三个待决策项 + 缺口清单 + 硬约束 + 验收要求 |
| `docs/CODEX_KNOWLEDGE_PROMPT.md` | **可直接粘贴给 Codex 的提示词**（决策 + 执行轮） |
| 本文件 | 滚动交接记录 |

**⚠️ 用户明确要求：本轮三项决策（业务边界 / 逆行闭环 / 检索技术路线）由 Codex 自己拍板，
用户不参与。** 接手方必须把决策写回本文件，注明「选了什么、为什么、放弃了什么、代价是什么」。

### C. 边界与遗留

- 本轮**只读**：临时探针脚本（`outputs/_kb_probe*.py`）跑完即删；未改 `knowledge/`、未改 `backend/`。
- 生产库 `backend/data/campus_safety.db` 与线上知识库仍是 **5 份 / 63 块**，未动。
- 用户级 skill `rag-knowledge-base-authoring` 已回写本次新增的两条坑
  （**概念不在模型输出类别集合里 = 结构性不可召回**、**通用词堆叠块会霸榜**）。

---

## 最新补充：用户截图差异整改与超宽屏复验（2026-09-13）

- 用户在 2353×1156 截图中发现新建巡检主列下方大段空白。根因不是缺内容，而是“最近真实巡检”位于整个左右 Grid 之后，被较高的右侧说明栏推迟；现已移入 `.inspection-primary`，专项验收将表单底到近期任务顶的间距限制为 0–20px。
- 侧栏已接入 `frontend/src/assets/campus-sidebar-skyline.png` 透明校园建筑线稿和“厚德 精技 / 笃行 创新”。这是品牌装饰，不作为实时业务数据；折叠侧栏与移动端隐藏。
- 文字令牌已提升为冷白/浅钢蓝/钢蓝三级，蓝色继续只用于 kicker、主操作和选中态，红黄绿紫语义状态不变。
- 复核详情已改为参考图拓扑：顶部人工复核/证据审查与六项元数据；首层原图/结果图 + 风险、知识、不确定性、模型来源；第二层横向 Agent 轨迹 + 结构化检测表。27 个真实节点不删除，只改变为可滚动呈现。
- 最终证据：后端 `64 passed`；前端 `vue-tsc -b && vite build` 通过（2292 modules）；Playwright `8/8 passed`，`pageErrors/consoleErrors/failedRequests/httpErrors` 全为 0。专项任务 `AX-20260910-B01B59` 含 5 条真实检测。
- 仍不一比一复制的部分只来自能力边界：无实时摄像头、SLA、风险坐标、直播 FPS 和逐帧缩略接口；不允许用参考图假数值补齐。Docker Engine 运行态边界没有变化。

---

## 最新一轮：六张 UI 参考图真实数据实施与视觉验收（2026-09-13）

**本轮主题**：将六张生成式 UI 参考图的布局、信息密度和视觉层级落到现有 Vue/FastAPI 系统中，同时删除前端业务假数据回退。训练继续保持停止，没有恢复任何 YOLO 训练或监控任务。

### A. 参考图实施范围

- 态势总览保留真实校园地图、四项态势指标、右侧真实风险队列和底部任务/检测表；没有接口的在线摄像头、风险坐标和重点区域明确显示“未接入”或禁用。
- 新建巡检增加 `/health` 运行能力、真实文件信息、提交准备度、Agent 链路、识别边界和真实近期任务；图片与视频仍走原后端上传/执行接口。
- 数据分析保持 `/api/v1/analytics/overview` 的 4 项 KPI 与 7 个 ECharts 面板，不生成参考图中的趋势、热力或运营建议数字。
- 人工复核详情调整为“真实风险研判 + 原图/结果图 + 双模型统计 + Agent 执行轨迹”首屏；未检出目标时如实显示 0 和空表。
- 知识库改为真实文档、来源元数据与在线 RAG 检索三栏工作台；设置页按 `/health` 展示六项服务，并区分已连接、已配置、按需加载和尚未验证联网调用。

### B. 真实性边界

- `DashboardPage.vue`、`InspectionsPage.vue`、`ReviewsPage.vue`、`KnowledgePage.vue` 已移除内置演示任务、文档、命中和“物化演示任务”逻辑。后端离线显示错误，业务库为空显示真实空状态。
- 参考图只作为构图依据；数字、事件、检测框、摄像头、热力点、模型状态和知识正文不得从参考图复制。
- 高德地图与 DeepSeek 的“密钥已配置”不等于已联网调用；YOLO 权重存在但 `loaded=false` 表示首次任务按需加载，不再统一写成“服务正常”。
- 当前线上知识库仍是 5 份真实文档 / 63 块；没有上传演示文档，也没有修改生产知识库。

### C. 最终验证

- 后端全量测试：**64 passed，0 failed，27.93 s**。
- 前端严格类型检查与生产构建：**通过，2291 modules**。
- Playwright：**7/7 passed**；覆盖 1489×1070、参考图同尺寸 1680×945、390×844、全部业务路由、真实详情、视频模式与 7 个 ECharts。
- 浏览器信号：`pageErrors=0`、`consoleErrors=0`、`failedRequests=0`、`httpErrors=0`。
- 视觉证据与报告位于 `frontend/output/playwright/visual-audit/`；设计规范已更新为 `frontend/DESIGN.md` v6。

### D. 保留边界

- 当前没有实时摄像头流接口和任务地理坐标接口，所以没有实现参考图里的实时监控视频、模拟风险点和校园热力图。
- Docker Engine 运行态未在本轮重新验收；不得沿用静态 Compose 校验冒充容器运行通过。
- `campus-safety-agent/` 工作树包含前序多轮未提交改动，本轮没有替用户提交或覆盖这些改动。

---

## 前一轮：Codex 缺陷修复、YOLO26m 与真实数据分析（2026-09-12）

**本轮主题**：关闭已定位的图片质量与判定语义缺陷，验证 medium 通用模型收益，补齐真实运营分析页，并完成后端/前端/浏览器回归。用户已明确停止继续训练，本轮没有恢复训练。

### A. 图片质量护栏已修复

- `backend/app/tools/image_quality.py` 将清晰度检测改为“长边归一到 1024px 后再算拉普拉斯方差”，避免同一画面仅因原始分辨率不同得到不可比的分数；返回值同时保留原始分数和归一化分数。
- `BLUR_THRESHOLD` 从旧的 80 调整为归一化口径 500；15 张真实审计样本中 14 张通过，肉眼清晰但低纹理的 `IMG_9794` 从误报恢复为通过（归一化分数 1010.3），只有已知柔焦 TT100K 样本告警（152.6）。
- 图片能解码但存在模糊/亮度告警时仍可继续 YOLO、RAG 和风险研判，并保留质量复核原因；只有无法解码时才短路。`graph.py` 现在只在 `analyzable is False` 时跳过分析。

### B. 人工复核采用后端策略 B（LLM 研判仍有残余非确定性）

- DeepSeek 输出不再拥有 `review_required` 决策权；人工复核布尔值和复核理由由后端统一落政策。`risk_level`/`risk_score` 仍是 LLM 的研判输出，因此真实供应商调用仍存在残余非确定性，温度 0 不等于机械确定性。
- 任何明确复核原因、结构化视觉事件、`medium/high/review` 风险均进入人工复核；只有“无复核原因 + 无视觉事件 + low”才能自动闭环。
- 低置信度规则由“存在任意低置信度检测即复核”改为“所有检测都低于各自模型阈值才复核”，避免一个低分框覆盖同图中的高置信证据。
- 同一真实任务连续重跑 3 次均得到 `status=review`、`risk_score=30`、`review_required=true`；该结果证明当次复验稳定，但不是跨供应商版本的确定性证明。后端已阻止 LLM 直接注入 `review_required`，并保留 `risk_level` 影响复核策略的残余非确定性说明。

### C. 通用模型切换为 `yolo26m.pt`

- 默认路径、Compose、示例环境变量与文档均改为 `models/yolo26m.pt`；源文件与目标文件 SHA-256 一致：`401CEA9AB23AD19246FF7744859816BC599F350E93C9DD30367B6F0A0745D0B7`。
- 15 个混合来源巡检文件按 SHA-256 去重后为 10 张唯一图片：nano 35 个检出 / 5 张有检出，medium 47 个检出 / 7 张有检出，检出量约提升 34%；平均置信度 0.5365 → 0.5638，最高置信度 0.9088 → 0.9540，低于 0.35 的框 12 → 11。样本并非全部本校实拍且没有人工真值，不用于宣称准确率或召回率提升。
- 权重文件继续由 `.gitignore` 排除，不进入 git；交付机器必须保留 `models/yolo26m.pt`。

### D. 新增真实数据分析工作台

- 后端新增只读 `GET /api/v1/analytics/overview`，聚合累计任务、30 日趋势、风险/状态构成、区域分布、按任务去重的复核原因、模型贡献、高频类别和 Agent 节点耗时。
- 前端新增 `/analytics` 与“数据分析”导航；`DataChart.vue` 统一管理 ECharts 生命周期、ResizeObserver、空状态和无障碍名称。
- 页面共 4 个核心 KPI + 7 个决策面板，不注入演示数值。当前真实副本实测 11 项任务、10 项待复核、5 个区域、2 类复核原因、两个历史模型来源和 10 个 Agent 节点统计。
- 1489×1070 Dashboard 已与用户选定参考图同屏比较，主层级和比例一致；分析页桌面 7/7 画布渲染，390×844 单列无横向溢出。规范已写回 `frontend/DESIGN.md`。

### E. 最终验证与当前预览

- 22:51 收口补充：重启过期预览后，加严浏览器验收仍 6/6；桌面与移动端均采集错误，HTTP 4xx/5xx 不再忽略，真实复核入口与刷新响应为必测。最新证据时间 `2026-09-12T14:51:20.960Z`。
- `scripts/start-backend.ps1` 已固定 conda 解释器并支持 `-Port`，`start-frontend.ps1` 支持 `-BackendPort/-Port` 与严格端口检查，`run-local-preview.ps1` 同步代理端口；日常启动方式见 README。
- 已实际尝试启动 Docker Desktop，但当前执行环境仍不能连接两个 Engine 管道，并有配置读取拒绝访问。Docker 运行态未执行，不能宣称通过；不要向正式知识库上传验收示例。
- 后端：**44 passed，0 failed**。
- 前端：`vue-tsc -b && vite build` 通过，2295 modules。
- 浏览器：`frontend/scripts/visual_acceptance.cjs` **6/6 通过**，页面错误、控制台错误、失败请求和 404 均为 0；覆盖所有当前路由、表单空校验、进入复核详情、分析刷新、桌面和移动布局。
- 真实服务：高德地理编码、天气和静态图均返回成功；DeepSeek、高德与出站代理健康状态均为已配置。正式双模型 E2E、规则降级与报告生成的已有证据保留在 `outputs/`。
- 为避免写入当前 8000 服务，本轮新版运行态使用生产 SQLite 的完整副本 `backend/data/analytics_preview_20260912.db`、内存 Qdrant 和 8010 后端；5173 Vite 当前代理到 8010。该副本完整性检查为 `ok`，初始任务数 11。
- 当前代码改动尚未提交；提交前只在本仓库操作并再次确认 `.env*`、`*.pt`、数据、上传和输出目录均未进入索引。

### F. 2026-09-13 审核整改与背景压灰

- 决策记录见 `docs/audit/REMEDIATION_2026-09-13.md`：保留保守策略 B、不提前放行 medium、不在 10 张无真值样本上重标定 0.35、不拆风险枚举，并明确 LLM 风险等级仍有残余非确定性。
- 风险策略理由改为服务层单次计算、工作流消费，并持久化到任务 `review_reasons_json`；LLM 输出 schema 不含后端复核字段。质量路由对缺失、空值和 `False` 均保守进入复核，仅显式 `analyzable=True` 才继续检测。
- 新增审计回归后，后端全量 **64 passed**；隔离 8020 服务健康、数据库、Qdrant 和分析接口均通过，未写入生产数据库。
- 前端只将 `styles.css` 的 8 个表面 token 从深蓝压为 GitHub 灰黑；文字、强调色、字体、布局和地图配色均未改。强制类型检查、生产构建和当前 5173 浏览器 6/6 通过；最新浏览器证据时间 `2026-09-13T03:45:43.912Z`。
- Docker Compose 静态配置通过；Docker Engine 仍不可连接，容器运行态继续标记为未执行。

证据：`outputs/general_model_comparison_unique_20260913.json`、`outputs/formal-model-e2e-current.json`、`frontend/output/playwright/visual-audit/`、`docs/audit/REMEDIATION_2026-09-13.md`、`docs/TEST_REPORT.md` 第 19 节。

---

## 最新一轮：WorkBuddy → 下一个接手方（2026-09-11 深夜，Codex 接手前收尾）

**本轮主题**：① 代码纳入 git 基线 ② 新增第 5 份知识文档（学校安全工作实践）③ 全量重跑巡检任务并量化非确定性

> 本轮**未改任何业务代码**，只新增了 2 个运维脚本、1 份知识文档、1 处 `.gitignore`，
> 外加一次数据侧重跑。Codex 可以直接在 `c464cc4` 这个基线上开工、diff、回滚。

### A. 代码已纳入 git 基线（保命项，先看这条）

- **`campus-safety-agent/` 现在是独立 git 仓库**（内层 `.git`），分支 `main`，首个提交 **`c464cc4`**，
  纳入 **141 个文件 / 41.2MB**，工作区干净、零未跟踪。
- **父仓库** `ultralytics-yolo11-main`（分支 `feat/agent-detection-api`，**未配置任何远程地址，纯本地**）
  的 `.gitignore` 已追加 `campus-safety-agent/`，父仓库不再把该目录当成未跟踪目录。
  **不要**再从父仓库 `git add` 这个目录，两边会打架。
- **未纳入版本控制**（有意为之）：`校园照片/`（280MB 原始实拍）、`frontend/node_modules/`、
  `frontend/dist/`、`backend/data/`（含当前在用的 `campus_safety.db` 与 qdrant 存储）、
  `uploads/`、`outputs/`、`*.pt`、`.env` 三个文件。
- `.gitignore` 本轮补齐：`校园照片/`、`output/`、`.playwright-cli/`、`debug.log`、
  `*-e2e[0-9]/`（原 `*-e2e/` 匹配不到 `uploads-e2e2`、`outputs-e2e2` 这类带数字后缀的目录）。
- **保留在基线内**：`frontend/public/campus/*.JPG`（约 28MB，被 `ReviewsPage.vue` 的
  `demoImage` 引用，删了示例图会挂）。

> ⚠️ 踩过的坑：`.gitignore` 对**已在索引中**的文件无效。补完规则必须
> `git rm -r --cached .` 再 `git add -A`，否则文件数纹丝不动（首次 `git add -A` 暂存了 397 个，
> 清理后才是 141 个——**不审计就会把 280MB 照片和 e2e 残留一起提交进去**）。

### B. 新增第 5 份知识文档：`校园交通安全管理实践（学校公开材料）.md`

- **8244 字 / 21 块**，已入库，document id `2d1e5e28-eac6-4d1e-8a22-b992a39c93bb`，
  `status=ready`，chunk 数与离线自检（`scripts/check_knowledge_chunks.py`）完全一致。
- 结构：学校安全管理组织与责任分工 → **按 8 个区域类型分节**（与检索查询词首字段对齐）→
  常态化机制 → 省级政策依据 → 16 条来源清单 + 核验说明。
  每条做法自带区域名称，每节有「检索关键词」行，**全文无 Markdown 表格**。
- 线上知识库现状：**5 份文档 / 63 块**
  （学校实践 21 / 判定规范 13 / 整改建议库 12 / 法规摘录 10 / TT100K 释义 7）。
  **演示文档《校园交通巡检示例规范》已在本轮从线上库移除**（详见 I 节），5 份全部为真实制度/法规材料。

**来源原则（务必延续）**：只收录能给出公开网址的材料，逐条标注标题 + 日期 + 发布单位。
核心来源为学校官网 `www.scmvc.cn`（安委会办公室 / 安全稳定工作委员会办公室 / 国家安全教育办公室）
及三个二级学院站 `jzgc` / `szjj` / `swyy`，省级来源为四川省教育厅 `edu.sc.gov.cn` 与四川长安网。

**两个「宁缺毋滥」的实例，后续写文档请照此办理**：

1. **「四川省高等学校平安校园建设重点工作指南」这个名称未能核实**——在四川省教育厅、
   四川省人民政府等官方渠道检索不到该确切名称的公开文件。因此本轮**没有引用它的任何条文**。
   名称最接近的公开材料是《四川省高等学校校园安全稳定重点工作清单》，
   但它只出现在第三方知识库分享链接中、拿不到官方发布网址，同样未引用原文，
   只在文档「核验说明」一节写明情况。**不要为了凑权威感去引一个查不到出处文号的文件。**
2. 某公开文章把「全国交通安全日」写成「11.2」，与 12 月 2 日（「122」）不符，疑为笔误，不予采用。

### C. 检索审计（新数据）

工具：新增 **`scripts/verify_knowledge_recall.py`**（严格按 `graph.py` 的查询拼装方式构造
`{区域类型} {地点} {YOLO 类别} 校园交通安全巡检`，覆盖全部 8 个区域类型）。

- **零命中 0/16**；分数区间 **0.2777 ~ 0.5558**（阈值 0.08，最低分是阈值 3.5 倍）。
- top5 共 80 席分布：新文档 **51**、判定规范 **19**、整改建议库 **10**。
- 演示文档《校园交通巡检示例规范》**0 席**（本轮已从线上库移除，见 I 节；移除后复跑本审计，
  16 查询仍 0 零命中、分数区间与移除前**逐位一致** `0.2777 ~ 0.5558`，证实零退化）。

**新观察**：新文档占 64% 席位，可能挤占《判定规范》（风险等级口径所在）。
这不影响结论正确性，根因仍是哈希嵌入的排序噪声——
**调措辞调不出更好的分布，只能把 `EMBEDDING_PROVIDER` 换成 `openai_compatible` 接语义嵌入模型。**

### D. 全量重跑 11 个任务（两轮对照，产出可复现数据）

工具：新增 **`scripts/rerun_all_inspections.py`**。
注意 `POST /inspections/{id}/execute` 返回 **202 异步**，必须轮询 `GET /inspections/{id}` 直到
status 不再是 `queued`/`running`；`require_api_key` 在 `api_key` 为空时短路，本机调用无需 header。
结果快照写入 `outputs/rerun_result.json`（第一轮备份为 `outputs/rerun_result_round1.json`）。

| 时点 | risk_level 分布 |
|---|---|
| 本轮开始时 | `{review: 11}` |
| 第 1 轮重跑后 | `{review: 8, medium: 1, low: 2}` |
| 第 2 轮重跑后（新文档已入库） | `{review: 9, low: 2}` |

**结论 1：知识库把 2 个任务拉出了 review，但第 5 份文档的边际收益为 0。**
第 1 轮（新文档只覆盖到后 2 个任务）对比第 2 轮（全覆盖），只有 1 个任务变化，
且是往保守方向变（`medium → review`）。**这 11 个任务的瓶颈不在知识侧。**

**结论 2：9/11 仍是 `review`，但原因不是知识库没命中。** 逐条核对 `review_reasons` 后分四类：

- **图片质量护栏拦截**（1 个）：`AX-20260911-B91639` 判「图片可能模糊」，0 检出。
- **检测置信度过低**（4 个）：路边停车区 8 个框里 5 个置信度 < 0.5；
  东门 4 个 `car` 置信度仅 0.245~0.380。
- **单帧证据形态不足**（3 个）：宿舍区检出 13 人达聚集阈值，模型的措辞是
  「**按知识库判定应升为高风险**，但单帧静态图无法确认是否实际占用疏散通道」——
  **知识库在起作用，是证据形态挡住了结论**。
- **无检测目标**（1 个）：消防通道 0 检出，正确套用了「不得仅凭单张图片断言通道畅通」的判定纪律。

**结论 3：知识库确实被引用并驱动了推理**（不是「检索到了但没用」）：
`AX-20260911-0B6FF9` 把 `p11` 正确译为「禁止鸣喇叭」并给出 `low / 15`；
`AX-20260910-B01B59` 把 `pl60` 译为「限速60」；宿舍区任务明确写出「按知识库判定应升为高风险」。

### E. ⚠️ 交给 Codex 的缺陷清单（本轮最重要的产出）

**缺陷 1：判定链路存在非确定性，同输入会得到不同结论。**

1. **同一任务连续两轮判定翻转**：`AX-20260911-12AF90`（人车混行道路）
   第 1 轮 `medium`（risk_score 62），第 2 轮 `review`（55）。同输入、同知识库。
2. **risk_score 普遍漂移**：`AX-20260911-67131D` 消防通道 **0 → 30**、
   `AX-20260911-77F6C0` 55 → 45、`AX-20260910-81C7D0` 15 → 20、`AX-20260910-B01B59` 30 → 35。
3. **同一张图片的两个任务结论不一致**：`AX-20260911-0B6FF9`（IMG_9781）与
   `AX-20260910-81C7D0`（图书馆北侧道路，实为前端示例图 `library-no-horn.JPG`）的检测结果
   **逐位相同**（`p11` 置信度 `0.941981`、bbox 均为 `[1098.82, 3107.34, 1579.83, 3654.66]`），
   风险等级都是 `low`、`risk_score` 都是 `15`，但 `review_required` 一个 `False` 一个 `True`，
   `status` 一个 `completed` 一个 `review`。

#### 用 `check_risk_determinism.py` 复现的结果（连跑 3 次）

| 任务 | 3 次结果 | 稳定性结论 |
|---|---|---|
| `AX-20260911-BABB48`（减速带路段） | `review` / `review` / `review`，risk_score **45 / 35 / 40** | `risk_level` 一致，**score 极差 10、标准差 4.08 → 不稳定** |
| `AX-20260911-12AF90`（人车混行道路） | `medium` / `medium` / `medium`，risk_score 55 / 55 / 55 | **本次一致** |

**把话说准**（避免后人误判严重程度）：

- **`risk_score` 的抖动是稳定可复现的** —— `BABB48` 三次跑出 45/35/40，这是最硬的证据。
- **`risk_level` 的翻转是低概率而非必然** —— `12AF90` 在两轮全量重跑之间翻过一次
  （`medium` 62 → `review` 55），但单独连跑 3 次又稳定在 `medium/55`。
  所以**不能靠单次重跑判断改动效果**，也不能因为「连跑 3 次都对」就认为没问题。
- **`review_required` 的语义不一致是最硬的缺陷** —— 它不依赖概率：
  同一张图的两个任务拿到不同结果，且根因已定位到代码（见下）。

**排查方向**（按可能性排序）：
① LLM 温度未设为 0；② `review_required` 的推导是否复用了不稳定的中间状态；
③ 任务重跑时是否残留了上一轮的状态（`risk_assessments` 是否追加而非覆盖）。

#### ✅ 根因已定位（不必重新排查，直接看这里）

追查链路与证据：

1. **排除「知识库未命中」**：两个同图任务（`0B6FF9` / `81C7D0`）的
   `risk_result.knowledge_references` 都有 **5 条**，`risk_score` 分别为 15/20，
   `analysis_mode` 均为 `llm`——不是走了规则兜底。
2. **排除「内部 reasons 非空」**：两者的 `task.review_reasons` 都是 `[]`，
   即 `risk.py` 里 `reasons` 为空，**`risk.py:60-62` 的强制覆盖没有触发**。
3. **锁定**：`risk_result.review_required` 与 `task.review_required` 完全一致
   （一个 `False`/`False`，一个 `True`/`True`），说明这个布尔值
   **直接来自大模型返回的 JSON 字段**，中间没有任何确定性校验。

**根因：`review_required` 在「无强制复核理由」时由大模型自由裁量，而提示词
只规定了它何时必须为 `true`，从未规定何时必须为 `false`。**

- `backend/app/services/llm.py:35` —— system prompt 原文：
  「信息不足时必须 review_required=true，并说明不确定性。」
  **只有 true 的条件，没有 false 的条件**，模型对「什么算信息不足」没有统一标尺。
- `backend/app/services/llm.py:44` —— `"temperature": 0.1`（**不是 0**），
  放大了同输入下的输出抖动（这也是 `risk_score` 从 0 漂到 30 的原因）。
- `backend/app/services/risk.py:57-65` —— 仅在 `if reasons:` 分支里强制
  `result.review_required = True`；`reasons` 为空时**原样放行 LLM 的返回值**。
- `backend/app/schemas.py` 的 `RiskResult` 把 `review_required` 定义成
  LLM 需要输出的字段之一，即**让模型自己决定要不要转人工**。

一致性佐证：`81C7D0` 的 `uncertainty_note` 写的是
「p11 标志的物理状态（是否破损、遮挡、反光失效）未在检测结果中体现，需现场复核确认」——
**这个 `true` 本身是合理的**；问题在于同图同检测的 `0B6FF9` 没得到同样处理。
所以缺陷的本质是**同类情形未给同类结论**，而不是「该 true 却 false」。

**修复建议（需要产品先拍板，不要直接照改）**：

- **首选：把 `review_required` 从 LLM 输出里摘出来，改成证据的确定性函数。**
  在 `risk.py` 中显式计算并覆盖模型返回值，例如
  `result.review_required = bool(reasons) or bool(vision_events) or result.risk_level in {"high", "review"}`
  （具体条件需产品确认），同时把它从 `RiskResult` 的 LLM 输出 schema 中移除或忽略其值，
  让「是否转人工」只有一个事实来源。
- **辅助：`temperature` 由 0.1 改为 0.0**，减少 `risk_score` 抖动。
  注意即使设 0，多数推理服务也不保证逐位一致，**不能只靠这个**。
- **回归验证**：修复后跑 `scripts/check_risk_determinism.py <任务号> --rounds 3`，
  要求 `risk_level` / `review_required` 一致、`risk_score` 极差为 0。
- **需要产品决策的点**：一张清晰图片、高置信度检出、无低置信度目标、无视觉事件、
  风险等级为 `low` 时，到底应不应该要求人工复核？
  现状是「模型高兴就 true，不高兴就 false」，这是不可接受的，必须二选一定死。

**缺陷 2：`risk_level` 与 `status` 语义重叠（与缺陷 1 同源）。**
出现 `risk_level=low` + `status=review` + `review_reasons=[]` 的组合
（`AX-20260910-81C7D0`、`AX-20260911-BABB48`），即**无复核理由却要求复核**。
按上面的根因，这不是 `status` 单独的问题，而是 `review_required` 被大模型自由裁量后的必然表现：
`status` 在 `graph.py:154` / `graph.py:423` 由 `review_required` 直接推导，
所以只要 `review_required` 不确定，`status` 就不确定。
**修好缺陷 1，本条自动消解。**
（该问题与「上一轮」遗留的第 6 条「人工确认后 risk_level 仍为 review」是同一类问题的两面。）

**缺陷 3（产品可用性，非代码 bug）：82% 转人工。**
9/11 的默认产出是「转人工复核」。从工程角度这是**正确的保守**，
但从产品角度，一个巡检系统 82% 不落地风险等级，可用性存疑。

阻塞点如何产生（已定位到代码）：`graph.py:191-209` 的 `check_detection_result` 节点，
**任何**置信度低于 `general_yolo_review_conf`（0.35，通用模型）或 `yolo_review_conf`
（0.5，标志模型）的检测，都会追加一条「有 N 个低置信度检测结果」→ 进而强制
`review_required=True` → `status=review`。
**所以只要检测置信度跨过 0.35，4 个任务就能自动脱离 review。**

#### 已实测：换用 medium 通用模型能解决多少？（`scripts/compare_general_models.py`）

现状：通用人车检测用的是 `models/yolo26n.pt`（**nano，5.5MB**），
而项目根目录躺着 `yolo26m.pt`（**medium，44MB**，正是 TT100K 模型的训练基座，当前未被使用）。
两个模型都是官方 COCO 80 类、目标 6 类完全一致，**可直接替换**。
用 15 张真实巡检图、同阈值 `conf=0.2`、`imgsz=640` 实测对比：

| 指标 | yolo26n（nano） | yolo26m（medium） |
|---|---|---|
| 检出总数 | 61 | **91**（+49%） |
| 有检出的图片数 | 7 / 15 | **11 / 15** |
| 平均置信度 | 0.5283 | 0.5309（**几乎持平**） |
| 最高置信度 | 0.9088 | **0.954** |
| 置信度 < 0.35 的检出数 | 22 | **25（反而增加）** |

> **2026-09-13 数据勘误（保留上表作为历史记录）**：上述 15 个文件包含内容重复别名。按 SHA-256 去重后实际为 10 张唯一图片；nano/medium 的检出总数为 35/47（约 +34%），有检出图片为 5/7，低于 0.35 的框为 12/11。样本为混合来源且无人工真值，不能据此宣称准确率或召回率提升。证据见 `outputs/general_model_comparison_unique_20260913.json`。

**按图看，收益和代价都具体**：

- ✅ **`IMG_9759`（路边停车区，即任务 `AX-20260911-1D4782`「5 个低置信度」）**：
  nano 5 检出 / **3 个低置信** → medium 5 检出 / **0 个低置信**，这条 review 理由**直接消失**。
- ✅ **`proxy-live-e2e`（东门一带）**：nano 4 检出 / 3 个低置信 → medium 4 检出 / **1 个**，明显减少。
- ✅ **4 张图 nano 完全漏检（0 检出），medium 能检出 5 / 5 / 5 / 1 个目标**：
  `dormitory-road-c49d63487609.jpg`、`tt100k-dormitory-road-*.jpg`（2 张）、`tt100k-10132-*.jpg`。
  **漏检比低置信度更严重**——安防巡检漏报的风险高于「报了但标待复核」。
- ❌ **宿舍人群图没改善**：nano 13 检出 / 5 低置信 → medium **17** 检出 / 5 低置信。
  **两个模型对同一张人群图给出 13 与 17 人，差约 30%**（都已超过聚集阈值 8，不影响判定，
  但说明模型选择会实质影响计数）。
- ❌ **`IMG_9769`（减速带）反而变差**：nano 1 检出 / 0 低置信 → medium 2 检出 / 1 低置信。
- ❌ **总低置信度 22 → 25**：因为检出变多，多出来的中低置信度检测同样计入。

> **2026-09-13 勘误**：该句是未去重文件口径。唯一图片口径为 12 → 11，方向是小幅改善；历史原句保留仅用于解释当时为何得出旧判断。

**结论（请不要简单理解成「换 medium 就好了」）**：
medium 补的是**召回率（修复漏检）**，**不是**置信度。
平均置信度几乎没动，低置信度总数反而略增。
因此正确做法是**换模型 + 配合调阈值，两者缺一不可**：

1. **换 `GENERAL_YOLO_MODEL_PATH` 为 `yolo26m.pt`** —— 主要为了消除那 4 张图的完全漏检。
   注意：`yolo26m.pt` 当前**不在 `models/` 目录**而是在项目根，
   建议移入 `models/` 并同步 `.dockerignore` / `docker-compose` 的模型挂载（否则容器里取不到）。
   两份权重都是 `*.pt`、已被 gitignore，**不会进版本库，需在部署时单独准备**。
2. **下调 `general_yolo_review_conf`（当前 0.35）** —— 因为换模型并不能把低置信度数量降下来，
   光靠换模型解决不了 4 个任务里的多数。这个阈值需要**基于实测分布重新标定**，
   而不是拍脑袋。建议先跑 `scripts/compare_general_models.py` 拿到分布再定。
3. 其他可选方向：允许「单帧 + 图片质量合格 + 高置信度」直接出结论；
   把「人员聚集」改成必须视频输入的子任务（单帧本就无法定性）。

**缺陷 4：图片质量护栏会误判「模糊」，且误判会短路整条链路。**

护栏实现在 `backend/app/tools/image_quality.py:44`：
`blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()`，
`blurred = blur_score < settings.blur_threshold`（默认 **80.0**）。
**危害**：`graph.py:522-526` 的 `_route_quality` 在质量不过关时直接路由到 `review` 节点，
**跳过 `detect`** —— 检测与大模型分析完全不执行。
任务 `AX-20260911-B91639` 就是这样：`detections=0`、`analysis_mode=manual_review_guardrail`，
一个字的风险分析都没做，直接被判「图片可能模糊 + 无法判定 + 转人工」。

#### 补充：全链路「短路点」清单（2026-09-12 逐条核对源码得出）

上一节只说了一个短路点，**实际有且仅有两个，且都在 `detect` 之前**。
把真实拓扑摆出来，避免接手方误判「低置信度会跳过分析」：

```
START → validate_input
          ├─ [短路点 1] review → manual_review ─┐
          └─ quality → check_image_quality      │
                 ├─ [短路点 2] review → manual_review ─┤
                 └─ detect → detect_traffic_signs       │
                        └─ check_detection_result       │   ← 低置信度只在这里「加理由」，
                             └─ retrieve_knowledge      │      不短路，分析照常跑到底
                                  └─ evaluate_risk      │
                                       └─ generate_recommendations
                                            → generate_report → save_result → END
        manual_review ────────────────────────────────────→ generate_report（同上）
```

- **短路点 1 = `_route_validation`（`graph.py:518-520`）**：`validate_input`（`159-168`）
  在**地点为空**或**图片文件不存在**时置 `review_required=True` → 直接跳 `manual_review`，
  连质量检查都不做。触发条件窄（属于输入不合法），但性质上同样是「不分析就出结论」，
  而且走的是 `manual_review` 而不是 `handle_error`。
- **短路点 2 = `_route_quality`（`graph.py:522-526`）**：即上面说的质量护栏，**本轮缺陷 4 的主角**。
- **关键澄清：`check_detection_result` → `retrieve_knowledge` 是「无条件边」（`graph.py:85`）**，
  所以低置信度理由只影响**最终 `status`**（`graph.py:154` / `:423`），
  **不会跳过检索与大模型分析**。缺陷 3 的「转人工」是「分析了但拒绝自动定级」，
  与缺陷 4 的「压根没分析」是**两种不同性质的问题，不要混为一谈**。

**根因：这个指标量的是「画面里有多少高频纹理」，不是「对焦准不准」。** 三条实测证据：

1. **可视对照（决定性）**：把被判「模糊」的 `IMG_9794` 与「通过」的 `IMG_9759`
   做**同分辨率、同坐标的 1:1 裁切**对比（两张都是 3072×4096）——
   `IMG_9794` 的招牌字边缘**清晰锐利**，但整块是**纯平蓝色**（低纹理）；
   `IMG_9759` 那一块是**树叶**，每片叶子边缘都是高频细节（高纹理）。
   **差距来自纹理密度，不是清晰度。**
2. **分辨率归一化**：全部缩到长边 1024 后再算，`IMG_9794` 从 64.7 → **1010.3（涨 15.6 倍）**，
   `IMG_9769` 从 264.6 → **4060.6（涨 15.3 倍）**。说明该指标**对图像尺寸极度敏感**，
   未归一化的绝对阈值本身就不成立。
3. **模糊阶梯标定**：对最清晰的 `IMG_9759` 逐级加高斯模糊，
   `sigma=1.0 → 134.6`、`sigma=1.5 → 31.9` 才跨过阈值 80。
   即**阈值 80 对应的实际模糊程度约为 sigma≈1.2**，而 `IMG_9794` 的 64.7 并非失焦所致。

**判定结论**：`IMG_9794` 归一化得分 1010.3 **落在「通过」组区间（622.1~4060.6）之内**
→ 确认是尺度/纹理导致的**误判**。
另一张被判模糊的 `tt100k-10132`（归一化 152.6）**低于**该区间 → 可能是真的偏软，
**不要一刀切说阈值太严**。

**为什么这对本项目特别重要**：校园巡检画面大量是墙面、水泥路面、天空、平面标志牌——
**全是低纹理场景**，正好命中这个误判模式。

**修复建议**（按性价比排序）：

1. **先归一化再判定**（改动最小、收益最直接）：把图缩到固定长边（如 1024）后
   再算 Laplacian 方差，并重新标定阈值。**注意阈值必须重新标定**，
   因为归一化后分数整体抬高（实测同一批图抬高 1~15 倍）。
2. **换用纹理无关的清晰度指标**：例如测量强边缘的 **10%–90% 上升宽度**
   （对焦正确时约 1–3 像素，失焦时随 sigma 线性变宽），该指标不受纹理密度影响。
3. **降级处理而非短路**：即使判定质量偏低，也应**继续跑检测**，
   只把「图片可能模糊」作为一条复核理由附加，而不是跳过 detect。
   当前的短路设计把一个「可分析但需谨慎」的场景变成了「完全没分析」。
4. 新增的诊断工具 `scripts/check_image_quality.py` 已可直接复跑
   （输出全图 / 归一化 / 分块最大 / 分块中位四个分数，并自动指出归一化得分是否落在通过组区间内），
   用于重新标定阈值。

### F. 本轮新增 / 修改文件

| 文件 | 类型 | 说明 |
|---|---|---|
| `scripts/rerun_all_inspections.py` | 新增 | 批量重跑 + 前后快照对比 |
| `scripts/verify_knowledge_recall.py` | 新增 | 按真实查询格式做召回审计 |
| `scripts/check_risk_determinism.py` | 新增 | 同一任务连跑 N 次，量化判定链路确定性（缺陷复现 + 修复后回归） |
| `scripts/compare_general_models.py` | 新增 | 对比 nano/medium 通用模型在真实巡检图上的检出数与置信度分布 |
| `scripts/check_image_quality.py` | 新增 | 诊断图片质量护栏：全图/归一化/分块多口径打分，辅助重新标定 blur_threshold |
| `outputs/crops/side_by_side.png` | 运行产物 | 误判举证用 1:1 对照裁切图（已被 gitignore，需要时可重新生成） |
| `knowledge/校园交通安全管理实践（学校公开材料）.md` | 新增 | 第 5 份知识文档，21 块 |
| `.gitignore` | 修改 | 补 5 条忽略规则 |
| `docs/HANDOFF.md` | 修改 | 本小节 |
| `.workbuddy/memory/2026-09-11.md` | 修改 | 本轮工作日志 |
| `outputs/rerun_result*.json` / `*.log` | 运行产物 | 已被 gitignore，不进版本库 |

### G. 接手方须知

- **开工第一条消息直接用 `docs/CODEX_KICKOFF_PROMPT.md` 里的提示词**（2026-09-12 新增）。
  它把「读哪些文档 / 环境事实 / 跑哪几条只读命令核对 / 产出什么理解报告 / 铁律」串成一轮，
  目的是让接手方**先建立准确现状认知再动手**，并防止它踩已踩过的坑（Python 解释器、CWD、
  误删被脚本引用的文件、往生产库传演示文档）。把它原样粘给 Codex 即可。
- 后端必须**以 `backend/` 为 CWD** 启动，否则 `sqlite:///./data/campus_safety.db`、
  `./data/qdrant`、`../uploads` 这些相对路径都会指错地方。
- **Python 解释器用 conda 环境的 `yolo_change`**（完整路径见上方「项目速览」），
  Git Bash 里直接敲 `python` 会解析到没装 pytest 的托管 Python 3.13。
- 两个新脚本都假设后端已跑在 `127.0.0.1:8000`，直接 `python scripts/xxx.py` 即可。
- **本机 Docker 守护进程未启动**（CLI 是装了的，v29.6.1），
  `scripts/docker-runtime-acceptance.ps1` 仍未执行，留给 Codex（先起 Docker Desktop）。
- ~~未处理遗留：`uploads/knowledge/` 下 4 个孤儿文件 `campus-inspection-rules-*.md`（已解除 DB 引用，可删）；
  `knowledge/校园交通巡检示例规范.md` 仍是演示材料（用户未决定是否删除）。~~
  → **两项均已于本轮处理完毕，见 I 节。**

### H. 交接前健康体检结果（2026-09-11 深夜，全绿）

| 检查项 | 结果 |
|---|---|
| 后端测试套件 | **36 passed / 17.71s**（`cd backend && yolo_change 解释器 -m pytest -q`） |
| 后端健康 `/api/v1/health` | `ok`；db `ok`、qdrant `embedded`、双 YOLO 均已 loaded |
| 知识库 | **5 份文档 / 63 块**，全部 `status=ready`（演示文档移除后） |
| `uploads/knowledge/` | **5 个文件 ↔ 5 份线上文档，一一对应，零孤儿**（本轮清理后） |
| Dashboard 真实模式 | `total_tasks=11`、`review_required=10`、`risk_counts={low:2, medium:1, review:8}`——与重跑后的最新库内状态一致 |
| git 工作区 | 干净，零未跟踪（三个提交：`c464cc4` → `6cbaf2e` → `3dd8d74`） |

> 说明：Dashboard 的 `risk_counts` 是 `{low:2, medium:1, review:8}`，
> 比上面 D 节表格里的第二轮结果（`{review:9, low:2}`）少 1 个 review、多 1 个 medium，
> 差异来自随后做的确定性复测——`AX-20260911-12AF90` 在复测中被重新执行为 `medium`。
> 这是**同一任务的又一次结果变化**，正好再次印证缺陷 1。

### I. 知识库收尾清理（两项历史遗留，用户授权直接决策执行）

**决策 ①：`knowledge/校园交通巡检示例规范.md` —— 保留源文件，从线上知识库移除。**

侦察中推翻了「纯演示材料可删」的初始判断，依据是**引用关系**：

| 引用位置 | 用途 | 后果 |
|---|---|---|
| `scripts/docker-runtime-acceptance.ps1:174` | 以该路径做 multipart 上传到 **Docker 栈 `127.0.0.1:8080`** | 删源文件 → 脚本 `Get-Item` 直接抛错 |
| `scripts/final-acceptance.ps1:127` | `e2e_smoke.py --knowledge <路径>`，配合 `DATABASE_URL=sqlite:///./data/final-acceptance.db` | 删源文件 → 端到端验收失败 |

两个脚本**都往独立库上传**（一个 Docker MySQL、一个 `final-acceptance.db`），
**不会回灌本地生产库**，所以「源文件留、线上条目删」是干净且持久的方案。

执行：
```
DELETE /api/v1/knowledge/documents/93487206-8b2a-4667-9d42-b610901ad869
→ {"deleted":true,"removed_chunks":1,"file_removed":true}
```
该接口（`router.py:573-611`）会同时清 向量分块 + DB 记录 + **已上传的源文件**，
所以 `uploads/knowledge/校园交通巡检示例规范-1d047aba57ee.md` 也被一并清掉了。

移除理由：文档自述「不是国家标准、法律法规或学校正式制度」，
留在线上库的唯一风险是**报告把它当作「知识依据」引用**（制度性文本的假象）；
而它在 16 查询 × top5 = 80 席中占 **0 席**，检索价值为零。

**移除后回归验证（关键）**：

| 指标 | 移除前 | 移除后 |
|---|---|---|
| 零命中数 | 0/16 | **0/16** |
| 分数区间 | 0.2777 ~ 0.5558 | **0.2777 ~ 0.5558** |
| top5 席位分布 | 51 / 19 / 10 | **51 / 19 / 10** |

逐位一致 → **零退化**，实证了「它本就是 0 席」的判断。

**决策 ②：删除 `uploads/knowledge/` 下 4 个孤儿文件。**

先做 MD5 取证，结果是**6 个文件同哈希** `66f39d3d6c0f315448c888c65bab88fc`：

```
campus-inspection-rules-2081232dc8ec.md   ┐
campus-inspection-rules-6410e9d76501.md   ├ 4 个孤儿（不在任何 DB 记录里）
campus-inspection-rules-c49a218382bc.md   │
campus-inspection-rules-c9317ff1cfd2.md   ┘
校园交通巡检示例规范-1d047aba57ee.md        ← 线上库引用（已随 DELETE 清除）
knowledge/校园交通巡检示例规范.md           ← 源文件（保留）
```

即 4 个孤儿**与保留中的源文件逐字节相同**，删除**零信息损失**、随时可从源文件复原。
交叉核验 `backend/data/campus_safety.db` 的 `knowledge_documents.stored_path`，
确认 4 个 `campus-inspection-rules-*` 均无引用（其余 5 份文档的 `stored_path` 一一命中现存文件）。

**清理后状态**：`uploads/knowledge/` 5 个文件 ↔ 线上 5 份文档，**一一对应，零孤儿；零孤儿零多余。**

> 🔎 **注意一个会误导人的数字**：`scripts/check_knowledge_chunks.py` 扫描的是**源目录 `knowledge/*.md`**
> （现在仍是 **6 个文件 → 64 块**，因为示例规范源文件保留作验收夹具），
> 而**线上库是 5 份 / 63 块**。`64 − 63 = 1` 就是那份**未入库**的示例规范。
> 别看到 64 就以为线上库没删干净。

> ⚠️ **教训（后续一律照此办理）**：判断一个文件能不能删，
> **必须先 grep 全仓路径引用 + 查 DB 引用，再看内容是否可复原**，三件事缺一不可。
> 本次若只按「它是演示材料」就删源文件，会直接打断 `final-acceptance.ps1` 整条验收链。
> 另一个反复出现的坑：`.gitignore` 对**已在索引中**的文件不生效，补规则后需 `git rm -r --cached .` 再重加。

---

## 前一轮：WorkBuddy → 下一个接手方（2026-09-11 晚）

**本轮主题**：① 前端视觉风格演进（仅视觉，业务功能未动）② 补充校园知识库

### A. 前端视觉风格演进（历史脉络，避免重复走弯路）

用户对页面的硬约束是「**功能不变，只改视觉**」，且不满意时倾向**整体换风格**而不是小步微调。
到目前为止共四代：

| 代 | 风格 | 产出方 | 结果 |
|---|---|---|---|
| v1 | 浅色企业级控制台 | WorkBuddy | **用户否决**，理由是布局呆板、卡片不精致、缺科技感 |
| v2 | 深色玻璃指挥中心（画布 `#0b0e14`、玻璃卡、品牌色 `#8b93f8`） | WorkBuddy | 用户接受方向，随后继续调整 |
| v3 | 普通数据卡工作台 | 第三方 | 被替换 |
| **v4** | **高密度 GIS 校园安防指挥台** | 第三方 | **当前生效**（2026-09-07 用户选定） |

WorkBuddy 实际改过的文件（如需回溯可用）：

- `frontend/src/styles.css`（两次整体重写）
- `frontend/DESIGN.md`（两次重写，**现已被迭代到 v4，WorkBuddy 写的版本已废弃**）
- `frontend/src/pages/NewInspectionPage.vue`（仅 1 处：`style="width:100%"` → `class="block-select"`）
- `frontend/index.html`（`theme-color`）

**接手提示**：`DESIGN.md` 现在是 v4 规范（229 行），改任何样式前先读它。

### B. 知识库补充（本轮主要交付）

改造前知识库只有 1 份项目内示例 + 5 份重复的 `DEMO_GUIDE.md`，
巡检报告引用的「知识依据」其实是演示文本，不是真实依据。本轮补齐 4 份**可溯源**的真实文档：

| 文件（`knowledge/`） | 分块 | 作用 |
|---|---|---|
| `校园交通安全巡检判定规范.md` | 13 | 按 8 个区域类型分节：典型风险 / 判定要点 / 整改要求 / 法定依据 |
| `校园交通隐患整改建议库.md` | 12 | 按 10 类隐患给标准化整改模板：措施 / 责任方向 / 复查要求 / 依据 |
| `校园交通与消防安全法规依据摘录.md` | 10 | 14 条法规原文摘录，每条标注法规全称与条款号 |
| `交通标志类别释义（TT100K 45 类）.md` | 7 | 把模型输出的 `p11`/`w57`/`pl50` 翻译成中文标志名与现场含义 |

**写这些文档时踩过的坑（后来者别再踩）**：

1. **绝不编造校规**。学校官网没有公开的交通/保卫制度文件，所以依据只用国家法律、行政法规、
   部门规章与强制性国家标准，每条都标注法规全称与条款号。
   已核实的来源：《消防法》第二十八条、第六十条；《高等学校消防安全管理规定》第十三、十四、十六、
    十八、二十九、三十条；《企业事业单位内部治安保卫条例》第八、十一、十三条；
   《道路交通安全法》第五十七、五十八条；GB 17761-2024；GB 5768.2-2022。
2. **哈希嵌入是字面匹配**。`EMBEDDING_PROVIDER=hash` 用中文字符 n-gram + sha256 打分，
   靠字面重合度。所以每份文档都显式写出检索词，例如
   「检索关键词：消防通道 消防车通道 疏散通道 校园交通安全巡检」。
3. **表格会被切碎**。`chunk_text()` 用固定 500 字符窗口、重叠 80，边界优先落在换行或句号。
   Markdown 表格一定会被从中间切开，后面的分块丢掉表头，大模型拿到
   「| `pl50` | 限制速度…… |」这种残块根本看不懂。
   **结论：知识文档一律用条目式**（`- \`pl50\` 限制速度 50 km/h：……`），不要用表格。
   这一条是实测出来的：TT100K 文档最初用表格，61 个分块里有 4 个是无表头残块，改条目式后消失。
4. **新增自检工具** `scripts/check_knowledge_chunks.py`：入库前离线复现同一套分块逻辑，
   报告分块数、表格残块、过短分块。以后加知识文档，改完跑一次即可。
5. **分块器不认识 `##` 章节边界，每个分块必然横跨两节。**
   `chunk_text()` 是对整篇文档滑动的固定窗口，没有按标题切分的能力。
   实测结构是「**上一节的正文 + 下一节的标题**」：

   ```
   [校门口的 典型风险/判定要点/整改要求 全文]
   ---
   ## 三、停车场（含路边停车区）      <-- 标题属于下一节
   检索关键词：停车场 路边停车区 ...
   ```

   后果：正文与标题**错位**。检索命中一个片段时，片段里的章节标题可能指向别的区域，
   大模型有把「校门口」的规则套到「停车场」上的风险。
   **对策：每条判定要点自带区域名称**（如「校门口检出…」「宿舍区检出…」），
   并在文档开头写明「请以条文中标注的区域为准，不要依据片段中的章节标题归属风险」。
   注意：缩短章节**解决不了**这个问题，因为滑窗是全局的、会漂移。
6. **按「隐患类型／业务分类」组织的文档，如果不写检索词就基本检不到。**
   系统的查询词固定是「区域类型 + 地点 + YOLO 类别 + 校园交通安全巡检」，
   而《整改建议库》原本按「消防车通道被占用」「人员聚集」这类隐患名组织，
   与该查询词几乎没有重合面 —— 改造前 16 个真实查询里它只进了 4 次 top5，基本等于摆设。
   **给每个条目补上 `**检索关键词**：` 行（含区域名与类别代号）后，召回提升到 43 次。**

**入库与验证结果**（预览库 `backend/data/campus_safety.db` + `backend/data/qdrant`）：

- 5 份文档全部上传成功，`status=ready`，分块数与离线自检**完全一致**。
- **检索审计（16 个真实查询，覆盖全部 8 个区域类型）**：

  | 指标 | 改进前 | 改进后 |
  |---|---|---|
  | 零命中查询 | 0 / 16 | 0 / 16 |
  | 演示文档进 top5 | 1 / 16 | **0 / 16** |
  | top5 命中来源 | 真实 79 + 演示 1 | **真实 80** |
  | 《判定规范》占 top5 席位 | 62 | 34 |
  | 《整改建议库》占 top5 席位 | 4 | 43 |
  | 分数区间 | 0.133 – 0.488 | 0.149 – 0.533 |

  **结论：演示文档（`DEMO_GUIDE.md`）的实际污染远比预期小** —— 5 份副本从未进过 top5，
  唯一进过的是《示例规范》1 次且排第 5。所以「清理演示文档」是整洁性需求，不是正确性需求。
- **端到端验证 1**：重跑 `AX-20260911-0B6FF9`（校园主干道 / 禁鸣标志路段 / `p11` 0.94）。
  结果 `completed`、`low`、风险分 15、`analysis_mode=llm`。模型把 `p11` 正确翻译为「禁止鸣喇叭」，
  证据栏引用的正是新写的带区域前缀条文：
  「知识片段：校园主干道检出 p11（禁止鸣喇叭）标志，说明该点位为禁鸣区；
  若同帧检出车辆密集通行，应核查是否存在鸣笛扰民问题」。
  《标志类别释义》被召回（0.3264）用于代号翻译。
  **改造前该任务是 review 状态，现在能给出有依据的确定结论。**
- **端到端验证 2**：重跑 `AX-20260911-67131D`（消防通道 / `IMG_9805`，无检出目标）。
  结果 `review`。不确定性说明正确套用了文档纪律「不得仅凭单张图片断言标志缺失或通道畅通」；
  整改建议直接复用《整改建议库》模板：「立即移除占道车辆与杂物，恢复通道全宽畅通」
  「在通道地面施划黄色网格禁停线，两端及中段设置警示标志」
  「对反复占用的点位加装硬质隔离柱、U 型护栏或违停抓拍设备」。
  知识依据命中《判定规范》（0.3915 / 0.3756）、**《法规依据摘录》（0.334）**、《整改建议库》（0.3837）。
- 复跑自检：`python scripts/check_knowledge_chunks.py` → **43 个分块，0 个需要关注**。
- 后端测试：**36 passed**（含新增的删除接口测试）。

> **观察（未处理，供参考）**：哈希嵌入是**带符号**的（`sign = ±1` 取决于 sha256 摘要奇偶），
> 向量分量会相互抵消，因此排序带噪声。实测一个「校园主干道」查询里，
> 排第 1 的是《判定规范》中宿舍区的整改要求片段（因含「限速」「校园交通」等词）。
> 这不影响最终结论正确性（大模型从 5 个片段里挑得出正确内容），
> 但**不要指望靠调措辞把排序调到完美**。若将来要提升排序质量，正解是把
> `EMBEDDING_PROVIDER` 换成 `openai_compatible` 接一个真正的语义嵌入模型。

### B2. 新增知识文档删除接口（本轮新增的唯一后端接口）

**背景**：知识库原先只能新增不能删除，没有任何接口可以移除文档。
后果有两个：① 写错的文档永久留在库里参与召回；② Claude 交接文档里记的
「5 份重复的 `DEMO_GUIDE.md`」根本无法清理。
另外向量库是 **embedded 模式**（`qdrant_path`），目录被后端进程独占，
**无法从外部脚本改写**，所以删除必须由后端进程提供。

**改动**：

- `backend/app/services/rag.py`：新增 `KnowledgeBaseService.delete_document(document_id)`，
  用 `Filter + FieldCondition(document_id)` 统计并删除该文档的全部分块，返回删除数量。
- `backend/app/api/router.py`：新增 `DELETE /api/v1/knowledge/documents/{document_id}`，
  同时清理向量库分块、数据库记录与已上传源文件；文档不存在返回 404，
  向量库异常返回 503。源文件删除失败不阻断接口（在响应里返回 `file_removed=false`）。
- `backend/tests/test_knowledge_api.py`：新增
  `test_delete_knowledge_removes_chunks_and_stops_matching`，断言删除后检索不再命中该文档、重复删除返回 404。

这是**纯新增**接口，未改动任何既有接口的语义。前端 `KnowledgePage.vue` 尚未接入删除按钮，
如需在页面上提供删除能力，需要另外加 UI（本轮未做）。

### B3. 本轮已执行的运维操作（接手方注意）

1. **重启了 8000 端口后端**（原进程 PID 33004 被 `Stop-Process -Force` 终止）。
   新进程仍按原命令启动：工作目录 `backend/`，
   `<LOCAL_PATH> -m uvicorn app.main:app --host 127.0.0.1 --port 8000`，
   无 `--reload`、无环境变量覆盖，日志仍写 `outputs/preview-backend.stdout.log` / `.stderr.log`。
   **重启原因：新增的删除接口需要重新加载代码。**
2. **替换了 2 份知识文档**：先删旧版（各移除 11 / 12 块），再上传改进版（12 / 13 块）。
   预览库中不存在同名重复项。
3. **重新执行了 2 个巡检任务**（`AX-20260911-0B6FF9`、`AX-20260911-67131D`），
   风险结论已按新知识库刷新。
4. 5173 前端进程**未动**。
5. **按用户要求清空了 5 份重复的 `DEMO_GUIDE.md`**（用新增的删除接口，各移除 2 块，源文件同步删除）。
   清理后线上知识库为 **5 份文档 / 43 个分块**，`DEMO_GUIDE` 记录 0 条。

### C. 本轮遗留（需用户决定）

1. ~~5 份重复的 `DEMO_GUIDE.md` 仍在预览库中~~ → **已于本轮按用户要求删除完毕**。
   5 份各移除 2 块，源文件同步删除，线上库 `DEMO_GUIDE` 记录为 0。
   删除后复跑检索审计：16 个查询仍 0 零命中、top5 全部来自真实文档（80/80）、
   分数区间 0.149–0.533，最低分仍是阈值（0.08）的 1.9 倍。端到端任务照常出结论。
   **注意**：`docs/DEMO_GUIDE.md`（源文档，用于 E2E 演示）与
   `uploads-e2e*/knowledge/`、`uploads-e2e2/knowledge/` 下的副本**未动** ——
   它们是独立测试目录的产物，不在线上知识库中，删除它们会破坏 E2E 脚本。
2. ~~`knowledge/校园交通巡检示例规范.md` 仍是演示材料（含「不是国家标准、法律法规或学校正式制度」声明），
   实测只进过 top5 一次且排第 5。保留或删除由用户决定。~~
   → **已于本轮处理：源文件保留、线上库移除。见上方「最新一轮」I 节。**
3. 前端 `KnowledgePage.vue` **没有接入删除按钮**，删除能力目前只能通过 API 使用。
4. 前端视觉改造**未经用户最终验收**，用户可能还会要求换风格。
5. ~~`uploads/knowledge/` 下残留 4 个孤儿文件 `campus-inspection-rules-*.md`
   （各 1169 字节，2026-09-08 上传，**已不被数据库引用**，属早期入库遗留）。
   不影响检索，可安全删除；本轮未动。~~
   → **已于本轮删除。见上方「最新一轮」I 节。**

### D. 本节新增/修改文件

新增：

- `knowledge/校园交通安全巡检判定规范.md`（13 块）
- `knowledge/校园交通隐患整改建议库.md`（12 块）
- `knowledge/校园交通与消防安全法规依据摘录.md`（10 块）
- `knowledge/交通标志类别释义（TT100K 45 类）.md`（7 块）
- `scripts/check_knowledge_chunks.py`（分块自检工具）

修改：

- `backend/app/services/rag.py`（新增 `delete_document`）
- `backend/app/api/router.py`（新增 `DELETE /knowledge/documents/{document_id}`）
- `backend/tests/test_knowledge_api.py`（新增删除接口测试）
- `docs/HANDOFF.md`（本文件）

> 说明：`knowledge/` 下的 4 份文档在写入后上传入库，但**上传的副本存放在
> `backend/uploads/knowledge/`（已被 gitignore 忽略）**，源文件以 `knowledge/` 为准。

> **以下为上一轮（Claude → Codex）原文，未作改动。**
> 其「当前运行环境状态」（原第 5 节）与「待办与建议」（原第 6 节）**仍然有效**，
> 本轮没有重跑 Docker、没有提交 git，那几条待办状态不变。

---

## 上一轮：Claude → Codex（2026-09-11 白天）

**日期：** 2026-09-11
**交接方：** Claude（Claude Code）
**接手方：** Codex
**项目路径：** `<LOCAL_PATH>`

## 0. 一句话状态

在“不恢复训练、不改变既有 API 语义”的前提下，本轮修复了 5 类问题：视频跟踪污染图片推理、Docker 探针版本写死、Nginx 上传上限、Dashboard 真实模式假数据、知识检索失败被演示数据掩盖，并修正了相关文档。后端 35 项测试、前端类型检查与构建、项目原版浏览器 E2E（9/9）均通过。**Docker 运行态没有重跑，全部改动都没有提交 git（整个目录在父仓库里是未跟踪状态）。**

## 1. 本轮范围

用户要求：先通读项目，再按发现的问题直接修改，最后写这份交接文档，方便 Codex 接力。

没做的事：

- 没有恢复或改动 YOLO26 训练（状态仍为 `completed_partial_by_user`）。
- 没有删除、重命名或改变任何已有接口的语义；只新增了字段、一个接口和一个配置项。
- 没有提交 git。Codex 启动的 8000 端口后端在用户要求验收后才按原命令重启为新代码（见第 5 节）。

## 2. 修改清单（按严重程度）

### 2.1 视频跟踪污染图片推理（严重，已修复）

- **现象：** 同一后端进程里只要跑过一次视频分析，之后的图片巡检人员/车辆检测就会被 ByteTrack 过滤。用正式 `yolo26n.pt` 和宿舍区照片实测：人员 **13 → 6**，而人员聚集阈值是 8，因此“人员聚集候选”会漏报。
- **根因：** `VideoAnalyticsTool` 原先对图片推理用的同一个模型对象调用 `model.track(persist=True)`。Ultralytics 8.4.138 的 `register_tracker()` 把跟踪回调挂在模型的 `callbacks` 上，且从不移除；预测器与模型共享这个回调字典，所以之后每次 `predict()` 都会经过残留的跟踪器（见 `site-packages/ultralytics/trackers/track.py` 与 `engine/model.py` 的 `track()`）。另外视频路径不持有 `_predict_lock`，图片与视频并发时会共用一个非线程安全的预测器。
- **修改：**
  - `backend/app/tools/yolo.py`：新增 `TrafficSignDetectionTool.create_general_model()`，每次返回一个新的、不共享的通用模型实例；`get_general_model()` 改为调用它并缓存为图片单例（行为不变）。
  - `backend/app/tools/video_analytics.py`：新增 `_tracking_model()`，在 `self._lock` 内懒加载视频专用实例并复用；新增 `model_loaded`、`load_count`。
  - `backend/app/api/router.py`：`/health` 的 `general_yolo` 增加 `tracking_loaded`、`tracking_load_count`。
- **约束（请保持）：** 视频跟踪永远不要调用 `get_general_model()`；需要新的跟踪用途时也用 `create_general_model()`。

### 2.2 Docker 探针版本写死（高，已修复）

- **现象：** `app/docker_probe.py` 期望版本写死为 `0001_initial`，而迁移 head 已是 `0002_multimodel_vision`。容器启动会 `alembic upgrade head`，所以下次运行 `scripts/docker-runtime-acceptance.ps1` 必然在表结构探针（原第 160 行）失败，`final-acceptance.ps1` 也会随之失败。原单元测试插入的正是这个常量，所以测不出来。
- **修改：** `docker_probe.py` 新增 `alembic_config()` 与 `expected_revision()`，从 `backend/alembic` 读取 head；`inspect_database()` 增加可选参数 `expected`。`Config()` 故意不加载 `alembic.ini`，避免改写整个进程的日志配置。
- **测试：** `tests/test_docker_contract.py` 新增 `test_docker_schema_probe_accepts_database_migrated_to_head`，对临时 SQLite 真实执行 `alembic upgrade head` 后再跑探针。以后新增迁移不需要再改探针。

### 2.3 Nginx 上传上限（中，已修复）

- **现象：** `frontend/nginx.conf` 的 `client_max_body_size 20m`，但页面和后端允许 100 MB 视频。Docker 部署下 20–100 MB 的视频会被 Nginx 返回 413。
- **修改：** 调到 `110m`（100 MB 加 multipart 开销）；各接口仍由后端各自限制（图片/知识 20 MB，视频 100 MB）。

### 2.4 Dashboard 真实模式假数据（中，已修复）

前三轮视觉验收都在空库上做，一直处于演示态势，所以没暴露。有真实任务后仍存在：

| 位置 | 原行为 | 现行为 |
|---|---|---|
| 近期任务置信度 | 恒为 78%（接口没返回检测，前端落到默认值 `.78`） | 取任务 `max_confidence`；无检测显示“—” |
| 今日巡检 | 显示历史总数，变化文本写死“+12%” | 取 `today_tasks`，变化为与昨日的差值 |
| 三条火花线 | 写死数组 | 取 `daily_trend` 近 7 日 |
| 在线摄像头 | 写死“12 / 14 路，在线率 86%” | 真实模式显示“— / 摄像头接口未接入”，不画火花线 |
| 地图风险点、摄像头点 | 永远显示 5 个演示事件和 6 个摄像头 | 只在演示态势显示；真实模式两个图层置灰 |
| “重点区域”图层 | 可勾选但没有任何作用 | 始终置灰，提示未接入 |
| 处置状态 | 按行号生成（待处置/待审核/已忽略） | 取任务 `status` |
| 巡检进度 | 按行号给 68/46/22% | 流程已结束 100%、未开始 0%、执行中“—” |
| 风险等级 | `review` 显示成中风险，未研判显示成低风险 | 原值显示高/中/低/待复核（紫）/未研判（灰），筛选新增“仅待复核” |
| 负责人 | 空值显示“巡检组” | 显示“未填写” |
| 顶栏天气 | 写死“22°C 多云”（当晚实况为阴 21°C） | 高德实况天气，不可用时隐藏 |
| 复核角标 | 无数据时默认 5 | 只取接口 `review_required`，为 0 或不可用时不显示 |
| 演示 KPI | 未标注演示 | 变化文本以“演示 ·”开头，巡检任务面板加“演示数据”标记 |

涉及文件：

- 后端 `backend/app/api/router.py`：`task_to_dict()` 增加 `detection_count`、`max_confidence`；`/dashboard` 增加 `today_tasks`、`daily_trend`（`_daily_trend()` 在 Python 里按本地自然日分桶，兼容 SQLite/MySQL 的朴素 UTC 时间）；新增 `GET /maps/weather`。
- 后端 `backend/app/services/amap.py`：新增 `weather(adcode)`，10 分钟进程内缓存。
- 后端 `backend/app/config.py`：新增 `app_timezone`（默认 `Asia/Shanghai`，启动时校验）与 `display_timezone` 属性。
- 后端 `backend/requirements.txt`：新增 `tzdata>=2024.1`。
- 前端 `frontend/src/pages/DashboardPage.vue`（改动最大）、`components/AppLayout.vue`、`types.ts`、`config/campus.ts`（新增 `adcode: '510116'`，双流区）、`styles.css`（待复核/未研判样式、`is-disabled` 图层、`panel-actions`）。
- 规则已写入 `frontend/DESIGN.md` 第 3、5、6 节。**以后改 Dashboard 请先看这些规则，不要把写死数值加回去。**

版本兼容：新前端遇到旧后端（例如旧容器镜像）时，缺失的今日/趋势字段显示“—”和“后端未提供趋势数据”，天气隐藏，不会用 0 冒充。

### 2.5 知识检索失败被演示结果掩盖（低，已修复）

`frontend/src/pages/KnowledgePage.vue`：已有真实文档时检索失败会弹出错误并清空结果，且不再把整页切成“演示”；只有离线预览（`isDemo`）才回退到带标记的演示命中。

### 2.6 文档修正

- `README.md`、`training/README.md`：原评估命令把 `models/yolo26-tt100k-best.pt` 传给 `evaluate_yolo26.py`，但脚本只接受训练目录里的 `best.pt`，且默认 `--imgsz 960` 与 baseline 的 640 不一致，命令必然失败。已改为训练目录路径并说明尺寸规则。
- `docs/DATABASE.md`、`docs/COMPETITION_ALIGNMENT.md`：补上 `0002_multimodel_vision`。
- `docs/API.md`：补上原本缺失的 `/maps/*`、`/video-analytics` 与新增字段说明。
- `.env.example`：新增 `APP_TIMEZONE=Asia/Shanghai`（Compose 的 backend 会读取它）。
- `design-qa.md`：新增 Pass 4，如实记录真实模式问题及修复。
- `docs/CHANGELOG.md`、`docs/TEST_REPORT.md` 第 17 节：本轮变更与实测结果。

## 3. 接口与配置契约变化（全部为新增）

| 类型 | 名称 | 说明 |
|---|---|---|
| 接口 | `GET /api/v1/maps/weather?adcode=510116` | 永远 HTTP 200：可用时 `{"available": true, weather, temperature, report_time, ...}`；未配置 Key 或供应商失败时 `{"available": false, "message": ...}`。这样设计是为了避免顶栏在每个页面制造 503 控制台错误，请保持 |
| 字段 | 任务对象 `detection_count`、`max_confidence` | 列表、仪表盘、详情都有；无检测时 `max_confidence=null` |
| 字段 | `/dashboard` 的 `today_tasks`、`daily_trend` | 固定 7 项，`review_required` 指当天创建且仍待复核的任务数 |
| 字段 | `/health` 的 `general_yolo.tracking_loaded`、`tracking_load_count` | 视频专用模型状态 |
| 配置 | `APP_TIMEZONE` | IANA 时区名，非法值启动即报错 |
| 依赖 | `tzdata` | Windows 与精简容器解析时区需要 |

## 4. 验证结果（详见 `docs/TEST_REPORT.md` 第 17 节）

- 后端：`python -m pytest` **35 passed，0 failed**（新增 8 项）。
- 前端：`vue-tsc -b && vite build` 通过。
- 真实权重：修复前 13 → 6 人，修复后 13 → 13 人且逐项一致；探针用 head 通过、用旧常量失败。
- 浏览器 E2E：项目原版 `frontend/scripts/e2e_existing_features.py` **9/9 通过**，0 页面/控制台/网络错误，DeepSeek `llm`，高德可用。本机没有 Python Playwright，本轮在临时 venv 装了 Playwright 1.62，并用启动器让它调用系统 Chrome（`channel="chrome"`）；E2E 脚本本身没有改。
- 真实数据 Dashboard：视频之后的图片巡检仍为 13 人并触发聚集候选；KPI、置信度、状态、天气全部来自接口；演示标记 0 个；移动端 390px 无溢出。
- 证据目录：`frontend/output/playwright/claude-handoff-2026-09-11/`（已被 `.gitignore` 忽略）。Codex 之前 `standard-test/` 下的证据没有被覆盖。

复跑命令（在项目根目录）：

```powershell
Set-Location backend
<LOCAL_PATH> -m pytest -q
Set-Location ..\frontend
npm run build
```

## 5. 当前运行环境状态（接手先看）

1. **8000 端口后端已换成新代码。** 原进程由 Codex 会话启动（父进程 `codex-command-runner`）。用户要自己验收，所以 Claude 按原命令重启了它：工作目录 `backend/`，`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`，无 `--reload`、无环境变量覆盖，因此仍使用默认数据 `backend/data/campus_safety.db` 与 `backend/data/qdrant`。日志写到 `outputs/preview-backend.stdout.log` / `.stderr.log`。Codex 会话里原来那条后台命令会显示为已退出，这是预期现象。
2. **5173 端口 Vite 仍是 Codex 启动的那个进程**，已热更新到新前端，没有重启。
3. 手动验收素材：`outputs/manual-acceptance/dormitory-crowd-test.mp4`，是用宿舍区照片生成的 3 秒静止画面 MP4，只能验证人员聚集和“视频后图片不受影响”，不能证明逆行准确率。
4. **预览库里新增了 6 个真实照片巡检任务**（巡检人员“Claude 代上传”，都在待复核）。用户要求从 `校园照片/` 选图上传，地点名只描述画面内容并附文件名，没有编造具体楼名：
   - IMG_9781：`p11` 0.94。
   - IMG_9769：`w57` 0.86，外加 1 辆车。
   - IMG_9759：`w57` 0.86、`w57` 0.43，把限速 5 误识为 `pl50` 0.36，外加 5 辆车，因低置信度转复核。
   - 1F8ECA8A.png：11 人、1 辆车，触发人员聚集候选。
   - IMG_9805：未检出目标，按规则转复核。
   - IMG_9794：清晰度分数 64.7 低于阈值 80，被质量护栏拦下。这张照片肉眼看并不明显模糊，大面积墙面和天空会拉低拉普拉斯方差，阈值是否要按分辨率调整需要用户决定。

   各任务的现场说明是 Claude 写的，DeepSeek 结论里提到的“地面标线”等内容来自说明文字，不是模型识别到的。
5. **预览库知识库只有 5 份重复的 `DEMO_GUIDE.md`**：之前每次标准 E2E 都对预览库上传一次。因此这些任务引用的“知识依据”是演示说明，不是校园制度。建议上传 `knowledge/校园交通巡检示例规范.md` 或学校真实制度，并让 E2E 只跑独立数据库（本轮就是这样做的）。
   > ⚠️ **此条建议已过时（2026-09-11 深夜更新）**：真实制度文档已补齐 5 份，
   > 且《校园交通巡检示例规范》**已从线上库移除**（详见「最新一轮」I 节）。
   > 它现在只作为验收脚本的**输入夹具**保留在 `knowledge/`，**不要再上传到生产知识库**。
6. **`yolo_change` 环境多装了 `lap==0.5.13`。** 我读 Ultralytics 源码时导入了其跟踪模块，触发了 Ultralytics 的自动安装。它本来就在 `requirements.txt`（`lap>=0.5.12,<0.6`），所以现在 ByteTrack 不再依赖 `backend/.runtime/python-packages` 的回退。如需撤销：`pip uninstall lap`。
7. 本轮的临时验证环境（8010/5176 端口、临时数据库、`%TEMP%\cc-pwv` Playwright venv）已全部停止并删除；除第 4 条的 6 个任务外，没有写入项目的 `data/`、`uploads/`。
8. `frontend/dist/` 已按新代码重新构建（被 Git 忽略）。

## 6. 待办与建议（按优先级）

1. **看用户手动验收的反馈**：8000 后端已换成新代码，用户正在自己验收页面，有反馈先处理反馈。
2. **重跑 Docker 运行态验收**：后端镜像要重建（新增 `tzdata`、代码变更），前端镜像要重建（`nginx.conf`）。执行 `pwsh ./scripts/docker-runtime-acceptance.ps1`，预期探针通过、`expected_revision` 为 `0002_multimodel_vision`。
3. **纳入版本管理（需用户决定）**：`campus-safety-agent/` 整个目录在父仓库 `feat/agent-detection-api` 分支上是未跟踪状态，没有任何提交历史，建议先提交一个基线。注意 `.env`、`.env.amap`、`.env.proxy` 已被忽略，提交前再确认一次。
4. **巡检档案没有分页**：`InspectionsPage.vue` 只请求第一页（后端默认 `page_size=20`），筛选在前端做，页面没有分页控件，超过 20 条的历史任务在档案页看不到；侧栏的闭环率、状态分布也只基于这一页。建议改为服务端分页与筛选，统计改用接口汇总。
5. **地图标注未校准**：Dashboard 上的地标文字（图书馆、实验楼等）和门岗是按参考图写死的百分比坐标，叠在真实高德底图上位置对不上。建议用高德地理编码拿到真实经纬度，再按静态图的中心、缩放级别换算到像素；做不到之前，可以只在随包 GIS 备用图上显示。
6. **人工确认后风险等级仍是 `review`**：`/review` 支持 `risk_level`，但详情页“人工确认”没有让复核人选择最终等级，所以确认后的任务在列表和队列里仍显示“待复核”等级。需要产品决定：确认时是否必须选择最终等级。
7. 小问题：
   - `InspectionDetailPage.vue` 的报告链接写死 `/api/v1`，没有使用 `VITE_API_BASE_URL`。
   - 前端 `VisionEvent.status` 类型只有 `candidate | confirmed`，视频接口实际返回 `confirmed_by_video`/`confirmed_by_track`；目前视频结果不入库所以无影响，若将来持久化需要对齐。
   - `scripts/final-acceptance.ps1`、`run-local-preview.ps1` 写死了本机 Python 与训练目录路径。
   - Ruff 未安装，代码风格检查一直没执行。

## 7. 注意事项

- 训练已锁定，不要恢复训练或修改 `status.json`；报告中不得把 32/80 轮写成完整训练。
- Dashboard 规则见 `frontend/DESIGN.md` 第 6 节：没有接口支撑的数字只能显示“—/未接入”，演示内容必须带标记。
- 密钥只在 `.env`、`.env.amap`、`.env.proxy`，不要写进代码、日志、报告或前端。
- `GET /maps/weather` 在失败时返回 200 加 `available=false` 是有意设计，不要改成 503。
- OpenCV 写 VP8/WebM 时的 `tag 0x30385056/'VP80' is not supported` 警告早已存在，文件仍可正常播放。

## 8. 本轮变更文件清单

后端：

- `backend/app/tools/yolo.py`
- `backend/app/tools/video_analytics.py`
- `backend/app/docker_probe.py`
- `backend/app/api/router.py`
- `backend/app/services/amap.py`
- `backend/app/config.py`
- `backend/requirements.txt`
- `backend/tests/test_docker_contract.py`
- `backend/tests/test_tools_and_services.py`
- `backend/tests/test_api.py`

前端：

- `frontend/src/pages/DashboardPage.vue`
- `frontend/src/components/AppLayout.vue`
- `frontend/src/pages/KnowledgePage.vue`
- `frontend/src/types.ts`
- `frontend/src/config/campus.ts`
- `frontend/src/styles.css`
- `frontend/nginx.conf`
- `frontend/DESIGN.md`

文档与配置：

- `.env.example`
- `README.md`
- `training/README.md`
- `design-qa.md`
- `docs/API.md`
- `docs/DATABASE.md`
- `docs/COMPETITION_ALIGNMENT.md`
- `docs/CHANGELOG.md`
- `docs/TEST_REPORT.md`（第 17 节）
- `docs/HANDOFF.md`（本文件，新建）
