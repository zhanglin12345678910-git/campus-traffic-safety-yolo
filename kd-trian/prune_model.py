"""
真正的结构化通道剪枝脚本 - 基于BN缩放因子的Network Slimming
=================================================
【重要】本脚本使用 torch-pruning 进行真正的结构化剪枝：
- 真正删除卷积核和通道（不是置零！）
- 减少模型参数量（Parameters）
- 减少计算量（GFLOPs / FLOPs）
- 自动处理层间依赖关系（Concat、残差连接等）

实现思路：
1. 加载稀疏训练后的模型
2. 收集所有BN层的γ参数，按绝对值全局排序
3. 根据剪枝率ρ确定剪枝阈值
4. 使用torch-pruning处理层间依赖关系
5. 执行物理剪枝，真正删除对应的通道和卷积核
6. 保存剪枝后的模型

安装依赖：
    pip install torch-pruning

Author: 林哥
Date: 2026-01-29
"""

import argparse
import os
import copy
from pathlib import Path
from collections import defaultdict

import torch
import torch.nn as nn
import numpy as np
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultralytics import YOLO
from ultralytics.utils import LOGGER
from ultralytics.nn.modules import Conv, C2f, SPPF, Concat, Detect
from ultralytics.nn.modules.block import Bottleneck


# ============================================================================
# 检查 torch-pruning 是否安装
# ============================================================================

try:
    import torch_pruning as tp
    TORCH_PRUNING_AVAILABLE = True
    LOGGER.info(f"✓ torch-pruning 已安装，版本: {tp.__version__}")
except ImportError:
    TORCH_PRUNING_AVAILABLE = False
    LOGGER.warning("✗ torch-pruning 未安装！真正的结构化剪枝需要此库")
    LOGGER.warning("  请运行: pip install torch-pruning")


# ============================================================================
# 工具函数：分析模型的BN层
# ============================================================================

def collect_bn_weights(model):
    """
    收集模型中所有BN层的gamma权重
    
    Returns:
        bn_weights: dict, {layer_name: gamma_tensor}
        all_gammas: list, 所有gamma值的列表（用于全局排序）
    """
    bn_weights = {}
    all_gammas = []
    
    for name, module in model.named_modules():
        if isinstance(module, (nn.BatchNorm2d, nn.BatchNorm1d)):
            if module.weight is not None:
                gamma = module.weight.data.abs().cpu().numpy()
                bn_weights[name] = {
                    'gamma': module.weight.data.clone(),
                    'module': module,
                    'num_channels': module.num_features,
                }
                all_gammas.extend(gamma.flatten().tolist())
    
    return bn_weights, np.array(all_gammas)


def compute_pruning_threshold(all_gammas, prune_ratio):
    """
    计算剪枝阈值
    
    Args:
        all_gammas: 所有BN层gamma值的数组
        prune_ratio: 剪枝率（0-1之间）
    
    Returns:
        threshold: 剪枝阈值
    """
    sorted_gammas = np.sort(all_gammas)
    threshold_idx = int(len(sorted_gammas) * prune_ratio)
    threshold = sorted_gammas[threshold_idx]
    return threshold


def analyze_model_sparsity(model, threshold=0.01):
    """
    分析模型的稀疏程度
    """
    bn_weights, all_gammas = collect_bn_weights(model)
    
    if len(all_gammas) == 0:
        LOGGER.warning("No BN layers found in model!")
        return {'total': 0, 'near_zero': 0, 'sparsity': 0}
    
    near_zero = np.sum(np.abs(all_gammas) < threshold)
    total = len(all_gammas)
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Model Sparsity Analysis (threshold={threshold})")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Total BN channels: {total}")
    LOGGER.info(f"Near-zero channels: {near_zero}")
    LOGGER.info(f"Sparsity ratio: {near_zero/total*100:.2f}%")
    LOGGER.info(f"|γ| range: [{np.min(all_gammas):.4f}, {np.max(all_gammas):.4f}]")
    LOGGER.info(f"|γ| mean: {np.mean(all_gammas):.4f}")
    LOGGER.info(f"|γ| std: {np.std(all_gammas):.4f}")
    LOGGER.info(f"{'='*60}\n")
    
    return {
        'total': total,
        'near_zero': near_zero,
        'sparsity': near_zero / total,
        'all_gammas': all_gammas,
    }


def get_model_complexity(model, input_size=(1, 3, 640, 640)):
    """
    计算模型的参数量和FLOPs
    """
    device = next(model.parameters()).device
    
    # 参数量
    params = sum(p.numel() for p in model.parameters())
    
    # FLOPs (使用torch-pruning的工具)
    flops = 0
    if TORCH_PRUNING_AVAILABLE:
        try:
            example_inputs = torch.randn(*input_size).to(device)
            flops_count, _ = tp.utils.count_ops_and_params(model, example_inputs)
            flops = flops_count
        except Exception as e:
            LOGGER.warning(f"FLOPs calculation failed: {e}")
    
    return params, flops


