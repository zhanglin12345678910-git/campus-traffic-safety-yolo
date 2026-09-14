"""知识库文档分块自检工具。

用途
----
`backend/app/services/rag.py` 的 `chunk_text()` 使用固定窗口切分：
`chunk_size=500` 字符、`chunk_overlap=80`，边界优先落在换行或句号处。
这意味着 **Markdown 表格一定会被从中间切开**，后续分块会失去表头，
大模型拿到「| `pl50` | 限制速度 50 km/h |」这种没有列名的残块时无法理解。

本脚本在入库前离线复现同一套分块逻辑，报告：
  - 每份文档的分块数量与长度分布；
  - 疑似失去表头的表格残块；
  - 过短分块（信息量不足，检索时容易被噪声压过）。

使用方法
--------
    python scripts/check_knowledge_chunks.py
    python scripts/check_knowledge_chunks.py path/to/other.md

编写知识库文档的经验规则（由本项目实测得出）
------------------------------------------
1. 表格请改写为条目式，每行自带「代号 + 名称 + 说明」，切到哪里都能独立读懂，例如：
   - `pl50` 限制速度 50 km/h：校园外围道路常见限速值。
2. 每个语义小节控制在 500 字符以内，让一个小节尽量落在一个分块里。
3. 在正文中显式写出该区域的检索词（区域类型、地点、YOLO 类别代号），
   因为哈希向量靠字面重合度打分，用词不一致会检不到。
4. `EMBEDDING_PROVIDER=hash` 时为字面匹配，非语义嵌入，同义改写不会提升召回。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """复刻 KnowledgeBaseService.chunk_text 的切分逻辑，保证与本工具结论一致。"""
    cleaned = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    if not cleaned:
        return []
    overlap = min(overlap, size - 1)
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


def inspect(path: Path) -> tuple[int, int]:
    """检查单份文档，返回 (分块数, 问题数)。"""
    text = path.read_text(encoding="utf-8", errors="ignore")
    chunks = chunk_text(text)
    if not chunks:
        print(f"\n=== {path.name} | 空文档，无法入库")
        return 0, 1

    lengths = [len(chunk) for chunk in chunks]
    print(
        f"\n=== {path.name} | {len(text)} 字 -> {len(chunks)} 块 "
        f"| 长度 min={min(lengths)} max={max(lengths)} 平均={sum(lengths) // len(lengths)}"
    )

    problems = 0
    for index, chunk in enumerate(chunks):
        head = chunk.split("\n")[0][:46]
        notes = []
        # 以管道符开头且不是首个分块：说明表格被切开且本块没有表头
        if index > 0 and chunk.lstrip().startswith("|"):
            notes.append("疑似无表头表格残块")
        if len(chunk) < 200:
            notes.append("分块过短，信息量偏低")
        if notes:
            problems += 1
        suffix = f"   <-- {'；'.join(notes)}" if notes else ""
        print(f"  [{index:02d}] {len(chunk):>3}字 | {head}{suffix}")
    return len(chunks), problems


def main(argv: list[str]) -> int:
    targets = [Path(arg) for arg in argv[1:]]
    if not targets:
        knowledge_dir = Path(__file__).resolve().parent.parent / "knowledge"
        targets = sorted(knowledge_dir.glob("*.md"))
    if not targets:
        print("没有找到待检查的文档")
        return 1

    total_chunks = 0
    total_problems = 0
    for target in targets:
        if not target.exists():
            print(f"跳过不存在的文件：{target}")
            continue
        chunks, problems = inspect(target)
        total_chunks += chunks
        total_problems += problems

    print(f"\n合计 {total_chunks} 个分块，{total_problems} 个需要关注")
    if total_problems:
        print("建议：把表格改为条目式，或缩短小节，使每块都能独立读懂。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
