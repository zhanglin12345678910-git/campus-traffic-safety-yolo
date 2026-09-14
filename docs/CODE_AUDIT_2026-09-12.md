# 代码审核报告 · Codex 未提交改动集

- **审核人**：WorkBuddy（应用户要求以「只读审核」身份进行）
- **审核时间**：2026-09-12 23:00–23:20（本地时间）
- **审核对象**：工作区**未提交**的改动集 —— 30 个已修改文件 + 3 个新增文件
  （基线 `63df367`，`git status` 显示 29 个 tracked 变更 + 3 个 untracked）
- **审核方式**：只读。**未修改任何源文件、未提交、未回滚、未重启服务。**
  执行的写入型动作仅有：运行后端测试（临时目录）、前端类型检查（产物已被 gitignore）。
- **约束声明**：本报告只提出发现与待核验任务，**修复由 Codex 执行**。

---

## 0. 结论速览

| 级别 | 数量 | 摘要 |
|---|---|---|
| 🔴 高 | **1** | 模型选型比对数据被**重复样本加权**，关键指标符号反转，且错误数字已写入 CHANGELOG |
| 🟠 中 | **3** | `general_yolo_review_conf` 未按上一轮要求重新标定；`models/yolo26m.pt` 不在版本控制；标定样本量仅 1 个告警样本 |
| 🟡 低 | **4** | 分析页未标注「当前模型」；根目录 `yolo26m.pt` 冗余 44MB；知识理由在 LLM payload 中重复；生产库仍为修复前数据 |
| ✅ 已核实无误 | **9 项** | 见第 5 节；另**主动撤回 2 条我自己的误判**（第 4 节） |

**四个缺陷的修复质量总体是高的**：修法对症、有针对性测试（新增 6 个）、44 passed、
`review_required` 已从大模型契约中摘除并改为无条件覆盖 —— 这是正确的根治方向。

**但有一条必须回炉**：模型选型的量化依据不成立（第 1 节）。它不影响「该不该换 medium」的方向，
却影响「该不该同时调阈值」这个**尚未执行的决策**。

---

## 1. 🔴 高：模型比对样本含大量重复图，结论被夸大且一处符号反转

### 1.1 用户问题的直接回答（顺带排除）

> 前端写的是 `yolo26n`，是不是有问题？我们用的不是 yolo11m 吗？

**不是 bug，前端显示是对的，而且项目里没有 yolo11m。** 证据链：

1. 截图的来源是 `frontend/src/pages/AnalyticsPage.vue:239-242`：
   ```js
   function modelLabel(role: string, name: string) {
     const roleName = role === 'traffic_sign' ? '交通标志' : role === 'general_object' ? '人员车辆' : role
     return `${roleName}\n${name.replace('.pt', '')}`
   }
   ```
   `name` 来自接口，**前端零硬编码**（`grep yolo26 / yolo11` 在 `frontend/src` 下 0 命中）。
2. 接口侧 `backend/app/api/router.py:348-357` 的 `model_rows` 是对 `detection_results`
   按 `model_role, model_name` 分组聚合 —— 而 `model_name` 是**检测发生当时**由
   `yolo.py:160` / `video_analytics.py:253` 写入的 `settings.general_yolo_model_path.name`。
   **即：它显示的是每条检测记录的历史来源，是「发生时的真相」，不是「当前配置」。**
3. 那张图里全是 `yolo26n`，是因为这些检测记录产生于**旧配置**（模型切换前）。
   `frontend/DESIGN.md:163` 已明文规定「历史记录中旧的 `yolo26n.pt` 与当前 `yolo26m.pt` 必须如实分开，
   **不得改写历史模型名称**」——所以这是**有意设计**，不是漏洞。
4. `models/yolo26m.pt` 的 **Birth = 2026-09-12 02:06:52**，即 Codex 本轮才把它从项目根拷入 `models/`；
   项目根 `yolo26m.pt` 的 Birth 是 2026-09-04。两份 SHA-256 相同（见 5.3）。
5. 全仓 `yolo11` 唯一命中是 `models/README.md:25` 里一个历史训练目录名
   `runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/weights/best.pt`。**不存在 yolo11m。**