# ============================================================================
# 使用 torch-pruning 进行真正的结构化剪枝
# ============================================================================

def structural_prune_with_torch_pruning(model_path, prune_ratio=0.3, save_dir=None,
                                         example_input_size=(1, 3, 640, 640),
                                         iterative_steps=1, round_to=1,
                                         global_pruning=False):
    """
    使用 torch-pruning 库进行真正的结构化剪枝
    
    【重要】这会真正删除通道和卷积核，减少模型参数量和计算量！
    
    Args:
        model_path: 模型路径 (.pt 文件)
        prune_ratio: 剪枝率 (0-1)，例如0.3表示剪掉30%的通道
        save_dir: 保存目录
        example_input_size: 示例输入大小
        iterative_steps: 迭代剪枝步数（推荐1）
        round_to: 通道数取整到此倍数（对GPU推理友好）
    
    Returns:
        pruned_model_path: 剪枝后的模型路径
    """
    if not TORCH_PRUNING_AVAILABLE:
        raise ImportError(
            "\n" + "=" * 60 + "\n"
            "错误：torch-pruning 未安装！\n"
            "这是进行真正结构化剪枝的必需库。\n\n"
            "请运行以下命令安装：\n"
            "    pip install torch-pruning\n"
            "或指定版本：\n"
            "    pip install torch-pruning==1.3.0\n"
            "=" * 60
        )
    
    save_dir = Path(save_dir) if save_dir else Path('runs/pruned')
    save_dir.mkdir(parents=True, exist_ok=True)
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"🔧 Structural Pruning with torch-pruning")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Model: {model_path}")
    LOGGER.info(f"Prune Ratio: {prune_ratio} ({prune_ratio*100:.0f}% channels will be removed)")
    LOGGER.info(f"Round to: {round_to} (channels will be multiples of {round_to})")
    LOGGER.info(f"Global pruning: {global_pruning}")
    LOGGER.info(f"{'='*60}\n")
    
    # ========== 1. 加载模型 ==========
    LOGGER.info("[1/6] Loading model...")
    yolo = YOLO(model_path)
    model = yolo.model
    device = next(model.parameters()).device
    
    # 确保模型在eval模式
    model.eval()
    
    # ========== 2. 分析剪枝前的模型 ==========
    LOGGER.info("[2/6] Analyzing model before pruning...")
    analyze_model_sparsity(model)
    
    params_before, flops_before = get_model_complexity(model, example_input_size)
    LOGGER.info(f"Parameters BEFORE: {params_before:,} ({params_before/1e6:.2f}M)")
    LOGGER.info(f"FLOPs BEFORE: {flops_before:,} ({flops_before/1e9:.2f}G)")
    
    # ========== 3. 创建示例输入 ==========
    LOGGER.info("[3/6] Setting up pruner...")
    example_inputs = torch.randn(*example_input_size).to(device)
    
    # ========== 4. debug: 打印所有模块类型 ==========
    LOGGER.info("DEBUG: Inspecting all modules to find Detect Head...")
    all_types = set()
    for name, module in model.named_modules():
        all_types.add(module.__class__.__name__)
        # 如果名字里包含 head 或 detect，打印出来
        if 'head' in name.lower() or 'detect' in name.lower():
            LOGGER.info(f"Potential Head Module: {name} ({module.__class__.__name__})")
            
    LOGGER.info(f"All module types found: {all_types}")

    # ========== 5. 设置忽略的层（检测头的输出层不能剪枝）==========
    ignored_layers = []
    
    # 策略升级：通过类名字符串匹配强制忽略 Detect 头及其子模块
    for name, module in model.named_modules():
        module_type = module.__class__.__name__
        # 匹配各种可能的 Head (Detect_LSCD added!)
        if module_type in ['Detect', 'Segment', 'Pose', 'Classify', 'RTDETRDecoder', 'v10Detect', 'PMSFADetect', 'Detect_LSCD']:
            LOGGER.info(f"Found Head Module: {name} ({module_type}) -> Adding to ignored_layers")
            ignored_layers.append(module)
            for sub_name, sub_module in module.named_modules():
                if isinstance(sub_module, (nn.Conv2d, nn.BatchNorm2d, nn.Linear)):
                    ignored_layers.append(sub_module)
                    
        # 最后的兜底策略：最后一层直接忽略
        if name == 'model.26' or name == 'model.26.dfl': # 根据经验，26通常是head
             LOGGER.info(f"Force ignoring last layer: {name}")
             ignored_layers.append(module)
             for m in module.modules():
                 ignored_layers.append(m)

    # 去重
    ignored_layers = list(set(ignored_layers))
    LOGGER.info(f"Ignored layers (Detect Head Protection): {len(ignored_layers)}")
    
    # ========== 5. 创建剪枝器并执行剪枝 ==========
    LOGGER.info("[4/6] Creating pruner and executing pruning...")
    
    # 使用BN的gamma作为重要性指标（若不可用则回退到权重幅值）
    importance_name = "BNScaleImportance"
    try:
        importance = tp.importance.BNScaleImportance()
    except Exception: 
        importance_name = "MagnitudeImportance(p=1)"
        importance = tp.importance.MagnitudeImportance(p=1)
    LOGGER.info(f"Importance: {importance_name}")
    
    # 创建剪枝器
    pruner = tp.pruner.MetaPruner(
        model,
        example_inputs,
        importance=importance,
        iterative_steps=iterative_steps,
        pruning_ratio=prune_ratio,
        ignored_layers=ignored_layers,
        # 使用可配置的剪枝策略
        global_pruning=global_pruning,
        # 关闭通道对齐限制，避免全部被round掉
        round_to=round_to,
    )
    
    # 执行剪枝
    LOGGER.info(f"\n>>> Executing {iterative_steps} pruning step(s)...")
    params_current = None
    for i in range(iterative_steps):
        pruner.step()
        params_current = sum(p.numel() for p in model.parameters())
        LOGGER.info(f"    Step {i+1}/{iterative_steps}: Parameters = {params_current:,}")

    # 若无任何变化，尝试回退到全局幅值剪枝
    if params_current == params_before:
        LOGGER.warning("No parameters removed; retrying with global magnitude pruning...")
        importance = tp.importance.MagnitudeImportance(p=1)
        pruner = tp.pruner.MetaPruner(
            model,
            example_inputs,
            importance=importance,
            iterative_steps=iterative_steps,
            pruning_ratio=prune_ratio,
            ignored_layers=ignored_layers,
            global_pruning=True,
            round_to=round_to,
        )
        for i in range(iterative_steps):
            pruner.step()
            params_current = sum(p.numel() for p in model.parameters())
            LOGGER.info(f"    Retry Step {i+1}/{iterative_steps}: Parameters = {params_current:,}")
    
    # ========== 6. 分析剪枝后的模型 ==========
    LOGGER.info("\n[5/6] Analyzing model after pruning...")
    analyze_model_sparsity(model)
    
    params_after, flops_after = get_model_complexity(model, example_input_size)
    LOGGER.info(f"Parameters AFTER: {params_after:,} ({params_after/1e6:.2f}M)")
    LOGGER.info(f"FLOPs AFTER: {flops_after:,} ({flops_after/1e9:.2f}G)")
    
    # 计算压缩率
    params_reduction = (params_before - params_after) / params_before * 100
    flops_reduction = (flops_before - flops_after) / flops_before * 100 if flops_before > 0 else 0
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"📊 PRUNING RESULTS SUMMARY")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Parameters: {params_before/1e6:.2f}M → {params_after/1e6:.2f}M (↓{params_reduction:.1f}%)")
    LOGGER.info(f"FLOPs:      {flops_before/1e9:.2f}G → {flops_after/1e9:.2f}G (↓{flops_reduction:.1f}%)")
    LOGGER.info(f"{'='*60}")
    
    # ========== 7. 保存剪枝后的模型 ==========
    LOGGER.info("\n[6/6] Saving pruned model...")
    
    pruned_model_path = save_dir / 'pruned_model.pt'
    
    # 保存为YOLO格式的checkpoint
    ckpt = {
        'model': copy.deepcopy(model).half(),
        'ema': None,
        'updates': None,
        'optimizer': None,
        'train_args': getattr(yolo, 'overrides', {}),
        'date': __import__('datetime').datetime.now().isoformat(),
        'version': getattr(yolo, '__version__', ''),
        'pruning_info': {
            'prune_ratio': prune_ratio,
            'params_before': params_before,
            'params_after': params_after,
            'flops_before': flops_before,
            'flops_after': flops_after,
        }
    }
    torch.save(ckpt, pruned_model_path)
    LOGGER.info(f"✓ Pruned model saved to: {pruned_model_path}")
    
    # 保存剪枝信息到文本文件
    info_path = save_dir / 'pruning_info.txt'
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write(f"Pruning Information\n")
        f.write(f"{'='*40}\n")
        f.write(f"Original Model: {model_path}\n")
        f.write(f"Prune Ratio: {prune_ratio}\n")
        f.write(f"Parameters: {params_before:,} → {params_after:,} (↓{params_reduction:.1f}%)\n")
        f.write(f"FLOPs: {flops_before/1e9:.2f}G → {flops_after/1e9:.2f}G (↓{flops_reduction:.1f}%)\n")
    LOGGER.info(f"✓ Pruning info saved to: {info_path}")
    
    return str(pruned_model_path)


