# 工程师只读审核报告 — 转人工策略修复（Codex 未提交改动集）

- 审核人：寇豆码（engineer）
- 审核对象：工作区**尚未提交**的改动（`git status` 中 `backend/app/services/risk.py`、`backend/app/services/llm.py`、`backend/app/agents/graph.py`、`backend/app/tools/image_quality.py`、`backend/app/config.py`、`backend/app/api/router.py` 等）
- 基线提交：`63df367`（`git rev-parse --short HEAD`）
- 解释器：`<LOCAL_PATH>`
- **性质：只读审核。本报告仅为意见产出物，未修改任何源码 / 配置 / 测试 / 脚本，未执行任何 git 写操作。**

---

## 0. 结论速览

| 级别 | 数量 | 条目 |
| --- | --- | --- |
| **阻断** | **0** | 未发现会导致崩溃 / 数据错写 / 反序列化失败的缺陷 |
| **重要** | 3 | I-1 `review_required` 的确定性仅「就地降级」，仍透传依赖 LLM 的 `risk_level`；I-2 转人工策略在 `risk.py` 与 `graph.py` 两处各算一遍（潜在分叉）；I-3 `_route_quality` 对缺失 `analyzable` 键兜底方向偏「继续」 |
| **建议** | 4 | S-1 `output_schema["required"]` 过滤为死代码；S-2 `review_policy_reasons` 对非 dict 视觉事件会抛 `AttributeError`；S-3 `blur_threshold=500`/长边 1024 的标定不可由代码自证；S-4 双阈值量化闭环缺自动化回归 |

**四项缺陷的代码级判断：**
- ① `review_required` 由大模型自由裁量 → **已消除直接裁量**（无条件覆盖），但确定性只是「降级传递」，见 I-1。
- ② `status` / `risk_level` 语义重叠 → 本轮改动**未触及**（`status` 仍由 `review_required` 派生，属架构师 / PM 议题）。
- ③ 转人工率过高 → 部分改善（干净低风险可自动完成），但 `medium` 起即转人工，方向与幅度需 PM 复核。
- ④ 图片质量护栏误判且短路跳过检测 → **短路已修复**（`_route_quality` 改用 `analyzable`，质量告警不再跳过 detect）；误判通过「长边归一化 + 阈值 80→500」缓解。

---

## 1. `backend/app/services/risk.py`

### 1.1 `review_policy_reasons` 静态方法（策略 B）— 实现正确

`risk.py:91-116` 原文：

```python
91  @staticmethod
92  def review_policy_reasons(
...
106     reasons = list(dict.fromkeys(item for item in review_reasons if item))
107     for event in vision_events:
108         if event.get("requires_manual_review"):
109             reason = str(event.get("evidence") or event.get("label") or "视觉事件需要人工复核")
110             if reason not in reasons:
111                 reasons.append(reason)
112     if risk_level in {"medium", "high", "review"}:
113         reason = f"风险等级为 {risk_level}，按校园安全复核策略需人工确认"
114         if reason not in reasons:
115             reasons.append(reason)
116     return reasons
```

判定：与策略 B 描述一致 —— 显式理由 / 质量 / 工具原因 ∪ 视觉事件 ∪ `risk_level ∈ {medium,high,review}`。去重使用 `dict.fromkeys`，顺序稳定（可复现）。**正确。**

### 1.2 `review_required` 是否被无条件覆盖 — 是

`risk.py:70-79` 原文：

```python
70  policy_reasons = self.review_policy_reasons(
71      risk_level=result.risk_level,
72      review_reasons=reasons,
73      vision_events=events,
74  )
75  result.review_required = bool(policy_reasons)
76  if policy_reasons:
77      result.uncertainty_note = self._merge_uncertainty(
78          result.uncertainty_note, policy_reasons
79      )
```

`result.review_required` 是**无条件赋值**（既不看 LLM 返回值，也不写作 `result.review_required = result.review_required or ...`）。即使大模型返回 `review_required=True` 但策略为空，也会被覆盖为 `False`。

