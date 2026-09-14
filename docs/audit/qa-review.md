# QA 只读审核报告 · Codex 未提交改动集

- **审核人**：Edward（QA / 严过关），SoftwareCompany 专家团
- **审核时间**：2026-09-12 23:20–23:35（**本地时间**，见第 5 节时区说明）
- **审核对象**：`git status` 中**未提交**的改动集（基线 `63df367`；29 tracked modified + 3 untracked）
- **审核方式**：**只读**。未修改/未提交任何源码、配置、测试、脚本、模型。
  写入型动作仅为：① 后端 pytest（临时目录 `--basetemp`，不污染仓库）；② `vue-tsc -b` 类型检查（产物已被 gitignore）；③ 本报告。
  **未覆盖** `outputs/general_model_comparison.json`（重算结果只打印到终端）。
- **环境**：Python `<LOCAL_PATH>`；Node `<LOCAL_PATH>`

---

## 0. 结论速览

| 项 | 结论 | 口径 |
|---|---|---|
| 后端测试 | ✅ **44 passed / 0 failed，16.96s** | 独立复跑（修复了 basetemp 坑，见 §1） |
| 前端类型检查 | ✅ **`vue-tsc -b --force` 退出码 0、零输出** | 独立复跑（带 `--force`） |
| 测试充分性 | ⚠️ **6 个新测试覆盖 3/4 个缺陷**；缺陷 2 无专属回归；**4 处回归缺口** | 见 §2 |
| **量化声明（去重）** | 🔴 **记录值被重复样本加权**；**「低于 0.35 检出数」符号反转**（22→25「变差」实为 12→11「变好」） | 见 §3 |
| 图片质量护栏 | ✅ **14 通过 / 1 告警**；`IMG_9794` 64.7→**1010.3** 复核一致 | 见 §4 |
| 时区 | ✅ DB 时间戳 = **UTC**，文件 mtime = **本地**，相差 8h | 见 §5 |

**一句话**：四个缺陷的代码修复方向正确、有针对性测试、全量测试真过；**但支撑「换 medium 模型」的量化依据不成立 —— 数字被重复样本放大，且一个关键指标符号被算反，错误数字已写入 CHANGELOG/HANDOFF/README。**

---

## 1. 测试独立复跑（真实数字 + 复现命令）

### 1.1 后端 pytest

```bash
# 注意：必须用【全新的】basetemp 路径
cd backend && "local-path/python.exe" \
  -m pytest -p no:cacheprovider --basetemp=/tmp/pytest-qa-edward -q
```

原始输出：
```
............................................                             [100%]
44 passed in 16.96s
```

> **复核工具坑（给后续接手方）**：题面建议的 `--basetemp=/tmp/pytest-audit` 在**本机第一次跑就会崩**：
> `SystemExit: 1`，41 errors，报 `[SAFE_DELETE_BULK_CONFIRM_REQUIRED] {"count":56,"threshold":50,...targets:["\\?\<LOCAL_PATH>"]}`。
> 根因：该路径已被**上一轮**跑出的 56 个临时子目录占满，pytest 会话开始时 `rmtree` 它 → 命中沙箱「单轮 >50 项批量删除守卫」。
> **解决**：换成尚不存在的新路径（如 `/tmp/pytest-qa-edward`）即可。44 passed 是**真实且可复现**的。

### 1.2 前端类型检查

```bash
cd frontend && export PATH="local-path/22.22.2-3:$PATH"
./node_modules/.bin/vue-tsc -b --force ; echo "EXIT_CODE=$?"
```
原始输出：
```
vue-tsc
v22.22.2
EXIT_CODE=0
```
**退出码 0、无任何诊断输出 → 类型检查通过。**（`--force` 强制全量，规避增量模式假通过。）

### 1.3 测试计数自证

- 函数计数：`test_api.py`=19，`test_tools_and_services.py`=18，`test_knowledge_api.py`=2，`test_docker_contract.py`=3 → 42 个函数。
- 其中 `test_risk_review_policy_requires_confirmation_for_non_low_levels` 为 `@pytest.mark.parametrize(3)` → **42 − 1 + 3 = 44** 个用例，与 pytest 输出一致。

