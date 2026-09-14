# Codex 开工提示词（任务执行轮 · 审核发现落地）

> **用法**：把下面横线以内的全部内容，原样粘贴给 Codex 作为第一条消息。
> **与上一轮的关系**：`docs/CODEX_KICKOFF_PROMPT.md` 是「现状认知轮」（建立认知、不写代码）；
> 本份是**执行轮**——专家组刚做了一轮只读审核，发现了必须处理的问题，由你接手核验并修复。
> **基线**：git HEAD `63df367`，工作区 **36 项未提交变更**（你上一轮的改动 + 专家组新增的 5 份报告）。
> **已自校验（2026-09-12 深夜）**：本提示词引用的**每一个行号均已实测核对、全部命中**——
> `risk.py:50`/`:53`/`:70`/`:75`/`:98`/`:112`、`graph.py:85`/`:198`/`:246`/`:523`/`:525`/`:548`、
> `image_quality.py:30`/`:47-49`/`:51`/`:77`/`:87`、`schemas.py:32`、`llm.py:35`/`:45`，
> 以及 7 处错误数字的落点。**你改动文件后行号会漂移，届时以源码为准，不要盲信本文行号。**

---

你是接手「安巡智脑」项目的工程师。

上一轮你建立现状认知、动手改了一版代码。**现在，一个四方专家组（工程师 / 架构师 / 产品经理 / QA）对你的改动做了一轮只读审核**，产出 5 份报告，发现了：**0 项阻断、7 项重要、8 项建议**，其中有 **1 项客观数据错误**和 **1 项根因未除**。

本轮你的任务：**先核验这些问题，再按优先级修复。**

## 第一步：按顺序读审核报告

1. **`docs/audit/EXPERT_PANEL_SYNTHESIS_2026-09-12.md`** —— **主报告，先读这个**。
   它含：只读自证、四方分级汇总、交叉印证矩阵、合并去重后的发现、**已核实无误清单（让你免于返工）**、
   未验证项汇总、**§7 任务清单**、**§8 待用户拍板清单**。
2. 需要细节时再下钻四份分域报告：
   - `docs/audit/engineer-review.md` —— 代码正确性与边界条件
   - `docs/audit/architect-review.md` —— 链路拓扑、职责分层、部署影响
   - `docs/audit/pm-review.md` —— 转人工策略合理性、产品验收口径
   - `docs/audit/qa-review.md` —— 测试充分性、量化声明取证
3. 另有一份**上一轮的**单点审核报告 `docs/CODE_AUDIT_2026-09-12.md`，其中「**主动撤回**」一节值得看——
   它记录了两条审核方自己提出又推翻的误判。

## 第二步：先核验，再动手（这一步不能跳）

**审核方也可能是错的。** 上一轮主理人就主动撤回了自己两条误判，理由是「局部变量看起来不同 ≠ 真实数据流分叉，必须追到写入方」。

所以规则是：

- **报告里的每一条结论，你都要先自己复算或读码确认，再决定是否采信。**
- **若你确认报告有误** → **先告诉用户，不要闷头按错的改**。
- **若你确认报告成立** → 按第三步的清单处理。
- 核验方法见报告 §附录的「复现命令」，以及下文第五步的「已核验事实」。

## 第三步：按优先级处理

### P0 —— 数据正确性（先做，后续所有决策都依赖它）

**T1 · 给比对脚本加内容哈希去重**

`scripts/compare_general_models.py` 直接 `glob` 整个 `uploads/inspections/`，**不做任何去重**。
实测该目录 **15 个文件只有 10 张唯一图片**（`dormitory-road`×3、`dormitory-crowd`×3、`demo-r1`/`IMG_9781`×2）。

要求：
- 按内容哈希（MD5 或 SHA256）去重后再统计，输出里增加「唯一图片数」字段。
- 重跑后给出新数字，并与去重前的旧数字并列展示。
- ⚠️ **该脚本的 `main()` 会覆写 `outputs/general_model_comparison.json`** —— 重跑前先备份该文件，
  否则你会毁掉物证（QA 因此当初没有全量重跑，而是用「读已有 JSON 重算 + 2 张图现场推理交叉验证」替代）。

