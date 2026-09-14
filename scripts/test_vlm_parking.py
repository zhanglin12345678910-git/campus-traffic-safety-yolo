"""VLM（qwen3.7-flash）识图研判零风险实验 —— 不动任何业务代码。

对应 docs/VLM_INTEGRATION_PROPOSAL.md 3.3 节：
1. 先用纯文本请求验证专属端点连通性与模型可用性；
2. 再对真实校园样本发问「图中车辆停放是否合规，依据是什么」，评估方向性判断质量。

实验约定（遵循项目纪律）：
- 样本量小（<30）且无系统真值，**只能支持选型，不得宣称准确率**；
- 每张样本跑 2 轮，顺带观察输出一致性（确定性）；
- 图像上送前长边归一到 1024，base64 内联；
- 记录 usage token 与延迟，供成本对账；
- 密钥只从 .env 读取，绝不打印。

用法（项目根目录）：
    <LOCAL_PATH> scripts/test_vlm_parking.py
"""

from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path

import cv2
import httpx
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SAMPLES: list[tuple[str, str, str]] = [
    # (相对路径, 预期方向, 预期依据)
    ("校园照片/新增照片/车/IMG_9752.JPG", "疑似违停", "车辆沿路边无车位线区域成排停放，未见明确车位"),
    ("校园照片/新增照片/车/IMG_9759.JPG", "违停", "大量车辆横向占据道路/广场区域，无车位线"),
    ("校园照片/新增照片/车/IMG_9773.JPG", "合规", "车辆整齐停放在黄色车位线内"),
    ("uploads/inspections/IMG_9781-f97235ed242c.jpg", "不确定", "图书馆北侧道路，画面以禁鸣标志/道路为主，基本无停放车辆可判"),
    ("uploads/inspections/dormitory-road-c49d63487609.jpg", "不确定", "宿舍区道路远景车辆疑似停放，画质偏糊"),
    ("uploads/inspections/IMG_9769-eb284c099f6f.jpg", "不确定", "图像倒置，画面为限速5与连续弯路标志、树木，无停放车辆"),
]

SYSTEM_PROMPT = (
    "你是校园交通安全巡检辅助智能体的视觉研判模块。你只能依据图片中可见的证据判断，"
    "看不出就明确说不确定，不得编造画面里不存在的东西。"
    "判断「车辆停放是否合规」时，必须排除以下合法情形：等交通灯、排队通行、礼让行人、"
    "装卸货临时停靠、执行公务的车辆；只有在图内可见证据表明车辆无合法理由占用车行道、"
    "人行道、绿化区域、消防车通道或未按车位线停放时，才能判断为违停。"
    "图片模糊、角度异常、倒置或没有车辆时，结论必须是不确定。"
    "先描述看到什么，再给结论。只返回合法 JSON。"
)

