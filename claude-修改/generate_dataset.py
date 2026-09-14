"""
步骤二：生成 20,000 张 New-TT100K 增强数据集。

策略：
  - 加权采样：含稀有类的图片被更频繁选中增强
  - 物理一致性：沿用 verify 阶段验证过的轻度退化管线
  - 备份：每 1000 张保存 checkpoint
  - 记录：生成 metadata.csv，对比增强前后类别分布

用法：
    python generate_dataset.py
"""
import cv2
import numpy as np
import albumentations as A
from pathlib import Path
from collections import Counter, defaultdict
import random
import json
import time
import sys
import warnings
warnings.filterwarnings("ignore")

# ============================================================
# 配置区
# ============================================================
DATASET_ROOT  = Path(r"<LOCAL_PATH>")
TRAIN_IMG     = DATASET_R你OOT / "images" / "train"
TRAIN_LBL     = DATASET_ROOT / "labels" / "train"
OUT_DIR       = Path(__file__).parent / "New-TT100K"
OUT_IMG       = OUT_DIR / "images" / "train"
OUT_LBL       = OUT_DIR / "labels" / "train"
CHECKPOINT    = OUT_DIR / "checkpoint.json"
METADATA_CSV  = OUT_DIR / "metadata.csv"

TOTAL_TARGET  = 20000          # 目标总图片数
SAVE_EVERY    = 1000           # 每 N 张保存 checkpoint

CLASS_NAMES = [
    'i2','i4','i5','il100','il60','il80','io','ip',
    'p10','p11','p12','p19','p23','p26','p27',
    'p3','p5','p6','pg','ph4','ph4.5','ph5',
    'pl100','pl120','pl20','pl30','pl40','pl5','pl50',
    'pl60','pl70','pl80','pm20','pm30','pm55',
    'pn','pne','po','pr40',
    'w13','w32','w55','w57','w59','wo',
]
NUM_CLASSES = len(CLASS_NAMES)

# ============================================================
# 增强管线（与 verify 阶段一致，物理一致性限制）
# ============================================================
AUG_PIPELINE = A.Compose([
    A.RandomRain(slant_lower=-3, slant_upper=3, drop_length=2, drop_width=1,
                 drop_color=(240, 242, 247), blur_value=1, brightness_coefficient=0.98,
                 rain_type='drizzle', p=0.12),
    A.RandomShadow(shadow_roi=(0.0, 0.0, 1.0, 1.0), num_shadows_lower=1,
                   num_shadows_upper=1, shadow_dimension=3, p=0.25),
    A.RandomFog(fog_coef_lower=0.01, fog_coef_upper=0.05, alpha_coef=0.015, p=0.2),
    A.RandomBrightnessContrast(brightness_limit=0.1, contrast_limit=0.1, p=0.5),
    A.HueSaturationValue(hue_shift_limit=5, sat_shift_limit=10, val_shift_limit=10, p=0.3),
    A.RandomGamma(gamma_limit=(95, 105), p=0.2),
    A.GaussNoise(var_limit=(3.0, 15.0), p=0.3),
    A.ISONoise(color_shift=(0.005, 0.02), intensity=(0.05, 0.15), p=0.2),
    A.MotionBlur(blur_limit=(3, 5), p=0.2),
    A.GaussianBlur(blur_limit=3, p=0.2),
    A.ImageCompression(quality_lower=80, quality_upper=95, p=0.2),
    A.CLAHE(clip_limit=1.2, tile_grid_size=(8, 8), p=0.15),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'],
                            min_visibility=0.3, min_area=0.0))


def imwrite_unicode(path, img):
    ret, buf = cv2.imencode(Path(path).suffix, img)
    if ret:
        Path(path).write_bytes(buf.tobytes())
    return ret


def read_labels(path):
    """读取 YOLO 格式标签，返回 [(cls, cx, cy, w, h), ...]"""
    bboxes, classes = [], []
    if not path.exists():
        return bboxes, classes
    for line in path.read_text().strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 5:
            classes.append(int(parts[0]))
            bboxes.append([float(x) for x in parts[1:5]])
    return bboxes, classes


