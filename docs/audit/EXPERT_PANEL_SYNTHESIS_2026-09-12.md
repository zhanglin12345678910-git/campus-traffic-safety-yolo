# 专家团审核汇编报告 · 安巡智脑 Codex 改动集

- **审核对象**：Codex 未提交改动集（基线 `63df367`，工作区 36 项变更）
- **审核性质**：只读审核（Read-Only）。**未修改任何源码 / 配置 / 测试 / 脚本 / 模型 / 已有文档**
- **审核方式**：SoftwareCompany 专家团并行分域审核，主理人齐活林（交付总监）汇编
- **时间窗口**：2026-09-12 23:2x – 23:3x
- **分域报告**：
  - `docs/audit/engineer-review.md`（工程师 寇豆码）
  - `docs/audit/architect-review.md`（架构师 高见远）
  - `docs/audit/pm-review.md`（产品经理 许清楚）
  - `docs/audit/qa-review.md`（QA 严过关）
  - 本文（主理人汇编）

---

## 0. 只读自证

| 证据 | 结果 |
|---|---|
| 已跟踪文件 mtime 上限 | **22:53**（专家团 23:2x 启动，全部早于审核） |
| 审核窗口内新增内容 | **仅 `docs/audit/` 4 份报告**（mtime 23:30–23:32） |
| 审核窗口内 `outputs/general_model_comparison.json` | mtime **未变**（仍 Sep 12 02:08），未被重跑覆盖 |
| git 写操作 | 无 add / commit / stash / checkout / 建分支 |
| 结论 | **只读约束 100% 遵守** |

> 附注：`git status --porcelain` 行数在审核前后由 29 → 36。逐项按 mtime 排查，多出的 7 项来自 Codex 在 **21:40–22:52** 的既有改动（3 个 `scripts/*.ps1`、`README.md`、`docs/TEST_REPORT.md` 等），**全部早于本次审核**，非专家团所为。

---

## 1. 结论速览

### 1.1 四方分级汇总

| 分域 | 阻断 | 重要 | 建议 | 一句话 |
|---|---|---|---|---|
| 工程师（代码正确性） | 0 | 3 | 4 | 缺陷 ①④ 已修（①略打折），②完全未触及，③部分改善 |
| 架构师（拓扑/部署） | 0 | 3 | 4 | 拓扑结论成立、短路风险已消除；部署前置条件未声明 |
| 产品经理（策略合理性） | 0 | 2 | 2 | 策略 B 方向对但边界过宽，且**无用户批准依据** |
| QA（测试/取证） | 0 | 3 | 4 | 44 passed 可复现；**量化声明符号反转** |
| **合计（去重后）** | **0** | **7** | **8** | 无崩溃级问题，但存在 1 项数据错误 + 1 项根因未除 |

### 1.2 四缺陷修复评估（合并四方结论）

| # | 缺陷 | 评级 | 依据 |
|---|---|---|---|
| ① | `review_required` 非确定性 | 🟡 **部分修复** | 大模型直接裁量已消除（`risk.py:75` 无条件覆盖），但决策**透传依赖 LLM 的 `risk_level`**，`temperature=0.0` 只降不除 |
| ② | `status` / `risk_level` 语义重叠 | 🟡 **结构性消解、无回归锚** | 职责已收敛到后端策略，但**无专属回归测试**（QA 缺口①） |
| ③ | 转人工率过高 | 🟡 **未改善** | `general_yolo_review_conf=0.35` 未重标定；策略 B 边界过宽 |
| ④ | 图片质量护栏误判 + 短路 | 🟢 **已修复** | 归一化 + 阈值 500；短路解除（14 通过 / 1 告警，未过松） |

---

## 2. 交叉印证矩阵（本轮最硬的证据）

同一结论由**不同专家、不同路径独立得出**，可信度显著高于单人审核。

