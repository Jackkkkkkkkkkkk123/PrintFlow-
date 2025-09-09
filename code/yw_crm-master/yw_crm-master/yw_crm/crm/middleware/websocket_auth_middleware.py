"""
WebSocket认证中间件
"""

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.utils import timezone
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from crm.models import UserInfo


@database_sync_to_async
def get_user_from_session(session_key):
    """从session获取用户信息"""
    try:
        session = Session.objects.get(session_key=session_key)
        if session.expire_date < timezone.now():
            return AnonymousUser()
        
        session_data = session.get_decoded()
        user_id = session_data.get('user_id')
        
        if user_id:
            user = UserInfo.objects.get(id=user_id)
            return user
        else:
            return AnonymousUser()
            
    except (Session.DoesNotExist, UserInfo.DoesNotExist):
        return AnonymousUser()


class SessionAuthMiddleware(BaseMiddleware):
    """基于Django session的WebSocket认证中间件"""
    
    async def __call__(self, scope, receive, send):
        # 只处理WebSocket连接
        if scope["type"] == "websocket":
            # 从cookie中获取session key
            cookies = {}
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"cookie":
                    cookie_string = header_value.decode()
                    for cookie in cookie_string.split(";"):
                        if "=" in cookie:
                            key, value = cookie.strip().split("=", 1)
                            cookies[key] = value
            
            session_key = cookies.get("sessionid")
            
            if session_key:
                scope["user"] = await get_user_from_session(session_key)
            else:
                scope["user"] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


def SessionAuthMiddlewareStack(inner):
    """创建session认证中间件堆栈"""
    return SessionAuthMiddleware(inner) 