> 残留疑虑（🟡 低）：切换模型后，新老记录会**并列成两根柱子**，图表不告诉你「哪根是当前模型」。
> `SettingsPage.vue:14-15` 只显示当前模型（读 `/health`）。建议在分析页图例或 Tooltip 标注当前模型，
> 但这属于 UX 打磨，非缺陷。

### 1.2 真正的问题：比对数据的样本不独立

`scripts/compare_general_models.py` 的输入是 `uploads/inspections/` 下 **glob 到的全部图片（15 个）**，
**脚本内没有任何去重**（`git diff` 确认本轮只改了路径与文档串）。

对这 15 个文件做 MD5 取证 —— **只有 10 张唯一图片**：

```
文件数: 15      唯一图片数: 10

[重复 x3]  dormitory-road-c49d63487609.jpg
           tt100k-dormitory-road-172a1148bbf9.jpg
           tt100k-dormitory-road-747ac84e5621.jpg
[重复 x3]  demo-r5-a7d2a7d9e6b6.jpg
           dormitory-crowd-a79bfe7b55e5.png
           dormitory-crowd-ba637029e751.png
[重复 x2]  demo-r1-147636384369.jpg
           IMG_9781-f97235ed242c.jpg
```

用 `outputs/general_model_comparison.json` 的 `raw` 明细重算（**同一张图只算一次**），
方法与被测脚本一致（对 15 文件复算能得到脚本记录的 61/7、91/11、22、25，证明口径相同）：

| 指标 | 记录值（15 文件） | **去重值（10 唯一图）** | 影响 |
|---|---|---|---|
| 检出总数 nano → medium | 61 → 91（**+49%**） | **35 → 47（+34%）** | 夸大 |
| 有检出的图片数 | 7 → 11 | **5 → 7** | 夸大 |
| 修复的「完全漏检」图 | 4 张 | **2 张** | 夸大 |
| **低于 0.35 阈值的检出数** | 22 → 25（**变差**） | **12 → 11（变好）** | ⚠️ **符号反转** |

**为什么这条重要：**

- 「4 张图修复漏检」里，`dormitory-road` 那一张**被算了 3 遍**（3 个同图文件），
  它恰好是 nano 检出 0、medium 检出 5 的具体案例 → 数量被三倍计。
- 上一轮据此写下的结论是
  > 「medium 补的是**召回率**，**不是**置信度……低置信度总数反而 22→25」
  去重后**这个结论不成立**：低置信度检出数实际是 **12 → 11（略降）**。
  换言之 medium **同时**改善了召回与低置信占比，只是幅度都不大。
- 错误数字**已经写进正式文档**，会被后续接手方当作既定事实：
  - `docs/CHANGELOG.md:7`：「15 张真实图片同口径检出 61 → 91，覆盖 7 → 11 张」
  - `docs/HANDOFF.md`（Codex 新增的 C 节）：「nano 61 个检出 / 覆盖 7 张，medium 91 个检出 / 覆盖 11 张，检出量提升 49%」
  - `models/README.md`：「其检出总数比 nano 高 49%」
- 该数据正是**阈值重新标定**的依据来源（见 2.1），而标定尚未执行 → **现在纠正代价最小。**

**建议修复（交 Codex）：**

1. `scripts/compare_general_models.py` 增加**按内容哈希去重**（读入时对 bytes 做 MD5/SHA-256，
   同哈希只保留一个代表，并在报告中列出被合并的文件名与数量）。
2. 重跑并更新 `outputs/general_model_comparison.json`。
3. 用去重后的数据**修正** `docs/CHANGELOG.md`、`docs/HANDOFF.md`、`models/README.md` 里的三处数字，
   并明确标注「按 10 张唯一图片统计」。
4. 若扩样，请从 `校园照片/`（58 张 JPG + 4 PNG，**未被此前的比对使用**）补充独立样本，
   把样本量抬到 ≥30 张唯一图后再定阈值 —— 当前 10 张不足以支撑阈值决策。

---

## 2. 🟠 中：三处需处理的遗留

### 2.1 `general_yolo_review_conf` 未按上一轮要求重新标定

上一轮 HANDOFF 明确写过：「换 `GENERAL_YOLO_MODEL_PATH` 为 `yolo26m.pt` + **下调
`general_yolo_review_conf`（当前 0.35）**，两者缺一不可」。

