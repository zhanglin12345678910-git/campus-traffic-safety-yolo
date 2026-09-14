import warnings
warnings.filterwarnings('ignore')
import os
import time
import numpy as np
import torch
from tqdm import tqdm
from ultralytics import YOLO
from ultralytics.utils.torch_utils import select_device

def get_weight_size(path):
    """获取模型文件大小（MB）"""
    stats = os.stat(path)
    return f'{stats.st_size / 1024 / 1024:.1f}'

def test_fps(weights_path, batch_size=1, img_size=(640, 640), device='', half=False, warmup=200, test_time=1000):
    """
    测试模型FPS
    
    Args:
        weights_path: 模型权重路径
        batch_size: 批次大小
        img_size: 图片尺寸 (height, width)
        device: 设备 ('0', 'cpu', '')
        half: 是否使用FP16
        warmup: 预热次数
        test_time: 测试次数
    """
    print(f"开始FPS测试...")
    print(f"模型: {weights_path}")
    print(f"批次大小: {batch_size}")
    print(f"图片尺寸: {img_size}")
    print(f"设备: {device if device else 'auto'}")
    print(f"FP16: {half}")
    print("-" * 50)
    
    # 选择设备
    device = select_device(device, batch=batch_size)
    print(f"使用设备: {device}")
    
    # 加载模型
    print("加载模型...")
    if weights_path.endswith('.pt'):
        model = YOLO(weights_path).model
        model.fuse()  # 融合模型
        print(f'已加载模型: {weights_path}')
        print(f'模型大小: {get_weight_size(weights_path)}MB')
    else:
        model = YOLO(weights_path).model
        model.fuse()
        print(f'已加载YAML模型: {weights_path}')
    
    model = model.to(device)
    
    # 准备输入数据
    example_inputs = torch.randn((batch_size, 3, *img_size)).to(device)
    
    if half:
        model = model.half()
        example_inputs = example_inputs.half()
        print("使用FP16模式")
    
    # 预热
    print(f"开始预热 ({warmup}次)...")
    with torch.no_grad():
        for i in tqdm(range(warmup), desc='预热中'):
            model(example_inputs)
    
    # 测试推理时间
    print(f"开始测试 ({test_time}次)...")
    time_arr = []
    
    with torch.no_grad():
        for i in tqdm(range(test_time), desc='测试中'):
            if device.type == 'cuda':
                torch.cuda.synchronize()
            start_time = time.time()
            
            model(example_inputs)
            
            if device.type == 'cuda':
                torch.cuda.synchronize()
            end_time = time.time()
            time_arr.append(end_time - start_time)
    
    # 计算统计结果
    std_time = np.std(time_arr)
    mean_time = np.mean(time_arr)
    infer_time_per_image = mean_time / batch_size
    fps = 1 / infer_time_per_image
    
    # 输出结果
    print("\n" + "=" * 60)
    print("FPS测试结果:")
    print("=" * 60)
    print(f"模型文件: {weights_path}")
    if weights_path.endswith('.pt'):
        print(f"模型大小: {get_weight_size(weights_path)}MB")
    print(f"批次大小: {batch_size}")
    print(f"图片尺寸: {img_size[0]}x{img_size[1]}")
    print(f"设备: {device}")
    print(f"FP16: {half}")
    print("-" * 60)
    print(f"平均推理时间: {mean_time:.5f}s")
    print(f"单张图片时间: {infer_time_per_image:.5f}s")
    print(f"时间标准差: ±{std_time:.5f}s")
    print(f"FPS: {fps:.1f}")
    print(f"吞吐量: {fps * batch_size:.1f} images/s")
    print("=" * 60)
    
    return {
        'model_path': weights_path,
        'batch_size': batch_size,
        'img_size': img_size,
        'device': str(device),
        'fp16': half,
        'mean_time': mean_time,
        'infer_time_per_image': infer_time_per_image,
        'std_time': std_time,
        'fps': fps,
        'throughput': fps * batch_size
    }

if __name__ == '__main__':
    # ===================== 配置参数 =====================
    # 修改这里的参数来测试不同的配置
    
    # 模型路径 - 修改为你的模型路径
    WEIGHTS_PATH = r"<LOCAL_PATH>"
    
    # 测试配置
    BATCH_SIZE = 64        # 批次大小
    IMG_SIZE = (640, 640)   # 图片尺寸 (高度, 宽度)
    DEVICE = '0'             # 设备 ('0'=GPU0, 'cpu'=CPU, ''=自动选择)
    USE_FP16 = False        # 是否使用FP16加速
    WARMUP = 200            # 预热次数
    TEST_TIME = 1000        # 测试次数
    
    # ===================== 开始测试 =====================
    
    # 检查模型文件是否存在
    if not os.path.exists(WEIGHTS_PATH):
        print(f"错误: 模型文件不存在: {WEIGHTS_PATH}")
        print("请修改 WEIGHTS_PATH 为正确的模型路径")
        exit(1)
    
    # 运行FPS测试
    try:
        results = test_fps(
            weights_path=WEIGHTS_PATH,
            batch_size=BATCH_SIZE,
            img_size=IMG_SIZE,
            device=DEVICE,
            half=USE_FP16,
            warmup=WARMUP,
            test_time=TEST_TIME
        )
        
        # 保存结果到文件
        import json
        with open('normal_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n结果已保存到: normal_results.json")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        print("请检查模型路径和设备配置") 