def write_labels(path, bboxes, classes):
    """写入 YOLO 格式标签"""
    lines = []
    for cls, bbox in zip(classes, bboxes):
        lines.append(f"{cls} {' '.join(f'{x:.8f}' for x in bbox)}")
    path.write_text("\n".join(lines))


def compute_rarity_weights(img_paths, class_counts):
    """为每张图计算权重：含越稀有类的图权重越高"""
    total = sum(class_counts.values())
    weights = []
    for img_path in img_paths:
        lbl_path = TRAIN_LBL / (img_path.stem + ".txt")
        _, classes = read_labels(lbl_path)
        if not classes:
            weights.append(0.0)
            continue
        # 取图中最稀有类的权重（count 越小 rarity 越高）
        min_count = min(class_counts.get(c, 1) for c in classes)
        rarity = total / max(min_count, 1)
        weights.append(rarity)
    return weights


def build_image_index():
    """构建图片索引：每张图的路径、类别列表、标签"""
    img_index = []
    class_counts = Counter()

    for img_path in sorted(TRAIN_IMG.glob("*.jpg")):
        lbl_path = TRAIN_LBL / (img_path.stem + ".txt")
        bboxes, classes = read_labels(lbl_path)
        if not bboxes:
            continue
        for c in classes:
            class_counts[c] += 1
        img_index.append({
            "path": img_path,
            "labels": lbl_path,
            "bboxes": bboxes,
            "classes": classes,
        })

    return img_index, class_counts


def augment_one(entry, out_name):
    """对一张图做增强，保存图片+标签。返回是否成功。"""
    img = cv2.imread(str(entry["path"]))
    if img is None:
        return False

    bboxes = [b.copy() for b in entry["bboxes"]]
    classes = list(entry["classes"])

    try:
        transformed = AUG_PIPELINE(image=img, bboxes=bboxes, class_labels=classes)
    except Exception:
        return False

    aug_img = transformed["image"]
    aug_bboxes = transformed["bboxes"]
    aug_classes = transformed["class_labels"]

    if not aug_bboxes:
        return False

    # 保存图片
    img_out = OUT_IMG / f"{out_name}.jpg"
    if not imwrite_unicode(img_out, aug_img):
        return False

    # 保存标签
    lbl_out = OUT_LBL / f"{out_name}.txt"
    new_bboxes = [[cx, cy, w, h] for cx, cy, w, h in aug_bboxes]
    write_labels(lbl_out, new_bboxes, aug_classes)

    return True


def save_checkpoint(state):
    CHECKPOINT.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def load_checkpoint():
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text())
    return None


def log(msg):
    print(msg, flush=True)

