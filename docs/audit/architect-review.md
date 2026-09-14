# 架构级只读审核报告 —— 安巡智脑（Codex 未提交改动集）

- **审核人**：架构师（高见远 / architect）
- **审核对象**：工作区**未提交**改动集（`git status` 显示的 31 个 modified + 4 个 untracked），基线 HEAD 分支 `main`
- **审核方式**：**只读**。全程仅使用 `git status` / `git diff` / `git diff --name-only` / `grep` / `ls` / `sha256sum` / `sed` 与文件读取。**未修改任何源码、配置、docker 文件、脚本；未执行 git add/commit/stash/checkout/branch。**
- **产出物性质**：本报告为审核意见文件，不属于源码改动。
- **项目根**：`<LOCAL_PATH>`

---

## 0. 结论速览

| 级别 | 数量 | 结论 |
|------|------|------|
| 🔴 阻断 | 0 | 未发现阻断级问题。改动集在架构上是自洽、可交付的。 |
| 🟠 重要 | 3 | (1) `review_policy_reasons` 双处计算，当前无分叉但违反单一事实源；(2) 模型切换后部署机必须单独准备 `models/yolo26m.pt`，文档/脚本未显式声明该前置条件；(3) 通用模型 nano→medium 的 CPU 冷启动与推理耗时**本轮无实测证据**（compose 默认 `YOLO_DEVICE=cpu`）。 |
| 🟡 建议 | 4 | (1) 根目录 44MB 冗余 `yolo26m.pt` 应清理；(2) Analytics 页未标注"当前配置模型"，历史/当前两类柱子无提示；(3) `_route_quality` 的 `analyzable is False` 硬编码语义建议注释固化；(4) `/analytics/overview` 未挂 API key（与 `/dashboard` 一致，属既有约定，仅提示）。 |

**对团队已给结论的独立复核**：team-lead 转述的"全链路只有 2 个短路点、`check_detection_result → retrieve_knowledge` 是无条件边"结论 **成立**，我已用 `graph.py:69-100` 逐条边复核（见第一节）。唯一需要修正的措辞：`_route_quality` 除 `review` 分支外**还**有一条 `error → handle_error` 分支，不是"只跳 manual_review"。

---

## 一、工作流拓扑与短路点（独立复核）

### 1.1 证据来源

`backend/app/agents/graph.py` 第 55–101 行 `_build_graph()`；`backend/app/agents/state.py`（`InspectionState` 为 `total=False` 的 `TypedDict`，**无 reducer**，即键为"后写覆盖"语义）。

### 1.2 实际拓扑（节点 + 边 + 判定函数行号）

```
START
  │ add_edge                       graph.py:69   （无条件）
  ▼
validate_input                      graph.py:159
  │ add_conditional_edges          graph.py:70-74
  │   _route_validation            graph.py:515-516
  │     review_required==True ────────────────► manual_review   ★短路点1
  │     else ────────────────────────────────► check_image_quality
  ▼ quality
check_image_quality                 graph.py:170
  │ add_conditional_edges          graph.py:75-79
  │   _route_quality               graph.py:519-523
  │     error ────────────────────────────────► handle_error
  │     image_quality.analyzable is False ────► manual_review    ★短路点2
  │     else ────────────────────────────────► detect_traffic_signs
  ▼ detect
detect_traffic_signs                graph.py:180
  │ add_conditional_edges          graph.py:80-84 ; _route_error graph.py:548-549
  │     error ─► handle_error ; else ─► check_detection_result
  ▼ continue
check_detection_result              graph.py:191
  │ add_edge                       graph.py:85   ★★ 无条件边：低置信度不短路 ★★
  ▼
retrieve_knowledge                  graph.py:215
  │ add_conditional_edges          graph.py:86-90 ; _route_error
  │     error ─► handle_error ; else ─► evaluate_risk
  ▼ continue
evaluate_risk                       graph.py:234   ← 二次调用 review_policy_reasons（见第二节）
  │ add_conditional_edges          graph.py:91-95 ; _route_error
  │     error ─► handle_error ; else ─► generate_recommendations
  ▼ continue
generate_recommendations            graph.py:259
  │ add_edge                       graph.py:96  （无条件）
  ▼
generate_report                     graph.py:318
  │ add_edge                       graph.py:99  （无条件）
  ▼
save_result                         graph.py:370
  │ add_edge                       graph.py:100 （无条件）
  ▼
END

manual_review  graph.py:270 ─┐
handle_error   graph.py:293 ─┼──► generate_report   graph.py:97-98
```