**运行证据**（解释器实测，单位测试 `test_tools_and_services.py:282` FakeLLM 返回 `review_required=True` 且 `risk_level="low"`）：

```
6 passed, 14 deselected in 0.15s      # pytest -k "quality or review_policy or confidence or normaliz"
```

其中 `test_risk_review_policy_is_deterministic_and_ignores_llm_boolean` 断言 `clean.review_required is False`（LLM 谎报 True 也不采纳）。**正确。**

### 1.3 摘除 `output_schema` 中的 `review_required` — 已摘除；附带一个死代码

`risk.py:46-54` 原文：

```python
46  output_schema = RiskResult.model_json_schema()
50  output_schema.get("properties", {}).pop("review_required", None)
51  if "required" in output_schema:
52      output_schema["required"] = [
53          name for name in output_schema["required"] if name != "review_required"
54      ]
```

运行证据（`RiskResult.model_json_schema()` 实测）：

```
[schema] required = ['risk_level', 'risk_score', 'problem_summary']
[schema] properties keys = [..., 'review_required', ...]
```

即：`review_required` 因带默认值，**从来不在 `required` 列表里**。因此 51-54 行的过滤是**恒等操作（死代码）**，无害但会误导读者以为该字段曾是必填。→ 见 **S-1**。

### 1.4 边界核验（lead 指定项）— 实测结果

以真实类调用 `RiskAssessmentService.review_policy_reasons(...)`：

| 输入 | 实测返回 | 判断 |
| --- | --- | --- |
| `reasons` 空、`risk_level="low"`、`vision_events=[]` | `[]` | 干净低风险 → 不转人工 ✔ |
| `reasons` 空、`risk_level="medium"` | `['风险等级为 medium，按校园安全复核策略需人工确认']` | ✔ |
| `risk_level=None` | `[]` | **不抛异常**，返回空（`None not in {…}`）✔ |
| `risk_level="weird"`（非法字符串） | `[]` | **不抛异常** ✔ |
| `review_reasons=["", None, "模糊"]` | `['模糊']` | 过滤空值 ✔ |
| `vision_events=[{"requires_manual_review":True,"evidence":"人员聚集"}]` | `['人员聚集']` | ✔ |
| `vision_events=[{"requires_manual_review":True}]`（无 evidence/label） | `['视觉事件需要人工复核']` | 兜底文案 ✔ |
| `vision_events=[None]`（元素非 dict） | **抛 `AttributeError: 'NoneType' object has no attribute 'get'`** | 见 **S-2** |

- `reasons` 为空：返回「视觉事件 + 风险等级」派生结果，不报错。
- `risk_level` 为 None / 非法：不报错，按「无风险等级理由」处理。
- `vision_events` 为空：`for` 循环不执行，无副作用。
- 是否会抛异常：**唯一**抛点是非 dict 的视觉事件元素（见 S-2）；在当前调用链中 `vision_events` 恒为 `list[dict]`（`graph.py:186` 取自 YOLO 工具输出），故当前不可达。

### 1.5 关键交叉验证：`RiskResult.review_required` 默认值（lead 指定项）

`backend/app/schemas.py:32` 原文：

```python
32  review_required: bool = False
```

**结论：摘除 schema 不会导致反序列化爆炸。** 运行证据：

```
[validate-no-field] review_required = False bool     # 缺字段 → 用默认 False
[validate-with-true] review_required = True          # 模型仍返回该字段也接受
```

`llm.py:68` 用 `RiskResult.model_validate(parsed)`：LLM 省略该字段 → 默认 `False` → 随后被 `risk.py:75` 无条件覆盖。**全链路安全，无阻断。**

---

## 2. `backend/app/services/llm.py`

### 2.1 prompt 改写 + `temperature: 0.0`

`llm.py:32-37` 原文（新 system prompt）：

```python
35  "信息不足时必须将 risk_level 设为 review，并在 uncertainty_note 说明不确定性。"
36  "是否转人工由后端确定性策略决定，不由大模型自由裁量。只返回合法 JSON。"
```

