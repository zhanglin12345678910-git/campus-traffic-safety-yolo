"""
步骤一：验证增强逻辑 — 确认 YOLO 标签框在 Albumentations 处理后依然精准对齐。

用法：
    python verify_augmentation.py

    
输出：
    在 verify_aug_output/ 下生成 10 张对比图（原图 vs 增强后），每张图叠加了目标框。
"""
import cv2
import numpy as np
import albumentations as A
from pathlib import Path
import random
import traceback
import warnings
warnings.filterwarnings("ignore")


def imwrite_unicode(path, img):
    """cv2.imwrite 不支持含中文的路径，用 imencode + Python I/O 替代。"""
    ret, buf = cv2.imencode(Path(path).suffix, img)
    if ret:
        Path(path).write_bytes(buf.tobytes())
    return ret

# ============================================================
# 配置区
# ============================================================
DATASET_ROOT = Path(r"<LOCAL_PATH>")
TRAIN_IMG   = DATASET_ROOT / "images" / "train"
TRAIN_LBL   = DATASET_ROOT / "labels" / "train"
OUT_DIR     = Path(__file__).parent / "verify_aug_output"
NUM_SAMPLES = 10

CLASS_NAMES = [
    'i2','i4','i5','il100','il60','il80','io','ip',
    'p10','p11','p12','p19','p23','p26','p27',
    'p3','p5','p6','pg','ph4','ph4.5','ph5',
    'pl100','pl120','pl20','pl30','pl40','pl5','pl50',
    'pl60','pl70','pl80','pm20','pm30','pm55',
    'pn','pne','po','pr40',
    'w13','w32','w55','w57','w59','wo',
]

# ============================================================
# "物理一致性" 增强管线 — 退化但非毁坏
# ============================================================
# 原则：天气/光照/退化三类扰动，强度控制在"真实场景可能遇到"的范围。
# 不加入旋转/缩放等会改变检测框的几何变换，只做光度+退化级扰动。
# （如需测试几何对齐，见下方 GEOMETRY_CHECK 开关）
# ============================================================

PHOTOMETRIC_PIPELINE = A.Compose([
    # ---- 天气模拟（极轻，防止图像内容被掩盖） ----
    A.RandomRain(slant_lower=-3, slant_upper=3, drop_length=2, drop_width=1,
                 drop_color=(240, 242, 247), blur_value=1, brightness_coefficient=0.98,
                 rain_type='drizzle', p=0.12),
    A.RandomShadow(shadow_roi=(0.0, 0.0, 1.0, 1.0), num_shadows_lower=1,
                   num_shadows_upper=1, shadow_dimension=3, p=0.25),
    A.RandomFog(fog_coef_lower=0.01, fog_coef_upper=0.05, alpha_coef=0.015, p=0.2),

    # ---- 光照扰动（小幅变化） ----
    A.RandomBrightnessContrast(brightness_limit=0.1, contrast_limit=0.1, p=0.5),
    A.HueSaturationValue(hue_shift_limit=5, sat_shift_limit=10, val_shift_limit=10, p=0.3),
    A.RandomGamma(gamma_limit=(95, 105), p=0.2),

    # ---- 退化/噪声（轻微） ----
    A.GaussNoise(var_limit=(3.0, 15.0), p=0.3),
    A.ISONoise(color_shift=(0.005, 0.02), intensity=(0.05, 0.15), p=0.2),
    A.MotionBlur(blur_limit=(3, 5), p=0.2),
    A.GaussianBlur(blur_limit=3, p=0.2),
    A.ImageCompression(quality_lower=80, quality_upper=95, p=0.2),

    # ---- 轻微色彩抖动 ----
    A.CLAHE(clip_limit=1.2, tile_grid_size=(8, 8), p=0.15),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'],
                            min_visibility=0.3, min_area=0.0))

# 几何变换检查（默认关闭，用户确认光度对齐后再开启测试）
GEOMETRY_CHECK = False
GEOMETRY_PIPELINE = A.Compose([
    A.RandomScale(scale_limit=0.15, p=0.5),
    A.Rotate(limit=10, border_mode=cv2.BORDER_CONSTANT, p=0.5),
], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'],
                            min_visibility=0.3, min_area=0.0))


def read_yolo_labels(label_path, img_w, img_h):
    """读取 YOLO 格式标签，返回 bbox 列表和 class_labels 列表。"""
    bboxes = []
    class_labels = []
    if not label_path.exists():
        return bboxes, class_labels
    for line in label_path.read_text().strip().splitlines():
        parts = line.strip().split()
        if len(parts) < 5:
            continue
        cls_id = int(parts[0])
        cx, cy, w, h = map(float, parts[1:5])
        bboxes.append([cx, cy, w, h])
        class_labels.append(cls_id)
    return bboxes, class_labels


