# VLM 识图研判层接入评估（供 Codex 评审）

> 写作日期：2026-09-13 ｜ 作者：WorkBuddy（齐活林）｜ 读者：Codex
> 性质：**方案评估文档，尚未实施任何代码改动**。请你评估可行性、找出方案漏洞、给出「建议接入 / 缓一缓 / 修改后接入」的结论，**不要直接动手改代码**，先回评估意见等用户拍板。

---

## 0. 一句话背景

安巡智脑现在的风险研判（`backend/app/services/risk.py` → `llm.py`）只把**检测结果的文字**发给 DeepSeek，模型是"听转述"而不是"亲眼看图"。本文档评估：给研判环节加一双眼睛——接入阿里云百炼视觉模型 **`qwen3.7-flash`**，让它看原图判断"车辆是否乱停/占道/堵消防通道"这类**需要视觉语义**的风险。

**用户已拍板的架构决策（2026-09-13 晚）**：
- ✅ **双模型分工**：DeepSeek `v4-flash` 继续管**文字研判**（现有链路零改动）；`qwen3.7-flash` 管**图像理解**（新增旁挂能力）。
- ✅ DeepSeek 走官方 API（现有 `LLM_API_KEY` 不动）；百炼走阿里云专属端点或公共端点（新增 `DASHSCOPE_API_KEY`，与 `LLM_API_KEY` 并列进 `.env`，**不写进代码**）。
- ❌ **不用中转站（Rainbow Gate）**。
- ❌ **不用本地模型**（Ollama 全系排除）。
- 备选（若 qwen3.7-flash 识图效果不行）：DeepSeek 官方 `deepseek-v4-flash-vision-exp`（同一把 key 可切换，2026-08-21 上线，与 v4-flash 同价、384 token/图上限，实验性模型需注意下线风险）。
- 参考蓝本：台湾高通黑客松项目 `solveillegalparkingbyVLM`（下文第 2 节）。

---

## 1. 视觉模型选型：qwen3.7-flash 关键事实（已核实）

阿里云官方帮助中心（`help.aliyun.com/zh/model-studio/qwen3-7-flash`）确认：

| 事实 | 数值 | 对本项目的意义 |
|---|---|---|
| 模型类型 | **Qwen3.7 原生视觉语言系列 Flash 模型**（3.6-flash 是纯文本，这一代升级为多模态） | 识图任务能力对口 |
| 输入模态 | **Image / Text / Video**（输出 Text） | 单模型覆盖图+视频帧 |
| 上下文 / 最大输出 | 1M / 131,072 | 足够 |
| 生产级能力 | Function Calling、**结构化 JSON 输出**、上下文缓存、前缀续写、批量推理 | 与现有 `response_format: json_object` 兼容 |
| 协议 | OpenAI 兼容（`/compatible-mode/v1`） | 与 httpx 调用方式同构 |
| 微调 | 不支持（仅 API） | 无影响，我们不微调 |
| 定位 | Flash = 高吞吐低成本档；万物识别、真实世界感知强，复杂图文推理上限弱于 Plus | 识图判违停属"万物识别"档，够用 |

**接入时必须注意的三个坑（从用户提供的示例代码发现）**：
1. **`enable_thinking` 必须显式设 False**。巡检研判是 JSON 结构化短任务，开思维链会拖慢且答案可能混入思考流——与现有 DeepSeek `thinking:disabled` 的决策同因（`llm.py:48-52` 注释）。调用应为**非流式**。
2. **端点要实测**：用户示例用的是专属端点 `ws-3r5econmdf5bentm.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`，需确认该实例已部署 `qwen3.7-flash`；若没有，换公共端点 `dashscope.aliyuncs.com/compatible-mode/v1`（key 通用）。
3. **中国大陆节点直连**，不需要走 `OUTBOUND_HTTP_PROXY`（该代理目前只服务 DeepSeek 出站）。
4. 图片按分辨率折算 token 计费，具体单价以百炼控制台为准；上送前长边归一控制成本。