### 1.3 条件边清单（逐条判定函数 + 行号）

| 源节点 | 判定函数 | 行号 | 分支目标 | 性质 |
|---|---|---|---|---|
| `validate_input` | `_route_validation` | 515-516 | review→`manual_review`；quality→`check_image_quality` | **短路点1** |
| `check_image_quality` | `_route_quality` | 519-523 | error→`handle_error`；review→`manual_review`；detect→`detect_traffic_signs` | **短路点2（含 error 支线）** |
| `detect_traffic_signs` | `_route_error` | 548-549 | error→`handle_error`；continue→`check_detection_result` | 异常护栏 |
| `retrieve_knowledge` | `_route_error` | 548-549 | error→`handle_error`；continue→`evaluate_risk` | 异常护栏 |
| `evaluate_risk` | `_route_error` | 548-549 | error→`handle_error`；continue→`generate_recommendations` | 异常护栏 |

**`check_detection_result → retrieve_knowledge`（`graph.py:85`）确认为 `add_edge` 无条件边**，即低置信度/未检出**不会**短路，会继续走 RAG 与研判。team-lead 转述的核心结论成立。

### 1.4 短路风险是否真的消除？—— 判断：**是（针对图片质量告警）**

本轮 diff 的关键修改（`git diff backend/app/agents/graph.py`）：

```diff
-        return "review" if state.get("review_required") else "detect"
+        quality = state.get("image_quality", {})
+        return "review" if quality.get("analyzable") is False else "detect"
```

改动前 `_route_quality` 读的是 `review_required`（该值由 `check_image_quality` 在 `graph.py:176` 置为 `bool(reasons)`）；而 `reasons` 只要含模糊/过暗/过曝/尺寸等任一告警就非空 → **任何质量告警都会短路到 `manual_review`，跳过检测、RAG、研判**。这正是"短路风险"。

改动后改读 `image_quality.analyzable`。核对写入方 `backend/app/tools/image_quality.py`：

- 解码失败/损坏：`"analyzable": False`（`image_quality.py:30`）
- 解码成功（任何质量告警）：`"analyzable": True`（`image_quality.py:77`），注释明确 "Only corrupt or undecodable inputs are non-analyzable."

因此：**只要图片能解码，即使模糊/过暗/过曝/过小，也会继续跑完全链路**；这些质量告警仍被写入 `review_reasons`（`graph.py:175`），并最终在 `evaluate_risk` 经策略统一裁决为 `review_required=True`（见第二节）。→ **预期修复目标达成，质量告警不再短路。**

**残留短路点评估（均为合理硬门禁，非缺陷）**：

- 短路点1 `validate_input`：仅当 `location` 为空或图片文件不存在时触发（`graph.py:162-165`）。缺图无法继续，属合理。
- 短路点2 `_route_quality`：仅当 `analyzable is False`（无法解码）触发。无法解码无法检测，属合理。
- `_route_error`：仅在 `error` 已置位时走 `handle_error`，属异常护栏。

**结论**：修复后"质量告警导致的提前转人工"风险已消除；剩余两条短路均为不可分析/缺输入的硬门禁，不构成缺陷。

---

## 二、`review_required` 的职责边界（追写入方）

### 2.1 状态读写追踪（写入方 / 读出方）

`InspectionState` 无 reducer（`state.py:7` 起为普通 `TypedDict`），因此各键为"后写覆盖"。追踪如下（行号为当前工作区版本）：

**写入 `state["review_required"]` 的节点**：
| 节点 | 行号 | 写入值 |
|---|---|---|
| `validate_input` | 166 | `bool(reasons)` |
| `check_image_quality` | 176 | `bool(reasons)` |
| `check_detection_result` | 211 | `bool(reasons)` |
| `retrieve_knowledge` | 228 | `bool(reasons)` |
| `evaluate_risk` | 253 | `result.review_required` |
| `manual_review` | 287 | `True` |
| `handle_error` | 312 | `True` |
| `_execute_step` 异常分支 | 449 | `True` |

**读出 `review_required` 用于"路由"的判定函数**：
| 判定函数 | 行号 | 读出用途 |
|---|---|---|
| `_route_validation` | 516 | `return "review" if state.get("review_required") else "quality"` |
| `_route_quality` | 519-523 | **本轮改动后已不再读它**（改读 `image_quality.analyzable`） |
| `run()` | 145 / 154 | 收尾时用最终值决定 `run.status` / `task.status` |