`llm.py:45`：`"temperature": 0.0,`（原 `0.1`，`git diff` 确认）。

判定：prompt 已把「自由裁量」表述改为「设 `risk_level=review` + 后端决定」，与 `risk.py` 的覆盖逻辑自洽。**正确。**

### 2.2 残留要求核验：schema 摘除后 prompt 是否仍要求输出 `review_required`

逐字核对。`risk.py:46-54` 已把 `review_required` 从 `output_schema.properties` 摘除；该 `output_schema` 随 `payload`（`risk.py:65`）进入 `llm.py:38` 的 `user_prompt`。system prompt（32-37）**全文不含 `review_required` 字样**（`grep` 证据：`低置信度 / review_conf` 命中的 `llm.py` 仅第 34 行，与字段名无关）。

→ **无残留要求，无多余 token，无字段歧义。**（`response_format` 仅为 `{"type": "json_object"}`，未把 schema 作为强约束下发；模型即使凭习惯多回 `review_required` 也会被 `risk.py:75` 覆盖。）

**但见 I-1：** `risk_level` 仍是 LLM 输出，且现在是转人工的**直接输入**。

---

## 3. `backend/app/agents/graph.py`

### 3.1 `_route_quality` 判定条件

`graph.py:519-523` 原文：

```python
519  def _route_quality(state: InspectionState) -> Literal["detect", "review", "error"]:
520      if state.get("error"):
521          return "error"
522      quality = state.get("image_quality", {})
523      return "review" if quality.get("analyzable") is False else "detect"
```

判定：短路已从旧的 `review_required` 改为 `analyzable is False`（仅无法解码才 review）。质量告警不再跳过 detect。与 `image_quality.py:77`（可解码恒 `analyzable=True`）一致。**正确，缺陷④的短路问题已修复。**

端到端证据（`test_api.py:225 test_quality_warning_continues_detection_and_analysis`）：mock 一张 `valid=False, analyzable=True` 的模糊图后，断言 trace 含 `detect_traffic_signs`、`retrieve_knowledge`、`evaluate_risk`，且 `status=="review"`。即「不再短路，但质量告警仍计入转人工理由」。**符合设计。**

### 3.2 `_confidence_review_reason` — 确认为 **AND 语义**（逐字核验）

`graph.py:525-545` 原文：

```python
532      if not detections:
533          return None
534      reliable_count = sum(
535          float(item.get("confidence", 0))
536          >= (
537              self.settings.general_yolo_review_conf
538              if item.get("model_role") == "general_object"
539              else self.settings.yolo_review_conf
540          )
541          for item in detections
542      )
543      if reliable_count:
544          return None
545      return f"全部 {len(detections)} 个检测结果均低于对应模型的可靠置信度阈值"
```

逐字结论：函数统计「**过阈值**」的检测数（`>=`），只要**存在一个**过阈值即返回 `None`（不转人工）；**仅当全部低于各自阈值**（`reliable_count == 0`）才给出理由。→ **是 AND 语义，不是 OR。** 与旧实现（`low_confidence` 非空即追加，OR）方向相反，**符合修复目标**。

阈值实测：`yolo_review_conf=0.5`、`general_yolo_review_conf=0.35`（`config.py:42/54`）。

**三种输入推演表（真实运行结果）：**

| 输入类别 | 具体输入 | 实测返回 | 语义 |
| --- | --- | --- | --- |
| 空检出 | `[]` | `None` | 不因置信度转人工（空检出另有 `graph.py:196` 理由） |
| 单检出 · 过阈值 | `[{0.95, traffic_sign}]` | `None` | 不转 |
| 单检出 · 不过阈值 | `[{0.30, traffic_sign}]` | `'全部 1 个检测结果均低于对应模型的可靠置信度阈值'` | 转 |
| 混合 · 一过一不过 | `[{0.95,ts},{0.10,general}]` | `None` | **不转**（AND 语义关键点） |
| 全部不过 | `[{0.30,ts},{0.20,general}]` | `'全部 2 个…'` | 转 |
| 边界 · 恰等阈值 | `[{0.50==yolo_review_conf,ts}]` | `None` | `>=` 视为可靠，与旧 `<` 判定互补一致 |
| general 恰 = 0.35 | `[{0.35,general}]` | `None` | 一致 |

