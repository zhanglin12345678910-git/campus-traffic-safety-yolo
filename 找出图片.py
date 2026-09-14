import os
from pathlib import Path
from collections import defaultdict

# ======== 路径自己改 =========
GT_DIR   = Path(r"%USERPROFILE%\Desktop\CCTSDB 2021\实验\labels\test")        # 真实标注 txt（5 列）
OLD_DIR  = Path(r"<PROJECT_ROOT>\runs\detect\原模型-带txt2\labels")      # 旧模型预测 txt（6 列）
NEW_DIR  = Path(r"<PROJECT_ROOT>\runs\detect\完全修改好的结果-带txt2\labels")       # 新模型预测 txt（6 列）
DELTA_CF = 0.10                           # 置信度提升阈值
# ============================

def load_file(txt):
    """返回 {cls: [conf1,conf2,...]}，GT conf=1.0"""
    d = defaultdict(list)
    if not txt.exists():
        return d
    with txt.open() as f:
        for line in f:
            nums = list(map(float, line.strip().split()))
            if len(nums) == 5:
                cls, *_ = nums
                conf = 1.0
            else:                       # 预测多一列置信度
                cls, *_, conf = nums
            d[int(round(cls))].append(conf)
    return d

miss2hit, conf_gain = [], []

all_stems = {p.stem for p in GT_DIR.glob("*.txt")}   # 以 GT 为基准遍历

for stem in sorted(all_stems):
    gt  = load_file(GT_DIR / f"{stem}.txt")
    old = load_file(OLD_DIR / f"{stem}.txt")
    new = load_file(NEW_DIR / f"{stem}.txt")

    # -------------------------------- miss → hit
    if any(cls not in old and cls in new for cls in gt):
        miss2hit.append(stem)

    # -------------------------------- conf gain
    for cls in gt:
        if cls in old and cls in new:
            if max(new[cls]) - max(old[cls]) >= DELTA_CF:
                conf_gain.append(stem)
                break    # 同一图满足一次即可

# -------- 保存结果 --------
def dump(name, lst):
    with open(name, "w") as f:
        for s in lst:
            f.write(s + "\n")
    print(f"{name}  共 {len(lst)} 张")

dump("cls_miss2hit.txt", miss2hit)
dump("conf_gain.txt",    conf_gain)
