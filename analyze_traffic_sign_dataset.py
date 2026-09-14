"""
交通标志数据集完整分析脚本
================================
分析 YOLO 格式数据集，输出：
  1. 数据集概况（图片数、实例数、类别数）
  2. 类别分布（每类实例数、图片数、占比、不平衡比）
  3. 边界框尺寸分布（绝对像素尺寸 + COCO 标准 small/medium/large）
  4. 宽高比分布
  5. 每图框数分布
  6. 图片分辨率分布
  7. 边界框位置热力图
  8. 自动检测 train/val/test 分割

用法：
    python analyze_traffic_sign_dataset.py                          # 自动检测 data.yaml
    python analyze_traffic_sign_dataset.py --data_dir D:/path/to/data  # 指定目录
    python analyze_traffic_sign_dataset.py --data_yaml data.yaml       # 指定 yaml
"""

import argparse
import sys
from pathlib import Path
from collections import Counter, defaultdict
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# ============================================================
# TT100K 类名（如果找不到 data.yaml 则使用）
# ============================================================
TT100K_CLASS_NAMES = [
    'i2', 'i4', 'i5', 'il100', 'il60', 'il80', 'io', 'ip',
    'p10', 'p11', 'p12', 'p19', 'p23', 'p26', 'p27',
    'p3', 'p5', 'p6', 'pg', 'ph4', 'ph4.5', 'ph5',
    'pl100', 'pl120', 'pl20', 'pl30', 'pl40', 'pl5', 'pl50',
    'pl60', 'pl70', 'pl80', 'pm20', 'pm30', 'pm55',
    'pn', 'pne', 'po', 'pr40',
    'w13', 'w32', 'w55', 'w57', 'w59', 'wo',
]

# 交通标志类别语义分组
TT100K_CLASS_GROUPS = {
    "禁令标志 (Prohibition)": ["p3", "p5", "p6", "p10", "p11", "p12", "p19", "p23", "p26", "p27", "pn", "pne", "po"],
    "指示标志 (Mandatory)": ["i2", "i4", "i5", "io", "ip"],
    "限速标志 (Speed Limit)": ["pl5", "pl20", "pl30", "pl40", "pl50", "pl60", "pl70", "pl80", "pl100", "pl120",
                              "il60", "il80", "il100"],
    "停车/让行 (Stop/Yield)": ["pg", "ph4", "ph4.5", "ph5", "pm20", "pm30", "pm55", "pr40"],
    "警告标志 (Warning)": ["w13", "w32", "w55", "w57", "w59", "wo"],
}


def parse_args():
    p = argparse.ArgumentParser(description="交通标志数据集完整分析")
    p.add_argument("--data_yaml", type=str, default=None, help="data.yaml 路径（自动检测类名和分割）")
    p.add_argument("--data_dir", type=str, default=None, help="数据集根目录（含 images/ 和 labels/ 子目录）")
    p.add_argument("--class_names", type=str, default=None, help='类名文件，每行一个类名，或 JSON list')
    p.add_argument("--output_dir", type=str, default="./dataset_analysis_output", help="输出目录")
    p.add_argument("--splits", type=str, nargs="+", default=None, help='要分析的分割名，如 train val test')
    return p.parse_args()


# ============================================================
# 工具函数
# ============================================================

def find_data_yamls(root_dir):
    """在目录中查找 data.yaml / dataset.yaml"""
    candidates = list(Path(root_dir).rglob("data*.yaml")) + list(Path(root_dir).rglob("*.yaml"))
    # 过滤掉模型配置文件
    excluded = {"coco", "voc", "imagenet", "argoverse", "objects365", "visdrone", "xview",
                "globalwheat", "sku", "dota", "yolo"}
    results = []
    for c in candidates:
        name_lower = c.stem.lower()
        if not any(ex in name_lower for ex in excluded):
            results.append(c)
    return results


def load_class_names_from_yaml(yaml_path):
    """从 YAML 文件中提取类名"""
    try:
        with open(yaml_path) as f:
            content = f.read()
    except Exception:
        return None, None

    # 简单解析 YAML 的 names 部分
    import re
    names = {}
    # 匹配 names: 后面跟的字典
    # 支持两种格式：names: ['a','b'] 或 names:\n  0: a\n  1: b
    list_match = re.search(r'names\s*:\s*\[([^\]]+)\]', content)
    if list_match:
        items = re.findall(r"['\"]([^'\"]*)['\"]", list_match.group(1))
        names = {i: item for i, item in enumerate(items)}
    else:
        # 尝试解析 dict 格式
        dict_section = re.search(r'names\s*:\s*\n((?:\s+\d+\s*:.*\n?)+)', content)
        if dict_section:
            for line in dict_section.group(1).strip().splitlines():
                m = re.match(r'\s*(\d+)\s*:\s*(.+)', line)
                if m:
                    names[int(m.group(1))] = m.group(2).strip().strip("'\"")

    if not names:
        return None, yaml_path.parent if yaml_path else None

    # 转为有序列表
    max_idx = max(names.keys())
    class_list = [names.get(i, f"class_{i}") for i in range(max_idx + 1)]

    # 尝试找出数据路径
    data_root = None
    path_match = re.search(r'path\s*:\s*(.+)', content)
    if path_match:
        p = path_match.group(1).strip()
        data_root = Path(p)
        if not data_root.is_absolute():
            data_root = (Path(yaml_path).parent / data_root).resolve()

    return class_list, data_root