**要点**：链路中段虽有 4 个节点反复写 `review_required`，但中段**没有任何条件边读它**（中段只读 `error`），故中段写入不影响路由。唯一在下游被消费的位置是 `evaluate_risk`（写终值）与 `run()` 收尾读取。

### 2.2 分层判断：策略在 `risk.py`，编排在 `graph.py` —— 基本恰当，但存在"二次计算"

- `review_policy_reasons` 作为 `RiskAssessmentService` 的 `@staticmethod`（`risk.py:91-116`）承载**业务策略**，放在服务层是恰当的。
- 但 `graph.evaluate_risk`（`graph.py:246-250`）在 `risk_service.evaluate()` 内部**已经算过一次**后，又**原样再算一遍**取列表：

```python
# risk.py:69-82 —— 第 1 次计算（内部），决定 result.review_required
result = self.llm.generate_risk(payload)
policy_reasons = self.review_policy_reasons(
    risk_level=result.risk_level, review_reasons=reasons, vision_events=events)
result.review_required = bool(policy_reasons)
...
```
```python
# graph.py:246-254 —— 第 2 次计算（编排层），取列表写回 state
review_reasons = self.risk_service.review_policy_reasons(
    risk_level=result.risk_level,
    review_reasons=state.get("review_reasons", []),
    vision_events=state.get("vision_events", []),
)
return {"risk_result": result.model_dump(),
        "review_required": result.review_required,   # ← 来自第 1 次
        "review_reasons": review_reasons}            # ← 来自第 2 次
```

**是否存在"同一决策多处各算一遍导致分叉"？—— 当前无分叉，但设计脆弱。**

逐项比对两次调用的入参：

| 入参 | 第 1 次（risk.py 内部） | 第 2 次（graph.py） | 是否一致 |
|---|---|---|---|
| `risk_level` | `result.risk_level` | `result.risk_level` | ✅ 同一对象 |
| `vision_events` | `events = vision_events or []`（= 传入的 state 值） | `state.get("vision_events", [])` | ✅ 同一来源 |
| `review_reasons` | `reasons`＝`dict.fromkeys(传入 review_reasons)` + 可能追加"未检索到足够可靠的知识依据" | `state.get("review_reasons", [])` | ⚠️ 见下 |

第 1 次的 `reasons` 唯一可能比第 2 次多出的项是 `"未检索到足够可靠的知识依据"`（`risk.py:43-44`）。但该字符串**已由上游 `retrieve_knowledge` 在命中为空时写入**（`graph.py:222-224`），且 `review_policy_reasons` 内部再用 `dict.fromkeys` 去重（`risk.py:106`）。因此两次调用的**去重后集合完全相同 → 输出列表相同 → `review_required` 与 `review_reasons` 不会分叉**。（已用 `state.py` 无 reducer + `graph.py:222-228` 交叉验证。）

**判断**：这是一次**冗余计算**（同一策略算两遍），当前**幂等、无害**；但它违反"单一事实源"，且存在**潜在分叉**：一旦未来 `risk.evaluate()` 内部再追加任何"只有第 1 次能看到"的理由（例如新增知识置信度过滤、LLM 自评理由），第 1 次会据此置 `review_required=True`，而第 2 次写入 state 的 `review_reasons` 却**不含该理由** → 出现"`review_required=True` 但理由列表里没有对应原因"的不一致。

**建议（🟠 重要，但不阻断本轮）**：让 `evaluate()` 成为唯一裁决方并**回传**策略结果，`graph.py` 直接消费、不再重算。可选实现：
- 方案 A：`evaluate()` 返回 `(RiskResult, policy_reasons)`，`graph.evaluate_risk` 用返回值；
- 方案 B：在 `RiskResult` 上增加一个内部字段（如 `policy_reasons: list[str]`，`model_dump` 时保留）承载裁决明细；
- 方案 C：把 `review_policy_reasons` 收敛为一个纯函数，`evaluate()` 与 `graph` 都调用**同一份已经算好的结果**（至少让 graph 复用 `risk.py` 已计算并缓存的值）。

---

## 三、模型切换（nano → medium）的部署影响

### 3.1 权重是否进入版本控制 / 镜像？

