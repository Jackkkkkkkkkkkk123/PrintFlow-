#!/usr/bin/env python
"""
WebSocket服务器启动脚本 - 修复Windows事件循环问题
"""

import os
import sys
import asyncio
import django

# 修复Windows事件循环问题 - 必须在导入任何其他模块之前设置
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yw_crm.settings')

try:
    django.setup()
    print("✅ Django设置完成")
except Exception as e:
    print(f"❌ Django设置失败: {e}")
    sys.exit(1)

if __name__ == "__main__":
    try:
        print("🚀 启动WebSocket服务器...")
        
        # 导入ASGI应用
        from yw_crm.asgi import application
        print("✅ ASGI应用加载成功")
        
        # 使用uvicorn启动（更稳定，支持Windows）
        import uvicorn
        
        print("📍 服务器地址: http://localhost:5173")
        print("🔌 WebSocket端点: ws://localhost:5173/ws/notifications/")
        print("⏹️  按 Ctrl+C 停止服务器")
        print("-" * 50)
        
        uvicorn.run(
            "yw_crm.asgi:application",
            host="0.0.0.0",
            port=5173,
            reload=False,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请安装uvicorn: pip install uvicorn")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc() 