| 结论 | 工程师 | 架构师 | PM | QA | 主理人 | 强度 |
|---|:--:|:--:|:--:|:--:|:--:|---|
| 全链路仅 2 个跳 `manual_review` 的短路点 | ✔ | ✔ | — | — | ✔ | **三方独立** |
| 缺陷①只是「把非确定性从 A 字段搬到 B 字段」 | ✔ | — | ✔ | — | — | **两方独立** |
| `review_policy_reasons` 被调用两次 | ✔ | ✔ | — | — | — | **两方独立** |
| 模型比对因重复样本被夸大 | — | — | — | ✔ | ✔ | **两方独立** |
| 根目录 `yolo26m.pt` 冗余（同 sha256） | — | ✔ | — | ✔ | ✔ | **三方独立** |
| `schemas.py:32` 有默认值 → 反序列化不炸 | ✔ | — | — | — | ✔ | 两方 |
| 模型权重不入版本控制 → 部署需自带 | — | ✔ | — | — | — | 单方 |
| 生产库仍是修复前数据 | — | — | ✔ | ✔ | — | **两方独立** |

---

## 3. 必须上报的合并发现

### 🔴 A-1【数据错误·最高优先】模型比对结论符号反转

**发现人**：QA（独立复算）+ 主理人（上轮初查）

`scripts/compare_general_models.py` 直接 `glob` 整个 `uploads/inspections/`，**零去重**。实测 MD5 取证：**15 个文件 = 10 张唯一图片**（3 组重复：`dormitory-road`×3、`demo-r5`/`dormitory-crowd`×3、`IMG_9781`/`demo-r1`×2）。

QA 先用 15 文件口径**精确复现**出记录值（61/7/22 与 91/11/25），再去重重算 —— 口径与脚本一致，故重算可信：

| 指标 | 记录值（15 文件） | 去重值（10 唯一图） | 性质 |
|---|---|---|---|
| 检出总数 | 61 → 91（+49%） | **35 → 47（+34%）** | 幅度夸大 |
| 有检出图片数 | 7 → 11 | **5 → 7** | 夸大 |
| 修复漏检图数 | 4 | **2** | `dormitory-road` 被 3 倍计 |
| **低于 0.35 检出数** | **22 → 25（变差）** | **12 → 11（变好）** | ⚠️ **符号反转** |

**定性方向仍成立**（medium 提升召回、修复漏检），但幅度被夸大，且「低于阈值变差」这一结论**反了**。

**错误数字的完整扩散清单**（主理人于汇编后追加一轮全仓 grep，**实测为 7 个位置 / 5 个文件**——此前 QA 与本报告只点了 3 处，漏了 `TEST_REPORT.md` 与根 `README.md`）：

| # | 位置 | 原文片段 |
|---|---|---|
| 1 | `docs/CHANGELOG.md:7` | 「15 张真实图片同口径检出 61 → 91，覆盖 7 → 11 张」 |
| 2 | `docs/HANDOFF.md:94`（Codex 新增 C 节） | 「nano 61 个检出 / 覆盖 7 张，medium 91 个检出 / 覆盖 11 张，检出量提升 **49%**」 |
| 3 | `docs/HANDOFF.md:323`（**历史轮次**表格） | 「\| 检出总数 \| 61 \| **91**（**+49%**）\|」 |
| 4 | `docs/HANDOFF.md:341`（**历史轮次**） | 「❌ **总低置信度 22 → 25**」 |
| 5 | `models/README.md:6` | 「真实校园图片对比中其检出总数比 nano 高 **49%**」 |
| 6 | `docs/TEST_REPORT.md:653` | 「\| 总检出数 \| 61 \| 91 \| **+49%** \|」 |
| 7 | `README.md:12` | 「medium 相比 nano 的检出总数由 61 提升至 91（**+49%**）」 |

> 注意 #3/#4 位于 HANDOFF 的**历史轮次**区。按本项目「不删历史轮次」的惯例，应**加批注**（指向本报告）而非直接改写历史记录；#1/#2/#5/#6/#7 属当前有效文档，须直接更正。

**已排除脚本造假的可能**：QA 现场重跑 2 张图双模型推理，结果与 `outputs/general_model_comparison.json` **逐值完全一致** → JSON 本身真实，问题只出在**样本未去重**。

---

### 🔴 A-2【根因未除】缺陷① 的确定性只是「就地降级」

**发现人**：工程师 I-1（静态推断）+ PM（独立同向结论）