def load_class_names(class_file):
    """从文件加载类名"""
    p = Path(class_file)
    if not p.exists():
        raise FileNotFoundError(f"类名文件不存在: {class_file}")
    if p.suffix == '.json':
        return json.loads(p.read_text(encoding='utf-8'))
    else:
        return [line.strip() for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]


def discover_splits(data_root):
    """自动发现数据集的 train/val/test 分割"""
    data_root = Path(data_root)
    splits = set()

    # 模式1: data_root/images/train, data_root/labels/train
    for sub in ["images", "labels"]:
        d = data_root / sub
        if d.exists():
            for child in d.iterdir():
                if child.is_dir():
                    splits.add(child.name)

    # 模式2: data_root/train/images, data_root/train/labels
    for child in data_root.iterdir():
        if child.is_dir():
            imgs = child / "images"
            lbls = child / "labels"
            if imgs.exists() or lbls.exists():
                splits.add(child.name)

    return sorted(splits)


def find_images_and_labels(data_root, split_name):
    """找到指定分割的 images 和 labels 目录"""
    data_root = Path(data_root)

    patterns = [
        (data_root / "images" / split_name, data_root / "labels" / split_name),
        (data_root / split_name / "images", data_root / split_name / "labels"),
        (data_root / "images" / split_name, data_root / "labels" / split_name),
    ]

    for img_dir, lbl_dir in patterns:
        if img_dir.exists() and lbl_dir.exists():
            return img_dir, lbl_dir

    # 宽松匹配：只要求 labels 存在
    for img_dir, lbl_dir in patterns:
        if lbl_dir.exists():
            return img_dir if img_dir.exists() else None, lbl_dir

    return None, None


def read_yolo_label(label_path, img_w=None, img_h=None):
    """读取 YOLO 格式标签，返回 [(class_id, cx, cy, w, h), ...]"""
    bboxes = []
    if not label_path.exists():
        return bboxes
    raw = label_path.read_text(encoding='utf-8', errors='ignore').strip()
    if not raw:
        return bboxes
    for line in raw.splitlines():
        parts = line.strip().split()
        if len(parts) >= 5:
            cls = int(parts[0])
            vals = [float(x) for x in parts[1:5]]
            # 验证归一化坐标范围
            if all(0 <= v <= 1 for v in vals) or (img_w and img_h):
                bboxes.append((cls, *vals))
    return bboxes


def get_image_size(img_path):
    """获取图片尺寸（不加载全图，只读头部）"""
    try:
        import struct
        with open(img_path, 'rb') as f:
            header = f.read(32)
            if header[:2] == b'\xff\xd8':  # JPEG
                f.seek(0)
                size = _get_jpeg_size(f)
                if size:
                    return size
    except Exception:
        pass

    # 回退：用 cv2 读取
    try:
        import cv2
        img = cv2.imread(str(img_path))
        if img is not None:
            return img.shape[1], img.shape[0]
    except Exception:
        pass

    return None, None


def _get_jpeg_size(f):
    """解析 JPEG 头部获取尺寸"""
    import struct
    try:
        f.seek(2)
        while True:
            marker = f.read(2)
            if len(marker) < 2 or marker[0] != 0xFF:
                break
            if marker[1] in (0xC0, 0xC1, 0xC2):
                f.read(3)
                h, w = struct.unpack('>HH', f.read(4))
                return w, h
            seg_len = struct.unpack('>H', f.read(2))[0]
            f.seek(seg_len - 2, 1)
    except Exception:
        pass
    return None, None


def classify_bbox_size(w_px, h_px):
    """按 COCO 标准分类框大小：small(<32^2), medium(32^2~96^2), large(>96^2)"""
    area = w_px * h_px
    if area < 32 * 32:
        return "small"
    elif area < 96 * 96:
        return "medium"
    else:
        return "large"


def classify_aspect_ratio(w, h):
    """宽高比分类"""
    if w == 0 or h == 0:
        return "unknown"
    ratio = w / h
    if ratio < 0.5:
        return "tall (<0.5)"
    elif ratio < 0.8:
        return "slightly tall (0.5-0.8)"
    elif ratio <= 1.25:
        return "square (0.8-1.25)"
    elif ratio <= 2.0:
        return "slightly wide (1.25-2.0)"
    else:
        return "wide (>2.0)"


