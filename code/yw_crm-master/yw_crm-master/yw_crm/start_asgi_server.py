#!/usr/bin/env python
"""
ASGI服务器启动脚本
使用Daphne启动支持WebSocket的服务器
"""

import os
import sys
import asyncio
import django

# 修复Windows事件循环问题
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yw_crm.settings')
django.setup()

if __name__ == "__main__":
    try:
        from daphne.server import Server
        from yw_crm.asgi import application
        
        print("🚀 启动ASGI WebSocket服务器...")
        print("📍 服务器地址: http://localhost:5173")
        print("🔌 WebSocket端点: ws://localhost:5173/ws/notifications/")
        print("⏹️  按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        # 启动Daphne服务器
        server = Server(application)
        server.run(host='0.0.0.0', port=5173)
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc() 