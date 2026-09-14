#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 多模型系统测试脚本
测试模型配置、切换和API功能
"""

import requests
import json
from colorama import init, Fore, Style

init(autoreset=True)

BASE_URL = "http://localhost:5000"

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

def print_success(text):
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

def print_error(text):
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

def print_info(text):
    print(f"{Fore.YELLOW}ℹ️  {text}{Style.RESET_ALL}")

def test_health():
    """测试系统健康状态"""
    print_header("测试1: 系统健康检查")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        
        print_success(f"系统状态: {data.get('status')}")
        print_info(f"当前激活模型: {data.get('active_model_id')}")
        print_info(f"模型已加载: {data.get('active_model_loaded')}")
        print_info(f"可用模型数量: {len(data.get('available_models', []))}")
        print_info(f"数据库状态: {data.get('database_status')}")
        print_info(f"检测记录数: {data.get('detection_count')}")
        
        return True
    except Exception as e:
        print_error(f"健康检查失败: {e}")
        return False

def test_model_list():
    """测试获取模型列表"""
    print_header("测试2: 获取模型列表")
    try:
        response = requests.get(f"{BASE_URL}/api/models")
        data = response.json()
        
        if data.get('success'):
            print_success(f"成功获取 {len(data['models'])} 个模型")
            print_info(f"当前激活: {data['active_model_id']}")
            
            print(f"\n{Fore.CYAN}模型详情:{Style.RESET_ALL}")
            for i, model in enumerate(data['models'], 1):
                status = "✓ 当前使用" if model['is_active'] else ""
                loaded = "已加载" if model['is_loaded'] else "未加载"
                exists = "✓" if model['exists'] else "⚠️ 文件缺失"
                
                print(f"  {i:2d}. {model['model_id']:20s} - {exists} {loaded} {status}")
            
            return data['models']
        else:
            print_error("获取模型列表失败")
            return None
    except Exception as e:
        print_error(f"获取模型列表失败: {e}")
        return None

def test_model_switch(model_id):
    """测试模型切换"""
    print_header(f"测试3: 切换到模型 [{model_id}]")
    try:
        response = requests.post(
            f"{BASE_URL}/api/models/active",
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'model_id': model_id})
        )
        data = response.json()
        
        if data.get('success'):
            print_success(f"成功切换到: {data['active_model_id']}")
            return True
        else:
            print_error(f"切换失败: {data.get('error')}")
            return False
    except Exception as e:
        print_error(f"切换失败: {e}")
        return False

def test_get_active_model():
    """测试获取当前激活模型"""
    print_header("测试4: 获取当前激活模型")
    try:
        response = requests.get(f"{BASE_URL}/api/models/active")
        data = response.json()
        
        if data.get('success'):
            print_success(f"当前激活模型: {data['active_model_id']}")
            return data['active_model_id']
        else:
            print_error("获取激活模型失败")
            return None
    except Exception as e:
        print_error(f"获取激活模型失败: {e}")
        return None

def test_stats():
    """测试统计信息"""
    print_header("测试5: 获取统计信息")
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        data = response.json()
        
        if data.get('success'):
            stats = data['stats']
            print_success("统计信息获取成功")
            print_info(f"总检测数: {stats.get('total_detections')}")
            print_info(f"今日检测: {stats.get('today_detections')}")
            print_info(f"成功率: {stats.get('success_rate')}%")
            return True
        else:
            print_error("获取统计信息失败")
            return False
    except Exception as e:
        print_error(f"获取统计信息失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print(f"{Fore.MAGENTA}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           🧪 多模型检测系统 - 自动化测试                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(Style.RESET_ALL)
    
    print_info("请确保Web服务已启动 (python web_app.py)")
    print_info(f"测试地址: {BASE_URL}\n")
    
    # 测试1: 健康检查
    if not test_health():
        print_error("系统健康检查失败，请检查服务是否启动")
        return
    
    # 测试2: 获取模型列表
    models = test_model_list()
    if not models:
        print_error("获取模型列表失败")
        return
    
    # 测试3: 模型切换（切换到第2个模型）
    if len(models) > 1:
        test_model = models[1]['model_id']
        test_model_switch(test_model)
    
    # 测试4: 获取当前模型
    test_get_active_model()
    
    # 测试5: 切换回默认模型
    if len(models) > 0:
        default_model = models[0]['model_id']
        if default_model != 'PSSM-YOLO':
            # 找到PSSM-YOLO
            for m in models:
                if m['model_id'] == 'PSSM-YOLO':
                    test_model_switch('PSSM-YOLO')
                    break
    
    # 测试6: 统计信息
    test_stats()
    
    # 总结
    print_header("测试完成")
    print_success("所有测试已完成！")
    print_info("详细结果请查看上方输出")
    
    print(f"\n{Fore.MAGENTA}💡 提示:{Style.RESET_ALL}")
    print("  • 在Web界面中切换模型: http://localhost:5000")
    print("  • 查看API文档: 参考 web_app.py 中的路由定义")
    print("  • 模型配置: 编辑 web_app.py 第65-76行")

if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}测试已中断{Style.RESET_ALL}")
    except Exception as e:
        print_error(f"测试出错: {e}")