**T2 · 纠正已扩散的错误数字（7 个位置，不是 3 个）**

QA 与本报告最初只点出 3 处，主理人追加一轮全仓 grep 后确认为 **7 个位置 / 5 个文件**：

| # | 位置 | 原文片段 | 改成 |
|---|---|---|---|
| 1 | `docs/CHANGELOG.md:7` | 「15 张真实图片同口径检出 61 → 91，覆盖 7 → 11 张」 | 61→91 改 **35→47**；7→11 改 **5→7** |
| 2 | `docs/HANDOFF.md:94`（你的 C 节） | 「nano 61 个检出 / 覆盖 7 张，medium 91 个检出 / 覆盖 11 张，检出量提升 49%」 | 同左 + 49% 改 **+34%** |
| 3 | `docs/HANDOFF.md:323`（**历史轮次**表格） | 「\| 检出总数 \| 61 \| **91**（+49%）\|」 | **加批注**，不改写历史 |
| 4 | `docs/HANDOFF.md:341`（**历史轮次**） | 「❌ **总低置信度 22 → 25**」 | **加批注**，不改写历史 |
| 5 | `models/README.md:6` | 「其检出总数比 nano 高 49%」 | 改 **+34%** |
| 6 | `docs/TEST_REPORT.md:653` | 「\| 总检出数 \| 61 \| 91 \| **+49%** \|」 | 同左 |
| 7 | `README.md:12` | 「medium 相比 nano 的检出总数由 61 提升至 91（+49%）」（**根目录 README**） | 同左 |

**为什么必须改**：真实值是 **35→47（+34%）**、覆盖 **5→7**、修复漏检 **2 张（不是 4 张）**，
而「低于 0.35 阈值的检出数」是 **12→11（略降，变好）**，**不是** 22→25（变差）——**符号反了**。
按错数去调阈值会把方向调反。

**处理方式区别**：#3/#4 在 HANDOFF 的**历史轮次**区，按本项目「不删历史轮次」的惯例**加批注指向本报告**即可；
#1/#2/#5/#6/#7 属当前有效文档，**直接更正**。

### P1 —— 根因与流程（**先交核验结论与计划，等用户确认再改**）

**T3 · 让缺陷① 真正确定性**（⚠️ **涉及产品决策，先看第四步 Q6，不要自己定**）

现状：你已经把 `review_required` 从 LLM schema 摘除（`risk.py:50`）、在 `risk.py:75` 无条件覆盖、把 `temperature` 降到 0（`llm.py:45`）。
但工程师与产品经理**从两条独立路径得出同一结论**：
`risk.py:112` 的 `if risk_level in {"medium", "high", "review"}:` 让决策**透传依赖 LLM 输出的 `risk_level`**；
而 `llm.py:35` 的 prompt 又要求模型「信息不足时必须将 `risk_level` 设为 `review`」，实测 **8/11（73%）**任务 LLM 直接给 `review`。
→ **非确定性只是从 `review_required` 字段转移到了 `risk_level` 字段**，`temperature=0.0` 只降不除。

**T4 · 消除 `review_policy_reasons` 双处调用**

同一策略被算了两次：`risk.py:70` 与 `graph.py:246` 各调一次。
今日两者入参重合、结果一致（**当前无分叉，不必惊慌**），但属「一个策略、两次调用、两套入参」，
未来任一侧改追加逻辑即**静默错配**，并**污染 `/analytics` 的 `review_rate` 与 `review_reason_counts` 两个口径**。
建议：`evaluate()` 回传策略结果，`graph` 消费而不再重算。

**T5 · 把模型部署前置条件写进文档**

`.gitignore` 与 `.dockerignore` 均排除权重、`Dockerfile` 无 `COPY`、`docker-compose.yml` 靠 bind mount。
→ 切换 `yolo26m.pt`（44MB）后，**部署机必须自带该文件**，否则路径失效。目前**没有任何文档写明这一点**。

