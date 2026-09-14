#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚦 智能交通标志检测系统 - Web版本演示脚本
展示API使用方法和功能测试
"""

import requests
import json
import base64
import time
from pathlib import Path

class WebAPIDemo:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def test_health(self):
        """测试健康检查API"""
        print("🔍 测试健康检查...")
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            data = response.json()
            
            if data['status'] == 'ok':
                print("✅ 服务器运行正常")
                print(f"   模型状态: {'已加载' if data['model_loaded'] else '未加载'}")
                return True
            else:
                print("❌ 服务器状态异常")
                return False
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    def test_image_detection(self, image_path):
        """测试图片检测API"""
        print(f"📸 测试图片检测: {image_path}")
        
        if not Path(image_path).exists():
            print(f"❌ 图片文件不存在: {image_path}")
            return None
        
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/api/detect/image",
                    files=files
                )
                end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    print("✅ 检测成功!")
                    print(f"   上传+检测总用时: {(end_time - start_time)*1000:.1f} ms")
                    print(f"   AI检测用时: {data['detection_time']} ms")
                    print(f"   检测到目标数: {data['results']['object_count']}")
                    print(f"   主要类别: {data['results']['main_class']}")
                    print(f"   置信度: {data['results']['confidence']:.3f}")
                    
                    if data['results']['bbox']:
                        bbox = data['results']['bbox']
                        print(f"   边界框: ({bbox['x1']}, {bbox['y1']}) -> ({bbox['x2']}, {bbox['y2']})")
                    
                    return data
                else:
                    print(f"❌ 检测失败: {data.get('error', '未知错误')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"   响应: {response.text}")
        
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        return None
    
    def test_video_detection(self, video_path):
        """测试视频检测API"""
        print(f"🎬 测试视频检测: {video_path}")
        
        if not Path(video_path).exists():
            print(f"❌ 视频文件不存在: {video_path}")
            return None
        
        try:
            with open(video_path, 'rb') as f:
                files = {'file': f}
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/api/detect/video",
                    files=files
                )
                end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    print("✅ 视频检测成功!")
                    print(f"   上传+检测总用时: {(end_time - start_time):.1f} s")
                    print(f"   视频时长: {data['video_info']['duration']:.1f} s")
                    print(f"   视频帧率: {data['video_info']['fps']:.1f} fps")
                    print(f"   总检测用时: {data['detection_summary']['total_detection_time']:.1f} ms")
                    print(f"   有目标的帧数: {data['detection_summary']['frames_with_objects']}")
                    print(f"   处理的总帧数: {data['detection_summary']['total_frames_processed']}")
                    
                    if data['results']:
                        print(f"   首个检测结果: {data['results'][0]['main_class']} ({data['results'][0]['confidence']:.3f})")
                    
                    return data
                else:
                    print(f"❌ 视频检测失败: {data.get('error', '未知错误')}")
            else:
                print(f"❌ HTTP错误: {response.status_code}")
                print(f"   响应: {response.text}")
        
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        return None
    
    def test_camera_detection(self):
        """测试摄像头检测API"""
        print("📹 测试摄像头检测...")
        
        try:
            # 启动摄像头
            response = self.session.post(f"{self.base_url}/api/camera/start")
            data = response.json()
            
            if data['success']:
                print("✅ 摄像头启动成功")
                
                # 获取几帧画面
                for i in range(3):
                    time.sleep(1)  # 等待1秒
                    frame_response = self.session.get(f"{self.base_url}/api/camera/frame")
                    frame_data = frame_response.json()
                    
                    if frame_data['success']:
                        print(f"   帧 {i+1}: {frame_data['results']['object_count']} 个目标, "
                              f"主类别: {frame_data['results']['main_class']}, "
                              f"用时: {frame_data['detection_time']} ms")
                    else:
                        print(f"   帧 {i+1}: 获取失败 - {frame_data.get('error', '未知错误')}")
                
                # 停止摄像头
                stop_response = self.session.post(f"{self.base_url}/api/camera/stop")
                stop_data = stop_response.json()
                
                if stop_data['success']:
                    print("✅ 摄像头停止成功")
                    return True
                else:
                    print(f"❌ 摄像头停止失败: {stop_data.get('error', '未知错误')}")
            else:
                print(f"❌ 摄像头启动失败: {data.get('error', '未知错误')}")
        
        except Exception as e:
            print(f"❌ 摄像头测试失败: {e}")
        
        return False
    
    def test_history(self):
        """测试历史记录API"""
        print("📚 测试历史记录...")
        try:
            response = self.session.get(f"{self.base_url}/api/history?page=1&per_page=5")
            data = response.json()
            
            if data['success']:
                records = data['data']
                pagination = data['pagination']
                
                print(f"✅ 获取历史记录成功")
                print(f"   总记录数: {pagination['total']}")
                print(f"   当前页: {pagination['page']}/{pagination['pages']}")
                print(f"   本页记录数: {len(records)}")
                
                for i, record in enumerate(records[:3], 1):  # 只显示前3条
                    print(f"   [{i}] {record['original_filename']} - {record['main_class']} ({record['confidence']:.3f})")
                
                return data
            else:
                print(f"❌ 获取历史记录失败: {data.get('error', '未知错误')}")
        
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        return None
    
    def test_stats(self):
        """测试统计信息API"""
        print("📊 测试统计信息...")
        try:
            response = self.session.get(f"{self.base_url}/api/stats")
            data = response.json()
            
            if data['success']:
                stats = data['stats']
                print("✅ 获取统计信息成功")
                print(f"   总检测次数: {stats['total_detections']}")
                print(f"   用户数量: {stats['total_users']}")
                print(f"   近7天检测: {stats['recent_detections']}")
                
                if stats['top_classes']:
                    print("   热门类别:")
                    for i, item in enumerate(stats['top_classes'][:3], 1):
                        print(f"     {i}. {item['class']} ({item['count']}次)")
                
                return data
            else:
                print(f"❌ 获取统计信息失败: {data.get('error', '未知错误')}")
        
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        return None
    
    def save_result_image(self, detection_data, output_path="demo_result.jpg"):
        """保存检测结果图片"""
        if detection_data and 'result_image' in detection_data:
            try:
                image_data = base64.b64decode(detection_data['result_image'])
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                print(f"💾 结果图片已保存: {output_path}")
                return True
            except Exception as e:
                print(f"❌ 保存图片失败: {e}")
        return False
    
    def run_full_demo(self, test_image_path=None):
        """运行完整演示"""
        print("🚦 智能交通标志检测系统 - Web API 演示")
        print("=" * 60)
        
        # 1. 健康检查
        if not self.test_health():
            print("❌ 服务器未运行，请先启动Web应用")
            return
        
        print()
        
        # 2. 图片检测
        if test_image_path:
            detection_result = self.test_image_detection(test_image_path)
            if detection_result:
                self.save_result_image(detection_result)
        else:
            print("⚠️ 未提供测试图片，跳过图片检测测试")
        
        print()
        
        # 2.5 摄像头检测测试
        print("📹 测试摄像头检测功能...")
        self.test_camera_detection()
        
        print()
        
        # 3. 历史记录
        self.test_history()
        
        print()
        
        # 4. 统计信息
        self.test_stats()
        
        print()
        print("🎉 演示完成!")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web API 演示脚本")
    parser.add_argument("--url", default="http://localhost:5000", help="Web应用URL")
    parser.add_argument("--image", help="测试图片路径")
    parser.add_argument("--test", choices=['health', 'detect', 'history', 'stats', 'all'], 
                       default='all', help="测试类型")
    
    args = parser.parse_args()
    
    demo = WebAPIDemo(args.url)
    
    if args.test == 'all':
        demo.run_full_demo(args.image)
    elif args.test == 'health':
        demo.test_health()
    elif args.test == 'detect':
        if args.image:
            demo.test_image_detection(args.image)
        else:
            print("❌ 检测测试需要提供图片路径 --image")
    elif args.test == 'history':
        demo.test_history()
    elif args.test == 'stats':
        demo.test_stats()

if __name__ == "__main__":
    main()

# 使用示例:
# python demo_web.py --image test.jpg
# python demo_web.py --test health
# python demo_web.py --url http://192.168.1.100:5000 --image test.jpg
