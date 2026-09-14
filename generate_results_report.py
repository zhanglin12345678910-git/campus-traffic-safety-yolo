#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动生成训练结果报告
功能：
1. 从 results.csv 读取数据
2. 生成 Excel 报告
3. 生成 results.png 结果图
4. 生成详细的分析报告

使用方法：
    python generate_results_report.py --csv runs/train/你的实验/results.csv
    或
    python generate_results_report.py --dir runs/train/你的实验/
"""

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def plot_results_figure(csv_file, save_path=None):
    """
    绘制训练结果图（类似 results.png）
    
    Args:
        csv_file: CSV文件路径
        save_path: 保存路径，默认保存在csv同级目录
    """
    # 读取数据
    data = pd.read_csv(csv_file)
    
    # 创建子图
    fig, ax = plt.subplots(2, 5, figsize=(15, 8))
    fig.tight_layout(pad=3.0)
    
    # 列名
    columns = [x.strip() for x in data.columns]
    
    # 绘图索引（对应不同指标）
    indices = [2, 3, 4, 5, 6, 9, 10, 11, 7, 8]  # precision, recall, mAP50, mAP50-95, box_loss, cls_loss等
    
    ax = ax.ravel()
    
    x = data.values[:, 0]  # epoch
    
    for i, idx in enumerate(indices):
        if idx < len(columns):
            y = data.values[:, idx].astype("float")
            
            # 绘制原始数据
            ax[i].plot(x, y, marker=".", linewidth=2, markersize=6, label='原始数据', color='#1f77b4')
            
            # 绘制平滑曲线
            try:
                y_smooth = gaussian_filter1d(y, sigma=2)
                ax[i].plot(x, y_smooth, ":", linewidth=2, label='平滑曲线', color='red', alpha=0.7)
            except:
                pass
            
            ax[i].set_title(columns[idx], fontsize=11, fontweight='bold')
            ax[i].grid(True, alpha=0.3)
            ax[i].set_xlabel('Epoch', fontsize=9)
            ax[i].set_ylabel('Value', fontsize=9)
            ax[i].legend(fontsize=8)
    
    # 保存
    if save_path is None:
        save_path = Path(csv_file).parent / "results_enhanced.png"
    else:
        save_path = Path(save_path)
    
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 结果图已保存: {save_path}")
    
    return save_path


def generate_excel_report(csv_file, save_path=None):
    """
    生成Excel报告
    
    Args:
        csv_file: CSV文件路径
        save_path: Excel保存路径
    """
    # 读取数据
    data = pd.read_csv(csv_file)
    
    if save_path is None:
        save_path = Path(csv_file).parent / "训练结果报告.xlsx"
    else:
        save_path = Path(save_path)
    
    # 创建Excel写入器
    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
        
        # 1. 完整数据表
        data.to_excel(writer, sheet_name='完整数据', index=False)
        
        # 2. 摘要统计表
        summary_data = {
            '指标': ['最佳精度(mAP50)', '最低Box Loss', '最低Class Loss', '最高精确度', '最高召回率'],
            '数值': [
                data['metrics/mAP50(B)'].max() if 'metrics/mAP50(B)' in data.columns else 'N/A',
                data['train/box_loss'].min() if 'train/box_loss' in data.columns else 'N/A',
                data['train/cls_loss'].min() if 'train/cls_loss' in data.columns else 'N/A',
                data['metrics/precision(B)'].max() if 'metrics/precision(B)' in data.columns else 'N/A',
                data['metrics/recall(B)'].max() if 'metrics/recall(B)' in data.columns else 'N/A',
            ],
            'Epoch': [
                data['metrics/mAP50(B)'].idxmax() + 1 if 'metrics/mAP50(B)' in data.columns else 'N/A',
                data['train/box_loss'].idxmin() + 1 if 'train/box_loss' in data.columns else 'N/A',
                data['train/cls_loss'].idxmin() + 1 if 'train/cls_loss' in data.columns else 'N/A',
                data['metrics/precision(B)'].idxmax() + 1 if 'metrics/precision(B)' in data.columns else 'N/A',
                data['metrics/recall(B)'].idxmax() + 1 if 'metrics/recall(B)' in data.columns else 'N/A',
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='摘要统计', index=False)
        
        # 3. 训练损失统计
        if all(col in data.columns for col in ['train/box_loss', 'train/cls_loss', 'train/dfl_loss']):
            loss_data = {
                'Epoch': data['epoch'] if 'epoch' in data.columns else range(1, len(data) + 1),
                '训练Box Loss': data['train/box_loss'],
                '训练Cls Loss': data['train/cls_loss'],
                '训练DFL Loss': data['train/dfl_loss'],
                '验证Box Loss': data['val/box_loss'] if 'val/box_loss' in data.columns else 'N/A',
                '验证Cls Loss': data['val/cls_loss'] if 'val/cls_loss' in data.columns else 'N/A',
            }
            loss_df = pd.DataFrame(loss_data)
            loss_df.to_excel(writer, sheet_name='损失曲线', index=False)
        
        # 4. 验证指标统计
        if 'metrics/precision(B)' in data.columns:
            metrics_data = {
                'Epoch': data['epoch'] if 'epoch' in data.columns else range(1, len(data) + 1),
                '精确度(Precision)': data['metrics/precision(B)'],
                '召回率(Recall)': data['metrics/recall(B)'],
                'mAP50': data['metrics/mAP50(B)'],
                'mAP50-95': data['metrics/mAP50-95(B)'],
            }
            metrics_df = pd.DataFrame(metrics_data)
            metrics_df.to_excel(writer, sheet_name='验证指标', index=False)
    
    print(f"✅ Excel报告已保存: {save_path}")
    return save_path


def generate_text_report(csv_file, save_path=None):
    """
    生成文本报告
    
    Args:
        csv_file: CSV文件路径
        save_path: 文本报告保存路径
    """
    data = pd.read_csv(csv_file)
    
    if save_path is None:
        save_path = Path(csv_file).parent / "训练结果报告.txt"
    else:
        save_path = Path(save_path)
    
    # 生成报告内容
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("训练结果报告")
    report_lines.append("=" * 60)
    report_lines.append(f"\n训练轮数: {len(data)} epochs\n")
    
    # 最佳指标
    if 'metrics/mAP50(B)' in data.columns:
        best_map50 = data['metrics/mAP50(B)'].max()
        best_epoch = data['metrics/mAP50(B)'].idxmax() + 1
        report_lines.append(f"最佳 mAP50: {best_map50:.4f} (Epoch {best_epoch})")
    
    if 'metrics/mAP50-95(B)' in data.columns:
        best_map = data['metrics/mAP50-95(B)'].max()
        best_epoch = data['metrics/mAP50-95(B)'].idxmax() + 1
        report_lines.append(f"最佳 mAP50-95: {best_map:.4f} (Epoch {best_epoch})")
    
    if 'metrics/precision(B)' in data.columns:
        best_prec = data['metrics/precision(B)'].max()
        best_epoch = data['metrics/precision(B)'].idxmax() + 1
        report_lines.append(f"最佳 Precision: {best_prec:.4f} (Epoch {best_epoch})")
    
    if 'metrics/recall(B)' in data.columns:
        best_rec = data['metrics/recall(B)'].max()
        best_epoch = data['metrics/recall(B)'].idxmax() + 1
        report_lines.append(f"最佳 Recall: {best_rec:.4f} (Epoch {best_epoch})")
    
    report_lines.append("\n" + "=" * 60)
    report_lines.append("损失统计")
    report_lines.append("=" * 60)
    
    if 'train/box_loss' in data.columns:
        report_lines.append(f"训练 Box Loss: 最低 {data['train/box_loss'].min():.4f}, 平均 {data['train/box_loss'].mean():.4f}")
    
    if 'train/cls_loss' in data.columns:
        report_lines.append(f"训练 Cls Loss: 最低 {data['train/cls_loss'].min():.4f}, 平均 {data['train/cls_loss'].mean():.4f}")
    
    report_lines.append("\n" + "=" * 60)
    
    # 写入文件
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"✅ 文本报告已保存: {save_path}")
    return save_path


def main():
    parser = argparse.ArgumentParser(description='生成训练结果报告')
    parser.add_argument('--csv', type=str, help='results.csv 文件路径')
    parser.add_argument('--dir', type=str, help='训练结果目录（会自动查找results.csv）')
    parser.add_argument('--output', type=str, help='输出目录（可选）')
    
    args = parser.parse_args()
    
    # 确定CSV文件路径
    if args.csv:
        csv_file = Path(args.csv)
    elif args.dir:
        csv_file = Path(args.dir) / 'results.csv'
    else:
        print("❌ 请提供 --csv 或 --dir 参数")
        return
    
    # 检查文件是否存在
    if not csv_file.exists():
        print(f"❌ 文件不存在: {csv_file}")
        return
    
    print(f"📊 正在处理: {csv_file}")
    
    # 确定输出目录
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = csv_file.parent
    
    # 生成Excel报告
    excel_path = generate_excel_report(csv_file, save_path=output_dir / "训练结果报告.xlsx")
    
    # 生成结果图
    plot_results_figure(csv_file, save_path=output_dir / "results_enhanced.png")
    
    # 生成文本报告
    generate_text_report(csv_file, save_path=output_dir / "训练结果报告.txt")
    
    print("\n✅ 所有报告已生成完成！")
    print(f"\n输出目录: {output_dir}")


if __name__ == '__main__':
    main()