**T6 · 显式记录「本轮不重标定 `general_yolo_review_conf=0.35`」及理由**

理由：本轮已把低置信度规则改为「全部低于阈值才触发」（`graph.py:525` 的 `_confidence_review_reason`，AND 语义），
阈值杠杆大降；且去重后样本只有 **10 张唯一图**，此时标定等于在污染样本上调参。
**必须在 HANDOFF 显式记录，否则这一项从「可延后」升级为「阻塞」。**

### P2 —— 收尾（**先交核验结论与计划，等用户确认再改**）

| # | 任务 |
|---|---|
| **T7** | 补 5 项回归缺口：① 无测试断言 `review_required=True ⇒ reasons 非空`；② `review_policy_reasons` 的「视觉事件」分支零覆盖；③ `analyzable=False` 短路路径无测试；④ `general_yolo_model_path` 改 medium 后无回归锚；⑤ `_review_reason_category` 7 类仅测 2 类 |
| **T8** | `graph.py:523` 的兜底方向不保守：`quality.get("analyzable") is False`，键缺失时 `None is False` 为假 → 走 `detect`。出错时应倾向「转人工」而非「继续跑」 |
| **T9** | 删死代码 `risk.py:53`（那段过滤 `required`）。实测 `required=['risk_level','risk_score','problem_summary']`，`review_required` 带默认值从不在必填列表里 |
| **T10** | 删根目录冗余 `yolo26m.pt`（44MB，与 `models/yolo26m.pt` 的 SHA-256 完全相同） |
| **T11** | Analytics 页加「当前配置模型」标识。历史柱保留 `yolo26n` 是**忠实历史**（`frontend/DESIGN.md:163` 要求不得改写历史模型名），**不是 bug** |
| **T12** | 自查 `frontend/scripts/e2e_existing_features.py` 的 61 行改动，确认断言未被放宽 |
| **T13** | 在**修复后**的代码上重跑生产库 11 个任务。⚠️ **先备份 `backend/data/campus_safety.db`**；当前库里是**修复前**数据 |

## 第四步：这 6 个问题必须问用户，不要自己定

> 依据：你在 `docs/CODEX_KICKOFF_PROMPT.md:107` 亲口被交代过「**缺陷1涉及产品决策，不要自己定，要列出选项让我选**」。
> 而 `risk.py:98` 的 docstring 却写着「the approved balanced review policy (policy B)」——
> **专家组在仓内（HANDOFF / CHANGELOG / git log / memory）查不到任何你被批准的记录，判定这是你自行拍板。**
> 本轮请把这 6 个问题一并交回用户。

- **Q1**：策略 B（`medium/high/review` 一律转人工）是用户定的吗？若是，请补记来源；若否，需回退重选边界。
- **Q2**：是否把 `medium` 从「一律转人工」改为「自动闭环 + 强制抽检 + 重复升级」？
- **Q3**：自动闭环率的价值下限定多少？（现状约 **9%**，PM 建议 ≥30%）可接受漏检率上限？（建议 ≤1~2%）
- **Q4**：是否接受「本轮不动 `general_yolo_review_conf=0.35`，待样本 ≥30 张唯一图后重标定」？
- **Q5**：是否把 `review` 从 `RiskLevel` 枚举拆出，改「`risk_level` + `evidence_sufficient`」两维？
- **Q6**：缺陷① 的残留非确定性（`risk_level` 仍由 LLM 裁量），是接受并记录，还是要求做到完全机械推导？

## 第五步：本轮已核验事实（可省你一轮验证）

**行号已逐条实测命中**（2026-09-12 深夜）：