本轮 `config.py` 只改了模型路径，`general_yolo_review_conf: float = 0.35` **原值未动**
（`git diff backend/app/config.py` 中该项为未变更的上下文行）。

缓冲因素：低置信度规则本轮同时被改（见 3.3），从「存在任意低置信即复核」改为
「全部低于阈值才复核」，这**部分替代**了降阈值的收益。所以不是漏改，而是**决策被推迟且未记录**。

**建议**：要么用去重后的分布重新标定 0.35；要么在 HANDOFF 明确写下
「决定不调阈值，理由 = 低置信度规则已改为 all-below 语义」——**不能留着不表态**。

### 2.2 `models/yolo26m.pt` 不在版本控制 —— 已在文档注明，但无自动守卫

- `.gitignore:21` 的 `*.pt` 使该权重**不可能进入 git**（`git check-ignore` 已确认）。
- `.dockerignore` 也排除 `models/*.pt`；`docker-compose.yml:63` 用
  `./models:/app/models:ro` **bind mount**，因此**交付机器的宿主目录必须有这个 44MB 文件**。
- Codex 已在 HANDOFF C 节与 `models/README.md` 写明「交付机器必须保留 `models/yolo26m.pt`」——
  **文档层面已尽职**。

**已核实的缓冲（这条比我预想的安全）**：若该文件缺失，
`yolo.py:115` 会抛 `YOLOToolError`，`yolo.py:148-166` 捕获后写入 `models[].error`，
`graph.py:204-210` 再把
「通用人员车辆模型暂不可用，交通标志模型已继续完成检测」
追加为**复核理由** → 任务进人工复核并**显式说明原因**。
**不是静默降级。**（该 `model_failures` 是 HEAD 里已有的代码，非本轮新增。）

**建议**：加一条启动自检 —— 若 `general_yolo_enabled` 为真而权重不存在，
让 `/health` 的 `general_yolo.configured=false` 并让 Settings 页显红（目前该字段语义见 5.6）。

### 2.3 `blur_threshold = 500` 的标定只有 1 个告警样本

去重后（同一结论）：**1 个告警样本（`tt100k-10132`，152.6）** vs **5 个不同的通过值**
（622.1 / 791.8 / 902.8 / 966.1 / 1010.3 / 2303.7 / 3627.4 / 3842.7 / 4060.6）。

阈值 500 落在 152.6 与 622.1 之间的空隙里，可用，但：
- 该空隙宽达 469，**500 偏向上沿**（距通过组下界仅 122，距告警样本 347）→ 偏保守、易误告警。
- 只有 1 个负样本，**无法估计误告警率**。
- 好在新的语义下「告警」只追加复核理由、不再短路（见 3.4），**误告警代价低**，所以可接受。

**建议**：不必立刻改，但应在 HANDOFF 记录「阈值 500 由 1 正 1 负样本空隙中点取得，
样本不足，待 ≥30 张唯一图后复核」。另建议把阈值写成
`(152.6 + 622.1) / 2 ≈ 387` 或直接取几何中点，使两侧裕度对称。

---

## 3. 四个缺陷的修复质量评估

### 3.1 缺陷 1 `review_required` 非确定性 —— ✅ 修法正确

三层改动，方向正确：

1. `risk.py:46-54` 把 `review_required` 从传给大模型的 `output_schema` 中**摘除**；
2. `risk.py:75` 改为 `result.review_required = bool(policy_reasons)` —— **无条件覆盖**，
   不再有「reasons 为空时原样放行模型返回值」的分支；
3. `llm.py:44` `temperature` 0.1 → **0.0**；`llm.py:35` prompt 改为
   「信息不足时必须将 risk_level 设为 review……**是否转人工由后端确定性策略决定，不由大模型自由裁量**」。

**我特别验证过的一个潜在坑（结论：安全）**：既然 schema 里删掉了 `review_required`，
模型就不会返回该字段 —— 若 `RiskResult.review_required` 是**必填**，反序列化会抛 ValidationError，
整条 LLM 路径会静默掉进规则兜底。实测 `schemas.py:32` 是 `review_required: bool = False`（**有默认值**）
→ 不会失败。且即使模型仍返回该字段，`risk.py:75` 也会覆盖它。**两条路都堵住了。**

