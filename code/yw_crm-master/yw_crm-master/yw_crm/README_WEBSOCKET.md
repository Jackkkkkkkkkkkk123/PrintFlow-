# WebSocket实时推送系统

## 功能概述

本系统实现了基于Django Channels和Redis的WebSocket实时推送功能，当数据库中的订单信息或进度信息发生变化时，会自动推送到所有连接的客户端，实现数据的实时同步。

## 技术架构

- **Django Channels**: 处理WebSocket连接和异步消息
- **Redis**: 作为通道层，支持多实例间的消息广播
- **WebSocket**: 建立客户端与服务器的持久连接
- **Django信号**: 监听模型变化并触发推送

## 安装和配置

### 1. 安装依赖包

```bash
pip install channels==2.4.0
pip install channels-redis==2.4.2
pip install redis==3.5.3
```

### 2. 启动Redis服务

```bash
# Ubuntu/Debian
sudo systemctl start redis-server

# CentOS/RHEL
sudo systemctl start redis

# 或者使用Docker
docker run -d -p 6379:6379 redis:latest
```

### 3. 配置Django设置

在`settings.py`中添加了以下配置：

```python
# 添加channels到INSTALLED_APPS
INSTALLED_APPS = [
    # ... 其他应用
    'channels',
]

# 配置ASGI应用
ASGI_APPLICATION = 'yw_crm.asgi.application'

# 配置通道层
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

### 4. 启动应用

```bash
# 使用ASGI服务器启动（开发环境）
python manage.py runserver

# 生产环境建议使用
daphne -p 5173 yw_crm.asgi:application
```

## 功能特性

### 1. 实时通知类型

- **订单通知**: 订单创建、更新、删除时推送
- **进度通知**: 订单进度变化时推送
- **仪表板更新**: 统计数据实时更新
- **一般通知**: 系统消息和提醒

### 2. 自动重连

- 连接断开时自动重连
- 最大重连次数: 5次
- 重连间隔: 3秒
- 心跳检测: 30秒间隔

### 3. 消息格式

```javascript
{
    "type": "order_notification",
    "data": {
        "order_id": 1,
        "order_no": "PO20231201001",
        "customer_name": "测试客户",
        "action": "created",
        "timestamp": "2023-12-01T10:00:00Z"
    }
}
```

## 使用说明

### 1. 客户端连接

WebSocket会在页面加载时自动连接到`/ws/notifications/`端点。

### 2. 连接状态显示

页面顶部会显示当前WebSocket连接状态：
- 🟢 **已连接**: 正常接收实时数据
- 🔴 **已断开**: 连接中断，正在尝试重连

### 3. 实时更新内容

- **统计数据**: 订单总数、待处理数量等自动更新
- **进度列表**: 当前进行中的步骤、等待开始的步骤实时刷新
- **通知提醒**: 右上角显示系统通知

### 4. 手动触发测试

可以通过以下方式测试实时推送：

```python
# 在Django shell中执行
from crm.signals import send_general_notification
send_general_notification("测试消息", "info")
```

## 文件结构

```
yw_crm/
├── yw_crm/
│   ├── asgi.py              # ASGI应用配置
│   └── settings.py          # Django设置
├── crm/
│   ├── consumers.py         # WebSocket消费者
│   ├── signals.py           # 模型信号处理器
│   └── apps.py              # 应用配置
├── static/js/
│   └── websocket-client.js  # 前端WebSocket客户端
└── templates/
    └── index.html           # 首页模板（支持实时更新）
```

## 监控和调试

### 1. 连接状态监控

- 查看页面顶部的连接状态指示器
- 检查浏览器开发者工具的WebSocket连接

### 2. 服务器日志

```bash
# 查看Django日志
tail -f /var/log/django/django.log

# 查看Redis日志
redis-cli monitor
```

### 3. 常见问题

#### WebSocket连接失败
- 检查Redis服务是否正常运行
- 确认防火墙设置允许WebSocket连接
- 检查ASGI应用配置是否正确

#### 消息推送不及时
- 检查Django信号是否正确注册
- 确认模型变化是否触发信号
- 检查通道层配置

#### 客户端断线重连
- 正常情况下会自动重连
- 如果重连失败，请刷新页面
- 检查网络连接是否稳定

## 扩展功能

### 1. 添加新的通知类型

在`consumers.py`中添加新的消息处理方法：

```python
async def custom_notification(self, event):
    await self.send(text_data=json.dumps({
        'type': 'custom_notification',
        'data': event['data']
    }))
```

### 2. 添加用户权限控制

在`consumers.py`的`connect`方法中添加权限检查：

```python
async def connect(self):
    user = self.scope["user"]
    if not user.has_perm('crm.view_printorder'):
        await self.close()
        return
    # ... 其他连接逻辑
```

### 3. 分组推送

可以根据用户角色或部门创建不同的推送组：

```python
# 根据用户部门创建组名
self.room_group_name = f'dept_{user.department.id}'
```

## 性能优化

### 1. Redis配置优化

```conf
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### 2. 连接池配置

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
            'capacity': 1500,
            'expiry': 60,
        },
    },
}
```

### 3. 消息频率控制

在信号处理器中添加防抖逻辑，避免频繁推送：

```python
import time
from django.core.cache import cache

def send_websocket_notification(group_name, notification_type, data):
    # 防抖：同一类型消息1秒内只发送一次
    cache_key = f'ws_debounce_{group_name}_{notification_type}'
    if cache.get(cache_key):
        return
    cache.set(cache_key, True, 1)
    
    # 发送消息
    # ... 原有逻辑
```

## 部署建议

### 1. 生产环境配置

```bash
# 使用Daphne作为ASGI服务器
pip install daphne

# 启动命令
daphne -p 5173 --access-log /var/log/daphne.log yw_crm.asgi:application
```

### 2. Nginx配置

```nginx
server {
    listen 80;
    server_name example.com;
    
    # WebSocket代理
    location /ws/ {
        proxy_pass http://127.0.0.1:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 静态文件和其他请求
    location / {
        proxy_pass http://127.0.0.1:5173;
        # ... 其他配置
    }
}
```

### 3. 监控脚本

```bash
#!/bin/bash
# websocket-monitor.sh
while true; do
    if ! pgrep -f "daphne.*yw_crm.asgi" > /dev/null; then
        echo "WebSocket服务已停止，正在重启..."
        nohup daphne -p 5173 yw_crm.asgi:application > /var/log/websocket.log 2>&1 &
    fi
    sleep 30
done
```

## 总结

WebSocket实时推送系统为印刷订单管理系统提供了实时数据同步功能，提升了用户体验和工作效率。通过合理的配置和优化，可以在生产环境中稳定运行，支持多用户并发访问。 