# ============================================================
# 分析核心
# ============================================================

class DatasetAnalyzer:
    def __init__(self, img_dir, lbl_dir, class_names, split_name="train", max_images_for_resolution=5000):
        self.img_dir = Path(img_dir) if img_dir else None
        self.lbl_dir = Path(lbl_dir)
        self.class_names = class_names
        self.split_name = split_name
        self.num_classes = len(class_names)
        self.max_images_for_resolution = max_images_for_resolution

        # 统计变量
        self.num_images = 0
        self.num_instances = 0
        self.num_empty_images = 0
        self.class_instance_counts = Counter()
        self.class_image_counts = Counter()
        self.bbox_areas = []          # 绝对面积 (px²)
        self.bbox_widths = []         # 绝对宽度 (px)
        self.bbox_heights = []        # 绝对高度 (px)
        self.bbox_rel_areas = []      # 相对面积 (归一化)
        self.aspect_ratios = []       # 宽高比 w/h
        self.bboxes_per_image = []    # 每图框数
        self.image_sizes = []         # (w, h) 图片尺寸
        self.bbox_centers = []        # (cx_norm, cy_norm) 归一化中心坐标
        self.missing_images = 0
        self.corrupted_bboxes = 0

    def run(self):
        print(f"\n{'='*60}")
        print(f"分析分割: {self.split_name}")
        print(f"  图片目录: {self.img_dir}")
        print(f"  标签目录: {self.lbl_dir}")
        print(f"{'='*60}")

        label_files = sorted(self.lbl_dir.glob("*.txt"))
        if not label_files:
            print(f"  [警告] 未找到 .txt 标签文件！")
            return

        print(f"  标签文件数: {len(label_files)}")
        print(f"  正在解析标签...")

        for i, lbl_path in enumerate(label_files):
            # 尝试匹配图片
            img_path = None
            img_w = img_h = None
            if self.img_dir:
                for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff']:
                    candidate = self.img_dir / (lbl_path.stem + ext)
                    if candidate.exists():
                        img_path = candidate
                        break
                if img_path is None:
                    # 不区分大小写再试
                    stem_lower = lbl_path.stem.lower()
                    for f in self.img_dir.iterdir():
                        if f.stem.lower() == stem_lower and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff']:
                            img_path = f
                            break

            # 读取标签
            bboxes = read_yolo_label(lbl_path, img_w, img_h)
            if not bboxes:
                self.num_empty_images += 1
            self.num_images += 1
            self.bboxes_per_image.append(len(bboxes))
            self.num_instances += len(bboxes)

            classes_in_img = set()
            for bbox in bboxes:
                cls_id, cx_n, cy_n, w_n, h_n = bbox
                classes_in_img.add(cls_id)
                self.class_instance_counts[cls_id] += 1
                self.bbox_rel_areas.append(w_n * h_n)
                self.bbox_centers.append((cx_n, cy_n))
                if w_n > 0 and h_n > 0:
                    self.aspect_ratios.append(w_n / h_n)

            for cls_id in classes_in_img:
                self.class_image_counts[cls_id] += 1

            # 获取图片尺寸（采样，避免对大数据集全量读取）
            if img_path and i < self.max_images_for_resolution:
                w, h = get_image_size(img_path)
                if w and h:
                    self.image_sizes.append((w, h))
                    # 计算绝对尺寸
                    for bbox in bboxes:
                        _, _, _, bw_n, bh_n = bbox
                        abs_w = bw_n * w
                        abs_h = bh_n * h
                        self.bbox_widths.append(abs_w)
                        self.bbox_heights.append(abs_h)
                        self.bbox_areas.append(abs_w * abs_h)

            # 进度提示
            if (i + 1) % 5000 == 0 or (i + 1) == len(label_files):
                print(f"    进度: {i+1}/{len(label_files)} "
                      f"({(i+1)/len(label_files)*100:.1f}%)")

        if self.img_dir and self.max_images_for_resolution < len(label_files):
            print(f"  [注] 分辨率只采样了前 {self.max_images_for_resolution} 张图片")

        self._print_summary()
        return self

    def _print_summary(self):
        print(f"\n{'─'*50}")
        print(f"📊 {self.split_name} 分割 - 基础统计")
        print(f"{'─'*50}")
        print(f"  总图片数:      {self.num_images}")
        print(f"  总实例数:      {self.num_instances}")
        print(f"  类别数:        {len(self.class_instance_counts)}")
        print(f"  空标注图片:    {self.num_empty_images} "
              f"({self.num_empty_images/self.num_images*100:.1f}%)" if self.num_images > 0 else "  空标注图片:    0")
        print(f"  平均框数/图:   {self.num_instances/self.num_images:.2f}" if self.num_images > 0 else "  平均框数/图:   N/A")
        print(f"  缺失图片:      {self.missing_images}")
        if self.num_instances > 0:
            max_cls_id = max(self.class_instance_counts, key=self.class_instance_counts.get)
            min_cls_id = min(self.class_instance_counts, key=self.class_instance_counts.get)
            max_name = self.class_names[max_cls_id] if max_cls_id < len(self.class_names) else f"cls{max_cls_id}"
            min_name = self.class_names[min_cls_id] if min_cls_id < len(self.class_names) else f"cls{min_cls_id}"
            max_count = self.class_instance_counts[max_cls_id]
            min_count = self.class_instance_counts[min_cls_id]
            print(f"  最多类别:      {max_name} ({max_count} 实例)")
            print(f"  最少类别:      {min_name} ({min_count} 实例)")
            print(f"  不平衡比:      {max_count/min_count:.1f}:1" if min_count > 0 else "  不平衡比:      ∞")


