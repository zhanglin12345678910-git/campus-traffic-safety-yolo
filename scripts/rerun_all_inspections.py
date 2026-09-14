"""批量重跑全部巡检任务，并输出前后风险判定对比。

用途：知识库补充/修订后，验证新知识库对历史任务判定结果的影响。

用法（后端需已启动在 127.0.0.1:8000）：
    python scripts/rerun_all_inspections.py

产出：outputs/rerun_result.json （前后完整快照对比，outputs/ 已被 gitignore）
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "http://127.0.0.1:8000/api/v1"
POLL_INTERVAL = 6          # 轮询间隔（秒）
TASK_TIMEOUT = 600         # 单个任务最长等待（秒）
OUT = Path("outputs/rerun_result.json")


def req(method: str, path: str, timeout: int = 90):
    r = urllib.request.Request(BASE + path, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)


def snapshot(task_id: str) -> dict:
    return req("GET", f"/inspections/{task_id}")


def main() -> None:
    started = datetime.now().isoformat(timespec="seconds")
    tasks = req("GET", "/inspections?page=1&page_size=100")["items"]
    print(f"[{started}] 发现 {len(tasks)} 个巡检任务", flush=True)

    before: dict[str, dict] = {}
    for t in tasks:
        before[t["id"]] = snapshot(t["id"])

    print("\n========== 重跑前风险分布 ==========", flush=True)
    _dist(before)

    after: dict[str, dict] = {}
    failures: list[dict] = []

    for idx, t in enumerate(tasks, 1):
        tid, tno = t["id"], t["task_no"]
        print(f"\n--- [{idx}/{len(tasks)}] {tno} {t.get('location')} ---", flush=True)
        try:
            req("POST", f"/inspections/{tid}/execute")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            print(f"    触发失败 HTTP {e.code}: {body}", flush=True)
            failures.append({"task_no": tno, "stage": "trigger", "error": f"{e.code} {body}"})
            continue
        except Exception as e:  # noqa: BLE001
            print(f"    触发异常: {e}", flush=True)
            failures.append({"task_no": tno, "stage": "trigger", "error": str(e)})
            continue

        deadline = time.time() + TASK_TIMEOUT
        last = None
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            try:
                d = snapshot(tid)
            except Exception as e:  # noqa: BLE001
                print(f"    轮询异常: {e}", flush=True)
                continue
            if d["status"] != last:
                print(f"    status -> {d['status']}", flush=True)
                last = d["status"]
            if d["status"] not in {"queued", "running"}:
                break

        d = snapshot(tid)
        after[tid] = d
        if d["status"] in {"queued", "running"}:
            failures.append({"task_no": tno, "stage": "timeout", "error": d["status"]})
            print(f"    ⏱ 超时，仍为 {d['status']}", flush=True)
        else:
            print(
                f"    ✅ {d['status']} / risk={d['risk_level']} / "
                f"review_required={d.get('review_required')}",
                flush=True,
            )

    print("\n========== 重跑后风险分布 ==========", flush=True)
    _dist(after)

    print("\n========== 变化明细 ==========", flush=True)
    changed = 0
    for t in tasks:
        tid = t["id"]
        b, a = before.get(tid), after.get(tid)
        if not a:
            continue
        if (b.get("risk_level"), b.get("status")) != (a.get("risk_level"), a.get("status")):
            changed += 1
            print(
                f"  {t['task_no']}: risk {b.get('risk_level')} -> {a.get('risk_level')} | "
                f"status {b.get('status')} -> {a.get('status')}",
                flush=True,
            )
    if not changed:
        print("  （无变化）", flush=True)

    if failures:
        print("\n========== 失败/超时 ==========", flush=True)
        for f in failures:
            print(f"  {f['task_no']} [{f['stage']}] {f['error']}", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "started_at": started,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "total": len(tasks),
                "changed": changed,
                "failures": failures,
                "before": before,
                "after": after,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n结果已写入 {OUT}", flush=True)


def _dist(store: dict[str, dict]) -> None:
    dist: dict[str, int] = {}
    for d in store.values():
        dist[d.get("risk_level") or "None"] = dist.get(d.get("risk_level") or "None", 0) + 1
    print(f"  risk_level: {dist}", flush=True)
    sd: dict[str, int] = {}
    for d in store.values():
        sd[d.get("status") or "None"] = sd.get(d.get("status") or "None", 0) + 1
    print(f"  status    : {sd}", flush=True)


if __name__ == "__main__":
    main()