## 2. 参考蓝本：solveillegalparkingbyVLM 五层流水线

该项目的完整链路（GitHub `Sakuya4/solveillegalparkingbyVLM`，MIT 协议）：

1. **采集层**：ESP32-CAM 低成本摄像头 → 云端。→ 我们的对应物：手机拍的巡检照片（`uploads/inspections/`）。
2. **检测层**：YOLO 找车辆 + ByteTrack 跟踪。→ **我们已具备**（双 YOLO26 + ByteTrack 视频链路）。
3. **隐私层（点睛之笔）**：上云前对**车牌区域与画面文字模糊处理**（他们用 NAFNet，我们可以用 OpenCV 传统算法）。一石二鸟：①数据合规（画面出校园进 API 厂商必须打码）；②防止 VLM 注意力被"读车牌"吸走，干扰"停得对不对"的判断。→ **我们暂缺**。
4. **研判层**：模糊后的图 + 提示词发 VLM 判断是否违停；看不清的画面由 SM3Det 增强后重判。→ **我们暂缺，即本次评估目标**。
5. **决策层**：AI 只初筛 + 出摘要，**开不开罚单由人确认**。→ **我们已具备**（策略 B 人工复核，`REMEDIATION_2026-09-13.md`）。

它的 2026 学术扩展版还有两招值得抄：
- **before/trigger/after 三帧证据包**：告警触发时自动截取事发前/时/后三帧，隐私化后交 VLM 出摘要 → 对我们视频巡检的报告证据链有直接参考价值。
- **诚实量化口径**：公开 F1 0.63~0.67、误报率 0.531→0.235、触发延迟 0.792s，并声明"单片段不代表全集召回" → 与本项目"无真值不得宣称准确率"的铁律同路。

**结论：五层里我们缺的只有 ③隐私层 和 ④VLM 研判层。** 且我们的检测层（双模型 + RAG）比它参赛版更强。

## 3. 建议的技术方案（供你挑刺）

### 3.1 改动面（刻意最小化，双 provider 架构）

```
config.py    + vision_llm_provider: str = "dashscope"        # dashscope | deepseek | off
             + vision_llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
             + vision_llm_api_key: str | None = None          # 读 .env 的 DASHSCOPE_API_KEY
             + vision_llm_model: str = "qwen3.7-flash"
             + vision_llm_enabled: bool = False               # 默认关，灰度开
             + vision_image_max_side: int = 1280              # 上送前长边归一（控 token）
llm.py       新增 VisionLLMService（或 generate_risk 内多模态分支）：
             messages = [ {text: 系统提示+YOLO检测结果JSON},
                          {image_url: base64(打码后的图)},
                          {text: 用户指令} ]
             调用要求：enable_thinking=False、非流式、response_format=json_object；
             DeepSeek 文字研判（generate_risk）**一行不动**——两个服务各管各的
             —— 百炼调用不走 OUTBOUND_HTTP_PROXY（大陆直连）
risk.py      evaluate() 的 payload 增加 image_path（打码后副本路径）；
             VLM 产出的视觉研判字段（如 vision_assessment）并入 evidence，不新增 LLM 可注入的决策字段
新文件        tools/privacy_mask.py —— OpenCV 车牌/人脸区域模糊（haar + 比例启发式，不引入新模型依赖）
graph.py     evaluate_risk 节点把 state["image_path"] 传进 risk_service.evaluate()
```