`>=` 与旧 `<` 互为补集，边界（恰等）行为与旧判定一致，无翻转。

**残留旧语义调用方核查：** `grep -rn "_confidence_review_reason" .` 仅命中 `graph.py:198`（唯一调用点）与 `tests/test_api.py:269-270`。`grep "低置信度\|confidence.*<"` 未发现其它内联的「任一低置信度即复核」逻辑。→ **无残留旧语义调用方。**（旧内联实现已在 diff 中被整体删除。）

### 3.3 ⚠️ 同一决策两处各算一遍（→ I-2）

`graph.py:243-255` 原文：

```python
246  review_reasons = self.risk_service.review_policy_reasons(
247      risk_level=result.risk_level,
248      review_reasons=state.get("review_reasons", []),
249      vision_events=state.get("vision_events", []),
250  )
251  return {
252      "risk_result": result.model_dump(),
253      "review_required": result.review_required,       # ← 来自 risk.py 的内部计算
254      "review_reasons": review_reasons,                # ← 本节点再独立算一遍
255  }
```

`review_required` 取自 `risk.py:75`（用 risk 内部 `reasons`，含 `risk.py:44` 追加的知识理由），而 `review_reasons` 在本节点用 `state["review_reasons"]` **重新计算**。见 §5 分叉分析。

---

## 4. `backend/app/tools/image_quality.py`

### 4.1 `_normalize_for_blur` 实现正确、保留长宽比

`image_quality.py:87-99` 原文：

```python
88  height, width = int(gray.shape[0]), int(gray.shape[1])
89  target = self.settings.blur_normalize_long_side
90  long_side = max(height, width)
91  if long_side == target:
92      return gray
93  scale = target / long_side
94  interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
95  return cv2.resize(
96      gray,
97      (max(1, round(width * scale)), max(1, round(height * scale))),
98      interpolation=interpolation,
99  )
```

判定：
- 降采样（`scale<1`，长边>目标）用 `INTER_AREA`、升采样（`scale>1`）用 `INTER_CUBIC` —— 符合 OpenCV 惯例。**正确。**
- 长宽用**同一** `scale` 缩放 → **保留长宽比**。**正确。**
- 长边已等于目标时直接返回原图（避免无谓重采样）。**正确。**
- 边界：`max(1, ...)` 防止 0 尺寸；`long_side==0` 实际不可达（解码图长边≥1）。**健壮。**
- 参数 `blur_normalize_long_side` 已在 `config.py:137` 纳入正整数字段校验。

### 4.2 `blur_score` 确实基于归一化后的灰度图

`image_quality.py:46-51` 原文：

```python
46  gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
47  raw_blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
48  normalized_gray = self._normalize_for_blur(gray)
49  blur_score = float(cv2.Laplacian(normalized_gray, cv2.CV_64F).var())
51  blurred = blur_score < self.settings.blur_threshold
```

判定：`blur_score` 在 `normalized_gray` 上计算，`blurred` 也用它；原始分另存 `blur_score_raw` 供诊断。**正确。** 证据：`test_tools_and_services.py:36` 断言 `blur_score_raw != blur_score`。

### 4.3 `analyzable` 语义变化的**下游影响** — 无其它消费方

`analyzable` 仅在 `image_quality.py:30/77`（写入）与 `graph.py:523`（读取）出现。`grep` 全仓：

- `backend/app`：仅 `graph.py:523`。
- `frontend/src`：`grep "analyzable"` **零命中**；`blur_score` 亦零命中；`frontend/src/pages/*.vue` 中的 `check_image_quality` 仅为**节点名中文标签**，不消费质量字段。
- 质量明细 dict **不落库**（`graph.py:426-428` 仅存 `width/height`），故无历史数据语义冲突。