# ============================================================
# 可视化
# ============================================================

def plot_class_distribution(analyzer, output_dir):
    """绘制每类实例数柱状图"""
    if not analyzer.class_instance_counts:
        return

    sorted_items = sorted(analyzer.class_instance_counts.items(), key=lambda x: x[1], reverse=True)
    cls_ids = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]
    names = [analyzer.class_names[c] if c < len(analyzer.class_names) else f"cls{c}" for c in cls_ids]

    fig, ax = plt.subplots(figsize=(16, 6))
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(cls_ids)))
    bars = ax.bar(range(len(cls_ids)), counts, color=colors, edgecolor='white', linewidth=0.5)

    # 标注数值
    for i, (c, n) in enumerate(zip(cls_ids, counts)):
        ax.text(i, c + max(counts) * 0.01, str(n), ha='center', va='bottom',
                fontsize=6, rotation=90)

    ax.set_xticks(range(len(cls_ids)))
    ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel("实例数", fontsize=12)
    ax.set_title(f"{analyzer.split_name} - 类别实例分布 (总数: {analyzer.num_instances})", fontsize=14, fontweight='bold')
    ax.set_xlabel("类别", fontsize=12)

    # 添加平均值线
    avg = np.mean(counts)
    ax.axhline(y=avg, color='red', linestyle='--', linewidth=1, alpha=0.7, label=f'平均值: {avg:.0f}')
    ax.legend()

    plt.tight_layout()
    fig.savefig(output_dir / f"{analyzer.split_name}_class_distribution.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 类别分布图已保存")