**设计原则**：
- **回退安全**：`vision_llm_enabled=False` 时代码路径与现在**逐字节等价**；VLM 分支任何异常（图片编码失败/接口 4xx/key 未配）→ 降级回 DeepSeek 纯文本研判 + 追加 review_reason，**不允许阻断巡检流程**。DeepSeek 本身挂了仍走现有 rules_only 兜底，两层降级互不干扰。
- **打码副本不覆盖原图**：模糊图存 `outputs/privacy_masked/`，`detection_results` 里原始 result_image_path 不动；报告里"原图/结果图"仍用未打码的本地图（本地存储合规），**只有上云的那份**打码。
- **确定性边界不动**：`review_required`/`policy_reasons` 仍由后端策略 B 独占（`risk.py:53-58` 的 schema 摘除逻辑保持）；VLM 只提供 `risk_level` 建议与视觉研判证据字段。残余非确定性口径按 `REMEDIATION_2026-09-13.md` 第 6 条继续记录。

### 3.2 提示词要点（从翻车案例学来的）

掘金那篇《违停检测翻车记》的核心教训：**等红灯的车被判违停，因为模型不懂"为什么停"**。对策（写进 system prompt）：
1. 枚举合法场景（等灯、排队、礼让行人、装卸货临停、公务车辆）；
2. 要求二段式输出：先描述看到什么，再给结论 + 置信度；
3. 明确"只能依据图内可见证据判断，看不出就说不确定"——与我们现有"信息不足设 review"的口径对齐。

### 3.3 验证计划（接入前必做，零风险实验先行）

**第一步（不动代码）**：写独立脚本 `scripts/test_vlm_parking.py`，用 `.env` 新增的 `DASHSCOPE_API_KEY` 调 `qwen3.7-flash`（先打一发纯文本"你是谁"确认专属/公共端点可用，再发图），对以下样本提问"图中车辆停放是否合规，依据是什么"：
- `校园照片/新增照片/车/IMG_9752.JPG` / `IMG_9759.JPG` / `IMG_9773.JPG`（3 张 JPG）
- ⚠️ 该目录另有 9 张 `.HEIC`，**OpenCV/PIL 均无法解码**（已实测），后端白名单也不收（`files.py:16`）；本实验只能用 3 张 JPG，扩样需先转格式。
- 对照组：`uploads/inspections/` 已有 10 张唯一图。

**准入线（建议）**：3+10 张样本上，方向性判断（违停/正常/不确定）与肉眼标注一致率 ≥ 80%，且"不确定"输出诚实（不硬编结论）才进入正式接入；否则换备选 `deepseek-v4-flash-vision-exp` 对比一轮再定。
**注意**：样本量 < 30 且无系统真值，按项目铁律**只能支持选型，不得写入"准确率 XX%"的结论**。

### 3.4 成本与延迟预估

- 单次巡检多一张图 ≈ 多 384 token 输入 ≈ 0.0006 元 + base64 编码/上传延迟（长边 1280 约 100-300ms）。
- 现有 `llm_timeout_seconds=30` / `llm_max_retries=2` 对视觉请求同样适用，无需改。

## 4. 风险清单（请你补充遗漏）

| 风险 | 等级 | 缓解 |
|---|---|---|
| VLM 误判（等灯判违停类） | 高 | 合法场景枚举 prompt + 二段式输出 + 策略 B 人工复核兜底（VLM 结论永远只是建议） |
| 隐私：未打码图上云 | 高 | `privacy_mask.py` 在上送前强制执行；打码失败 → 不上送图片，降级纯文本 |
| 专属端点未部署 qwen3.7-flash / 端点漂移 | 中 | 第一步实验先验证连通性；`vision_llm_base_url`/`vision_llm_model` 均可配置，可切公共端点或备选模型 |
| 双 provider 复杂度（两把 key、两个超时/重试策略） | 中 | VisionLLMService 单独实现，不与 DeepSeek 客户端耦合；任一失败降级互不传染 |
| 误开 `enable_thinking` / 流式调用导致 JSON 解析失败 | 中 | 代码里显式 `enable_thinking=False` + 非流式 + response_format；回归测试覆盖 |
| 图片 token 计费超预期 | 低 | 上送前长边归一 1280；实测核对账单 |
| 多模态分支引入非确定性扩大 | 中 | schema 不新增决策字段；`check_risk_determinism.py --rounds 3` 加入验证 |
| HEIC 样本进不了系统 | —（独立问题） | 若用户要扩样，另立"格式支持"小改动（pillow-heif + 白名单），与本方案解耦 |