- **工程师路径**：`risk.py:75` 的无条件覆盖确实消除了 LLM 直接裁量（FakeLLM 谎报 `True` 也被覆盖，实测通过）；但 `risk.py:112`「`risk_level ∈ {medium,high,review}` 即转人工」使最终决策**透传依赖 LLM 输出的 `risk_level`**。`temperature=0.0` 只降低波动、**不消除** —— `risk_level` 在 `low/medium` 之间抖动时，`review_required` 照样翻转。
- **PM 路径**：`llm.py:35` 的 prompt 要求「信息不足时必须把 risk_level 设为 review」，实测 **8/11（73%）** 任务 LLM 直接给 `review` → 策略 B 的**结构化下限被钉死在大模型的不确定率上**，保守度一点没降。

**合并结论**：缺陷① 的「非确定性」被从 `review_required` 字段**转移**到了 `risk_level` 字段，而非消除。这与 `AX-20260911-0B6FF9` / `AX-20260910-81C7D0` 那组「检测结果逐位相同但 `review_required` 一个 False 一个 True」的历史症状同源。

**待办**：让 `risk_level` 也走确定性规则（例如由 `risk_score` 阈值 + 视觉事件类型机械推导，不由 LLM 输出），或接受并**显式记录**残留非确定性。
**注**：工程师的该结论为**静态推断**，无 API key 未真实调 LLM，未实测 —— 见 §6。

---

### 🟠 B-1【单一事实源】`review_policy_reasons` 双处计算

**发现人**：架构师 I-1 + 工程师 I-2

同一策略被算两遍：`risk.py:70` 与 `graph.py:246` 各调一次。

| | 生产方 | 消费方 |
|---|---|---|
| `task.review_required` | `risk.py:70`（含 risk 内部追加的知识理由） | 落库 |
| `task.review_reasons_json` | `graph.py:246`（state 快照） | 落库 |

**当前幂等无分叉**（入参经比对一致：`risk_level`/`vision_events` 同源；`review_reasons` 仅差一个已被上游 `retrieve_knowledge` 写入、且被 `dict.fromkeys` 去重的字符串）。

**风险**：属「一个策略、两次调用、两套入参」。未来任一侧改追加逻辑即**静默错配**，并**污染 `/analytics` 的 `review_rate` 与 `review_reason_counts` 两个口径**。

**建议**：`evaluate()` 回传策略结果，`graph` 消费不再重算。

---

### 🟠 B-2【流程缺口】策略 B 无用户批准依据

**发现人**：PM（工程师、架构师未覆盖此角度）

- `risk.py:98` 的 docstring 写「the approved policy B」—— **代码自述，非批准记录**。
- 仓内检索结果：`docs/CODEX_KICKOFF_PROMPT.md:107` 用户原话明确「缺陷1涉及产品决策，**不要自己定**，要列出选项让我选」；`git log` 无选型记录；`.workbuddy/memory/` 同；`docs/CODE_AUDIT_2026-09-12.md` 的 Q1 独立提出同一质疑。
- **判定：Codex 自行拍板。** 方向（后端确定性替代 LLM 裁量）与用户诉求一致，但**具体边界未经确认**。

---

### 🟠 B-3【部署】模型权重不入版本控制，切换后需人工准备

**发现人**：架构师 I-2

- `.gitignore:19-21` 排除 `models/*` 与 `*.pt`；`.dockerignore:15-18` 同样排除；`Dockerfile` 无 `COPY` 模型；`docker-compose.yml:63` 靠 bind mount `./models:/app/models:ro`。
- **切换 `yolo26n.pt`(5.5MB) → `yolo26m.pt`(44MB) 后，部署机必须自带该文件**，否则路径失效。
- **未写入任何部署文档**（`DEPLOYMENT` / `README`）。
- 附：根目录存在 `yolo26m.pt` 与 `models/yolo26m.pt` **sha256 完全相同**（`401cea9a…`），配置只引用后者 → 根目录那份 44MB 属冗余。

---

### 🟠 B-4【性能无实测】默认跑 CPU

**发现人**：架构师 I-3

`docker-compose.yml:46` 默认 `YOLO_DEVICE=cpu`。medium 在 CPU 上的延迟高于 nano；「双模型显存远小于 12.5GB」是**量级估算，非实测**。需以 `nvidia-smi` 取证。

---

### 🟡 C 组（建议级，摘要）