**需要产品拍板的一点（请确认）**：`risk.py:88-114` 的 `review_policy_reasons` 实现的是
**策略 B** ——`risk_level ∈ {medium, high, review}` 一律转人工，只有
「无复核理由 + 无视觉事件 + low」才自动闭环。docstring 写的是
「the **approved** balanced review policy (policy B)」。
**如果 B 是你选定的，请回复确认；如果不是，这属于 Codex 自行拍板的产品决策，需要回退重做。**

### 3.2 缺陷 2 `status` / `risk_level` 语义重叠 —— ✅ 结构性消解

现在 `task.review_required`（`graph.py:425` 取自 `risk.review_required`）与
`task.review_reasons_json`（`graph.py:426` 取自同一 policy 的输出）**同源同算**，
所以「`review_required=True` 而 `review_reasons=[]`」在构造上不可能再出现。

我一开始怀疑这条**没修干净**并找到了看起来成立的路径（见 4.1），**经核实是我错了**，已撤回。

### 3.3 缺陷 3 转人工率高 —— 🟡 部分修复

已做：`graph.py:526-549` 的 `_confidence_review_reason` 把「存在任意低置信度检测即复核」
改为「**全部检测都低于各自阈值才复核**」，并保留候选框可见。这条改动是**对症**的 ——
原先一个 0.34 的框就能把整张有高置信证据的图拖进复核队列。

未做：阈值重新标定（见 2.1）。

### 3.4 缺陷 4 图片质量护栏误判 + 短路 —— ✅ 修法正确，且实测复现

- `image_quality.py:47-71`：先按**长边归一化到 1024** 再算 Laplacian 方差，
  同时保留 `blur_score_raw`；降采样用 `INTER_AREA`（正确选择），升采样用 `INTER_CUBIC`。
- `image_quality.py` 新增 `analyzable` 字段：**只对无法解码的图片为 False**。
- `graph.py:519-523` `_route_quality` 改判 `quality.get("analyzable") is False`
  → **质量告警不再短路，检测/检索/研判照常执行**，「降级而非短路」落地。
- 无法解码时仍短路到 `manual_review`（合理）。

**我独立复跑 `scripts/check_image_quality.py` 的实测结果（与 Codex 声明一致）：**

```
tt100k-10132-bfaa4790f351.jpg    47.9 → 152.6   质量告警 <<<
IMG_9794-b7120025621a.jpg        64.7 → 1010.3  通过     ← 上一轮的误判样本已恢复
IMG_9769-eb284c099f6f.jpg       264.6 → 4060.6  通过
IMG_9759-de44188b5e43.jpg      2077.6 → 3627.4  通过
通过组归一化区间：622.1 ~ 4060.6
产生质量告警 1 张 / 判定通过 14 张
```
Codex 声明的「15 张中 14 张通过、只有已知柔焦样本告警」**属实** ✓

---

## 4. 主动撤回：我自己提出又被自己推翻的两条（记录以免 Codex 白忙）

审核过程中我有两条怀疑，**经核实均不成立**，如实记录：

### 4.1 「两处策略调用输入不同 → 会重新造出缺陷 2」—— ❌ 不成立