---

## 2. 测试充分性：缺陷 → 测试映射

**本轮新增测试**（`git diff backend/tests/`）：6 个新函数（→ 8 个新用例），另 2 个既有测试加了断言。

| # | 缺陷 | 对应测试 | 覆盖判定 |
|---|---|---|---|
| 1 | `review_required` 确定性 | `test_risk_review_policy_is_deterministic_and_ignores_llm_boolean`（tools:282）<br>+ `test_llm_structured_output` 新增 `body["temperature"]==0.0`（tools:272） | ✅ **精准**：喂「LLM 返回 review_required=True 但低风险无理由」→ 断言 `review_required is False`；再喂带理由 → `True`，证明策略覆盖 LLM 布尔值 |
| 2 | `status` / `risk_level` 语义重叠 | 仅 `test_analytics_overview_...`（api:353）间接断言 `status_counts=={"review":1}`、`risk_counts=={"review":1}` | ⚠️ **无专属回归**：无任何测试断言「`review_required=True ⇒ review_reasons 非空`」这一不变量本身 |
| 3 | 转人工率高 | `test_low_confidence_candidates_only_force_review_when_all_are_unreliable`（api:258）<br>+ `test_risk_review_policy_requires_confirmation_for_non_low_levels`（tools:321，策略 B） | 🟡 **部分**：覆盖了「all-below 才复核」与策略 B 分支；无「整体转人工率下降」的聚合断言 |
| 4 | 图片质量误判 + 短路 | `test_quality_warning_continues_detection_and_analysis`（api:225）<br>+ `test_image_quality_normalizes_resolution_before_blur_scoring`（tools:36）<br>+ `test_image_quality_detects_dark_and_small`（新增 `analyzable`/`blur_normalized_long_side` 断言） | ✅ **精准**：mock 出「模糊」告警后，断言 trace 中 `detect_traffic_signs`/`retrieve_knowledge`/`evaluate_risk` **仍执行**，且 `review_reasons` 含该理由 |

### 2.1 回归缺口（未被任何测试锁定的改动）

1. **缺陷 2 的不变量无测试**。修复的本质是 `task.review_required` 与 `review_reasons_json` 同源（`graph.py:243-253` 用同一 `review_policy_reasons` 输出）。**没有测试**直接断言二者不再分叉。
2. **`review_policy_reasons` 的「视觉事件」分支完全未测**。唯一直接调用处（tools:322）传 `vision_events=[]`；全流程测试用的 `FakeYOLOTool.vision_events` 恒为 `[]`。即 `event.get("requires_manual_review")` 分支（risk.py:107-111）**零覆盖**。
3. **`analyzable=False` 的短路路径未测**。新测试只验证 `analyzable=True` 继续执行；`test_rejects_corrupted_image` 属**上传校验**，不是 `graph._route_quality` 的短路。即「无法解码 → 路由 review」这条被改动的路径无直接回归。
4. **默认通用模型切换无回归锚**。`config.py:52` 的 `general_yolo_model_path` 由 `yolo26n.pt` 改为 `models/yolo26m.pt`，但**没有测试**断言该默认值；测试里都手动指向 tmp 路径。若有人改回 nano，测试**不会红**。
5. **`_review_reason_category`（router.py:261-278）7 个分类仅断言 2 个**（`知识依据`/`风险策略`）；`图片质量`/`检测可信度`/`视觉事件`/`模型或服务`/`其他原因` 未测。

> 上述均为**回归缺口**（不阻塞交付），建议补 3–4 个纯函数级测试即可闭环，成本极低。

---

## 3. 【最重要】量化声明取证 —— 重复样本 + 符号反转

### 3.1 取证表：`uploads/inspections/` 内容哈希去重

```bash
md5sum uploads/inspections/* | sort
sha256sum uploads/inspections/* | sort
```
原始结果（MD5，节选重复组）：