| # | 问题 | 发现人 | 位置 |
|---|---|---|---|
| C-1 | 测试回归缺口 5 项（见 §4） | QA | `backend/tests/` |
| C-2 | `graph.py:523` 兜底方向不保守：`quality.get("analyzable") is False`，键缺失→`None is False`→假→走 detect。当前不可达，但出错时倾向"继续跑"而非"转人工" | 工程师 I-3 | `graph.py:523` |
| C-3 | 死代码：`risk.py:51-54` 过滤 `required`。实测 `required=['risk_level','risk_score','problem_summary']`，`review_required` 带默认值从不在其中 | 工程师 S-1 | `risk.py:51-54` |
| C-4 | `risk.py:108` 对非 dict 视觉事件抛 `AttributeError`（实测 `[None]` 即抛）。当前调用链恒 `list[dict]`，不可达 | 工程师 S-2 | `risk.py:108` |
| C-5 | Analytics 页未标注「当前配置模型」；历史 `yolo26n` 与当前 `yolo26m` 分列两根柱是**忠实历史**、符合 `frontend/DESIGN.md:163` | 架构师 S-2 | `AnalyticsPage.vue:239-242` |
| C-6 | `/analytics/overview` 未挂 API key（与 `/dashboard` 既有约定一致，仅提示） | 架构师 S-4 | `router.py:304` |
| C-7 | `frontend/scripts/e2e_existing_features.py` 改动 +61 行，断言是否被放宽**未逐行审计** | QA | — |

---

## 4. 测试充分性（QA 独立复跑）

| 项目 | 结果 | 命令 |
|---|---|---|
| 后端 pytest | **44 passed / 0 failed，16.96s** | `cd backend && <py> -m pytest -p no:cacheprovider --basetemp=/tmp/pytest-qa-edward -q` |
| 前端类型检查 | **退出码 0、零输出** | `vue-tsc -b --force` |

**工具坑（可复用经验）**：
- pytest 的 `--basetemp` **必须用全新唯一路径**。固定路径 `/tmp/pytest-audit` 第二次跑会崩（`SystemExit:1`，41 errors）—— 该目录被上轮 56 个临时目录占满，pytest 会话开始时 `rmtree` 它 → 命中沙箱 >50 项批量删除守卫。
- `vue-tsc -b` 增量模式会**假通过**（空输出骗人），必须 `--force`。

**覆盖映射：6 个新测试覆盖 4 个缺陷中的 3 个**（①③④ 精准）。

**回归缺口 5 项**：
1. 缺陷②（`status`/`risk_level` 重叠）无专属回归；无测试断言 `review_required=True ⇒ reasons 非空`。
2. `review_policy_reasons` 的「视觉事件」分支**零覆盖**。
3. `analyzable=False` 短路路径无测试。
4. `general_yolo_model_path` 改 medium 后无回归锚。
5. `_review_reason_category` 7 类仅测 2 类。

---

## 5. 已核实无误（正面结论，供 Codex 免于返工）

| # | 结论 | 证据 |
|---|---|---|
| 1 | 短路点结论成立：仅 `_route_validation`(`graph.py:515-516`) 与 `_route_quality`(`graph.py:519-523`)，`check_detection_result→retrieve_knowledge` 为无条件边(`graph.py:85`, `add_edge`) | 架构师 + 工程师 + 主理人三方独立 |
| 2 | 短路风险已消除：`_route_quality` 改读 `image_quality.analyzable`，写入方仅解码失败为 `False`(`image_quality.py:30`)、能解码一律 `True`(`:77`) | 架构师 + 工程师 |
| 3 | `_confidence_review_reason` **确为 AND 语义**。推演表：空→None；单过阈值→None；单不过→触发；**混合一过一不过→None**；全不过→触发；恰等阈值→None | 工程师逐字核验 |
| 4 | 全仓无残留旧「任一低即复核」调用方（仅 `graph.py:198` 一处调用） | 工程师 grep |
| 5 | **反序列化不会炸**：`schemas.py:32` `review_required: bool = False` 仍有默认值，缺字段实测得 `False`、给 `True` 也接受（`llm.py:68 model_validate`） | 工程师 + 主理人 |
| 6 | `llm.py` system prompt 全文**无 `review_required` 字样**，schema 已摘除 → 无残留要求、无多余 token、无歧义 | 工程师 |
| 7 | `_normalize_for_blur` 正确（降采样 `INTER_AREA`/升采样 `INTER_CUBIC`，同一 scale → 保留长宽比）；`blur_score` 确实基于归一化灰度 | 工程师 |
| 8 | `analyzable` 下游**仅 `graph.py:523` 一处消费**，前端与落库均不消费 → 语义收窄无连带影响 | 工程师 |
| 9 | 质量护栏**未过松**：14 通过 / 1 告警（`tt100k-10132`=152.6）。阈值 500 落在 152.6 与通过组下界 622.1 之间，分类合理。`IMG_9794` 归一化前 64.7 / 后 1010.3 **完全复现** | QA |
| 10 | `/analytics/overview` 的 `model_rows` 按 `(model_role, model_name)` 聚合 COUNT/AVG **口径正确**；历史 `model_name` 为写入时真值(`yolo.py:142/160`)，属**忠实历史非脏数据** | 架构师 |
| 11 | 本轮 diff **未触及任何 rag/knowledge 文件**（`git diff --name-only \| grep rag` → NONE），RAG 链路不受影响 | 架构师 |
| 12 | **用户疑问已解答**：前端显示 `yolo26n` 非 bug —— 那是历史任务写入时的真实模型名，`frontend/DESIGN.md:163` 明文要求不得改写历史模型名称。**全仓无 `yolo11m`**（唯一 `yolo11` 命中是 `models/README.md:25` 的历史训练目录名） | 主理人 |