def draw_yolo_bboxes(img, bboxes, class_labels, color=(0, 255, 0)):
    """在图像上绘制 YOLO 格式的 bbox（normalized）。"""
    h, w = img.shape[:2]
    for bbox, cls_id in zip(bboxes, class_labels):
        cx, cy, bw, bh = bbox
        x1 = int((cx - bw / 2) * w)
        y1 = int((cy - bh / 2) * h)
        x2 = int((cx + bw / 2) * w)
        y2 = int((cy + bh / 2) * h)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        name = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else str(cls_id)
        cv2.putText(img, name, (x1, max(y1 - 4, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    return img


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- 诊断：检查数据路径 ----
    print(f"数据集根目录: {DATASET_ROOT}")
    print(f"图像目录:     {TRAIN_IMG}  (存在: {TRAIN_IMG.exists()})")
    print(f"标签目录:     {TRAIN_LBL}  (存在: {TRAIN_LBL.exists()})")

    # 同时匹配 .jpg / .JPG / .png / .PNG
    patterns = ["*.jpg", "*.JPG", "*.png", "*.PNG"]
    all_imgs = []
    for pat in patterns:
        all_imgs.extend(TRAIN_IMG.glob(pat))
    print(f"找到图片总数: {len(all_imgs)}")
    print("-" * 50)

    # 收集有标签的图片（优先选标签数 > 1 的图）
    candidates = []
    for img_path in sorted(all_imgs):
        lbl_path = TRAIN_LBL / (img_path.stem + ".txt")
        if lbl_path.exists():
            raw = lbl_path.read_text().strip()
            n_labels = len([l for l in raw.splitlines() if l.strip()]) if raw else 0
            if n_labels > 0:
                candidates.append((img_path, lbl_path, n_labels))

    if not candidates:
        print("错误：未找到任何包含有效标签的图片！")
        return

    # 选含多框的图
    candidates.sort(key=lambda x: -x[2])
    selected = candidates[:NUM_SAMPLES]
    random.shuffle(selected)

    print(f"有效图片对: {len(candidates)}，将处理其中 {len(selected)} 张")
    print("-" * 50)

    success_count = 0
    for idx, (img_path, lbl_path, n_lbl) in enumerate(selected):
        try:
            img = cv2.imread(str(img_path))
            if img is None:
                print(f"  [{idx+1}] 跳过: 无法读取 {img_path.name}")
                continue
            h, w = img.shape[:2]

            bboxes, class_labels = read_yolo_labels(lbl_path, w, h)
            if not bboxes:
                print(f"  [{idx+1}] 跳过: 无标签 {img_path.name}")
                continue

            # ---- 光度+退化增强 ----
            transformed = PHOTOMETRIC_PIPELINE(image=img, bboxes=bboxes.copy(),
                                               class_labels=class_labels.copy())
            aug_img = transformed['image']
            aug_bboxes = transformed['bboxes']

            # ---- 几何增强（可选） ----
            if GEOMETRY_CHECK:
                transformed2 = GEOMETRY_PIPELINE(image=aug_img, bboxes=aug_bboxes.copy(),
                                                 class_labels=class_labels.copy())
                aug_img = transformed2['image']
                aug_bboxes = transformed2['bboxes']

            # ---- 绘制 ----
            orig_vis = img.copy()
            draw_yolo_bboxes(orig_vis, bboxes, class_labels, color=(0, 255, 0))

            aug_vis = aug_img.copy()
            draw_yolo_bboxes(aug_vis, aug_bboxes, class_labels, color=(0, 255, 255))

            # ---- 拼接保存 ----
            max_h = max(orig_vis.shape[0], aug_vis.shape[0])
            orig_pad = np.zeros((max_h, orig_vis.shape[1], 3), dtype=np.uint8)
            aug_pad = np.zeros((max_h, aug_vis.shape[1], 3), dtype=np.uint8)
            orig_pad[:orig_vis.shape[0], :] = orig_vis
            aug_pad[:aug_vis.shape[0], :] = aug_vis

            side_by_side = np.hstack([orig_pad, aug_pad])
            cv2.putText(side_by_side, "Original", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(side_by_side, "Augmented", (orig_pad.shape[1] + 10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            out_path = OUT_DIR / f"{img_path.stem}_verify.png"
            imwrite_unicode(out_path, side_by_side)

            n_kept = len(aug_bboxes)
            print(f"  [{idx+1}/{len(selected)}] {img_path.name} "
                  f"({w}x{h}, {n_lbl}标签 → 增强后保留 {n_kept} 框) → {out_path.name}")
            success_count += 1

        except Exception as e:
            print(f"  [{idx+1}] 处理 {img_path.name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("-" * 50)
    print(f"完成！成功生成 {success_count}/{len(selected)} 张对比图，输出到: {OUT_DIR}")

    if not GEOMETRY_CHECK:
        print("提示：当前仅测试光度/退化增强。若需验证旋转缩放对齐，请将脚本中 GEOMETRY_CHECK 改为 True。")


if __name__ == '__main__':
    main()