def main():
    log("=" * 60)
    log("New-TT100K 数据集生成")
    log(f"目标总量: {TOTAL_TARGET} 张")
    log(f"原始数据: {DATASET_ROOT}")
    log("=" * 60)

    # ---- 检查断点 ----
    ckpt = load_checkpoint()
    if ckpt:
        log(f"\n发现断点: 已生成 {ckpt['generated']} 张，从该位置继续...")
        start_count = ckpt["generated"]
        gen_class_counts = Counter(ckpt.get("gen_class_counts", {}))
    else:
        start_count = 0
        gen_class_counts = Counter()

    # ---- 构建索引 ----
    log("\n[1/4] 分析原始数据类别分布...")
    img_index, orig_class_counts = build_image_index()
    n_orig = len(img_index)
    log(f"  原始有效图片: {n_orig} 张")
    log(f"  原始实例总数: {sum(orig_class_counts.values())}")
    log(f"  类别不平衡比: {max(orig_class_counts.values()) / min(orig_class_counts.values()):.1f}:1")

    # ---- 计算采样权重 ----
    log("\n[2/4] 计算加权采样策略...")
    n_needed = max(0, TOTAL_TARGET - n_orig - start_count)
    log(f"  还需生成: {n_needed} 张")

    img_paths = [e["path"] for e in img_index]
    weights = compute_rarity_weights(img_paths, orig_class_counts)

    # 归一化
    total_w = sum(weights)
    probs = [w / total_w if total_w > 0 else 1.0 / len(weights) for w in weights]

    # ---- 开始生成 ----
    log(f"\n[3/4] 开始生成 (每 {SAVE_EVERY} 张保存断点)...")
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    OUT_LBL.mkdir(parents=True, exist_ok=True)

    random.seed(42)
    success = 0
    fail = 0
    t_start = time.time()

    for i in range(n_needed):
        # 加权采样
        idx = random.choices(range(len(img_index)), weights=probs, k=1)[0]
        out_name = f"aug_{start_count + i + 1:06d}"

        if augment_one(img_index[idx], out_name):
            success += 1
            for c in img_index[idx]["classes"]:
                gen_class_counts[c] += 1
        else:
            fail += 1

        total_done = start_count + i + 1

        # 断点保存
        if (i + 1) % SAVE_EVERY == 0:
            elapsed = time.time() - t_start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (n_needed - i - 1) / rate if rate > 0 else 0
            save_checkpoint({
                "generated": start_count + success,
                "processed": total_done,
                "failures": fail,
                "gen_class_counts": dict(gen_class_counts),
                "target": TOTAL_TARGET,
            })
            log(f"  [断点] 已处理 {total_done}/{n_needed}, "
                  f"成功 {success}, 失败 {fail}, "
                  f"速率 {rate:.1f} 张/秒, 预计剩余 {eta:.0f} 秒")

        # 进度条
        if (i + 1) % 100 == 0:
            pct = (i + 1) / n_needed * 100
            log(f"  进度: {i+1}/{n_needed} ({pct:.1f}%)")

    elapsed = time.time() - t_start
    log(f"\n[4/4] 生成完成！耗时 {elapsed:.0f} 秒")
    log(f"  成功: {success}, 失败: {fail}")
    log(f"  总图片: {n_orig + success} (原始 {n_orig} + 增强 {success})")

    # ---- 生成 metadata.csv ----
    log(f"\n生成 metadata.csv...")
    total_new = sum(gen_class_counts.values())

    with open(METADATA_CSV, "w") as f:
        f.write("class_id,class_name,original_instances,augmented_instances,"
                "total_instances,original_pct,new_pct\n")
        for cls in range(NUM_CLASSES):
            orig = orig_class_counts.get(cls, 0)
            aug = gen_class_counts.get(cls, 0)
            name = CLASS_NAMES[cls]
            orig_pct = orig / sum(orig_class_counts.values()) * 100 if orig else 0
            new_pct = (orig + aug) / (sum(orig_class_counts.values()) + total_new) * 100
            f.write(f"{cls},{name},{orig},{aug},{orig + aug},{orig_pct:.2f},{new_pct:.2f}\n")

    # 不平衡比对比
    orig_max = max(orig_class_counts.values())
    orig_min = min(orig_class_counts.values())
    new_counts = Counter()
    for cls in range(NUM_CLASSES):
        new_counts[cls] = orig_class_counts.get(cls, 0) + gen_class_counts.get(cls, 0)
    new_max = max(new_counts.values())
    new_min = min(new_counts.values())

    log(f"  原始不平衡比: {orig_max / orig_min:.1f}:1")
    log(f"  增强后不平衡比: {new_max / new_min:.1f}:1")
    log(f"  metadata.csv 已保存至: {METADATA_CSV}")

    # ---- 清理断点 ----
    if CHECKPOINT.exists():
        CHECKPOINT.unlink()

    # ---- 生成 data.yaml ----
    yaml_path = OUT_DIR / "new_tt100k.yaml"
    yaml_path.write_text(f"""# New-TT100K Dataset
train: {OUT_IMG.as_posix()}
val: <LOCAL_PATH>
test: <LOCAL_PATH>
nc: {NUM_CLASSES}
names: {CLASS_NAMES}
""")
    log(f"  data.yaml 已保存至: {yaml_path}")

    log("\n" + "=" * 60)
    log("完成！数据集位置:")
    log(f"  图片: {OUT_IMG}")
    log(f"  标签: {OUT_LBL}")
    log(f"  统计: {METADATA_CSV}")
    log(f"  配置: {yaml_path}")
    log("=" * 60)


if __name__ == '__main__':
    main()
