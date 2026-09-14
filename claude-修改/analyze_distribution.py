"""分析 TT100K 训练集45类样本分布"""
from pathlib import Path
from collections import Counter

LABEL_DIR = Path(r"<LOCAL_PATH>")
CLASS_NAMES = [
    'i2','i4','i5','il100','il60','il80','io','ip',
    'p10','p11','p12','p19','p23','p26','p27',
    'p3','p5','p6','pg','ph4','ph4.5','ph5',
    'pl100','pl120','pl20','pl30','pl40','pl5','pl50',
    'pl60','pl70','pl80','pm20','pm30','pm55',
    'pn','pne','po','pr40',
    'w13','w32','w55','w57','w59','wo',
]

counter = Counter()
img_per_class = Counter()

for lbl_path in sorted(LABEL_DIR.glob("*.txt")):
    raw = lbl_path.read_text().strip()
    if not raw:
        continue
    classes_in_img = set()
    for line in raw.splitlines():
        parts = line.strip().split()
        if len(parts) >= 5:
            cls = int(parts[0])
            counter[cls] += 1
            classes_in_img.add(cls)
    for cls in classes_in_img:
        img_per_class[cls] += 1

print("=" * 60)
print("TT100K 训练集 45 类分布分析")
print("=" * 60)
print(f"{'ID':>3} {'类名':>8} {'实例数':>7} {'含该类图片数':>12} {'占比%':>8}")
print("-" * 45)

total_instances = sum(counter.values())
sorted_cls = sorted(counter.keys())

for cls in sorted_cls:
    name = CLASS_NAMES[cls] if cls < len(CLASS_NAMES) else f"cls{cls}"
    instances = counter[cls]
    imgs = img_per_class[cls]
    pct = instances / total_instances * 100
    print(f"{cls:>3} {name:>8} {instances:>7} {imgs:>12} {pct:>7.2f}%")

print("-" * 45)
print(f"总实例数: {total_instances}")
print(f"总图片数: {len(list(LABEL_DIR.glob('*.txt')))}")
print(f"类别数:   {len(counter)}")

# 找出最大/最小类别
max_cls = max(counter, key=counter.get)
min_cls = min(counter, key=counter.get)
max_name = CLASS_NAMES[max_cls] if max_cls < len(CLASS_NAMES) else f"cls{max_cls}"
min_name = CLASS_NAMES[min_cls] if min_cls < len(CLASS_NAMES) else f"cls{min_cls}"
print(f"\n最多: cls{max_cls} ({max_name}) = {counter[max_cls]} 实例")
print(f"最少: cls{min_cls} ({min_name}) = {counter[min_cls]} 实例")
print(f"不平衡比: {counter[max_cls] / counter[min_cls]:.1f}:1")

# 计算每类需要增强的倍数（目标: 每类达到最多种类的实例数）
target = counter[max_cls]
print(f"\n--- 均衡增强策略 (目标每类 {target} 实例) ---")
print(f"{'ID':>3} {'类名':>8} {'当前':>6} {'目标':>6} {'需增强倍数':>10} {'需新增实例':>10}")
for cls in sorted_cls:
    name = CLASS_NAMES[cls] if cls < len(CLASS_NAMES) else f"cls{cls}"
    current = counter[cls]
    needed = target - current
    ratio = target / current if current > 0 else float('inf')
    print(f"{cls:>3} {name:>8} {current:>6} {target:>6} {ratio:>10.2f}x {needed:>10}")