# ============================================================================
# 主函数：执行剪枝流程
# ============================================================================

def prune_model(model_path, prune_ratio=0.3, save_dir='runs/pruned', round_to=1, global_pruning=False):
    """
    模型剪枝主函数 - 默认使用真正的结构化剪枝
    
    【重要】这会真正删除通道和卷积核，减少模型参数量和计算量！
    
    Args:
        model_path: 稀疏训练后的模型路径 (.pt 文件)
        prune_ratio: 剪枝率 (0-1)，例如0.3表示剪掉30%通道
        save_dir: 保存目录
    
    Returns:
        pruned_model_path: 剪枝后模型的保存路径
    """
    # 检查 torch-pruning 是否安装
    if not TORCH_PRUNING_AVAILABLE:
        LOGGER.error("\n" + "=" * 60)
        LOGGER.error("错误：torch-pruning 未安装！")
        LOGGER.error("真正的结构化剪枝需要此库来处理层间依赖关系。")
        LOGGER.error("")
        LOGGER.error("请运行以下命令安装：")
        LOGGER.error("    pip install torch-pruning")
        LOGGER.error("=" * 60 + "\n")
        raise ImportError("请先安装 torch-pruning: pip install torch-pruning")
    
    return structural_prune_with_torch_pruning(
        model_path=model_path,
        prune_ratio=prune_ratio,
        save_dir=save_dir,
        round_to=round_to,
        global_pruning=global_pruning,
    )