## 5. 待用户拍板的决策点

1. 是否先跑 3.3 的零风险实验（推荐先跑）？
2. 隐私打码用 OpenCV 启发式（轻，够用）还是上 NAFNet/专用车牌模型（重，更准）？
3. `llm_vision_enabled` 灰度策略：全局开 or 按 area_type（如只有道路/停车区传图）？
4. HEIC 格式支持要不要顺带做（不做的话新照片 9/12 张用不上）？

## 6. 参考来源

- qwen3.7-flash 官方能力（输入模态/输出上限/结构化输出）：阿里云帮助中心 `help.aliyun.com/zh/model-studio/qwen3-7-flash`；国际站 `alibabacloud.com/help/en/model-studio/qwen3-7-flash`（注意：阿里云开发者社区个别横评文章称 Flash "仅纯文本"，与官方帮助中心矛盾，**以官方帮助中心为准——qwen3.7-flash 是视觉模型**）
- 用户提供示例代码（专属端点 `ws-*.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` + enable_thinking 流式调用）——接入时需改非流式 + 关 thinking
- 备选模型 `deepseek-v4-flash-vision-exp`：官方 changelog 2026-08-21；dev.to `mr_manushukla/deepseek-shipped-vision-on-21-august-2026`
- 蓝本项目：GitHub `Sakuya4/solveillegalparkingbyVLM`（MIT；NAFNet 模糊、SM3Det 兜底、before/trigger/after 证据包、F1/误报率公开口径）
- VLM 违停误判案例与 prompt 对策：掘金《记一次违停检测系统翻车》（juejin.cn/post/7611424362591305779）
- 本项目现状锚点：`backend/app/services/llm.py`（generate_risk 纯文本 + `thinking:disabled` 决策）、`risk.py:53-58`（schema 摘除）、`config.py:104-111`（LLM 配置）、`docs/audit/REMEDIATION_2026-09-13.md`（策略 B 决策记录）

---

**请你（Codex）回三样东西**：① 方案漏洞与改进点；② 3.1 改动面是否同意（不同意给替代）；③ 你判断「建议接入 / 缓一缓 / 修改后接入」哪档，理由。等用户确认后再动手。

---

## 7. 评审意见（WorkBuddy·阿克，2026-09-13 深夜 · 只读评审，未改任何代码）

> 评审前已核对真实代码锚点：`graph.py:123`（state 确有 `image_path`）、`risk.py:19-94`（evaluate 纯文字 payload + 策略 B 单点）、`llm.py:28-96`（DeepSeek 客户端 + `thinking:disabled`）、`config.py`（vision_* 键尚不存在）。方案引用的代码位置全部属实。

### ① 方案漏洞与改进点（按严重度排序）

**V-1（最关键）「合并模式」含糊——必须先定再动手。** 3.1 的伪代码暗示 qwen3.7-flash 直接产出完整 RiskResult JSON（含 `risk_level`），而设计原则又说「VLM 只提供 risk_level 建议与证据字段、不新增决策字段」，两者矛盾。两种模式的后果完全不同：

- **模式甲（qwen 全量接管研判）**：`risk_level` 由 qwen 输出 → 策略 B 消费它 → qwen 成为第二个可影响「转人工」的模型，非确定性叠加，且「DeepSeek 管文字、链路零动」名存实亡。**不推荐。**
- **模式乙（qwen 旁挂出证据，DeepSeek 仍是唯一决策者）**：qwen 只输出 `vision_assessment`（视觉描述 + 违停/正常/不确定 + 依据），作为新字段并入 DeepSeek 的 payload；最终 `risk_level` 仍出自 DeepSeek。与「schema 不新增决策字段」自洽，非确定性不叠加。**推荐，写方案时应明确为唯一模式。**