| 断言 | 位置 |
|---|---|
| 从 LLM output schema 摘除 `review_required` | `risk.py:50` |
| 过滤 `required` 的死代码 | `risk.py:53` |
| 第一处调用 `review_policy_reasons` | `risk.py:70` |
| `review_required` 无条件覆盖 | `risk.py:75` |
| 「the approved policy B」docstring | `risk.py:98` |
| medium/high/review 一律转人工 | `risk.py:112` |
| `check_detection_result → retrieve_knowledge` **无条件边** | `graph.py:85` |
| `_confidence_review_reason` 唯一调用点 | `graph.py:198` |
| 第二处调用 `review_policy_reasons` | `graph.py:246` |
| 不保守的兜底 | `graph.py:523` |
| `_confidence_review_reason` 定义（AND 语义，已核验正确） | `graph.py:525` |
| `_route_error` 定义（异常护栏，非短路点） | `graph.py:548` |
| `analyzable=False`（仅不可解码） | `image_quality.py:30` |
| 归一化后重算 blur | `image_quality.py:47-49` |
| `blurred = blur_score < blur_threshold` | `image_quality.py:51` |
| `analyzable=True`（能解码） | `image_quality.py:77` |
| `_normalize_for_blur` | `image_quality.py:87` |
| `review_required: bool = False`（**有默认值 → 反序列化不会炸**） | `schemas.py:32` |
| 「信息不足时必须将 risk_level 设为 review」 | `llm.py:35` |
| `temperature: 0.0` | `llm.py:45` |

**已被独立复核、确认无误的（别去返工）**：短路点仅 2 个且短路风险已消除；`_confidence_review_reason` 确是 AND 语义；
`llm.py` 无残留 `review_required` 字样；44 项后端测试全过；`vue-tsc -b --force` 退出码 0；
质量护栏未过松（14 通过 / 1 告警）；RAG 链路未受影响；`/analytics/overview` 聚合口径正确。

## 铁律（违反会造成不可逆损失）

- **先处理工作区状态再动手。** 当前有 **36 项未提交变更**。开始前先提交（或至少建一个可回滚的备份分支），
  否则你的新改动会和旧改动混在一起，出问题无法归因。
- **P0 可以直接改；P1/P2 先交「核验结论 + 修改计划」，等用户确认再动手。** Q1~Q6 交回用户。
- **不要向生产知识库上传任何演示文档。** `knowledge/校园交通巡检示例规范.md` 只作验收脚本输入夹具，**已从线上库移除**。
- **不要删任何文件**，除非走完三步：① grep 全仓路径引用 → ② 查 DB 引用 → ③ 确认内容可从留存副本复原，并把结论告诉用户。
- **`.gitignore` 对已在索引中的文件不生效**：补规则后必须 `git rm -r --cached .` 再 `git add -A`。
- **改前端样式前先读 `frontend/DESIGN.md`**（当前 v4）。`frontend/src/styles.css` 是全局唯一、无 scoped 的样式表；
  侧边栏菜单在 `router.ts` 与 `AppLayout.vue` **两处独立定义**，增删必须同步。
- **本机两个跑测试的坑**（不看会白费一轮）：
  - `pytest` 必须加隔离参数，且 `--basetemp` **必须用全新唯一路径**：
    `-p no:cacheprovider --basetemp=/tmp/pytest-csa-$(date +%s)`
    （用固定路径第二次跑会被上一轮残留撑满，触发沙箱批量删除守卫 → `SystemExit:1` + 几十个 errors，
    这**不是**代码回归。）
  - `vue-tsc -b` 是增量模式，别人刚跑过 build 会**直接跳过检查、空输出**，会被误读成通过 → 必须加 **`--force`**。
- **没有 API key 就不要断言「确定性已修复」。** 本机无 key，`temperature=0.0` 的实际效果无法实测——
  这种情况如实写「未验证」，不要拿静态推断当实测结论。
- **改完每一项，更新 `docs/HANDOFF.md`**（项目惯例：滚动交接文档，最新一轮在最上面，不删历史轮次）。
- **交付前后端测试与 `npm run build` 都必须过**（构建会先跑 `vue-tsc -b`，类型错误**直接阻断构建**）。