# ============================================================================
# 配置区
# ============================================================================

CONFIG = {
    # 输入：稀疏训练后的模型（必须是 .pt 文件）
    'model': '<PROJECT_ROOT>\\runs\\sparse_train\\PSSM-YOLO-Lite-稀疏训练-Phase22\\weights\\best.pt',
    
    # 剪枝参数
    'prune_ratio': 0.3,        # 剪枝率 (推荐 0.2-0.5)
                               # 0.2 = 轻度剪枝
                               # 0.3 = 中度剪枝（推荐）
                               # 0.5 = 重度剪枝
    'round_to': 1,             # 通道数取整倍数（1表示不对齐）
    'global_pruning': False,   # 先用非全局剪枝，确保能剪掉通道
    
    # 输出目录
    'save_dir': 'runs/pruned/PSSM-YOLO-Lite-结构化剪枝',
}


if __name__ == '__main__':
    """
    ========================================================================
    真正的结构化通道剪枝 - 使用说明
    ========================================================================
    
    【重要】本脚本使用 torch-pruning 进行真正的结构化剪枝：
    ✓ 真正删除卷积核和通道（不是置零！）
    ✓ 减少模型参数量（Parameters）
    ✓ 减少计算量（GFLOPs）
    ✓ 自动处理层间依赖关系（Concat、残差连接等）
    
    【安装依赖】
        pip install torch-pruning
    
    【训练流程】
    1. 稀疏训练 (train_sparse.py)
    2. 结构化剪枝（本脚本）← 你在这里
    3. 微调训练 (finetune.py)
    4. 蒸馏增强 (train_kd_after_prune.py)
    
    【参数说明】
    - prune_ratio: 剪枝率
      * 0.2: 轻度剪枝，参数量减少~20%
      * 0.3: 中度剪枝，参数量减少~30%（推荐）
      * 0.5: 重度剪枝，参数量减少~50%，需要更多微调
    
    【输出】
    - pruned_model.pt: 剪枝后的模型（参数量和计算量真正减少！）
    - pruning_info.txt: 剪枝统计信息
    
    【验证剪枝效果】
    剪枝后可以使用以下代码验证参数量变化：
    
        from ultralytics import YOLO
        model = YOLO('runs/pruned/xxx/pruned_model.pt')
        print(model.info())  # 查看参数量和GFLOPs
    
    ========================================================================
    """
    
    # 检查 torch-pruning
    if not TORCH_PRUNING_AVAILABLE:
        print("\n" + "=" * 60)
        print("❌ 错误：torch-pruning 未安装！")
        print("")
        print("真正的结构化剪枝需要此库。请运行以下命令安装：")
        print("    pip install torch-pruning")
        print("=" * 60 + "\n")
        sys.exit(1)
    
    # 执行剪枝
    pruned_path = prune_model(
        model_path=CONFIG['model'],
        prune_ratio=CONFIG['prune_ratio'],
        save_dir=CONFIG['save_dir'],
        round_to=CONFIG['round_to'],
        global_pruning=CONFIG['global_pruning'],
    )
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"✅ Structural Pruning Completed!")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Pruned model: {pruned_path}")
    LOGGER.info(f"")
    LOGGER.info(f"Next step: python finetune.py")
    LOGGER.info(f"{'='*60}")