USER_PROMPT = (
    "这是校园交通巡检现场照片。请判断图中车辆的停放行为是否合规，依据是什么。"
    "返回 JSON：{\"description\": \"先客观描述画面\", "
    "\"conclusion\": \"合规|疑似违停|违停|不确定\", "
    "\"confidence\": 0到1的小数, "
    "\"evidence\": [\"支撑结论的画面内可见证据\"], "
    "\"legal_scenarios_checked\": [\"你排除过的合法停放情形\"]}"
)


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in (PROJECT_ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def encode_image(path: Path, max_side: int = 1024) -> tuple[str, tuple[int, int]]:
    raw = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法解码: {path}")
    h, w = img.shape[:2]
    scale = min(1.0, max_side / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError("JPEG 编码失败")
    return base64.b64encode(buf.tobytes()).decode("ascii"), (img.shape[1], img.shape[0])


def chat(client: httpx.Client, base: str, model: str, key: str, messages: list, timeout: float) -> dict:
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "stream": False,
        "response_format": {"type": "json_object"},
    }
    if "deepseek" in base.lower():
        body["thinking"] = {"type": "disabled"}  # DeepSeek 用 thinking 字段关思维链
    else:
        body["enable_thinking"] = False  # 百炼 OpenAI 兼容端用 enable_thinking
    t0 = time.perf_counter()
    r = client.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=body,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - t0
    r.raise_for_status()
    data = r.json()
    return {
        "content": data["choices"][0]["message"]["content"],
        "usage": data.get("usage"),
        "elapsed": round(elapsed, 2),
    }


def main() -> None:
    import argparse

    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None, help="覆盖 .env 里的 VISION_LLM_MODEL")
    parser.add_argument("--base-url", default=None, help="覆盖 .env 里的 VISION_LLM_BASE_URL")
    parser.add_argument("--key-env", default="DASHSCOPE_API_KEY", help="读取密钥的环境变量名")
    parser.add_argument("--proxy", default=None, help="可选：出站代理（如 DeepSeek 需走代理时）")
    parser.add_argument("--output", default="outputs/vlm_experiment_20260913.json")
    args = parser.parse_args()

    env = load_env()
    key = env[args.key_env]
    base = (args.base_url or env["VISION_LLM_BASE_URL"]).rstrip("/")
    model = args.model or env.get("VISION_LLM_MODEL", "qwen3.7-flash")
    evidence: dict = {"model": model, "base_host": base.split("/")[2], "samples": []}

    client = httpx.Client(timeout=60.0, proxy=args.proxy)  # 百炼大陆直连无需代理；DeepSeek 需代理时显式传入
    try:
        # 第一步：纯文本连通性验证
        print(f"[1] 连通性验证 model={model} host={base.split('/')[2]}")
        try:
            ping = chat(
                client, base, model, key,
                [{"role": "user", "content": "只回复一个 JSON：{\"ok\": true}"}],
                timeout=30.0,
            )
            print(f"    OK, {ping['elapsed']}s, usage={ping['usage']}")
            evidence["ping"] = {"ok": True, "elapsed": ping["elapsed"], "usage": ping["usage"]}
        except httpx.HTTPStatusError as e:
            body = e.response.text[:400]
            print(f"    HTTP {e.response.status_code}: {body}")
            evidence["ping"] = {"ok": False, "status": e.response.status_code, "body": body}
            # 若模型名不对，列出可用模型名线索
            try:
                r = client.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=20.0)
                if r.status_code == 200:
                    names = [m.get("id") for m in r.json().get("data", [])]
                    hits = [n for n in names if "flash" in str(n).lower() or "vl" in str(n).lower() or "qwen" in str(n).lower()]
                    print(f"    /models 可用模型(过滤后 {len(hits)}/{len(names)}): {hits[:20]}")
                    evidence["models"] = hits
            except Exception as exc:  # noqa: BLE001
                print(f"    /models 也失败: {exc}")
            (PROJECT_ROOT / args.output).write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return

        # 第二步：逐样本识图
        for rel, expect, note in SAMPLES:
            path = PROJECT_ROOT / rel
            print(f"\n[样本] {rel}")
            print(f"    预期方向: {expect}（{note}）")
            try:
                b64, size = encode_image(path)
            except ValueError as exc:
                print(f"    跳过: {exc}")
                continue
            sample: dict = {"path": rel, "expect": expect, "image_size": size, "rounds": []}
            for rnd in (1, 2):
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "text", "text": USER_PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ]},
                ]
                try:
                    out = chat(client, base, model, key, messages, timeout=60.0)
                except Exception as exc:  # noqa: BLE001
                    print(f"    [第{rnd}轮] 调用失败: {exc}")
                    sample["rounds"].append({"error": str(exc)})
                    continue
                content = out["content"].strip()
                if content.startswith("```"):
                    lines = content.splitlines()
                    content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    parsed = {"_raw": content[:300]}
                print(f"    [第{rnd}轮] {out['elapsed']}s  结论={parsed.get('conclusion')}  "
                      f"置信度={parsed.get('confidence')}  usage={out['usage']}")
                desc = str(parsed.get("description", ""))[:120]
                print(f"          描述: {desc}")
                sample["rounds"].append(
                    {"elapsed": out["elapsed"], "usage": out["usage"], "result": parsed}
                )
            sample["consistent"] = (
                len(sample["rounds"]) == 2
                and all("result" in r for r in sample["rounds"])
                and sample["rounds"][0]["result"].get("conclusion") == sample["rounds"][1]["result"].get("conclusion")
            )
            evidence["samples"].append(sample)

        (PROJECT_ROOT / args.output).write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n证据已写入 {args.output}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