---

## 6. 未验证项汇总（四方均如实声明）

| # | 未验证项 | 声明人 | 影响 |
|---|---|---|---|
| U-1 | `temperature=0.0` 的确定性**未实测**（无 API key，未真实调 LLM）→ A-2 属静态推断 | 工程师 | A-2 结论强度受限 |
| U-2 | `check_risk_determinism.py` 未执行（需运行中服务 + 真实 LLM），「修复后确定性」不背书 | 工程师 | 同上 |
| U-3 | n→m 模型切换对置信度分布/转人工率的**实测影响**未测 | 工程师 + 架构师 | 缺陷③ 效果未知 |
| U-4 | 显存/延迟**无实测**（未在真实容器与 GPU 跑，未跑 `nvidia-smi`） | 架构师 | B-4 |
| U-5 | 未验证 `yolo26m.pt` 可被 ultralytics 正常加载；未定论「部署机缺权重」的失败形态 | 架构师 | B-3 |
| U-6 | 浏览器 6/6 验收、Docker 运行态未复跑（未启动服务） | QA | 端到端未验 |
| U-7 | `e2e_existing_features.py`(+61 行)、`visual_acceptance.cjs` 未逐行审计断言是否放宽 | QA | C-7 |
| U-8 | 完整 pytest 之外的 HTTP 端到端未做；`test_api.py` 未独立重跑 | 工程师 | — |
| U-9 | 策略 B 是否在**仓库外**被口头批准（只能证明仓内无依据） | PM | B-2 |
| U-10 | 「未检出目标能否自动闭环」涉及学校举证责任，需用户确认 | PM | 需拍板 |
| U-11 | ≤30% 不确定率目标的可达性未做实验 | PM | 验收口径 |

**⚠️ 贯穿性提醒**：**生产库 `backend/data/campus_safety.db` 仍是修复前数据**（PM、QA 两方独立确认，内含 2 条 `review_required=1` + `reasons=[]` 的旧症状记录）。因此 PM 实测的 **90.9% 转人工率是「修复前基线」**，**不能用来评价策略 B 的效果**——修复后代码从未在该库上跑过。

---

## 7. 交给 Codex 的任务清单（按优先级）

### P0 —— 数据正确性

| ID | 任务 | 依据 |
|---|---|---|
| **T1** | 给 `scripts/compare_general_models.py` 加**内容哈希去重**（MD5/SHA256），重跑并输出「唯一图片数」字段 | A-1 |
| **T2** | 按「10 张唯一图」口径修正**全部 7 个位置**（清单见 §3 A-1 表格）：`CHANGELOG.md:7`、`HANDOFF.md:94`、`HANDOFF.md:323`、`HANDOFF.md:341`、`models/README.md:6`、`TEST_REPORT.md:653`、`README.md:12`。**注意符号反转**：<0.35 检出数应改为 **12→11（改善）**，而非 22→25（变差）；+49% 应改为 **+34%**；覆盖 7→11 应为 **5→7**。HANDOFF 历史轮次两处**加批注**而非改写 | A-1 |