→ 语义变化（仅无法解码为 `False`）**仅影响 `_route_quality` 一条路径，无其它下游连带影响。** 返回 dict 在两个分支键集合一致（含 `analyzable`/`blur_score_raw`/`blur_normalized_long_side`），下游 `dict.get` 不会 KeyError。**无阻断。**

---

## 5. 全仓 grep：`review_required` / `policy_reasons` / `_confidence_review_reason` / `analyzable` — 读写点与分叉判定

**`review_required` 写点（`grep "review_required\s*="`，backend/app）：**

| 位置 | 语义 | 判定 |
| --- | --- | --- |
| `risk.py:75` | `bool(policy_reasons)` —— **唯一权威策略** | ✔ |
| `risk.py:148` / `graph.py:280` / `graph.py:305` / `graph.py:557` | 规则兜底 / 人工护栏 / 错误护栏，恒 `True`（保守） | ✔ 可接受 |
| `graph.py:137/211/228/253` | 各节点把 `bool(reasons)` 写入中间态 | ✔ 汇入同一 `reasons` 漏斗 |
| `router.py:634/638` | **人工**复核结果覆盖（confirm/modify→False，reject→True） | ✔ 人的决定，非策略分叉 |

**`policy_reasons` / `_confidence_review_reason` 调用点：** `review_policy_reasons` 有 `risk.py:70` 与 `graph.py:246` **两处**；`_confidence_review_reason` 仅 `graph.py:198` 一处。

**分叉判定（→ I-2）：** 唯一「同一决策算两遍」的是 §3.3：`task.review_required` 来自 `risk.py:75`（输入含 risk 内部追加的知识理由），而 `task.review_reasons_json` 来自 `graph.py:246`（输入为 `state["review_reasons"]`）。

- **今日是否已分叉？** 经推演：`risk.py:44` 追加的「未检索到足够可靠的知识依据」与 `graph.py:224`（retrieve 节点）追加的是**同一条**，且 `graph.evaluate_risk` 读取的 `state["review_reasons"]` 已包含它；视觉事件与 `risk_level` 两处一致。→ **当前两者结果一致，未观察到实际不一致。**
- **风险：** 两个调用点入参来源不同（risk 用「入参 `reasons`」，graph 用「state 快照」）。任何一方对 `reasons` 的追加逻辑变更（如新增仅在 `risk.evaluate` 内追加的理由），都会让 `review_required` 与 `review_reasons_json` 静默错配，并污染 `/analytics/overview` 的 `review_rate`（读 `review_required`）与 `review_reason_counts`（读 `review_reasons_json`）两个口径。→ 定为 **重要（潜在分叉）**。

`analyzable` 分叉：仅 `graph.py:523` 单点读取，无分叉。

---

## 6. 分级问题清单

### 阻断（0 项）
无。

### 重要（3 项）

**I-1 `review_required` 的确定性只是「就地降级」，仍透传依赖 LLM 的 `risk_level`。**
- 证据：`risk.py:112-115`（`risk_level ∈ {medium,high,review}` → 追加理由）→ `risk.py:75`（`bool(policy_reasons)`）。`risk_level` 来自 `llm.py:68` `RiskResult.model_validate(parsed)`，即大模型输出。`temperature: 0.0`（`llm.py:45`）降低但**不保证**确定性（跨 provider / 后端采样差异）。
- 影响：当 LLM 的 `risk_level` 在 `low` 与 `medium` 间抖动时，`review_required` 会随之翻转 —— 缺陷①的「非确定性」由「直接裁量」转为「经 `risk_level` 透传」，**未彻底根除**。
- 建议修法（只写在报告，不实施）：把转人工决策与 LLM 的 `risk_level` 解耦，例如引入后端可计算的确定性风险分（规则打分），或对 `risk_level` 做多次采样取众数 / 固定映射，使 `review_required` 完全由后端确定性函数决定。