**证据（`.gitignore`，行号）**：
```
19: models/*
20: !models/README.md
21: *.pt
22: *.pth
23: *.onnx
24: *.engine
```
→ `models/*` 与全局 `*.pt` 均被忽略。**模型权重不进入 Git**。`git status` 亦未列出任何 `.pt`。✅

**证据（`.dockerignore`，行号）**：
```
15: models/*.pt
16: models/*.pth
17: models/*.onnx
18: models/*.engine
```
→ 构建上下文**排除**模型文件。核对 `backend/Dockerfile`：仅 `COPY backend /app/backend`（第 19 行）与 `RUN mkdir -p /app/uploads /app/outputs /app/models`（第 20 行），**没有 COPY 任何权重**。

**证据（`docker-compose.yml`）**：
```
45:      GENERAL_YOLO_MODEL_PATH: /app/models/yolo26m.pt
63:      - ./models:/app/models:ro
```
→ 权重通过**宿主机 bind mount** 注入容器（只读）。

**架构结论**：
- 镜像体积**不因模型变大而增加**（权重不进镜像）。
- 但**部署机必须自行在 `./models/` 下准备 `yolo26m.pt`**。切换通用模型后，若部署机 `./models/` 只有旧的 `yolo26n.pt`，`GENERAL_YOLO_MODEL_PATH=/app/models/yolo26m.pt` 会指向不存在的文件。🟠 **重要**：这是一个**未被显式声明的部署前置条件**。
  - 缓解现状：通用模型失败被设计为**软降级**——`yolo.py` 中通用模型异常只记 `general_error`，交通标志模型继续（见 `check_detection_result` 对 `role=="general_object"` 且 `error` 的处理，`graph.py:204-210`），任务仍会完成但被追加复核理由。⚠️ 但我**未验证启动期模型是否预加载/预热**（见第六节"未能验证"），若启动即加载缺失文件也可能直接抛错。
  - 建议：在 `models/README.md` 与 `docs/DEPLOYMENT.md` 显式写入"部署前须放置 `models/yolo26m.pt`（约 44MB）"，并在 `docker-compose` healthcheck（现检查 `general_yolo.configured`）之外，补一条对**文件存在性/可加载性**的说明。

### 3.2 根目录冗余 `yolo26m.pt`

**证据（`sha256sum` 原始输出）**：
```
401cea9ab23ad19246ff7744859816bc599f350e93c9dd30367b6f0a0745d0b7  models/yolo26m.pt
401cea9ab23ad19246ff7744859816bc599f350e93c9dd30367b6f0a0745d0b7  yolo26m.pt
```
两份文件**字节完全一致**（均 44,255,705 字节，`ls -la` 佐证）。配置现指向 `models/yolo26m.pt`（`config.py:52` / `docker-compose.yml:45` / `.env.example:33`），根目录那份**无任何引用**（`grep` 未见代码引用根目录路径）。

**判断**：🟡 **建议清理根目录 `yolo26m.pt`**（释放 44MB；虽被 `*.pt` 忽略不入库，但属仓库目录污染，易误导他人以为"项目自带权重"）。同批的 `scripts/compare_general_models.py` 已把 medium 路径从 `yolo26m.pt` 改为 `models/yolo26m.pt`（见其 diff），进一步说明根目录那份已废弃。

### 3.3 5.5MB → 44MB 的架构影响

- **镜像体积**：不变（bind mount，见 3.1）。✅
- **磁盘**：每台部署机多占约 **+38.7MB**（44.3−5.5）。可忽略。
- **冷启动**：medium 权重体量约 nano 的 **8 倍**，权重加载（反序列化/上传设备）耗时线性增加。⚠️ 本轮**无实测数据**——`docs/TEST_REPORT.md` / `compare_general_models.py` 给的是检出/置信度对比，未见"冷启动/首帧耗时"实测。🟠 建议在目标机实测首次加载耗时。
- **显存 / 内存**：FP32 权重文件大小 ≈ 权重驻留量级（nano≈5.5MB、medium≈44MB），相对本机 RTX 4060 Ti **可用约 12.5GB** 属**极小头寸**；真正的峰值来自**激活值**（与输入分辨率 `imgsz`、batch 相关，而非仅与参数量相关）。**架构判断**：双模型（TT100K 130MB + 通用 44MB）同时驻留显存在 12.5GB 上**无压力**。⚠️ 该结论为**量级估算，未经本机实测**，不作为性能放行依据（应由 QA 用 `nvidia-smi` 取证）。
- **CPU 推理（关键风险）**：`docker-compose.yml` 默认 `YOLO_DEVICE: ${YOLO_DEVICE:-cpu}`（第 46 行）。**medium 在 CPU 上的单帧延迟显著高于 nano**，叠加"双模型串行"，可能拉长端到端时延。🟠 **重要**：切换后应实测 CPU 模式下的端到端耗时（`agent_performance` / 任务 `total_duration_ms`），确认在可接受范围；必要时改默认 device 或下调输入分辨率。

