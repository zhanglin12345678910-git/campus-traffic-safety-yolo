#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复数据库时间 - 将UTC时间转换为本地时间
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from web_app import app, db, Detection
    
    print("=" * 60)
    print("🔧 时间修复工具")
    print("=" * 60)
    
    with app.app_context():
        # 获取所有记录
        total_count = Detection.query.count()
        print(f"📊 数据库中总记录数: {total_count}")
        
        if total_count == 0:
            print("✅ 数据库为空，无需修复")
            sys.exit(0)
        
        print("\n⚠️  此操作将修改数据库中的时间记录")
        print("   UTC时间 → 本地时间（+8小时）")
        print()
        
        # 显示一些示例
        print("修复前的示例记录:")
        sample_records = Detection.query.order_by(Detection.created_at.desc()).limit(3).all()
        for r in sample_records:
            print(f"  ID:{r.id:4d} | {r.created_at} | {r.original_filename}")
        
        print()
        choice = input("是否继续修复？(y/n): ").strip().lower()
        
        if choice != 'y':
            print("❌ 已取消")
            sys.exit(0)
        
        print("\n🔄 开始修复...")
        
        # 获取时区偏移（假设为东八区 +8小时）
        # 如果需要其他时区，请修改这里
        timezone_offset = timedelta(hours=8)
        
        fixed_count = 0
        for record in Detection.query.all():
            # 将UTC时间转换为本地时间
            if record.created_at:
                # 检查是否已经是本地时间（启发式检测）
                now_local = datetime.now()
                if abs((now_local - record.created_at).total_seconds()) > 7 * 3600:
                    # 时间差大于7小时，可能是UTC时间
                    record.created_at = record.created_at + timezone_offset
                    fixed_count += 1
        
        # 提交更改
        try:
            db.session.commit()
            print(f"✅ 成功修复 {fixed_count} 条记录")
        except Exception as e:
            db.session.rollback()
            print(f"❌ 修复失败: {e}")
            sys.exit(1)
        
        print("\n修复后的示例记录:")
        sample_records = Detection.query.order_by(Detection.created_at.desc()).limit(3).all()
        for r in sample_records:
            print(f"  ID:{r.id:4d} | {r.created_at} | {r.original_filename}")
        
        print()
        print("=" * 60)
        print("✅ 时间修复完成")
        print("=" * 60)
        print()
        print("💡 提示:")
        print("   1. 新的检测记录将自动使用本地时间")
        print("   2. 请重启Web服务以应用更改")
        print("   3. 刷新浏览器页面查看效果")

except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在 web_version 目录下运行此脚本")
except Exception as e:
    print(f"❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()
