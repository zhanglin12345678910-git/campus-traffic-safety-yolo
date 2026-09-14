"""
稀疏化效果分析 - 对比第一阶段和第二阶段
=================================================

功能：
1. 加载两个模型的权重
2. 分析BN gamma参数的分布
3. 生成对比图表和统计报告
4. 评估稀疏化效果

Usage:
    python analyze_sparsity.py
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_bn_weights(model_path):
    """
    从模型中提取所有BN层的gamma参数
    
    Args:
        model_path: 模型权重路径
    
    Returns:
        gamma_values: numpy array of BN gamma values
        bn_info: 统计信息字典
    """
    model = YOLO(model_path)
    base_model = model.model
    
    gamma_values = []
    
    for name, module in base_model.named_modules():
        if 'BatchNorm' in module.__class__.__name__:
            if module.weight is not None:
                gamma_values.extend(module.weight.data.cpu().numpy())
    
    gamma_values = np.array(gamma_values)
    
    # 计算统计信息
    bn_info = {
        'total_params': len(gamma_values),
        'near_zero_count': np.sum(np.abs(gamma_values) < 0.01),
        'near_zero_pct': np.sum(np.abs(gamma_values) < 0.01) / len(gamma_values) * 100,
        'mean': np.mean(gamma_values),
        'std': np.std(gamma_values),
        'min': np.min(gamma_values),
        'max': np.max(gamma_values),
        'median': np.median(gamma_values),
    }
    
    return gamma_values, bn_info


def print_bn_stats(stage_name, gamma_values, bn_info):
    """打印BN统计信息"""
    print(f"\n{'='*60}")
    print(f"{stage_name}")
    print(f"{'='*60}")
    print(f"总BN参数数: {bn_info['total_params']}")
    print(f"接近零的参数(|γ|<0.01): {bn_info['near_zero_count']} ({bn_info['near_zero_pct']:.2f}%)")
    print(f"均值: {bn_info['mean']:.6f}")
    print(f"标准差: {bn_info['std']:.6f}")
    print(f"范围: [{bn_info['min']:.6f}, {bn_info['max']:.6f}]")
    print(f"中位数: {bn_info['median']:.6f}")
    print(f"{'='*60}")


def plot_comparison(gamma1, bn_info1, gamma2, bn_info2, output_path='sparsity_analysis.png'):
    """绘制对比图表"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Sparsity Analysis: Stage1 vs Stage2 Fine-tuning', fontsize=14, fontweight='bold')
    
    # 子图1: 直方图对比
    ax = axes[0, 0]
    bins = np.linspace(-0.5, 3.5, 50)
    ax.hist(gamma1, bins=bins, alpha=0.6, label='Stage1 (λ=1e-4)', edgecolor='black')
    ax.hist(gamma2, bins=bins, alpha=0.6, label='Stage2 (λ=5e-4)', edgecolor='black')
    ax.axvline(0.01, color='red', linestyle='--', linewidth=2, label='Threshold (0.01)')
    ax.set_xlabel('|γ| Value')
    ax.set_ylabel('Frequency')
    ax.set_title('BN Gamma Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 子图2: 箱线图
    ax = axes[0, 1]
    ax.boxplot([gamma1, gamma2], labels=['Stage1', 'Stage2'])
    ax.set_ylabel('|γ| Value')
    ax.set_title('BN Gamma Box Plot')
    ax.grid(True, alpha=0.3)
    
    # 子图3: 累积分布函数
    ax = axes[1, 0]
    sorted_gamma1 = np.sort(gamma1)
    sorted_gamma2 = np.sort(gamma2)
    ax.plot(sorted_gamma1, np.arange(len(gamma1)) / len(gamma1), 'o-', label='Stage1', markersize=2)
    ax.plot(sorted_gamma2, np.arange(len(gamma2)) / len(gamma2), 's-', label='Stage2', markersize=2)
    ax.axvline(0.01, color='red', linestyle='--', linewidth=2, label='Threshold')
    ax.set_xlabel('|γ| Value')
    ax.set_ylabel('Cumulative Probability')
    ax.set_title('Cumulative Distribution Function')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 子图4: 统计对比表
    ax = axes[1, 1]
    ax.axis('off')
    
    metrics = ['Total Params', 'Near-Zero (0.01)', 'Sparsity %', 'Mean', 'Std', 'Min-Max']
    stage1_vals = [
        f"{bn_info1['total_params']}",
        f"{bn_info1['near_zero_count']}",
        f"{bn_info1['near_zero_pct']:.2f}%",
        f"{bn_info1['mean']:.4f}",
        f"{bn_info1['std']:.4f}",
        f"[{bn_info1['min']:.4f}, {bn_info1['max']:.4f}]"
    ]
    stage2_vals = [
        f"{bn_info2['total_params']}",
        f"{bn_info2['near_zero_count']}",
        f"{bn_info2['near_zero_pct']:.2f}%",
        f"{bn_info2['mean']:.4f}",
        f"{bn_info2['std']:.4f}",
        f"[{bn_info2['min']:.4f}, {bn_info2['max']:.4f}]"
    ]
    
    table_data = []
    for i, metric in enumerate(metrics):
        table_data.append([metric, stage1_vals[i], stage2_vals[i]])
    
    table = ax.table(cellText=table_data, 
                     colLabels=['Metric', 'Stage1 (λ=1e-4)', 'Stage2 (λ=5e-4)'],
                     cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # 格式化表头
    for i in range(3):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # 交替行颜色
    for i in range(1, len(metrics) + 1):
        for j in range(3):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ 对比图表已保存: {output_path}")
    plt.close()


def main():
    """主程序"""
    work_dir = Path(__file__).parent
    
    # 模型路径
    model_stage1 = work_dir / "runs/sparse_train/PSSM-YOLO-Lite-稀疏训练2/weights/best.pt"
    # 第二阶段模型路径（完成后自动更新）
    model_stage2 = work_dir / "runs/sparse_train/PSSM-YOLO-Lite-稀疏微调/weights/best.pt"
    
    print(f"\nSparsity Analysis Tool")
    print(f"{'='*60}")
    
    # 检查stage1模型
    if not model_stage1.exists():
        print(f"❌ 找不到第一阶段模型: {model_stage1}")
        return
    
    print(f"✓ 找到Stage1模型: {model_stage1}")
    
    # 加载stage1模型
    try:
        gamma1, bn_info1 = get_bn_weights(str(model_stage1))
        print_bn_stats("Stage1: BN Parameter Distribution (λ=1e-4, 100 epochs)", gamma1, bn_info1)
    except Exception as e:
        print(f"❌ 加载Stage1模型失败: {e}")
        return
    
    # 检查stage2模型
    if not model_stage2.exists():
        print(f"\n⚠️ 第二阶段模型尚未完成: {model_stage2}")
        print(f"   请先运行: python run_finetune.py")
        print(f"\n   期望结果: 运行第二阶段后稀疏度应明显提升")
        return
    
    print(f"✓ 找到Stage2模型: {model_stage2}")
    
    # 加载stage2模型
    try:
        gamma2, bn_info2 = get_bn_weights(str(model_stage2))
        print_bn_stats("Stage2: BN Parameter Distribution (λ=5e-4, +50 epochs)", gamma2, bn_info2)
    except Exception as e:
        print(f"❌ 加载Stage2模型失败: {e}")
        return
    
    # 生成对比报告
    print(f"\n{'='*60}")
    print("Improvement Analysis")
    print(f"{'='*60}")
    
    sparsity_improvement = bn_info2['near_zero_pct'] - bn_info1['near_zero_pct']
    mean_reduction = bn_info1['mean'] - bn_info2['mean']
    
    print(f"稀疏度提升: {bn_info1['near_zero_pct']:.2f}% → {bn_info2['near_zero_pct']:.2f}% (+{sparsity_improvement:.2f}%)")
    print(f"平均γ值: {bn_info1['mean']:.6f} → {bn_info2['mean']:.6f} (↓{mean_reduction:.6f})")
    print(f"标准差: {bn_info1['std']:.6f} → {bn_info2['std']:.6f}")
    
    # 绘制对比图
    output_path = work_dir / "sparsity_analysis.png"
    plot_comparison(gamma1, bn_info1, gamma2, bn_info2, str(output_path))
    
    print(f"\n{'='*60}")
    if sparsity_improvement > 5:
        print("✓ 稀疏化效果显著！可以进行剪枝")
    elif sparsity_improvement > 1:
        print("⚠️ 稀疏化有所改善，但可能需要继续微调")
    else:
        print("⚠️ 稀疏化效果不明显，建议增大sparse_lambda")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