def plot_bbox_size_distribution(analyzer, output_dir):
    """绘制框尺寸分布（COCO small/medium/large 饼图 + 面积直方图）"""
    if not analyzer.bbox_areas:
        print("  [跳过] 无框尺寸数据（缺少图片或未启用分辨率采样）")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左图: COCO size 分类饼图
    size_categories = Counter()
    for area in analyzer.bbox_areas:
        size_categories[classify_bbox_size(np.sqrt(area), np.sqrt(area))] += 1

    labels = []
    sizes = []
    colors_pie = []
    color_map = {"small": "#ff6b6b", "medium": "#ffd93d", "large": "#6bcb77"}
    for cat in ["small", "medium", "large"]:
        if cat in size_categories:
            labels.append(f"{cat}\n(<32²)" if cat == "small" else f"{cat}\n(32²~96²)" if cat == "medium" else f"{cat}\n(>96²)")
            sizes.append(size_categories[cat])
            colors_pie.append(color_map[cat])

    ax = axes[0]
    if sizes:
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                           colors=colors_pie, startangle=90)
        for at in autotexts:
            at.set_fontsize(10)
    ax.set_title("框尺寸分类 (COCO 标准)", fontsize=13, fontweight='bold')

    # 右图: 面积分布直方图
    ax = axes[1]
    sqrt_areas = [np.sqrt(a) for a in analyzer.bbox_areas if a > 0]
    ax.hist(sqrt_areas, bins=80, color='steelblue', edgecolor='white', alpha=0.85, density=True)
    ax.set_xlabel("sqrt(area) = 边长几何均值 (px)", fontsize=11)
    ax.set_ylabel("密度", fontsize=11)
    ax.set_title("框尺寸 sqrt(area) 分布", fontsize=13, fontweight='bold')

    # 标注分界线
    for threshold, label, color in [(32, "small", "#ff6b6b"), (96, "large", "#6bcb77")]:
        ax.axvline(x=threshold, color=color, linestyle='--', linewidth=1.5, alpha=0.8)
        ax.text(threshold, ax.get_ylim()[1] * 0.95, label, ha='center', fontsize=9, color=color,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

    # 统计信息
    if sqrt_areas:
        mean_s = np.mean(sqrt_areas)
        median_s = np.median(sqrt_areas)
        ax.text(0.98, 0.95, f"均值: {mean_s:.1f} px\n中位数: {median_s:.1f} px",
                transform=ax.transAxes, ha='right', va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout()
    fig.savefig(output_dir / f"{analyzer.split_name}_bbox_size.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 框尺寸分布图已保存")


def plot_aspect_ratio_distribution(analyzer, output_dir):
    """宽高比分布"""
    if not analyzer.aspect_ratios:
        print("  [跳过] 无宽高比数据")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左图: 宽高比直方图
    ax = axes[0]
    ratios = [min(r, 5.0) for r in analyzer.aspect_ratios]  # 截断极端值
    ax.hist(ratios, bins=60, color='coral', edgecolor='white', alpha=0.85, density=True)
    ax.set_xlabel("宽高比 (w/h)", fontsize=11)
    ax.set_ylabel("密度", fontsize=11)
    ax.set_title("边框宽高比分布", fontsize=13, fontweight='bold')
    ax.axvline(x=1.0, color='black', linestyle='--', linewidth=1, alpha=0.5, label='1:1 正方形')
    ax.legend(fontsize=9)
    mean_r = np.mean(analyzer.aspect_ratios)
    median_r = np.median(analyzer.aspect_ratios)
    ax.text(0.98, 0.95, f"均值: {mean_r:.2f}\n中位数: {median_r:.2f}",
            transform=ax.transAxes, ha='right', va='top', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.9))

    # 右图: 宽高比分类饼图
    ax = axes[1]
    ar_categories = Counter()
    for r in analyzer.aspect_ratios:
        if r <= 0:
            continue
        ar_categories[classify_aspect_ratio(r, 1.0)] += 1

    labels = []
    vals = []
    pie_colors = plt.cm.Set2(np.linspace(0, 1, 6))
    for i, (cat, count) in enumerate(ar_categories.most_common()):
        labels.append(cat)
        vals.append(count)
    if vals:
        wedges, texts, autotexts = ax.pie(vals, labels=labels, autopct='%1.1f%%',
                                           colors=pie_colors[:len(vals)], startangle=90)
        for at in autotexts:
            at.set_fontsize(8)
    ax.set_title("宽高比分类", fontsize=13, fontweight='bold')

    plt.tight_layout()
    fig.savefig(output_dir / f"{analyzer.split_name}_aspect_ratio.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 宽高比分布图已保存")


def plot_bboxes_per_image(analyzer, output_dir):
    """每图框数分布"""
    if not analyzer.bboxes_per_image:
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    max_boxes = max(analyzer.bboxes_per_image)
    bins = min(50, max_boxes + 1)
    ax.hist(analyzer.bboxes_per_image, bins=bins, color='mediumseagreen',
            edgecolor='white', alpha=0.85)

    # 统计信息
    avg = np.mean(analyzer.bboxes_per_image)
    median = np.median(analyzer.bboxes_per_image)
    p99 = np.percentile(analyzer.bboxes_per_image, 99)

    ax.set_xlabel("每图框数", fontsize=12)
    ax.set_ylabel("图片数", fontsize=12)
    ax.set_title(f"{analyzer.split_name} - 每图标注框数分布", fontsize=14, fontweight='bold')
    ax.text(0.98, 0.95,
            f"总图片: {analyzer.num_images}\n"
            f"平均: {avg:.1f}\n"
            f"中位数: {median:.0f}\n"
            f"P99: {p99:.0f}\n"
            f"空图: {analyzer.num_empty_images}",
            transform=ax.transAxes, ha='right', va='top', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout()
    fig.savefig(output_dir / f"{analyzer.split_name}_boxes_per_image.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 每图框数分布图已保存")


def plot_image_resolution(analyzer, output_dir):
    """图片分辨率散点图"""
    if not analyzer.image_sizes:
        print("  [跳过] 无分辨率数据")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ws, hs = zip(*analyzer.image_sizes)
    ws = np.array(ws)
    hs = np.array(hs)

    # 左图: 散点
    ax = axes[0]
    ax.scatter(ws, hs, alpha=0.3, s=3, c='teal', edgecolors='none')
    ax.set_xlabel("宽度 (px)", fontsize=11)
    ax.set_ylabel("高度 (px)", fontsize=11)
    ax.set_title("图片分辨率分布", fontsize=13, fontweight='bold')

    # 标注常见分辨率
    common_res = [(2048, 2048), (1920, 1080), (1280, 720), (640, 640)]
    for rw, rh in common_res:
        ax.axhline(y=rh, color='gray', linestyle=':', alpha=0.3)
        ax.axvline(x=rw, color='gray', linestyle=':', alpha=0.3)

    mx = max(ws.max(), hs.max()) * 1.05
    ax.set_xlim(0, mx)
    ax.set_ylim(0, mx)
    ax.set_aspect('equal')

    ax.text(0.02, 0.98,
            f"图片数: {len(ws)}\n"
            f"分辨率范围: {ws.min()}x{hs.min()} ~ {ws.max()}x{hs.max()}\n"
            f"中位数: {int(np.median(ws))}x{int(np.median(hs))}",
            transform=ax.transAxes, ha='left', va='top', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.9))

    # 右图: 宽/高分别的直方图
    ax = axes[1]
    ax.hist(ws, bins=50, alpha=0.6, label=f'宽度 (μ={ws.mean():.0f})', color='steelblue', edgecolor='white')
    ax.hist(hs, bins=50, alpha=0.6, label=f'高度 (μ={hs.mean():.0f})', color='coral', edgecolor='white')
    ax.set_xlabel("像素", fontsize=11)
    ax.set_ylabel("图片数", fontsize=11)
    ax.set_title("宽/高分布", fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)

    plt.tight_layout()
    fig.savefig(output_dir / f"{analyzer.split_name}_resolution.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 分辨率分布图已保存")


def plot_bbox_heatmap(analyzer, output_dir):
    """边界框中心位置热力图"""
    if not analyzer.bbox_centers:
        print("  [跳过] 无中心坐标数据")
        return

    fig, ax = plt.subplots(figsize=(7, 6))
    cx, cy = zip(*analyzer.bbox_centers)

    # 2D 直方图
    h = ax.hist2d(cx, cy, bins=(40, 40), cmap='hot', range=[[0, 1], [0, 1]])
    plt.colorbar(h[3], ax=ax, label='框数量')
    ax.set_xlabel("归一化 X 中心", fontsize=11)
    ax.set_ylabel("归一化 Y 中心", fontsize=11)
    ax.set_title(f"{analyzer.split_name} - 边界框位置热力图", fontsize=14, fontweight='bold')
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)  # 翻转 y 轴使图像方向一致（上=0）

    ax.text(0.02, 0.02,
            f"总框数: {len(cx):,}\n"
            f"X均值: {np.mean(cx):.3f}\n"
            f"Y均值: {np.mean(cy):.3f}",
            transform=ax.transAxes, ha='left', va='bottom', fontsize=9,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    plt.tight_layout()
    fig.savefig(output_dir / f"{analyzer.split_name}_heatmap.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 位置热力图已保存")


def plot_group_distribution(analyzer, output_dir):
    """按语义分组绘制类别分布"""
    if not TT100K_CLASS_GROUPS:
        return

    # 检查是否使用了 TT100K 类名
    if analyzer.class_names[:7] != ['i2', 'i4', 'i5', 'il100', 'il60', 'il80', 'io']:
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    group_data = {}
    for gname, members in TT100K_CLASS_GROUPS.items():
        count = 0
        for m in members:
            if m in analyzer.class_names:
                idx = analyzer.class_names.index(m)
                count += analyzer.class_instance_counts.get(idx, 0)
        group_data[gname] = count

    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']
    bars = ax.bar(range(len(group_data)), list(group_data.values()), color=colors, edgecolor='white', linewidth=1)
    ax.set_xticks(range(len(group_data)))
    ax.set_xticklabels([g.split(' (')[0] for g in group_data.keys()], fontsize=10)
    ax.set_ylabel("实例数", fontsize=12)
    ax.set_title(f"{analyzer.split_name} - 交通标志类别分组统计", fontsize=14, fontweight='bold')

    # 标注
    for i, (gname, count) in enumerate(group_data.items()):
        pct = count / analyzer.num_instances * 100 if analyzer.num_instances > 0 else 0
        ax.text(i, count + max(group_data.values()) * 0.02, f"{count}\n({pct:.1f}%)",
                ha='center', fontsize=9, fontweight='bold')
        ax.text(i, count / 2, gname.split(' (')[1].rstrip(')') if ' (' in gname else '',
                ha='center', fontsize=7, color='white', fontweight='bold', rotation=90)

    plt.tight_layout()
    fig.savefig(output_dir / f"{analyzer.split_name}_group_distribution.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 分组统计图已保存")


def generate_report_json(analyzers, output_dir):
    """生成 JSON 格式的完整报告"""
    report = {
        "analysis_time": str(np.datetime64('now')),
        "splits": {},
        "overall_summary": {},
    }

    for analyzer in analyzers:
        split_data = {
            "num_images": analyzer.num_images,
            "num_instances": analyzer.num_instances,
            "num_empty_images": analyzer.num_empty_images,
            "num_classes": len(analyzer.class_instance_counts),
            "avg_bboxes_per_image": analyzer.num_instances / analyzer.num_images if analyzer.num_images > 0 else 0,
            "class_distribution": {},
        }

        for cls_id, count in sorted(analyzer.class_instance_counts.items()):
            name = analyzer.class_names[cls_id] if cls_id < len(analyzer.class_names) else f"cls{cls_id}"
            split_data["class_distribution"][name] = {
                "class_id": cls_id,
                "instances": count,
                "images": analyzer.class_image_counts.get(cls_id, 0),
            }

        # 框尺寸统计
        if analyzer.bbox_areas:
            areas = np.array(analyzer.bbox_areas)
            split_data["bbox_size"] = {
                "mean_area_px2": float(np.mean(areas)),
                "median_area_px2": float(np.median(areas)),
                "min_area_px2": float(np.min(areas)),
                "max_area_px2": float(np.max(areas)),
                "mean_sqrt_area_px": float(np.mean(np.sqrt(areas))),
                "size_categories": {},
            }
            for area in areas:
                cat = classify_bbox_size(np.sqrt(area), np.sqrt(area))
                split_data["bbox_size"]["size_categories"][cat] = \
                    split_data["bbox_size"]["size_categories"].get(cat, 0) + 1

        # 宽高比统计
        if analyzer.aspect_ratios:
            ratios = np.array(analyzer.aspect_ratios)
            split_data["aspect_ratio"] = {
                "mean": float(np.mean(ratios)),
                "median": float(np.median(ratios)),
                "std": float(np.std(ratios)),
                "min": float(np.min(ratios)),
                "max": float(np.max(ratios)),
            }

        # 图片分辨率统计
        if analyzer.image_sizes:
            ws = [s[0] for s in analyzer.image_sizes]
            hs = [s[1] for s in analyzer.image_sizes]
            split_data["image_resolution"] = {
                "sampled_images": len(analyzer.image_sizes),
                "mean_width": float(np.mean(ws)),
                "mean_height": float(np.mean(hs)),
                "median_width": float(np.median(ws)),
                "median_height": float(np.median(hs)),
                "min_width": int(np.min(ws)),
                "min_height": int(np.min(hs)),
                "max_width": int(np.max(ws)),
                "max_height": int(np.max(hs)),
            }

        report["splits"][analyzer.split_name] = split_data

    # 全局汇总
    total_instances = sum(a.num_instances for a in analyzers)
    total_images = sum(a.num_images for a in analyzers)
    all_classes = set()
    for a in analyzers:
        all_classes.update(a.class_instance_counts.keys())
    report["overall_summary"] = {
        "total_images": total_images,
        "total_instances": total_instances,
        "total_classes": len(all_classes),
        "splits_analyzed": [a.split_name for a in analyzers],
    }

    json_path = output_dir / "analysis_report.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n  [报告] JSON 报告已保存至: {json_path}")


