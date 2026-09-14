#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库检查工具 - 诊断历史记录问题
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from web_app import app, db, Detection
    
    print("=" * 60)
    print("🔍 数据库诊断工具")
    print("=" * 60)
    
    with app.app_context():
        # 1. 检查数据库文件
        db_path = 'traffic_detection.db'
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"✅ 数据库文件存在: {db_path}")
            print(f"   大小: {size:,} 字节 ({size/1024:.2f} KB)")
        else:
            print(f"❌ 数据库文件不存在: {db_path}")
            print("   正在创建数据库...")
            db.create_all()
            print("✅ 数据库已创建")
        
        print()
        
        # 2. 检查记录总数
        try:
            total_count = Detection.query.count()
            print(f"📊 总记录数: {total_count}")
        except Exception as e:
            print(f"❌ 查询记录数失败: {e}")
            total_count = 0
        
        print()
        
        # 3. 检查最近的记录
        if total_count > 0:
            print("📋 最近10条记录:")
            print("-" * 60)
            try:
                records = Detection.query.order_by(Detection.created_at.desc()).limit(10).all()
                for i, r in enumerate(records, 1):
                    created = r.created_at.strftime('%Y-%m-%d %H:%M:%S') if r.created_at else 'N/A'
                    print(f"{i:2d}. ID:{r.id:4d} | {r.original_filename:30s} | {r.file_type:8s}")
                    print(f"     对象数:{r.object_count:2d} | 类别:{r.main_class or 'N/A':15s} | 时间:{created}")
                    print()
            except Exception as e:
                print(f"❌ 查询记录失败: {e}")
        else:
            print("📭 数据库中没有记录")
        
        print()
        
        # 4. 检查不同文件类型的记录数
        print("📊 按类型统计:")
        print("-" * 60)
        try:
            for file_type in ['image', 'video', 'camera']:
                count = Detection.query.filter_by(file_type=file_type).count()
                print(f"  {file_type:10s}: {count:4d} 条")
        except Exception as e:
            print(f"❌ 统计失败: {e}")
        
        print()
        
        # 5. 检查今天的记录
        print("📅 今日记录:")
        print("-" * 60)
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = Detection.query.filter(Detection.created_at >= today_start).count()
            print(f"  今日检测数: {today_count}")
        except Exception as e:
            print(f"❌ 查询今日记录失败: {e}")
        
        print()
        
        # 6. 测试分页查询
        print("📄 测试分页查询:")
        print("-" * 60)
        try:
            pagination = Detection.query.order_by(Detection.created_at.desc()).paginate(
                page=1, per_page=10, error_out=False
            )
            print(f"  第1页记录数: {len(pagination.items)}")
            print(f"  总页数: {pagination.pages}")
            print(f"  总记录数: {pagination.total}")
            
            if len(pagination.items) > 0:
                print("\n  ✅ 分页查询正常")
                print(f"  第一条记录: {pagination.items[0].original_filename}")
            else:
                print("\n  ⚠️ 分页查询返回空结果")
        except Exception as e:
            print(f"  ❌ 分页查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        print("=" * 60)
        print("✅ 诊断完成")
        print("=" * 60)
        
        # 7. 如果没有记录，创建一条测试记录
        if total_count == 0:
            print("\n💡 数据库为空，是否创建测试记录？(y/n): ", end="")
            choice = input().strip().lower()
            if choice == 'y':
                test_record = Detection(
                    session_id='test-001',
                    original_filename='test_image.jpg',
                    file_path='/test/path/test_image.jpg',
                    result_path=None,
                    file_type='image',
                    file_size=1024,
                    detection_time=25.5,
                    object_count=3,
                    main_class='traffic_sign',
                    confidence=0.85,
                    bbox_x1=100,
                    bbox_y1=100,
                    bbox_x2=200,
                    bbox_y2=200
                )
                db.session.add(test_record)
                db.session.commit()
                print("✅ 测试记录已创建")
                print(f"   记录ID: {test_record.id}")

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在 web_version 目录下运行此脚本")
except Exception as e:
    print(f"❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()
