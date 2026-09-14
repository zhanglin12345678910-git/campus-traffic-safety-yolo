#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统测试脚本 - 检查Web版本的各项功能
"""

import os
import sys
import cv2
import requests
import time
from pathlib import Path

def test_model_path():
    """测试模型路径是否存在"""
    print("🔍 检查模型路径...")
    
    # 相对于web_version目录的模型路径
    model_path = Path("../runs/train/yolo11-第一个实验-newt100k2/weights/best.pt")
    
    if model_path.exists():
        print(f"✅ 模型文件存在: {model_path.absolute()}")
        return True
    else:
        print(f"❌ 模型文件不存在: {model_path.absolute()}")
        
        # 查找其他可用的模型
        print("🔍 查找其他可用模型...")
        runs_dir = Path("../runs/train")
        if runs_dir.exists():
            for exp_dir in runs_dir.iterdir():
                if exp_dir.is_dir():
                    weights_dir = exp_dir / "weights"
                    if weights_dir.exists():
                        best_pt = weights_dir / "best.pt"
                        if best_pt.exists():
                            print(f"📁 找到模型: {best_pt}")
        return False

def test_camera():
    """测试摄像头是否可用"""
    print("📷 检查摄像头...")
    
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            print("✅ 摄像头可用")
            return True
        else:
            print("❌ 摄像头无法读取画面")
            return False
    else:
        print("❌ 无法打开摄像头")
        return False

def test_dependencies():
    """测试依赖包是否安装"""
    print("📦 检查依赖包...")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy', 
        'flask_cors',
        'cv2',
        'PIL',
        'numpy',
        'ultralytics'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'PIL':
                from PIL import Image
            elif package == 'flask_sqlalchemy':
                from flask_sqlalchemy import SQLAlchemy
            elif package == 'flask_cors':
                from flask_cors import CORS
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 缺少依赖包: {', '.join(missing_packages)}")
        print("💡 请运行: pip install -r requirements_web.txt")
        return False
    else:
        print("✅ 所有依赖包已安装")
        return True

def test_web_server():
    """测试Web服务器是否启动"""
    print("🌐 检查Web服务器...")
    
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Web服务器运行正常")
            print(f"   模型加载状态: {'✅' if data.get('model_loaded') else '❌'}")
            return True
        else:
            print(f"❌ Web服务器响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Web服务器 (http://localhost:5000)")
        print("💡 请先启动Web服务器: python web_app.py")
        return False
    except Exception as e:
        print(f"❌ Web服务器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始系统测试...\n")
    
    tests = [
        ("模型路径", test_model_path),
        ("摄像头", test_camera),
        ("依赖包", test_dependencies),
        ("Web服务器", test_web_server)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        result = test_func()
        results.append((test_name, result))
        print(f"{'='*50}")
    
    # 总结
    print(f"\n🎯 测试总结:")
    print("-" * 30)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:10} : {status}")
        if not result:
            all_passed = False
    
    print("-" * 30)
    
    if all_passed:
        print("🎉 所有测试通过！系统可以正常使用")
        print("🌐 访问地址: http://localhost:5000")
    else:
        print("⚠️ 部分测试失败，请根据上述提示修复问题")
    
    print("\n💡 使用提示:")
    print("1. 确保模型文件路径正确")
    print("2. 检查摄像头连接")
    print("3. 安装所需依赖包")
    print("4. 启动Web服务器后再进行功能测试")

if __name__ == "__main__":
    main()
