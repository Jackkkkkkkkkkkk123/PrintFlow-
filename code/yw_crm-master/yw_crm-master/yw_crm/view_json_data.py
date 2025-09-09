#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
查看PrintOrderFlat表的四个JSON字段内容的独立脚本
运行方法: python view_json_data.py
"""

import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yw_crm.settings')
django.setup()

import json
from crm.models import PrintOrderFlat

def view_json_fields():
    """查看所有PrintOrderFlat记录的四个JSON字段"""
    try:
        # 获取所有主信息记录（detail_type=None）
        orders = PrintOrderFlat.objects.filter(detail_type=None).order_by('-id')
        
        if not orders.exists():
            print("数据库中没有找到任何订单记录")
            return
            
        print(f"找到 {orders.count()} 个订单记录\n")
        print("=" * 80)
        
        for i, order in enumerate(orders, 1):
            print(f"\n第 {i} 个订单:")
            print(f"订单号: {order.order_no}")
            print(f"ID: {order.id}")
            print(f"客户名称: {order.customer_name or '未填写'}")
            print(f"印品名称: {order.product_name or '未填写'}")
            print(f"拼晒要求: {order.imposition_requirement or '未填写'}")
            print("-" * 40)
            
            # 1. 用料明细JSON
            print("1. 用料明细JSON (material_json):")
            try:
                if order.material_json:
                    material_data = json.loads(order.material_json)
                    if material_data:
                        print(json.dumps(material_data, ensure_ascii=False, indent=2))
                    else:
                        print("  空数组 []")
                else:
                    print("  无数据")
            except Exception as e:
                print(f"  解析错误: {e}")
                print(f"  原始数据: {order.material_json}")
            
            # 2. 印前明细JSON
            print("\n2. 印前明细JSON (prepress_json):")
            try:
                if order.prepress_json:
                    prepress_data = json.loads(order.prepress_json)
                    if prepress_data:
                        print(json.dumps(prepress_data, ensure_ascii=False, indent=2))
                    else:
                        print("  空数组 []")
                else:
                    print("  无数据")
            except Exception as e:
                print(f"  解析错误: {e}")
                print(f"  原始数据: {order.prepress_json}")
            
            # 3. 印刷明细JSON
            print("\n3. 印刷明细JSON (process_json):")
            try:
                if order.process_json:
                    process_data = json.loads(order.process_json)
                    if process_data:
                        print(json.dumps(process_data, ensure_ascii=False, indent=2))
                    else:
                        print("  空数组 []")
                else:
                    print("  无数据")
            except Exception as e:
                print(f"  解析错误: {e}")
                print(f"  原始数据: {order.process_json}")
            
            # 4. 印后明细JSON
            print("\n4. 印后明细JSON (postpress_json):")
            try:
                if order.postpress_json:
                    postpress_data = json.loads(order.postpress_json)
                    if postpress_data:
                        print(json.dumps(postpress_data, ensure_ascii=False, indent=2))
                    else:
                        print("  空数组 []")
                else:
                    print("  无数据")
            except Exception as e:
                print(f"  解析错误: {e}")
                print(f"  原始数据: {order.postpress_json}")
            
            print("\n" + "=" * 80)
            
            # 如果记录太多，只显示前5个
            if i >= 5:
                remaining = orders.count() - 5
                if remaining > 0:
                    print(f"\n还有 {remaining} 个订单记录未显示...")
                break
                
    except Exception as e:
        print(f"查看失败: {e}")
        import traceback
        traceback.print_exc()

def view_specific_order(order_id):
    """查看指定订单的JSON字段"""
    try:
        order = PrintOrderFlat.objects.filter(id=order_id, detail_type=None).first()
        if not order:
            print(f"未找到ID为 {order_id} 的订单")
            return
            
        print(f"订单详情 (ID: {order_id})")
        print("=" * 50)
        print(f"订单号: {order.order_no}")
        print(f"客户名称: {order.customer_name or '未填写'}")
        print(f"印品名称: {order.product_name or '未填写'}")
        print(f"拼晒要求: {order.imposition_requirement or '未填写'}")
        print("-" * 30)
        
        json_fields = [
            ('用料明细JSON', order.material_json),
            ('印前明细JSON', order.prepress_json),
            ('印刷明细JSON', order.process_json),
            ('印后明细JSON', order.postpress_json)
        ]
        
        for i, (name, json_data) in enumerate(json_fields, 1):
            print(f"\n{i}. {name}:")
            try:
                if json_data:
                    data = json.loads(json_data)
                    if data:
                        print(json.dumps(data, ensure_ascii=False, indent=2))
                    else:
                        print("  空数组 []")
                else:
                    print("  无数据")
            except Exception as e:
                print(f"  解析错误: {e}")
                print(f"  原始数据: {json_data}")
                
    except Exception as e:
        print(f"查看失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 查看指定订单
        try:
            order_id = int(sys.argv[1])
            view_specific_order(order_id)
        except ValueError:
            print("请提供有效的订单ID数字")
    else:
        # 查看所有订单
        view_json_fields() 