def generate_csv(analyzers, output_dir):
    """生成 CSV 表格"""
    for analyzer in analyzers:
        csv_path = output_dir / f"{analyzer.split_name}_class_stats.csv"
        with open(csv_path, 'w', encoding='utf-8-sig') as f:
            f.write("class_id,class_name,instances,images_with_class,"
                    "instance_pct,image_pct,instances_per_image\n")
            for cls_id in sorted(analyzer.class_instance_counts.keys()):
                name = analyzer.class_names[cls_id] if cls_id < len(analyzer.class_names) else f"cls{cls_id}"
                inst = analyzer.class_instance_counts[cls_id]
                imgs = analyzer.class_image_counts.get(cls_id, 0)
                inst_pct = inst / analyzer.num_instances * 100 if analyzer.num_instances > 0 else 0
                img_pct = imgs / analyzer.num_images * 100 if analyzer.num_images > 0 else 0
                ipi = inst / imgs if imgs > 0 else 0
                semantic_group = ""
                if TT100K_CLASS_GROUPS:
                    for gname, members in TT100K_CLASS_GROUPS.items():
                        if name in members:
                            semantic_group = gname.split(' (')[0]
                            break
                f.write(f"{cls_id},{name},{inst},{imgs},{inst_pct:.2f},{img_pct:.2f},{ipi:.2f},{semantic_group}\n")
        print(f"  [CSV] 类别统计已保存至: {csv_path}")