| MD5 | 份数 | 文件（同一内容，多文件名） |
|---|---|---|
| `40f2240e8253d411ea31f7f46080b9d5` | **×3** | `demo-r5-a7d2a7d9e6b6.jpg`、`dormitory-crowd-a79bfe7b55e5.png`、`dormitory-crowd-ba637029e751.png` |
| `117b5cf394b6627c6ef23be051f44d2b` | **×3** | `dormitory-road-c49d63487609.jpg`、`tt100k-dormitory-road-172a1148bbf9.jpg`、`tt100k-dormitory-road-747ac84e5621.jpg` |
| `30d5c5a55a64c8c4cfda36e26a4a48e0` | **×2** | `demo-r1-147636384369.jpg`、`IMG_9781-f97235ed242c.jpg` |
| 其余 7 个哈希 | ×1 | `1F8ECA8A…png`、`IMG_9759`、`IMG_9769`、`IMG_9794`、`IMG_9805`、`proxy-live-e2e…`、`tt100k-10132…` |

> **文件总数 = 15；唯一图片数 = 10。**（3 组重复共 8 个文件 → 3 张唯一 + 7 张单例）

`scripts/compare_general_models.py:82` 以 `IMG_DIR.iterdir()` **glob 全目录、无任何去重**，故 8 个重复文件被**重复推理**。

### 3.2 重算口径自证（先复现 15 文件记录值，再去重）

用 `outputs/general_model_comparison.json` 的 **`raw` 逐图逐检测明细**重算（**未覆盖该文件**）：

```python
# 读取 JSON raw，对 nano/medium 逐图累加；键集取①全部15文件 ②按MD5去重后10代表文件
# 口径：total / images_with_detection / <0.35 检出数 / 修复漏检(该图 nano空 且 medium非空)
```

原始输出：
```
--- 15文件口径 (n=15) ---
检出总数        nano=  61  medium=  91  Δ=+30
有检出图片数    nano=   7  medium=  11  Δ=+4
修复漏检图数    4
<0.35 检出数    nano=  22  medium=  25  Δ=+3      <-- 与 JSON 记录值 61/7/22、91/11/25 完全一致 ✅

--- 去重后(唯一图片) (n=10) ---
检出总数        nano=  35  medium=  47  Δ=+12
有检出图片数    nano=   5  medium=   7  Δ=+2
修复漏检图数    2
<0.35 检出数    nano=  12  medium=  11  Δ=-1      <-- 符号反转
```

**能精确复现记录值（61→91、7→11、22、25），证明我的重算与脚本口径一致**，去重值因此可信。

### 3.3 逐图明细（去重后 10 张）

| 代表文件 | nano 检出 | medium 检出 | nano <0.35 | medium <0.35 | 修复漏检 |
|---|---:|---:|---:|---:|:--:|
| `1F8ECA8A…png` | 12 | 13 | 1 | 2 | |
| `IMG_9759` | 5 | 5 | 3 | 0 | |
| `IMG_9769` | 1 | 2 | 0 | 1 | |
| `IMG_9781` | 0 | 0 | 0 | 0 | |
| `IMG_9794` | 0 | 0 | 0 | 0 | |
| `IMG_9805` | 0 | 0 | 0 | 0 | |
| `demo-r5…jpg` | 13 | 17 | 5 | 5 | |
| `dormitory-road…jpg` | 0 | **5** | 0 | 2 | **YES**（原文件 ×3，被 3 倍计） |
| `proxy-live-e2e…jpg` | 4 | 4 | 3 | 1 | |
| `tt100k-10132…jpg` | 0 | 1 | 0 | 0 | **YES** |
| **合计（去重 10）** | **35** | **47** | **12** | **11** | **2** |

### 3.4 JSON 真实性交叉验证（防止「拿旧 JSON 说事」）

对 2 张图**现场重跑两个模型推理**（用 `importlib` 加载脚本函数、**不调用 `main()`**，故不写 JSON），与 JSON 逐值比对：