**V-2 隐私打码的失败模式比方案承认的更糟。** 「打码失败 → 降级纯文本」防的是打码**动作**失败；真正的洞是**启发式检测不到 ≠ 画面里没有**：OpenCV haar 对侧脸/遮挡人脸基本失效，比例启发式找车牌误漏都常见。漏打码 = 学生人脸/车牌原图出境。建议灰度门收紧为：**YOLO 检出 person 的图一律不上送**（纯车辆/标志场景先行），且补一条合规动作——查证百炼数据处理政策（输入是否用于训练），报告要交给学校，这句话必须有出处。

**V-3 成本口径用错了模型。** 「384 token/图 ≈ 0.0006 元」是备选 `deepseek-v4-flash-vision-exp` 的口径；qwen3.7-flash 按分辨率折算（约 28px/token），长边 1280 的图约 1500~1700 token。量级仍便宜，但数字应改，否则对账时会疑心超支。

**V-4 验证设计缺「人工真值先行」。** 「与肉眼标注一致率 ≥80%」在 13 张样本上 ≈ 10.4 张，且没说**谁、在什么时候标**。应改为：先由用户对 13 张样本逐张标注预期结论（三分类 + 依据），qwen 盲测两轮（顺带验证确定性），报告逐张对照而非一个百分比。项目「样本 <30 只支持选型」铁律方案已遵守，这点做得对。

**V-5 小改进**：(a) `vision_llm_provider` 的 `off` 取值与 `vision_llm_enabled=False` 语义重复，二选一；(b) 补 `vision_llm_timeout_seconds`（传图+推理与纯文本不同拍）；(c) `vision_image_max_side` 建议与质量护栏的 1024 对齐，一套归一两种用途；(d) **打码副本路径与本地 `image_path` 严禁进发给 LLM 的 JSON payload**（信息泄露 + 对模型无意义），只留在后端内部；(e) `evaluate()` 加参用默认值 None，65 个现有测试零破坏。

**V-6（时序硬约束，方案未考虑）** 比赛提交截止 **9/14 24:00、代码硬冻结线 12:00**（见 `.workbuddy/memory/2026-09-13.md` 末节）。VLM 接入 = 新 provider + 新文件 + graph/risk 改动 + 回归，任何一部分在冻结线后落地都会危及提交物。**现在不是接入时点**，连 3.3 实验脚本也应排到提交完成之后（且实验还缺 `DASHSCOPE_API_KEY`，.env 现在只有 `LLM_API_KEY`）。

### ② 3.1 改动面：同意（附上述修正）

方向全部符合本项目纪律：双 provider 独立不耦合、默认关灰度开、两级降级互不传染、打码副本不覆盖原图、策略 B 独占决策字段、`generate_risk` 一行不动。改动面确实是最小化的（`state["image_path"]` 现成、`evaluate()` 加参即可）。**前提是按 V-1 定死模式乙、按 V-5 修正细节后**才动手。

### ③ 结论档位：修改后接入，且明确排在比赛提交之后

- **方向对**：五层缺的确实是隐私层+VLM 层，检测层与人工复核层已具备，旁挂架构回退安全。
- **但当前不接**：V-1 未定案前动手必然返工；V-2/V-4 需要用户拍板（打码严格度、谁标真值）；更硬的是 V-6 时序——现有链路 65 passed、比赛材料不需要 VLM，为「锦上添花」冒「提交物翻车」的风险不划算。
- **建议节奏**：冻结线前零改动 → 比赛提交完成 → 用户拍板 V-1（推荐模式乙）与 V-2 灰度门 → 跑 3.3 零风险实验（届时再提供 `DASHSCOPE_API_KEY`）→ 达标则按修正后的 3.1 接入。
- 实验若不达标，备选 `deepseek-v4-flash-vision-exp` 同一把 key 可切，方案已预留，闭环完整。

**以上为评审意见，最终由用户拍板。**
