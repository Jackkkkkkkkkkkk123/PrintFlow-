import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket消费者，处理实时通知
    """
    
    async def connect(self):
        """
        WebSocket连接时调用
        """
        # 获取用户信息
        user = self.scope["user"]
        
        print(f"📡 WebSocket连接请求，用户: {user} (类型: {type(user).__name__})")
        
        # 检查用户是否已登录
        if isinstance(user, AnonymousUser):
            print("❌ 用户未登录，拒绝WebSocket连接")
            await self.close()
            return
        
        print(f"✅ 用户 {user.username} 认证通过")
        
        # 加入通知组
        self.room_group_name = 'notifications'
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # 接受WebSocket连接
        await self.accept()
        
        print(f"🔌 WebSocket连接已建立，用户: {user.username}")
        
        # 发送连接成功消息
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'WebSocket连接已建立，欢迎 {user.username}',
            'user': user.username
        }))
    
    async def disconnect(self, close_code):
        """
        WebSocket断开连接时调用
        """
        # 离开通知组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        接收来自WebSocket的消息
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # 心跳检测
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'pong'
                }))
        except json.JSONDecodeError:
            # 处理JSON解析错误
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无效的JSON格式'
            }))
    
    async def order_notification(self, event):
        """
        处理订单通知
        """
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'order_notification',
            'data': event['data']
        }))
    
    async def progress_notification(self, event):
        """
        处理进度通知
        """
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'progress_notification',
            'data': event['data']
        }))
    
    async def dashboard_update(self, event):
        """
        处理仪表板更新通知
        """
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))
    
    async def general_notification(self, event):
        """
        处理一般通知
        """
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'general_notification',
            'data': event['data']
        }))
    
    async def notification_message(self, event):
        """
        处理通知消息
        """
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification_message',
            'data': event['data']
        }))


# 辅助函数，用于发送通知到所有连接的客户端
async def send_notification_to_group(group_name, notification_type, data):
    """
    发送通知到指定的WebSocket组
    """
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        group_name,
        {
            'type': notification_type,
            'data': data
        }
    ) 