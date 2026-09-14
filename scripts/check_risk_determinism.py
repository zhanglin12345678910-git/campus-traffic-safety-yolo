"""重复执行同一个巡检任务 N 次，检测研判链路的确定性。

背景：本项目发现 `review_required` 在「无强制复核理由」时由大模型自由裁量
（`backend/app/services/risk.py` 只在 `reasons` 非空时强制置 True），
且 `backend/app/services/llm.py` 的 `temperature=0.1` 而非 0，
导致同一任务重复执行会得到不同的 risk_level / risk_score / review_required。

本脚本用于量化该不确定性，既可作为缺陷复现证据，也可作为修复后的回归验证。

用法：
    python scripts/check_risk_determinism.py AX-20260911-BABB48 --rounds 3
    python scripts/check_risk_determinism.py --list        # 列出全部任务
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
POLL_INTERVAL = 5
TASK_TIMEOUT = 600


def req(method: str, path: str, timeout: int = 90):
    r = urllib.request.Request(BASE + path, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)


def list_tasks() -> list[dict]:
    return req("GET", "/inspections?page=1&page_size=100")["items"]


def resolve(task_no_or_id: str) -> str:
    for t in list_tasks():
        if t["task_no"] == task_no_or_id or t["id"] == task_no_or_id:
            return t["id"]
    raise SystemExit(f"找不到巡检任务：{task_no_or_id}")


def run_once(task_id: str) -> dict:
    req("POST", f"/inspections/{task_id}/execute")
    deadline = time.time() + TASK_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        d = req("GET", f"/inspections/{task_id}")
        if d["status"] not in {"queued", "running"}:
            rr = d.get("risk_result") or {}
            return {
                "status": d["status"],
                "risk_level": d["risk_level"],
                "risk_score": rr.get("risk_score"),
                "review_required": d["review_required"],
                "review_reasons": d.get("review_reasons"),
                "analysis_mode": rr.get("analysis_mode"),
                "problem_summary": (rr.get("problem_summary") or "")[:80],
            }
    raise SystemExit("执行超时")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task", nargs="?", help="任务号（AX-...）或任务 id")
    ap.add_argument("--rounds", type=int, default=3, help="重复执行次数，默认 3")
    ap.add_argument("--list", action="store_true", help="列出全部任务后退出")
    args = ap.parse_args()

    if args.list or not args.task:
        for t in list_tasks():
            print(f"{t['task_no']:<20} {t['risk_level']:<8} {t['location']}")
        return

    task_id = resolve(args.task)
    print(f"任务 {args.task} 连续执行 {args.rounds} 次\n")

    runs = []
    for i in range(1, args.rounds + 1):
        r = run_once(task_id)
        runs.append(r)
        print(
            f"  第 {i} 次: {r['risk_level']:<7} score={r['risk_score']:<4} "
            f"review_required={str(r['review_required']):<6} status={r['status']}"
        )

    levels = {r["risk_level"] for r in runs}
    flags = {r["review_required"] for r in runs}
    scores = [r["risk_score"] for r in runs if isinstance(r["risk_score"], int)]

    print("\n" + "=" * 64)
    print(f"risk_level     : {sorted(levels)}  -> {'一致' if len(levels) == 1 else '★ 不一致'}")
    print(f"review_required: {sorted(flags)}  -> {'一致' if len(flags) == 1 else '★ 不一致'}")
    if scores:
        print(
            f"risk_score     : {scores}  min={min(scores)} max={max(scores)} "
            f"极差={max(scores) - min(scores)} 标准差={statistics.pstdev(scores):.2f}"
        )

    unstable = len(levels) > 1 or len(flags) > 1 or (scores and max(scores) - min(scores) > 0)
    print("\n结论：" + ("★ 判定链路存在非确定性" if unstable else "判定稳定"))


if __name__ == "__main__":
    main()