我的推理：`risk.py:32` 的 `reasons` 是局部副本，`risk.py:44` 把
「未检索到足够可靠的知识依据」追加进副本；而 `graph.py:246-250` 重新计算 `review_reasons` 时
传的是 `state.get("review_reasons")` —— 若 state 里没有这条理由，两处就会分叉，
产出「`review_required=True` 但 `review_reasons=[]」的缺陷 2 症状。

**推翻依据**：`graph.py:215-232` 的 `retrieve_knowledge` 节点**自己也会**在 `not hits` 时
把同一条理由追加并 `return {... "review_reasons": reasons}` **写回 state**。
所以 `evaluate_risk` 拿到的 state 已经包含该理由，**两处输入实际相同，不分叉**。

（曾用 `RiskAssessmentService.review_policy_reasons` 单独喂两种输入验证过「若输入不同则结果不同」，
但那只是证明了函数本身是纯函数，**不等于真实链路会分叉**。特此更正。）

### 4.2 「通用模型缺失会静默降级、漏报人员聚集」—— ❌ 不成立

推翻依据见 2.2：`graph.py:204-210` 会把通用模型失败转成显式复核理由。该防护在 HEAD 中已存在。

---

## 5. 已核实无误的检查项

| # | 检查项 | 结论 | 证据 |
|---|---|---|---|
| 5.1 | 后端测试 | ✅ **44 passed / 31.95s**（原 36 → 新增 8） | 实跑，`-p no:cacheprovider --basetemp=/tmp` |
| 5.2 | 前端类型检查 | ✅ **强制全量 `vue-tsc -b --force` 退出码 0、零错误** | 实跑（首次无意中用了增量缓存，已用 `--force` 重验） |
| 5.3 | 权重 SHA-256 声明 | ✅ 源/目标**逐字节一致** | 实算 `401CEA9A…D0B7`，与 Codex 声明完全吻合 |
| 5.4 | 前端无写死业务数值 | ✅ `AnalyticsPage.vue` 无演示数字，符合 `DESIGN.md` 第 6 节铁律 | 逐行检索，命中项全为样式/图表配置 |
| 5.5 | 接口鉴权一致性 | ✅ 新接口遵循既有约定 | 全部 `POST/DELETE` 带 `require_api_key`（8 个），全部 `GET` 不带；新 `GET /analytics/overview` 一致 |
| 5.6 | 前后端接口契约 | ✅ 路径一致 | `api.ts` 的 `getAnalyticsOverview()` → `/analytics/overview` ↔ `router.py:304` |
| 5.7 | 模型名残留一致性 | ✅ 无 stale 引用 | 全仓 `yolo26n` 命中项均为历史/测试/明确标注语境；`frontend/src` 下 0 命中 |
| 5.8 | 新增测试针对性 | ✅ 精准覆盖 4 个修复点 | 见下方列表 |
| 5.9 | 新代码端到端执行过 | ✅ 有证据 | `runtime_acceptance_20260912_b.db` 内 1 条评估：`review / score=30 / review_required=1 / analysis_mode=llm` |

新增测试（`git diff backend/tests/`）：
```
test_quality_warning_continues_detection_and_analysis      ← 缺陷 4「降级而非短路」
test_low_confidence_candidates_only_force_review_when_all_are_unreliable  ← 缺陷 3 规则
test_image_quality_normalizes_resolution_before_blur_scoring  ← 缺陷 4 归一化
test_risk_review_policy_is_deterministic_and_ignores_llm_boolean  ← 缺陷 1
test_risk_review_policy_requires_confirmation_for_non_low_levels  ← 策略 B（参数化）
test_analytics_overview_uses_persisted_tasks_detections_and_agent_steps  ← 新接口
```

---

## 6. 🟡 低优先级发现

1. **生产库仍持有修复前的数据**：`backend/data/campus_safety.db` 里 2 个任务
   （`432306cb`、`4edb2f27`）是 `review_required=True` + `review_reasons=[]` 的旧症状数据；
   最近一次执行时间是 **2026-09-11 22:52（本地）**，即上一轮 WorkBuddy 的重跑，
   **修复后的代码从未在生产库上跑过真实任务**。→ 修完后应重跑一遍让数据自证。
2. **根目录 `yolo26m.pt` 与 `models/yolo26m.pt` 双份**，合计冗余 44MB；建议删除根目录那份并
   在 README 注明唯一正确位置。
3. **知识未命中时理由重复**：`risk.py:32` 已 `dict.fromkeys` 去重，
   但 `risk.py:44` 又 append 一次同一字符串（因 `retrieve_knowledge` 已写入 state），
   导致传给大模型的 `required_review_reasons` 里同一理由出现两次。
   对最终 `review_reasons` 无影响（`review_policy_reasons` 会再去重），属脏但无害。
4. **时区陷阱（给后续排查者）**：数据库时间戳是 **UTC**，文件 mtime 是本地时间，
   两者差 8 小时。例如生产库最后执行 `2026-09-11 14:52`（UTC）= 本地 `22:52`。
   **排查时不要据此误判「今天没跑过」。**（我本人先踩了一次。）

---

## 7. 未验证项（诚实声明，不构成结论）

| 项 | 原因 |
|---|---|
| Codex 声明的「**连跑 3 次**均得 score=30」 | `risk_assessments` 每次执行**覆盖**而非追加（11 任务 ↔ 11 条），**无法从库里数出轮次**。只能确认「存在一次 score=30 的执行」，不能独立证实 3 次一致。 |
| 浏览器验收「6/6 通过」「0 页面/控制台/网络错误」 | 需要 Playwright + 已启动的前后端；**当前两个服务均已停止**（无 python/node 进程），本轮未复跑。 |
| Docker 运行态验收 | 与 Codex 一致：本机 Docker 守护进程未起，未执行。 |
| 前端视觉还原度（与参考图同屏比对） | 主观项，非本轮审核范围。 |
| `frontend/scripts/e2e_existing_features.py` 的 61 行改动 | 仅做了语法级浏览，未逐行审计；建议 Codex 自查该文件的断言是否被放宽。 |

---

## 8. 交给 Codex 的任务清单（按优先级）

### P0 — 必须回炉
- [ ] **T1** `compare_general_models.py` 增加内容哈希去重；重跑并覆盖
      `outputs/general_model_comparison.json`（记录被合并的文件名与数量）。
- [ ] **T2** 依据去重结果修正 `docs/CHANGELOG.md:7`、`docs/HANDOFF.md`（Codex 新增 C 节）、
      `models/README.md` 三处数字，标注「按 N 张唯一图片统计」。

### P1 — 需决策或补强
- [ ] **T3** 用去重分布重新标定 `general_yolo_review_conf`（当前 0.35）；
      **或**在 HANDOFF 明确记录「决定不调，理由 = 低置信度规则已改为 all-below 语义」。二选一，不可留空。
- [ ] **T4** 在 HANDOFF 记录 `blur_threshold=500` 的标定依据与样本不足的事实，
      并考虑把阈值改为两侧裕度对称的取值（如 387）。
- [ ] **T5** 用修复后代码在**生产库**重跑全部 11 个任务，让 `campus_safety.db` 自证；
      重跑前先备份，重跑后确认不再出现 `review_required=True` + `review_reasons=[]`。

### P2 — 打磨
- [ ] **T6** 分析页在「双模型贡献」图例或 Tooltip 标注哪个是**当前**模型
      （历史名不得改写，这是 DESIGN.md 的要求，只是缺一个提示）。
- [ ] **T7** 删除项目根冗余的 `yolo26m.pt`（44MB），README 注明唯一正确路径为 `models/yolo26m.pt`。
- [ ] **T8** 消除 `risk.py:44` 造成的理由重复（与 `retrieve_knowledge` 的重复追加合并为一处）。
- [ ] **T9** 自查 `frontend/scripts/e2e_existing_features.py` 的 61 行改动，确认断言未被放宽。

### 需用户回答（不是 Codex 能决定的）
- [ ] **Q1** 策略 B（`medium/high/review` 一律转人工，仅「low + 无理由 + 无视觉事件」自动闭环）
      是**你拍板的**吗？若是，请在 HANDOFF 记录决策来源；若不是，需回退重选。
- [ ] **Q2** 是否接受「本轮不动 `general_yolo_review_conf`」这个决定（见 T3）？

---

## 9. 附：本轮审核执行过的命令（可复现）

```bash
# 测试（临时目录，不污染项目）
cd backend && <yolo_change python> -m pytest -q -p no:cacheprovider --basetemp=/tmp/pytest-audit
# → 44 passed in 31.95s

# 前端类型检查（强制全量，产物已被 gitignore）
cd frontend && <node> ./node_modules/vue-tsc/bin/vue-tsc.js -b --force --pretty false
# → 退出码 0

# 质量护栏复跑（只读）
<yolo_change python> scripts/check_image_quality.py
# → 1 告警 / 14 通过

# 样本去重取证（只读）
md5sum uploads/inspections/*  → 15 文件 / 10 唯一

# 权重一致性（只读）
sha256(yolo26m.pt) == sha256(models/yolo26m.pt) == 401CEA9A…D0B7
```

> 再次确认：本报告**未修改任何源文件、未执行 git 提交/回滚、未重启或启动任何服务**。