### P1 —— 根因与流程

| ID | 任务 | 依据 |
|---|---|---|
| **T3** | 让缺陷① 真正确定性：`risk_level` 改为由 `risk_score` 阈值 + 视觉事件类型**机械推导**，不由 LLM 输出；或明确记录残留非确定性并说明理由 | A-2 |
| **T4** | 消除 `review_policy_reasons` 双处调用：`evaluate()` 回传策略结果，`graph.evaluate_risk` 消费而非重算 | B-1 |
| **T5** | 把「模型权重不入版本控制、部署机需自带 `models/yolo26m.pt`(44MB)」写入部署文档 | B-3 |
| **T6** | 显式记录「本轮决定不重标定 `general_yolo_review_conf=0.35`」及**理由**（样本仅 10 张唯一图，标定等于在污染样本上调参）。**不记录则升级为阻塞项** | 缺陷③ |

### P2 —— 收尾

| ID | 任务 | 依据 |
|---|---|---|
| **T7** | 补 5 项回归缺口（§4）：`review_required=True⇒reasons非空`、视觉事件分支、`analyzable=False` 路径、medium 模型回归锚、`_review_reason_category` 剩余 5 类 | C-1 |
| **T8** | `graph.py:523` 兜底改保守：`quality.get("analyzable", False) is False` 或显式 `if "analyzable" not in quality: return "review"` | C-2 |
| **T9** | 删死代码 `risk.py:51-54` | C-3 |
| **T10** | 删根目录冗余 `yolo26m.pt`（44MB，与 `models/yolo26m.pt` 同 sha256） | B-3 |
| **T11** | Analytics 页加「当前配置模型」标识（历史柱保留 `yolo26n`，符合 `frontend/DESIGN.md:163`） | C-5 |
| **T12** | 自查 `e2e_existing_features.py` 的 61 行改动，确认断言未被放宽 | C-7 |
| **T13** | 在修复后代码上重跑生产库 11 个任务，取得**真实的**修复后转人工率 | §6 提醒 |

---

## 8. 待用户拍板（合并清单）

| # | 问题 | 来源 |
|---|---|---|
| **Q1** | 策略 B 是你拍板的吗？若是，请记录来源；若否，需回退重选边界（`risk.py:98` 的 "approved" 无依据） | PM |
| **Q2** | 是否把 `medium` 从「一律转人工」改为「自动闭环 + 强制抽检 + 重复升级」？ | PM |
| **Q3** | 自动闭环率的价值下限（建议 ≥30%，现状约 9%）与可接受漏检率上限（建议 ≤1~2%）定多少？ | PM |
| **Q4** | 是否接受「本轮不动 0.35，待样本 ≥30 张唯一图后重标定」？ | PM |
| **Q5** | 是否把 `review` 从 `RiskLevel` 枚举拆出，改「`risk_level` + `evidence_sufficient`」两维？（涉及产品定义 + LLM 契约改动） | PM |
| **Q6** | 是否接受缺陷① 的残留非确定性（`risk_level` 仍由 LLM 裁量），还是要求做到完全机械推导？ | 工程师 A-2 |

---

## 附录：复现命令

```bash
# 0. 项目根
cd "local-path/campus-safety-agent"

# 1. 只读自证：全部已跟踪文件 mtime
for f in $(git diff --name-only); do echo "$(stat -c '%y' "$f" | cut -d. -f1)  $f"; done | sort -r

# 2. 后端测试（basetemp 必须用全新唯一路径）
cd backend && "local-path/python.exe" -m pytest \
  -p no:cacheprovider --basetemp=/tmp/pytest-qa-$(date +%s) -q

# 3. 前端类型检查（必须 --force，否则增量假通过）
cd frontend && "local-path/node.exe" \
  node_modules/typescript/bin/tsc --version && npx vue-tsc -b --force

# 4. 重复样本取证
cd uploads/inspections && md5sum * | sort | uniq -c -w32 | sort -rn

# 5. 图片质量复核
"local-path/python.exe" scripts/check_image_quality.py
```

**时区提醒**：数据库时间戳为 **UTC**，文件 mtime 为**本地时间**，相差 8 小时（如 `2026-09-11 13:23 UTC` = 本地 `21:23`）。统计任务时间时勿混用。
