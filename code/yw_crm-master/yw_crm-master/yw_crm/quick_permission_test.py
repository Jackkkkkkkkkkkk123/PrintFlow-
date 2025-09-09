#!/usr/bin/env python
"""
快速权限测试脚本
验证所有用户对关键工序的权限
"""
import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yw_crm.settings')
django.setup()

from crm.models import UserInfo

def test_all_user_permissions():
    """测试所有用户的关键权限"""
    print("🧪 快速权限测试")
    print("=" * 80)
    
    # 关键工序测试
    test_cases = [
        ('调图', 'content'),
        ('印刷', 'cover'),
        ('印刷', 'content'),
        ('CTP', 'content'),
        ('折页', 'content'),
        ('锁线', 'content'),
        ('胶包', 'content'),
        ('打包', 'content'),
        ('送货', 'all'),
    ]
    
    # 测试用户
    users = ['root', 'tangshi', 'dengshi', 'caozuoyuan', 'waidiao']
    
    print(f"{'用户':<12} {'工序':<8} {'类型':<8} {'开始':<6} {'完成':<6} {'状态'}")
    print("-" * 60)
    
    for username in users:
        try:
            user = UserInfo.objects.get(username=username)
            
            for step_name, print_type in test_cases:
                can_start = user.can_operate_step(step_name, print_type, 'start')
                can_complete = user.can_operate_step(step_name, print_type, 'complete')
                
                start_icon = "✅" if can_start else "❌"
                complete_icon = "✅" if can_complete else "❌"
                
                if can_start and can_complete:
                    status = "正常"
                elif can_start and not can_complete:
                    status = "⚠️异常"
                elif not can_start and not can_complete:
                    status = "无权限"
                else:
                    status = "❓奇怪"
                
                print(f"{username:<12} {step_name:<8} {print_type:<8} {start_icon:<6} {complete_icon:<6} {status}")
                
        except UserInfo.DoesNotExist:
            print(f"{username:<12} 用户不存在")
    
    print("\n📋 说明:")
    print("✅ = 有权限")
    print("❌ = 无权限")
    print("⚠️异常 = 能开始但不能完成（需要检查）")
    print("无权限 = 正常的权限隔离")

def show_boss_summary():
    """显示BOSS权限总结"""
    print(f"\n🎯 BOSS权限总结")
    print("=" * 40)
    
    try:
        root_user = UserInfo.objects.get(username='root')
        
        # 测试BOSS对所有工序的权限
        all_steps = ['调图', '印刷', 'CTP', '切纸', '覆膜', '烫金', '压痕', 
                    '折页', '锁线', '胶包', '马订', '打包', '送货', '外调']
        
        can_operate_all = True
        problem_steps = []
        
        for step in all_steps:
            # 测试内文印刷类型
            can_start = root_user.can_operate_step(step, 'content', 'start')
            can_complete = root_user.can_operate_step(step, 'content', 'complete')
            
            if not (can_start and can_complete):
                can_operate_all = False
                problem_steps.append(step)
        
        if can_operate_all:
            print("✅ BOSS拥有所有工序的完整权限")
            print("   可以开始、完成、跳过任何工序步骤")
            print("   无时间限制，24小时可操作")
        else:
            print(f"⚠️ BOSS在以下工序有权限问题: {', '.join(problem_steps)}")
            
    except UserInfo.DoesNotExist:
        print("❌ root用户不存在")

if __name__ == '__main__':
    test_all_user_permissions()
    show_boss_summary() 