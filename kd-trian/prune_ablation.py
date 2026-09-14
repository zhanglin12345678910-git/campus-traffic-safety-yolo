"""
剪枝率消融实验脚本 - 自动测试 20%, 30%, 50% 三种剪枝率
=================================================
功能：
1. 在稀疏训练完成后，自动测试多种剪枝率
2. 对每个剪枝率执行：剪枝 → 微调 → 验证
3. 生成对比报告，帮助选择最优剪枝率

使用方法：
1. 先完成稀疏训练（train_sparse.py）
2. 运行本脚本进行剪枝率消融实验
3. 查看生成的对比报告，选择最优剪枝率
4. 用最优剪枝率的模型进行蒸馏增强

Author: 林哥
Date: 2026-01-29
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultralytics import YOLO
from ultralytics.utils import LOGGER


# ============================================================================
# 配置区
# ============================================================================

CONFIG = {
    # ========== 输入模型（稀疏训练后的模型）==========
    'sparse_model': 'runs/sparse_train/PSSM-YOLO-Lite-稀疏训练/weights/best.pt',
    
    # ========== 数据集 ==========
    'data': '%USERPROFILE%\\Desktop\\CCTSDB 2021\\实验\\cctsdb.yaml',
    
    # ========== 剪枝率列表（消融实验）==========
    'prune_ratios': [0.2, 0.3, 0.5],  # 20%, 30%, 50%
    
    # ========== 微调参数 ==========
    'finetune_epochs': 50,     # 微调轮数
    'finetune_lr': 0.001,      # 微调学习率
    'batch': 32,
    'imgsz': 640,
    'device': '0',
    'workers': 8,
    
    # ========== 输出目录 ==========
    'output_dir': 'runs/prune_ablation',
}


# ============================================================================
# 核心函数
# ============================================================================

def prune_with_ratio(sparse_model_path, prune_ratio, save_dir):
    """
    使用指定剪枝率进行剪枝
    """
    from prune_model import prune_model
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Pruning with ratio: {prune_ratio*100:.0f}%")
    LOGGER.info(f"{'='*60}")
    
    pruned_path = prune_model(
        model_path=sparse_model_path,
        prune_ratio=prune_ratio,
        save_dir=save_dir,
    )
    
    return pruned_path


def finetune_model(pruned_model_path, config, experiment_name):
    """
    微调剪枝后的模型
    """
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Fine-tuning: {experiment_name}")
    LOGGER.info(f"{'='*60}")
    
    model = YOLO(pruned_model_path)
    
    results = model.train(
        data=config['data'],
        epochs=config['finetune_epochs'],
        batch=config['batch'],
        imgsz=config['imgsz'],
        device=config['device'],
        workers=config['workers'],
        lr0=config['finetune_lr'],
        project=config['output_dir'],
        name=f"{experiment_name}_finetune",
        exist_ok=True,
        mosaic=0.5,
        mixup=0.0,
    )
    
    # 返回最佳模型路径和验证结果
    best_model = Path(config['output_dir']) / f"{experiment_name}_finetune" / 'weights' / 'best.pt'
    return str(best_model), results


def evaluate_model(model_path, config):
    """
    评估模型性能
    """
    model = YOLO(model_path)
    
    # 获取模型信息
    model_info = model.info(verbose=False)
    
    # 验证
    results = model.val(
        data=config['data'],
        imgsz=config['imgsz'],
        device=config['device'],
        batch=config['batch'],
    )
    
    # 提取关键指标
    metrics = {
        'mAP50': results.box.map50,
        'mAP50-95': results.box.map,
        'precision': results.box.mp,
        'recall': results.box.mr,
    }
    
    # 获取参数量和GFLOPs
    params = sum(p.numel() for p in model.model.parameters())
    
    return {
        'params': params,
        'params_M': params / 1e6,
        **metrics
    }


def run_ablation_experiment(config):
    """
    运行完整的剪枝率消融实验
    """
    start_time = time.time()
    output_dir = Path(config['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    LOGGER.info(f"\n{'#'*60}")
    LOGGER.info(f"# Pruning Rate Ablation Study")
    LOGGER.info(f"# Prune Ratios: {[f'{r*100:.0f}%' for r in config['prune_ratios']]}")
    LOGGER.info(f"{'#'*60}\n")
    
    # 检查稀疏模型是否存在
    if not os.path.exists(config['sparse_model']):
        LOGGER.error(f"稀疏训练模型不存在: {config['sparse_model']}")
        LOGGER.error("请先运行 train_sparse.py 完成稀疏训练！")
        return None
    
    # 评估原始稀疏模型（基线）
    LOGGER.info("Evaluating baseline (sparse model without pruning)...")
    baseline_metrics = evaluate_model(config['sparse_model'], config)
    
    results = {
        'baseline': {
            'prune_ratio': 0,
            'model_path': config['sparse_model'],
            **baseline_metrics
        }
    }
    
    # 对每个剪枝率进行实验
    for prune_ratio in config['prune_ratios']:
        experiment_name = f"prune_{int(prune_ratio*100)}"
        
        LOGGER.info(f"\n{'#'*60}")
        LOGGER.info(f"# Experiment: {experiment_name} (Prune Ratio = {prune_ratio*100:.0f}%)")
        LOGGER.info(f"{'#'*60}\n")
        
        try:
            # 1. 剪枝
            prune_save_dir = output_dir / experiment_name / 'pruned'
            pruned_model_path = prune_with_ratio(
                config['sparse_model'], 
                prune_ratio, 
                str(prune_save_dir)
            )
            
            # 2. 评估剪枝后（微调前）
            LOGGER.info("Evaluating pruned model (before fine-tuning)...")
            pruned_metrics = evaluate_model(pruned_model_path, config)
            
            # 3. 微调
            finetuned_model_path, _ = finetune_model(
                pruned_model_path, 
                config, 
                experiment_name
            )
            
            # 4. 评估微调后
            LOGGER.info("Evaluating fine-tuned model...")
            finetuned_metrics = evaluate_model(finetuned_model_path, config)
            
            # 保存结果
            results[experiment_name] = {
                'prune_ratio': prune_ratio,
                'pruned_model': pruned_model_path,
                'finetuned_model': finetuned_model_path,
                'before_finetune': pruned_metrics,
                'after_finetune': finetuned_metrics,
            }
            
            LOGGER.info(f"\n✓ {experiment_name} completed!")
            LOGGER.info(f"  Params: {finetuned_metrics['params_M']:.2f}M")
            LOGGER.info(f"  mAP@0.5: {finetuned_metrics['mAP50']*100:.2f}%")
            
        except Exception as e:
            LOGGER.error(f"Experiment {experiment_name} failed: {e}")
            results[experiment_name] = {'error': str(e)}
    
    # 生成对比报告
    report = generate_comparison_report(results, config)
    
    # 保存结果
    results_path = output_dir / 'ablation_results.json'
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    LOGGER.info(f"\nResults saved to: {results_path}")
    
    # 保存报告
    report_path = output_dir / 'ablation_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    LOGGER.info(f"Report saved to: {report_path}")
    
    # 打印报告
    print(report)
    
    total_time = (time.time() - start_time) / 3600
    LOGGER.info(f"\n总耗时: {total_time:.2f} 小时")
    
    return results


def generate_comparison_report(results, config):
    """
    生成对比报告
    """
    report = []
    report.append("=" * 80)
    report.append("剪枝率消融实验报告 - Pruning Rate Ablation Study")
    report.append("=" * 80)
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"稀疏模型: {config['sparse_model']}")
    report.append(f"微调轮数: {config['finetune_epochs']}")
    report.append("")
    
    # 表格标题
    report.append("-" * 80)
    report.append(f"{'剪枝率':^10} | {'Params(M)':^12} | {'压缩率':^10} | {'mAP@0.5':^12} | {'mAP@0.5:0.95':^12} | {'精度变化':^10}")
    report.append("-" * 80)
    
    # 基线
    baseline = results.get('baseline', {})
    baseline_params = baseline.get('params_M', 0)
    baseline_map50 = baseline.get('mAP50', 0)
    baseline_map = baseline.get('mAP50-95', 0)
    
    report.append(f"{'0% (基线)':^10} | {baseline_params:^12.2f} | {'-':^10} | {baseline_map50*100:^12.2f}% | {baseline_map*100:^12.2f}% | {'-':^10}")
    
    # 各剪枝率结果
    best_ratio = None
    best_score = -1
    
    for prune_ratio in config['prune_ratios']:
        exp_name = f"prune_{int(prune_ratio*100)}"
        exp_result = results.get(exp_name, {})
        
        if 'error' in exp_result:
            report.append(f"{prune_ratio*100:^10.0f}% | {'ERROR':^12} | {'-':^10} | {'-':^12} | {'-':^12} | {'-':^10}")
            continue
        
        metrics = exp_result.get('after_finetune', {})
        params = metrics.get('params_M', 0)
        map50 = metrics.get('mAP50', 0)
        map_val = metrics.get('mAP50-95', 0)
        
        # 计算压缩率和精度变化
        compression = (1 - params / baseline_params) * 100 if baseline_params > 0 else 0
        map_change = (map50 - baseline_map50) * 100
        
        change_str = f"{map_change:+.2f}%" if map_change != 0 else "0%"
        
        report.append(f"{prune_ratio*100:^10.0f}% | {params:^12.2f} | {compression:^10.1f}% | {map50*100:^12.2f}% | {map_val*100:^12.2f}% | {change_str:^10}")
        
        # 找最优（平衡压缩和精度）
        # 评分 = mAP50 - 0.1 * 精度损失惩罚
        score = map50 - abs(map_change) * 0.01
        if score > best_score:
            best_score = score
            best_ratio = prune_ratio
    
    report.append("-" * 80)
    report.append("")
    
    # 推荐
    if best_ratio is not None:
        report.append(f"📌 推荐剪枝率: {best_ratio*100:.0f}%")
        best_exp = f"prune_{int(best_ratio*100)}"
        best_model = results.get(best_exp, {}).get('finetuned_model', 'N/A')
        report.append(f"📌 推荐模型路径: {best_model}")
        report.append("")
        report.append("下一步: 使用推荐的剪枝模型进行知识蒸馏增强")
        report.append(f"  python train_kd_after_prune.py")
        report.append(f"  (将 student 设置为: {best_model})")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)


# ============================================================================
# 主函数
# ============================================================================

if __name__ == '__main__':
    """
    ========================================================================
    剪枝率消融实验 - 使用说明
    ========================================================================
    
    【实验目的】
    测试不同剪枝率 (20%, 30%, 50%) 对模型性能的影响，
    找到精度和效率的最佳平衡点。
    
    【前置条件】
    需要先运行 train_sparse.py 完成稀疏训练
    
    【实验流程】
    对每个剪枝率执行：
    1. 结构化剪枝（使用 torch-pruning）
    2. 微调训练（恢复精度）
    3. 评估性能（mAP、参数量等）
    
    【输出】
    - ablation_results.json: 详细实验结果
    - ablation_report.txt: 对比报告表格
    - 各剪枝率的模型文件
    
    【推荐工作流】
    1. 运行本脚本进行消融实验
    2. 查看报告，选择最优剪枝率
    3. 用最优模型进行蒸馏增强
    
    ========================================================================
    """
    
    # 检查 torch-pruning
    try:
        import torch_pruning as tp
        LOGGER.info(f"✓ torch-pruning 已安装: {tp.__version__}")
    except ImportError:
        LOGGER.error("✗ torch-pruning 未安装！")
        LOGGER.error("请运行: pip install torch-pruning")
        sys.exit(1)
    
    # 运行消融实验
    results = run_ablation_experiment(CONFIG)
    
    if results:
        LOGGER.info("\n" + "=" * 60)
        LOGGER.info("✅ 消融实验完成！")
        LOGGER.info("请查看 runs/prune_ablation/ablation_report.txt 获取对比报告")
        LOGGER.info("=" * 60)