**I-2 同一决策在两处各算一遍（`risk.py:70` 与 `graph.py:246`），存在静默分叉风险。**
- 证据：见 §3.3 / §5。`review_required` 与 `review_reasons_json` 事实上已是「一个策略、两次调用、两套入参」。
- 建议修法（不实施）：让 `RiskResult` 携带最终 `policy_reasons`（新增只读字段），`graph.evaluate_risk` 直接复用，删除第二处 `review_policy_reasons` 调用，保证单一事实来源。

**I-3 `_route_quality` 对缺失 `analyzable` 键的兜底方向偏向「继续」。**
- 证据：`graph.py:523` `quality.get("analyzable") is False` —— 若键缺失（返回 `None`），`None is False` 为假 → 走 `detect`。
- 现状：正常路径 `check_image_quality` 恒产出该键，且节点异常时 `state.get("error")` 会先短路到 `error`（`graph.py:520-521`），故当前不可达。
- 建议修法（不实施）：改为白名单判定 `return "detect" if quality.get("analyzable") is True else "review"`，使「未知」更保守。

### 建议（4 项）

**S-1 `output_schema["required"]` 过滤是死代码。** `risk.py:51-54` 无实际作用（`review_required` 带默认值，从不在 `required` 中，实测 `required=['risk_level','risk_score','problem_summary']`）。建议删除或加注释说明，避免误导。

**S-2 `review_policy_reasons` 对非 dict 视觉事件抛 `AttributeError`。** `risk.py:108` `event.get(...)`；实测 `vision_events=[None]` 抛 `AttributeError`。当前调用链恒为 `list[dict]`，不可达。建议加 `isinstance(event, dict)` 守卫。

**S-3 `blur_threshold=500` / 长边 1024 的标定不可由代码自证。** `config.py:83` 注释称「500 分离 audited soft sample 152.6 与 clear set 最低 622.1」，但样本集与复算不在代码内。代码层面 `_normalize_for_blur` 与阈值消费逻辑正确；**标定数值需 QA 用真实图片集复算**。

**S-4 双阈值量化闭环缺自动化回归。** `general_yolo_model_path` 由 `yolo26n.pt` 改为 `yolo26m.pt`（`config.py:52`；两文件均在 `models/`。实测 `yolo26m.pt` 44MB 存在）。模型切换会改变置信度分布，从而影响 `_confidence_review_reason` 的 AND 判定结果，但现有测试用 mock，未覆盖真实分布回归。

---

## 7. 我未能验证的部分（如实声明）

1. **未真实调用大模型**：无可用 `llm_api_key`，`temperature=0.0` 是否真能让目标 provider 输出稳定，**未实测**（仅确认参数已下发）。I-1 的确定性风险为静态推断，非实测。
2. **未复算质量标定数值**：`blur_threshold=500`、长边 1024 的「152.6 vs 622.1」来自 `config.py` / `scripts/check_image_quality.py` 注释与脚本，缺样本图，**未独立复算**（属 QA 职责）。
3. **未做端到端运行**：未启动 FastAPI / Qdrant，未通过 HTTP `/execute` 跑真实任务；`test_api.py` 的完整工作流断言依赖测试夹具，我**未独立重跑** `test_api.py`（仅跑了 `test_tools_and_services.py` 相关 6 例）。
4. **未集成验证 `check_risk_determinism.py`**：该脚本需运行中的服务与真实 LLM，**未执行**；其"修复后确定性"结论我无法背书。
5. **未评估模型切换影响**：`yolo26n→yolo26m` 对实测置信度分布与转人工率的影响未测（属架构师 / QA 职责）。
6. **未完整运行测试套件**：仅运行相关子集（6 passed）；完整 `pytest` 因依赖（qdrant/ultralytics/真实模型）未跑。

---

## 8. 只读自证

- 本次审核仅执行：`git status` / `git diff` / `git rev-parse`、`grep` / `sed -n` / `ls` 只读命令、`python - <<PY` 只读调用（不落盘）、`pytest -k`（测试只读）。**未执行任何 git 写操作，未修改任何被审文件。**
- 本报告 `docs/audit/engineer-review.md` 为唯一新增产物。
- 基线 `63df367`；被审改动仍处于工作区未暂存状态。
