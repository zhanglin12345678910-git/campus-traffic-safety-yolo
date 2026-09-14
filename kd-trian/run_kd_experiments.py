"""
知识蒸馏温度对比实验批量运行脚本
自动运行多组不同温度和权重的对比实验
"""

import subprocess
import argparse
from pathlib import Path


def run_experiment(student, teacher, data, temp, weight, name, **kwargs):
    """运行单个蒸馏实验"""
    cmd = [
        'python', 'train_kd.py',
        '--student', student,
        '--teacher', teacher,
        '--data', data,
        '--kd-temp', str(temp),
        '--kd-weight', str(weight),
        '--name', name,
    ]
    
    # 添加其他参数
    for key, value in kwargs.items():
        cmd.extend([f'--{key}', str(value)])
    
    print(f"\n{'='*80}")
    print(f"运行实验: {name}")
    print(f"温度 T={temp}, 权重={weight}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'='*80}\n")
    
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description='批量运行知识蒸馏对比实验')
    parser.add_argument('--student', type=str, required=True, help='学生模型配置 (.yaml)')
    parser.add_argument('--teacher', type=str, required=True, help='教师模型权重 (.pt)')
    parser.add_argument('--data', type=str, required=True, help='数据集配置 (.yaml)')
    parser.add_argument('--epochs', type=int, default=100, help='训练轮数')
    parser.add_argument('--batch', type=int, default=16, help='批次大小')
    parser.add_argument('--device', type=str, default='0', help='GPU设备')
    parser.add_argument('--mode', type=str, default='trainer', help='训练模式')
    parser.add_argument('--experiments', type=str, default='all', 
                       choices=['all', 'temp', 'weight', 'quick'],
                       help='实验类型: all (全部), temp (温度), weight (权重), quick (快速)')
    
    args = parser.parse_args()
    
    # 公共参数
    common_kwargs = {
        'epochs': args.epochs,
        'batch': args.batch,
        'device': args.device,
        'mode': args.mode,
        'project': 'runs/kd_experiments',
    }
    
    print("\n" + "="*80)
    print("知识蒸馏对比实验")
    print("="*80)
    print(f"学生模型: {args.student}")
    print(f"教师模型: {args.teacher}")
    print(f"数据集: {args.data}")
    print(f"实验类型: {args.experiments}")
    print("="*80 + "\n")
    
    experiments = []
    
    if args.experiments == 'quick':
        # 快速实验：只测试3个温度
        experiments = [
            (2.0, 1.0, 'quick_T2'),
            (4.0, 1.0, 'quick_T4_baseline'),
            (6.0, 1.0, 'quick_T6'),
        ]
        print("运行快速对比实验 (3组)")
        
    elif args.experiments == 'temp':
        # 温度对比实验
        experiments = [
            (2.0, 1.0, 'temp_T2'),
            (3.0, 1.0, 'temp_T3'),
            (4.0, 1.0, 'temp_T4_baseline'),
            (5.0, 1.0, 'temp_T5'),
            (6.0, 1.0, 'temp_T6'),
        ]
        print("运行温度对比实验 (5组)")
        
    elif args.experiments == 'weight':
        # 权重对比实验（固定温度=4）
        experiments = [
            (4.0, 0.3, 'weight_W0.3'),
            (4.0, 0.5, 'weight_W0.5'),
            (4.0, 1.0, 'weight_W1.0_baseline'),
            (4.0, 1.5, 'weight_W1.5'),
            (4.0, 2.0, 'weight_W2.0'),
        ]
        print("运行权重对比实验 (5组)")
        
    else:  # all
        # 全面对比实验
        experiments = [
            # 温度系列
            (2.0, 1.0, 'full_T2_W1'),
            (3.0, 1.0, 'full_T3_W1'),
            (4.0, 1.0, 'full_T4_W1_baseline'),
            (5.0, 1.0, 'full_T5_W1'),
            (6.0, 1.0, 'full_T6_W1'),
            # 权重系列
            (4.0, 0.5, 'full_T4_W0.5'),
            (4.0, 1.5, 'full_T4_W1.5'),
            # 组合
            (3.0, 0.5, 'full_T3_W0.5'),
            (5.0, 1.5, 'full_T5_W1.5'),
        ]
        print("运行完整对比实验 (9组)")
    
    print(f"\n总计 {len(experiments)} 组实验\n")
    
    # 运行所有实验
    for i, (temp, weight, name) in enumerate(experiments, 1):
        print(f"\n进度: {i}/{len(experiments)}")
        run_experiment(
            student=args.student,
            teacher=args.teacher,
            data=args.data,
            temp=temp,
            weight=weight,
            name=name,
            **common_kwargs
        )
    
    print("\n" + "="*80)
    print("所有实验完成!")
    print("="*80)
    print("\n结果保存在: runs/kd_experiments/")
    print("\n查看结果:")
    print("  - 每个实验的详细日志: runs/kd_experiments/*/")
    print("  - 训练曲线: runs/kd_experiments/*/results.png")
    print("  - 最优模型: runs/kd_experiments/*/weights/best.pt")
    print("\n建议: 对比各实验的 mAP50 和 mAP50-95 指标，选择最优配置")
    print("="*80 + "\n")


if __name__ == '__main__':
    """
    使用示例:
    
    # 快速实验 (推荐首次使用)
    python run_kd_experiments.py \
        --student yolo11-CSP-PMSFA-Lite.yaml \
        --teacher teacher.pt \
        --data dataset/data.yaml \
        --experiments quick \
        --epochs 50 \
        --batch 16
    
    # 温度对比实验
    python run_kd_experiments.py \
        --student yolo11-CSP-PMSFA-Lite.yaml \
        --teacher teacher.pt \
        --data dataset/data.yaml \
        --experiments temp \
        --epochs 100 \
        --batch 16
    
    # 权重对比实验
    python run_kd_experiments.py \
        --student yolo11-CSP-PMSFA-Lite.yaml \
        --teacher teacher.pt \
        --data dataset/data.yaml \
        --experiments weight \
        --epochs 100 \
        --batch 16
    
    # 完整对比实验 (耗时较长)
    python run_kd_experiments.py \
        --student yolo11-CSP-PMSFA-Lite.yaml \
        --teacher teacher.pt \
        --data dataset/data.yaml \
        --experiments all \
        --epochs 100 \
        --batch 16
    """
    main()