```
### 1F8ECA8A…png
  nano   live: [0.9088, 0.8844, 0.8791, 0.7409, 0.7259, 0.7037, 0.6794, 0.6107, 0.4854, 0.3773, 0.3587, 0.2181]
  nano   json: [0.9088, 0.8844, 0.8791, 0.7409, 0.7259, 0.7037, 0.6794, 0.6107, 0.4854, 0.3773, 0.3587, 0.2181]
  medium live: [0.9309, 0.9183, 0.8725, 0.7855, 0.7173, 0.7161, 0.631, 0.6029, 0.4935, 0.4693, 0.4119, 0.2834, 0.27]
  medium json: [0.9309, 0.9183, 0.8725, 0.7855, 0.7173, 0.7161, 0.631, 0.6029, 0.4935, 0.4693, 0.4119, 0.2834, 0.27]
### dormitory-road-c49d63487609.jpg
  nano   live: []                                  | nano   json: []
  medium live: [0.6477, 0.5566, 0.3663, 0.2416, 0.2345] | medium json: [同]
```
**逐值完全一致 → JSON 系真实推理产物，去重重算基础可靠。**

### 3.5 判定

- **方向未变**：去重后 medium 仍**提升召回**（检出 35→47、覆盖 5→7、修复 2 张漏检）→ **「换 medium」的定性方向成立**。
- **幅度被夸大**：+49% → **+34%**；覆盖 +4 张 → **+2 张**；修复 4 张 → **2 张**（`dormitory-road` 被 3 倍计）。
- 🔴 **符号反转**：`<0.35 检出数` 记录为 **22→25（变差）**，去重后为 **12→11（变好）**。
  即上一轮「medium 只补召回、不改善置信度分布」的结论**不成立** —— medium 同时小幅改善了召回与低置信占比。
- 错误数字已落盘：`docs/CHANGELOG.md`、`docs/HANDOFF.md`（C 节）、`models/README.md` 三处需按「10 张唯一图片」口径更正。

---

## 4. 图片质量护栏验证

```bash
"local-path/python.exe" scripts/check_image_quality.py
```

原始输出（阈值 500.0，长边 1024）：
```
图片                                                  原图       归一化      分块最大      分块中位  当前判定
tt100k-10132-bfaa4790f351.jpg                     47.9     152.6     164.4      40.4  质量告警 <<<
dormitory-road-c49d63487609.jpg                  227.5     622.1     755.1     147.0  通过
1F8ECA8A397A292EBBC81FBB5FEF8E40-04114ad7c5e6.png     372.5     791.8     761.8     407.2  通过
proxy-live-e2e-27579d2016b0.jpg                  340.4     902.8     938.1     297.7  通过
demo-r5-a7d2a7d9e6b6.jpg                         849.2     966.1    1966.0     701.4  通过
IMG_9794-b7120025621a.jpg                         64.7    1010.3     122.0      62.7  通过
IMG_9805-f53a287a5c01.jpg                        299.5    2303.7     729.8     285.0  通过
IMG_9759-de44188b5e43.jpg                       2077.6    3627.4    6621.9    1588.5  通过
demo-r1-147636384369.jpg                         340.1    3842.7     705.3     348.5  通过
IMG_9769-eb284c099f6f.jpg                       264.6    4060.6     478.6     249.2  通过

产生质量告警 1 张 / 判定通过 14 张
通过组归一化得分区间：622.1 ~ 4060.6
```

**回答题面三问：**

1. **改后是否所有图都通过（过松风险）？** **否** —— 15 张里 **1 张仍告警**（`tt100k-10132`，归一化 152.6），14 张通过。
2. **是否把真模糊图放过了？** 被唯一告警的 `tt100k-10132` 恰是**原图分数最低**（47.9）的柔焦样本，阈值 500 落在「告警样本 152.6」与「通过组下界 622.1」的**空隙内（裕度 152.6↔500↔622.1）**，分类合理，**未见明显过松**。
3. **样本已复核**：`IMG_9794` **归一化前 64.7 / 归一化后 1010.3** —— 与题面给的 64.7 / 1010.3 **完全一致** ✅（上一轮的误判样本已恢复为「通过」）。

