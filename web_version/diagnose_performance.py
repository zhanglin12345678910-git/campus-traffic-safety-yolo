#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能诊断脚本 - 快速定位卡顿原因
"""

import os
import time
import cv2
import numpy as np
import psutil
import sys

def check_system_resources():
    """检查系统资源"""
    print("🖥️ 系统资源检查:")
    print("-" * 40)
    
    # CPU信息
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    print(f"CPU使用率: {cpu_percent}%")
    print(f"CPU核心数: {cpu_count}")
    
    # 内存信息
    memory = psutil.virtual_memory()
    print(f"内存使用率: {memory.percent}%")
    print(f"可用内存: {memory.available / 1024**3:.1f} GB")
    print(f"总内存: {memory.total / 1024**3:.1f} GB")
    
    # 判断资源是否充足
    if cpu_percent > 80:
        print("⚠️ CPU使用率过高，可能影响性能")
    if memory.percent > 85:
        print("⚠️ 内存使用率过高，可能影响性能")
    
    print()

def test_camera_performance():
    """测试摄像头性能"""
    print("📷 摄像头性能测试:")
    print("-" * 40)
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ 无法打开摄像头")
            return
        
        # 测试不同分辨率的性能
        resolutions = [
            (160, 120, "超低"),
            (320, 240, "低"),
            (640, 480, "中"),
            (1280, 720, "高")
        ]
        
        for width, height, desc in resolutions:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # 测试帧率
            frame_times = []
            for i in range(10):
                t0 = time.time()
                ret, frame = cap.read()
                if ret:
                    frame_times.append(time.time() - t0)
            
            if frame_times:
                avg_time = np.mean(frame_times) * 1000
                fps = 1000 / avg_time if avg_time > 0 else 0
                print(f"{desc}分辨率 ({width}x{height}): {avg_time:.1f}ms/帧, {fps:.1f} FPS")
            else:
                print(f"{desc}分辨率 ({width}x{height}): 读取失败")
        
        cap.release()
        
    except Exception as e:
        print(f"❌ 摄像头测试失败: {e}")
    
    print()

def test_model_performance():
    """测试模型推理性能"""
    print("🤖 模型推理性能测试:")
    print("-" * 40)
    
    try:
        # 尝试导入YOLO
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from ultralytics import YOLO
        
        model_path = r"../runs/train/yolo11-第一个实验-newt100k2/weights/best.pt"
        if not os.path.exists(model_path):
            print(f"❌ 模型文件不存在: {model_path}")
            return
        
        print("📂 加载模型...")
        model = YOLO(model_path)
        
        # 测试不同分辨率的推理性能
        test_sizes = [160, 320, 416, 640]
        
        for imgsz in test_sizes:
            # 创建测试图像
            test_img = np.random.randint(0, 255, (imgsz, imgsz, 3), dtype=np.uint8)
            
            # 预热
            model.predict(test_img, device="cpu", imgsz=imgsz, verbose=False)
            
            # 测试推理时间
            times = []
            for i in range(5):
                t0 = time.time()
                results = model.predict(test_img, device="cpu", imgsz=imgsz, conf=0.5, verbose=False)
                times.append((time.time() - t0) * 1000)
            
            avg_time = np.mean(times)
            print(f"分辨率 {imgsz}: {avg_time:.1f}ms/次")
        
    except ImportError:
        print("❌ 无法导入ultralytics，请检查安装")
    except Exception as e:
        print(f"❌ 模型测试失败: {e}")
    
    print()

def test_image_encoding():
    """测试图像编码性能"""
    print("🖼️ 图像编码性能测试:")
    print("-" * 40)
    
    try:
        # 创建测试图像
        test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # 测试不同质量的编码时间
        qualities = [30, 50, 70, 90]
        
        for quality in qualities:
            times = []
            sizes = []
            
            for i in range(5):
                t0 = time.time()
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
                _, buffer = cv2.imencode('.jpg', test_img, encode_params)
                times.append((time.time() - t0) * 1000)
                sizes.append(len(buffer))
            
            avg_time = np.mean(times)
            avg_size = np.mean(sizes) / 1024  # KB
            print(f"质量 {quality}: {avg_time:.1f}ms, {avg_size:.1f}KB")
        
    except Exception as e:
        print(f"❌ 图像编码测试失败: {e}")
    
    print()

def get_performance_recommendations():
    """获取性能优化建议"""
    print("💡 性能优化建议:")
    print("-" * 40)
    
    memory = psutil.virtual_memory()
    cpu_count = psutil.cpu_count()
    
    recommendations = []
    
    if memory.total < 4 * 1024**3:  # 小于4GB
        recommendations.append("• 内存不足4GB，建议使用超轻量级版本 (web_app_lite.py)")
    
    if cpu_count < 4:
        recommendations.append("• CPU核心数较少，建议降低检测分辨率到320或更低")
    
    recommendations.extend([
        "• 使用CPU推理而非GPU（避免显存不足）",
        "• 设置较高的置信度阈值（0.5以上）",
        "• 降低摄像头分辨率到320x240",
        "• 增加请求间隔到200ms以上",
        "• 使用较低的JPEG质量（50以下）"
    ])
    
    for rec in recommendations:
        print(rec)
    
    print()

def main():
    """主函数"""
    print("🔍 YOLO11 Web版本性能诊断")
    print("=" * 50)
    print()
    
    check_system_resources()
    test_camera_performance()
    test_model_performance()
    test_image_encoding()
    get_performance_recommendations()
    
    print("🎯 诊断完成！")
    print()
    print("📋 解决卡顿的步骤:")
    print("1. 关闭当前Web服务器 (Ctrl+C)")
    print("2. 运行超轻量级版本: python web_app_lite.py")
    print("3. 访问 http://localhost:5001")
    print("4. 如果还是卡，请降低系统其他程序的资源占用")

if __name__ == "__main__":
    main()