---

## 四、`GET /analytics/overview` 口径与历史数据语义

### 4.1 `model_rows` 分组口径是否正确？

实现（`backend/app/api/router.py`）：
```python
model_rows = db.execute(
    select(
        DetectionResult.model_role,
        DetectionResult.model_name,
        func.count().label("detection_count"),
        func.avg(DetectionResult.confidence).label("average_confidence"),
    )
    .group_by(DetectionResult.model_role, DetectionResult.model_name)
    .order_by(desc("detection_count"))
).all()
```

**判断：口径正确。**
- 分组键 `(model_role, model_name)` 能把两类视觉任务（`traffic_sign` / `general_object`）与各自实际模型名分开，避免把标志与人员车辆混成一个"准确率"。✅
- `detection_count = COUNT(*)`＝检测框条数，`average_confidence = AVG(confidence)`＝逐框置信度均值，语义一致、无重复计数（`DetectionResult` 一行＝一个检出）。✅
- 注意 `inference_ms` 是**任务级**字段（`save_result` 写入，`graph.py:380-396`），本查询**未**误用它，正确。

### 4.2 历史 `model_name` 是"忠实历史"还是"数据脏"？

**写入方取证**：`model_name` 在**检测发生当时**写入：
- `backend/app/tools/yolo.py:142`：交通标志 `model_name=self.settings.yolo_model_path.name`
- `backend/app/tools/yolo.py:160`：通用对象 `model_name=self.settings.general_yolo_model_path.name`
- 落库：`graph.py:390` `model_name=str(item.get("model_name", self.settings.yolo_model_path.name))`

即旧任务记录的是**当时真实使用的模型名**（如 `yolo26n.pt`）。

**设计约定取证**：`frontend/DESIGN.md:163`（本轮同时新增/更新）明文：
> 双模型贡献按 `model_role + model_name` 分组，同时展示检出数量和平均置信度；**历史记录中旧的 `yolo26n.pt` 与当前 `yolo26m.pt` 必须如实分开，不得改写历史模型名称。**

（注：task 提到的 `docs/DESIGN.md` 不存在，实际约定位于 `frontend/DESIGN.md`；已用 `ls docs/DESIGN.md` → `NO docs/DESIGN.md` 验证。）

**判断：这是"忠实历史"，是有意设计，不是数据脏。**
- 检测结果表是**事实流水**，`model_name` 是其审计属性，**不可改写**。改写历史会破坏可追溯性（无法解释"为什么同一张图两次检出数不同"）。
- 因此 `model_breakdown` 中 `yolo26n.pt` 与 `yolo26m.pt` **并存两根柱子是正确行为**。

### 4.3 前端是否需区分"当前配置模型"与"历史记录模型"？—— **需要**

现状取证（`frontend/src/pages/AnalyticsPage.vue`）：
- `modelLabel(role, name)`（第 239-242 行）只输出 `角色名 + 模型名`，**无"当前/历史"标记**。
- 卡片 footer（第 304 行）只说"交通标志与人员车辆分别统计，避免混成单一准确率"，**未提示"哪根柱子是当前配置"**。

**架构建议（🟡）**：在图例/坐标轴 label 或 Tooltip 上标注"当前配置模型"（可读后端 `/health` 的当前 `GENERAL_YOLO_MODEL_PATH` 或 `SettingsPage.vue` 已用的同一数据源），使"当前 vs 历史"在同一图中可辨。**不得**通过改写 `model_name` 来"合并"历史——那会违反 `frontend/DESIGN.md:163`。

### 4.4 其他口径提示

- `review_reason_counts`：按**任务内类别去重**后计数（`router.py` 中 `categories = {_review_reason_category(...) for reason in ...}`），与 `frontend/DESIGN.md:164`"按任务内类别去重、防止同类提示重复放大"一致。✅
- `_review_reason_category`（`router.py` 新增）用中文关键词折叠自由文本为稳定分组，属"解释性归类"，可接受；若未来复核理由文案大改需同步维护关键词表（维护性提示，非缺陷）。
- `/analytics/overview` 与 `/dashboard` 一样**未挂 `require_api_key`**（只读接口，与既有约定一致）——🟡 仅作提示，不作为本轮问题。