> 边界提示（非阻断）：通过组下界 622.1 与告警样本 152.6 之间空隙宽 469，500 偏上沿、偏保守；且**负样本仅 1 个**，无法估计误告警率。但新语义下「告警」只追加复核理由、**不再短路**，误告警代价低，可接受。

---

## 5. 时区核对

- **数据库时间戳 = UTC**。实测 `backend/data/campus_safety.db` 最新一行 `created_at = 2026-09-11 13:23:01`（UTC）= **本地 2026-09-11 21:23**。
- **文件 mtime = 本地时间**。如 `campus_safety.db` mtime 显示 `Fri Sep 11 23:55`（本地）。
- 二者相差 **8 小时**。**本报告中：pytest/类型检查的「现在」用本机时钟（本地 23:2x）；数据库时间戳一律按 UTC 解读并已标注。** 不会据此误判「今天没跑过任务」。

> 附带独立确认（只读）：该生产库 11 条任务中，`4edb2f27`（`status=review, risk=low, review_required=1, reasons=[]`）与 `432306cb`（`review_required=1, reasons=[]`）正是**缺陷 2 的修复前症状数据** —— 说明**修复后代码尚未在生产库跑过**，生产库仍是旧数据（本轮改动未触及该库）。

---

## 6. 未能验证的部分（诚实声明）

| 项 | 原因 |
|---|---|
| `scripts/compare_general_models.py` 全量 15 图**重跑推理** | 该脚本 `main()` 会**覆盖** `outputs/general_model_comparison.json`（禁改）。改为：① 复现其 15 文件记录值证明口径一致；② 对 2 张图现场重跑交叉验证 JSON 真实性。**全量重跑未做。** |
| 浏览器验收「6/6、0 页面/控制台/网络错误」 | 需 Playwright + 已启动前后端；本轮**未启动任何服务**，未复跑。 |
| Docker 运行态验收 | 与其他人一致：本机 Docker 守护进程未起，未执行。 |
| `frontend/scripts/e2e_existing_features.py`（+61 行）与 `visual_acceptance.cjs` | 仅做存在性/用途识别，**未逐行审计断言是否被放宽**。 |
| 前端视觉还原度（与参考图同屏比对） | 主观项，非本 QA 审核范围。 |

---

## 7. 附：本轮执行过的全部复现命令

```bash
# ① 后端全量测试（全新 basetemp，规避批量删除守卫）
cd backend && "local-path/python.exe" -m pytest -p no:cacheprovider --basetemp=/tmp/pytest-qa-edward -q
#   → 44 passed in 16.96s

# ② 前端严格类型检查
cd frontend && export PATH="local-path/22.22.2-3:$PATH" && ./node_modules/.bin/vue-tsc -b --force; echo $?
#   → 0

# ③ 图片质量护栏（只读）
"local-path/python.exe" scripts/check_image_quality.py
#   → 1 告警 / 14 通过；IMG_9794 64.7→1010.3

# ④ 样本去重取证（只读）
md5sum uploads/inspections/*    # → 15 文件 / 10 唯一
sha256sum uploads/inspections/*

# ⑤ 去重重算（只读，读 outputs/general_model_comparison.json 的 raw 明细，不写回）
#   → 15文件口径复现 61/7/22 与 91/11/25；去重口径 35→47 / 5→7 / 2 / 12→11

# ⑥ 权重一致性（只读）
sha256sum yolo26m.pt models/yolo26m.pt
#   → 401cea9a…45d0b7（两份一致）

# ⑦ 生产库只读查询（时区/旧数据核对）
#   sqlite3 file:backend/data/campus_safety.db?mode=ro
```

> 再次确认：本报告**未修改任何源文件/配置/测试/脚本/模型，未执行 git add/commit/stash/checkout/branch，未覆盖任何既有输出文件**（唯一新增文件为本报告）。
