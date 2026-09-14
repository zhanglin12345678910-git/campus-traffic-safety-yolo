"""离线模拟知识库召回：不依赖后端进程、不改任何数据。

用途：在把改写后的知识文档「删旧→传新」进线上库之前，
先离线复现 chunk_text + 哈希嵌入 + 余弦打分的完整检索链路，
对比「改前 / 改后」两个版本的召回差异，作为动库前的预检。

数据来源：
  --old rev   git 提交里的 knowledge/*.md（默认 HEAD，即改动前基线）
  --new disk  当前磁盘上的 knowledge/*.md（即改写后版本）

只模拟线上库实际收录的 5 份文档（《校园交通巡检示例规范》是验收夹具，不入库）。

用法（在项目根目录）：
  python scripts/simulate_knowledge_recall.py
"""

from __future__ import annotations

import hashlib
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
ONLINE_DOCS = [
    "校园交通安全巡检判定规范.md",
    "校园交通隐患整改建议库.md",
    "校园交通与消防安全法规依据摘录.md",
    "交通标志类别释义（TT100K 45 类）.md",
    "校园交通安全管理实践（学校公开材料）.md",
]
FIXTURE_DOC = "校园交通巡检示例规范.md"  # 不入库

DIMENSION = 384
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
TOP_K = 5
SCORE_THRESHOLD = 0.08

QUERIES: list[tuple[str, str]] = [
    # 区域维度（与 verify_knowledge_recall.py 一致）
    ("区域-校门口", "校门口 校门出入口 person car bus motorcycle 校园交通安全巡检"),
    ("区域-东门限速", "校门口 四川现代职业学院东门 pl60 car 校园交通安全巡检"),
    ("区域-停车场", "停车场 路边停车区 car truck 校园交通安全巡检"),
    ("区域-主干道混行", "校园主干道 人车混行道路 person car 校园交通安全巡检"),
    ("区域-图书馆禁鸣", "校园主干道 图书馆北侧道路 p11 校园交通安全巡检"),
    ("区域-宿舍区", "宿舍区 学生宿舍区域 person 校园交通安全巡检"),
    ("区域-食堂周边", "食堂周边 食堂 person car 校园交通安全巡检"),
    ("区域-教学楼路口", "教学楼路口 教学楼 person bicycle motorcycle 校园交通安全巡检"),
    ("区域-消防通道", "消防通道 教学楼消防通道 car truck 校园交通安全巡检"),
    ("区域-其他区域", "其他区域 运动场周边 person car 校园交通安全巡检"),
    # 隐患维度
    ("逆行-图片路径标志", "校园主干道 图书馆北侧道路 pne car 校园交通安全巡检"),
    ("逆行-非机动车", "校门口 校门出入口 bicycle motorcycle 校园交通安全巡检"),
    ("逆行-手动塞词(诊断)", "校园主干道 图书馆北侧道路 逆行 pne car 校园交通安全巡检"),
    ("违停-停车场", "停车场 地下车库 pn car 校园交通安全巡检"),
    ("占用消防通道", "消防通道 宿舍楼 car 校园交通安全巡检"),
    ("非机动车乱停-宿舍区", "宿舍区 宿舍楼 bicycle motorcycle 校园交通安全巡检"),
    ("共享单车-校门口", "校门口 校门出入口 bicycle 校园交通安全巡检"),
    ("外卖配送-食堂周边", "食堂周边 食堂门口 motorcycle 校园交通安全巡检"),
    ("恶劣天气-常规查询(结构性)", "校园主干道 图书馆北侧道路 car 校园交通安全巡检"),
    ("恶劣天气-雨天(诊断)", "校门口 东门 雨天 湿滑 car person 校园交通安全巡检"),
    ("恶劣天气-雾(诊断)", "校园主干道 图书馆北侧道路 雾 car 校园交通安全巡检"),
]

FINGERPRINTS: dict[str, list[str]] = {
    "判定规范-逆行条文": ["逆行线索", "逆行风险关注点", "右侧通行"],
    "判定规范-恶劣天气": ["恶劣天气", "能见度", "湿滑", "结冰"],
    "判定规范-非机动车专项": ["不得超过十五公里", "共享单车", "外卖"],
    "建议库-逆行整改": ["复新地面导向箭头", "被动逆行"],
    "建议库-违停整改": ["补划并复新车位标线", "越线、占道、跨位"],
    "建议库-消防整改": ["黄色网格禁停线"],
    "建议库-非机动车整改": ["集中充电棚", "飞线充电"],
    "建议库-恶劣天气整改": ["恶劣天气时段", "恶劣天气本身不构成隐患结论"],
    "管理实践-安全教育块": ["安全教育宣传"],
}