---

## 五、RAG 层是否受本轮改动影响 —— 结论：**未触及**

**证据（`git diff --name-only` 原始输出中检索 `rag|knowledge`）**：
```
=== any rag / knowledge service touched? ===
NONE
```
- 改动清单不含 `backend/app/services/rag.py`、也不含任何 `knowledge` 相关文件；`backend/app/tools/` 下仅 `image_quality.py` 被改（`git diff --name-only` 佐证）。
- `graph.py` 的 `retrieve_knowledge` 节点本体本轮**未改**；仅其上游 `check_detection_result` 的置信度理由逻辑、以及 `evaluate_risk` 的策略调用被改。
- `risk.py` 仍 import 并使用 `KnowledgeHit`（`risk.py:7`），知识片段照常进入 LLM payload（`risk.py:34-42`、`60-66`）；本轮对 `output_schema` 的改动（摘除 `review_required`）**不触及** RAG 检索与引用链路。

**结论**：RAG / 知识库层**不受本轮改动影响**，无需针对本轮 diff 评估 RAG 回归；但下述"未能验证"项包含 RAG 运行态（我未启动服务执行检索）。

---

## 六、我**未能验证**的部分（诚实声明）

1. **未运行任何服务/测试**：全程只读，未启动 FastAPI、未跑 pytest、未执行 `/analytics/overview`、未跑 `frontend` 构建。所有"行为正确性"均为**静态代码路径推演**，非运行态取证。
2. **未在真实容器/真实 GPU 上验证**：Docker Engine 未就绪（历史 `docs/TEST_REPORT.md:391` 亦记录本轮受管会话无法启动 Docker）。故 3.3 的**显存/冷启动/CPU 时延**结论均为**量级估算**，无实测数字，不能作为性能放行依据。
3. **未验证模型文件可加载性**：未实际 `YOLO(...).load()` 验证 `models/yolo26m.pt` 能被 ultralytics 正常加载（仅校验了文件存在、大小与哈希）。
4. **未验证"启动即加载模型"路径**：`yolo.py` 的模型是否在应用启动时预热（health 检查 `general_yolo.configured` 的来源）我**未追到**，因此"部署机缺 medium 权重"的确切失败形态（启动失败 vs 运行期软降级）我只能标注为**两种可能**，未定论。
5. **未验证 LLM 真实返回**：`risk.py` 摘除 `review_required` 后的 LLM 契约，我只静态确认了 `RiskResult.review_required` 有默认值 `False`（`schemas.py:32`），**未实测** DeepSeek 在 `response_format=json_object` 下确实不再返回该字段 / 返回也不报错。
6. **未复算量化声明**：`models/README.md` 的"medium 检出总数比 nano 高 49%"、`config.py` 注释里的"模糊样本 152.6 / 清晰集最低 622.1"等数字，我**未独立复算**（属 QA 取证范围）。
7. **未逐行审 `image_quality.py` 的模糊阈值标定**：`blur_threshold: 80→500` + 归一化到长边 1024（`config.py`）是算法标定问题，我仅确认了它与 `_route_quality` 的耦合关系，**未验证阈值是否合理**。

---

## 附：本次审核使用的只读证据命令

```bash
git status
git diff --stat
git --no-pager diff -- backend/app/agents/graph.py backend/app/services/risk.py
git --no-pager diff -- backend/app/api/router.py
git --no-pager diff -- backend/app/tools/image_quality.py backend/app/config.py docker-compose.yml .env.example models/README.md
git --no-pager diff -- frontend/DESIGN.md frontend/src/types.ts frontend/src/api.ts frontend/src/router.ts
git --no-pager diff --name-only
git --no-pager diff --name-only | grep -iE "rag|knowledge"      # → NONE
grep -nE "models|\.pt" .gitignore .dockerignore
grep -nE "COPY|mkdir|models" backend/Dockerfile
grep -n "models" docker-compose.yml
sha256sum models/yolo26m.pt yolo26m.pt models/yolo26n.pt
ls -la models/ *.pt
grep -n "model_name" backend/app/tools/yolo.py
grep -n "class RiskResult" -A 20 backend/app/schemas.py
```
（`cat`/读文件仅用于只读查看，未做任何写入。）
