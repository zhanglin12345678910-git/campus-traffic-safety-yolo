"""用系统真实的查询词格式验证知识库召回情况。

系统在 graph.py 中拼 query 的形式为：
    f"{area_type} {location} {class_names} 校园交通安全巡检"

本脚本覆盖两个维度：
  1. 区域维度：覆盖全部 8 个区域类型的 16 个查询（原有口径，用于零退化对比）。
  2. 隐患类型维度：逆行 / 违停 / 占用消防通道 / 非机动车乱停 / 共享单车 /
     外卖配送 / 恶劣天气等（2026-09-13 知识库缺口整改新增）。
     其中标「诊断」的查询把隐患词手动塞进查询词，仅用于对照，
     不代表系统真实查询形态（真实查询词只含区域+地点+模型输出类别）。

统计口径：零命中数 / top5 各文档席位数 / 分数区间，另按「指纹词」标注
命中块的真实归属（固定窗口分块会导致章节标题与正文错位，不能按标题判断）。

用法：
  python scripts/verify_knowledge_recall.py              # 打印全部结果
  python scripts/verify_knowledge_recall.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import Counter

BASE = "http://127.0.0.1:8000/api/v1"
TOP_K = 5

# (area_type, location, class_names) —— 严格模仿 graph.py 的拼装方式
REGION_QUERIES: list[tuple[str, str, str]] = [
    ("校门口", "校门出入口", "person car bus motorcycle"),
    ("校门口", "四川现代职业学院东门", "pl60 car"),
    ("停车场", "路边停车区", "car truck"),
    ("停车场", "停车场", "car motorcycle bicycle"),
    ("校园主干道", "人车混行道路", "person car"),
    ("校园主干道", "减速带路段", "w57 car"),
    ("校园主干道", "图书馆北侧道路", "p11"),
    ("宿舍区", "学生宿舍区域", "person"),
    ("宿舍区", "宿舍区疏散通道", "person bicycle"),
    ("食堂周边", "食堂", "person car"),
    ("教学楼路口", "教学楼", "person bicycle motorcycle"),
    ("消防通道", "教学楼消防通道", "car truck"),
    ("消防通道", "消防车通道", "car"),
    ("其他区域", "运动场周边", "person car"),
    ("其他区域", "校园周边围墙", "person"),
    ("其他区域", "创造广场", "person"),
]

# 隐患类型维度：(标签, 完整查询词)
HAZARD_QUERIES: list[tuple[str, str]] = [
    ("逆行-图片路径标志", "校园主干道 图书馆北侧道路 pne car 校园交通安全巡检"),
    ("逆行-非机动车", "校门口 校门出入口 bicycle motorcycle 校园交通安全巡检"),
    ("逆行-手动塞词(诊断)", "校园主干道 图书馆北侧道路 逆行 pne car 校园交通安全巡检"),
    ("违停-停车场", "停车场 地下车库 pn car 校园交通安全巡检"),
    ("违停-校门口", "校门口 东门 i5 motorcycle car 校园交通安全巡检"),
    ("占用消防通道", "消防通道 宿舍楼 car 校园交通安全巡检"),
    ("非机动车乱停-宿舍区", "宿舍区 宿舍楼 bicycle motorcycle 校园交通安全巡检"),
    ("共享单车-校门口", "校门口 校门出入口 bicycle 校园交通安全巡检"),
    ("外卖配送-食堂周边", "食堂周边 食堂门口 motorcycle 校园交通安全巡检"),
    ("恶劣天气-常规查询(结构性)", "校园主干道 图书馆北侧道路 car 校园交通安全巡检"),
    ("恶劣天气-手动塞词(诊断)", "校门口 东门 雨天 湿滑 car person 校园交通安全巡检"),
    ("恶劣天气-雾(诊断)", "校园主干道 图书馆北侧道路 雾 car 校园交通安全巡检"),
]

# 指纹词：用于识别命中块的真实归属（与章节标题无关）
FINGERPRINTS: dict[str, list[str]] = {
    "判定规范-逆行条文": ["判为逆行", "逆行线索"],
    "判定规范-消防通道": ["一律判为高风险"],
    "判定规范-恶劣天气": ["恶劣天气", "能见度", "湿滑"],
    "判定规范-非机动车专项": ["非机动车行驶", "不得超过十五公里"],
    "建议库-逆行整改": ["复新地面导向箭头", "被动逆行"],
    "建议库-违停整改": ["补划并复新车位标线", "越线、占道、跨位"],
    "建议库-消防整改": ["黄色网格禁停线"],
    "建议库-非机动车整改": ["集中充电棚", "飞线充电"],
    "建议库-恶劣天气整改": ["恶劣天气时段", "积水"],
    "管理实践-安全教育块": ["安全教育宣传"],
}


def search(query: str) -> list[dict]:
    body = json.dumps({"query": query, "top_k": TOP_K}).encode("utf-8")
    r = urllib.request.Request(
        BASE + "/knowledge/search", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        data = json.load(resp)
    return data.get("items") or data.get("results") or data.get("hits") or []


def tag_content(content: str) -> str:
    tags = [name for name, keys in FINGERPRINTS.items() if any(k in content for k in keys)]
    return "/".join(tags) if tags else "-"


def run_dimension(title: str, queries: list, evidence: dict) -> None:
    doc_seats: Counter[str] = Counter()
    zero_hit = 0
    scores: list[float] = []
    records = []

    for item in queries:
        if len(item) == 3:
            area, location, classes = item
            query = f"{area} {location} {classes} 校园交通安全巡检"
            label = query
        else:
            label, query = item[0], item[1]
        try:
            hits = search(query)
        except Exception as e:  # noqa: BLE001
            print(f"[ERR ] {label} -> {e}")
            continue

        tag = "零命中" if not hits else f"{len(hits)} 命中"
        if not hits:
            zero_hit += 1
        print(f"[{tag:>6}] {label}")
        record = {"label": label, "query": query, "hits": []}
        for h in hits:
            name = h.get("document") or h.get("document_name") or h.get("name") or "?"
            score = h.get("score")
            content = " ".join(str(h.get("content", "")).split())
            fp = tag_content(content)
            doc_seats[name] += 1
            if isinstance(score, (int, float)):
                scores.append(float(score))
            s = f"{score:.4f}" if isinstance(score, (int, float)) else str(score)
            print(f"           {s}  {name}  [{fp}]")
            record["hits"].append(
                {"document": name, "chunk_id": h.get("chunk_id"), "score": score, "fingerprint": fp,
                 "content_head": content[:80]}
            )
        records.append(record)

    summary = {
        "dimension": title,
        "query_count": len(queries),
        "zero_hit": zero_hit,
        "score_min": min(scores) if scores else None,
        "score_max": max(scores) if scores else None,
        "doc_seats": dict(doc_seats.most_common()),
        "records": records,
    }
    evidence[title] = summary
    print(f"\n--- {title} 汇总 ---")
    print(f"查询总数: {len(queries)}  零命中: {zero_hit}")
    if scores:
        print(f"分数区间: {min(scores):.4f} ~ {max(scores):.4f}")
    for name, cnt in doc_seats.most_common():
        print(f"  {cnt:>3}  {name}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="把完整审计结果写入 JSON 证据文件")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    evidence: dict = {"generated_at": None}
    run_dimension("region", list(REGION_QUERIES), evidence)
    run_dimension("hazard", list(HAZARD_QUERIES), evidence)

    if args.json:
        import datetime

        evidence["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2)
        print(f"证据已写入: {args.json}")


if __name__ == "__main__":
    main()