# ============================================================
# 主函数
# ============================================================

def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. 确定类名 ----
    class_names = None
    data_root = None

    if args.data_yaml:
        data_yaml_path = Path(args.data_yaml)
        class_names, yaml_root = load_class_names_from_yaml(data_yaml_path)
        if class_names:
            print(f"从 {data_yaml_path} 加载了 {len(class_names)} 个类别")
        if yaml_root:
            data_root = yaml_root
    elif args.data_dir:
        data_root = args.data_dir
    else:
        # 尝试自动搜索
        search_roots = [
            Path("."),
            Path("../TT100K"),
            Path("D:/project_workspace/TT100K"),
            Path("D:/project_workspace/TT100K/1"),
        ]
        for root in search_roots:
            yamls = find_data_yamls(root)
            for y in yamls:
                names, yaml_root = load_class_names_from_yaml(y)
                if names and len(names) >= 3:
                    class_names = names
                    data_root = yaml_root or root
                    print(f"自动检测到数据集配置: {y}")
                    print(f"数据根目录: {data_root}")
                    break
            if class_names:
                break

    # 加载类名文件
    if args.class_names:
        class_names = load_class_names(args.class_names)
        print(f"从文件加载了 {len(class_names)} 个类别")

    if class_names is None:
        print("未找到 data.yaml，使用默认 TT100K 45 类名")
        class_names = TT100K_CLASS_NAMES

    if data_root is None:
        if args.data_dir:
            data_root = args.data_dir
        else:
            # 尝试常见路径
            for candidate in [
                "D:/project_workspace/TT100K/1",
                "D:/project_workspace/TT100K",
                "../TT100K/1",
                "dataset",
                ".",
            ]:
                c = Path(candidate)
                if c.exists() and (list(c.glob("**/labels")) or list(c.glob("**/*.txt"))):
                    data_root = c
                    print(f"自动检测数据根目录: {data_root}")
                    break

    if data_root is None:
        print("错误: 无法确定数据集位置，请使用 --data_dir 参数指定")
        sys.exit(1)

    data_root = Path(data_root)
    print(f"\n数据根目录: {data_root}")
    print(f"类别数:    {len(class_names)}")
    print(f"类别:      {class_names[:10]}{'...' if len(class_names) > 10 else ''}")

    # ---- 2. 确定分割 ----
    if args.splits:
        splits = args.splits
    else:
        splits = discover_splits(data_root)
        if not splits:
            # 直接扫描 labels 目录
            lbl_dir = data_root / "labels"
            if lbl_dir.exists():
                if any(lbl_dir.glob("*.txt")):
                    splits = ["."]  # labels 目录下直接有 txt
                else:
                    splits = [d.name for d in lbl_dir.iterdir() if d.is_dir()]
            # 也可能标签就在 data_root 下
            if not splits and any(data_root.glob("*.txt")):
                splits = ["."]
        if not splits:
            splits = ["train"]
        print(f"检测到分割: {splits}")

    # ---- 3. 运行分析 ----
    analyzers = []
    for split in splits:
        img_dir, lbl_dir = find_images_and_labels(data_root, split)
        if lbl_dir is None:
            # 特殊处理：split 为 "." 表示 data_root 本身
            if split == ".":
                img_dir = data_root / "images" if (data_root / "images").exists() else None
                lbl_dir = data_root / "labels" if (data_root / "labels").exists() else data_root
            else:
                print(f"  [警告] 找不到分割 '{split}' 的标签目录，跳过")
                continue

        if not lbl_dir.exists():
            print(f"  [警告] 标签目录不存在: {lbl_dir}，跳过")
            continue

        analyzer = DatasetAnalyzer(img_dir, lbl_dir, class_names, split)
        analyzer.run()
        analyzers.append(analyzer)

    if not analyzers:
        print("\n错误: 没有找到任何可分析的数据！")
        print("请使用 --data_dir 指定数据根目录，格式为: data_dir/images/train + data_dir/labels/train")
        sys.exit(1)

    # ---- 4. 生成可视化 ----
    print(f"\n{'='*60}")
    print("生成可视化图表...")
    print(f"{'='*60}")

    for analyzer in analyzers:
        split_dir = output_dir / analyzer.split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        plot_class_distribution(analyzer, split_dir)
        plot_bbox_size_distribution(analyzer, split_dir)
        plot_aspect_ratio_distribution(analyzer, split_dir)
        plot_bboxes_per_image(analyzer, split_dir)
        plot_image_resolution(analyzer, split_dir)
        plot_bbox_heatmap(analyzer, split_dir)
        if class_names[:7] == ['i2', 'i4', 'i5', 'il100', 'il60', 'il80', 'io']:
            plot_group_distribution(analyzer, split_dir)

    # ---- 5. 生成报告 ----
    print(f"\n{'='*60}")
    print("生成报告文件...")
    print(f"{'='*60}")
    generate_report_json(analyzers, output_dir)
    generate_csv(analyzers, output_dir)

    # ---- 6. 打印最终汇总 ----
    print(f"\n{'='*60}")
    print("✅ 分析完成！")
    print(f"{'='*60}")
    print(f"输出目录: {output_dir.resolve()}")
    print(f"分割数:   {len(analyzers)}")

    total_instances = sum(a.num_instances for a in analyzers)
    total_images = sum(a.num_images for a in analyzers)
    print(f"总图片数: {total_images}")
    print(f"总实例数: {total_instances}")

    if len(analyzers) >= 1 and analyzers[0].num_instances > 0:
        c = analyzers[0].class_instance_counts
        if c:
            max_cls = max(c, key=c.get)
            min_cls = min(c, key=c.get)
            ratio = c[max_cls] / c[min_cls]
            max_name = class_names[max_cls] if max_cls < len(class_names) else f"cls{max_cls}"
            min_name = class_names[min_cls] if min_cls < len(class_names) else f"cls{min_cls}"
            print(f"不平衡比:  {ratio:.1f}:1 ({max_name}:{c[max_cls]} vs {min_name}:{c[min_cls]})")

    print(f"\n所有输出文件:")
    for f in sorted(output_dir.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(output_dir)}")


if __name__ == "__main__":
    main()