def chunk_text(text: str) -> list[str]:
    """与 backend/app/services/rag.py 完全一致的分块逻辑。"""
    cleaned = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    if not cleaned:
        return []
    size, overlap = CHUNK_SIZE, min(CHUNK_OVERLAP, CHUNK_SIZE - 1)
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        if end < len(cleaned):
            boundary = max(cleaned.rfind("\n", start, end), cleaned.rfind("。", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(start + 1, end - overlap)
    return chunks


def hash_embed(text: str) -> list[float]:
    """与 backend/app/services/rag.py::_hash_embed 完全一致。"""
    vector = [0.0] * DIMENSION
    normalized = re.sub(r"\s+", "", text.lower())
    tokens = [normalized[i : i + 2] for i in range(max(0, len(normalized) - 1))]
    tokens.extend(re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text.lower()))
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % DIMENSION
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def load_from_git(rev: str) -> dict[str, list[str]]:
    docs: dict[str, list[str]] = {}
    for name in ONLINE_DOCS:
        out = subprocess.run(
            ["git", "show", f"{rev}:knowledge/{name}"],
            capture_output=True, cwd=PROJECT_ROOT, check=True,
        )
        docs[name] = chunk_text(out.stdout.decode("utf-8"))
    return docs


def load_from_disk() -> dict[str, list[str]]:
    docs: dict[str, list[str]] = {}
    for name in ONLINE_DOCS:
        docs[name] = chunk_text((KNOWLEDGE_DIR / name).read_text(encoding="utf-8"))
    return docs


def tag(content: str) -> str:
    tags = [n for n, keys in FINGERPRINTS.items() if any(k in content for k in keys)]
    return "/".join(tags) if tags else "-"


def audit(docs: dict[str, list[str]]) -> dict:
    corpus: list[tuple[str, str, list[float]]] = []
    for name, chunks in docs.items():
        for i, c in enumerate(chunks):
            corpus.append((name, f"{name}:{i:02d}", hash_embed(c)))
    results = {}
    for label, query in QUERIES:
        qv = hash_embed(query)
        scored = [(cosine(qv, v), name, cid, c) for name, cid, v in corpus]
        scored.sort(key=lambda x: -x[0])
        hits = [
            {"score": round(s, 4), "document": n, "chunk": cid, "tag": tag(c), "head": c[:60]}
            for s, n, cid, c in scored[:TOP_K]
            if s >= SCORE_THRESHOLD
        ]
        results[label] = hits
    return results


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    old_docs = load_from_git("HEAD")
    new_docs = load_from_disk()

    print(f"改前（HEAD）块数: {sum(len(v) for v in old_docs.values())}  "
          f"改后（磁盘）块数: {sum(len(v) for v in new_docs.values())}  "
          f"（均为线上 5 份文档，不含夹具 {FIXTURE_DOC}）\n")

    old_res, new_res = audit(old_docs), audit(new_docs)
    for label, _query in QUERIES:
        print(f"### {label}")
        for tag_, res in (("改前", old_res), ("改后", new_res)):
            hits = res[label]
            if not hits:
                print(f"  {tag_}: 零命中")
                continue
            seats = Counter(h["document"] for h in hits)
            top = hits[0]
            top_desc = "%.4f %s[%s]" % (top["score"], top["document"][:6], top["tag"])
            print(f"  {tag_}: top1={top_desc} | 席位 {dict(seats)}")
            for h in hits[:3]:
                print("        %.4f %s[%s]" % (h["score"], h["document"][:4], h["tag"]))
        print()

    # 汇总
    for tag_, res in (("改前", old_res), ("改后", new_res)):
        zero = sum(1 for v in res.values() if not v)
        all_scores = [h["score"] for v in res.values() for h in v]
        seats: Counter[str] = Counter(h["document"] for v in res.values() for h in v)
        print(f"[{tag_}] 零命中 {zero}/{len(QUERIES)}  分数 {min(all_scores):.4f}~{max(all_scores):.4f}  席位 {dict(seats.most_common())}")


if __name__ == "__main__":
    main()
