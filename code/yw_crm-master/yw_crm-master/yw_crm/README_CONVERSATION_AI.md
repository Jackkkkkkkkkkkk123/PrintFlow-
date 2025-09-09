# 🤖 对话AI功能使用指南

## 📋 功能概述

本次更新为印刷订单管理系统的手机端AI助手添加了基于LangChain的自然语言对话功能，用户可以通过自然语言查询订单信息。

### ✨ 新增功能

1. **💬 自然语言对话**
   - 支持中文自然语言查询
   - 智能理解用户意图
   - 实时响应用户问题

2. **📊 智能订单查询**
   - 根据订单号查询详情
   - 按状态筛选订单
   - 时间范围查询（今天、昨天、本周、本月）
   - 紧急交期订单提醒

3. **🔄 降级处理机制**
   - AI不可用时自动降级到关键词匹配
   - 确保基本查询功能始终可用
   - 友好的错误提示和建议

4. **🎨 现代化界面**
   - 类似微信的聊天界面
   - 输入提示和快捷问题
   - 实时打字动画效果

---

## ⚙️ 配置步骤

### 1. 安装依赖包

```bash
# 进入项目目录
cd E:\Aprint\code\yw_crm-master\yw_crm-master\yw_crm

# 安装LangChain相关依赖
pip install -r requirements.txt
```

### 2. 配置OpenAI API

有两种方式配置API密钥：

#### 方式一：在Django设置中配置（推荐）

在 `settings.py` 文件末尾添加：

```python
# OpenAI API配置
OPENAI_API_KEY = 'your-actual-api-key-here'  # 替换为您的实际API密钥
OPENAI_BASE_URL = "https://api.openai-hk.com/v1"  # 或您使用的API服务地址
```

#### 方式二：使用环境变量

```bash
# Windows
set OPENAI_API_KEY=your-actual-api-key-here
set OPENAI_BASE_URL=https://api.openai-hk.com/v1

# Linux/Mac
export OPENAI_API_KEY=your-actual-api-key-here
export OPENAI_BASE_URL=https://api.openai-hk.com/v1
```

### 3. 启动服务

```bash
# 启动Django开发服务器
python manage.py runserver

# 启动WebSocket服务器（另一个终端）
python run_websocket_server.py
```

---

## 🚀 使用方法

### 手机端访问

1. 使用root账户登录系统
2. 在手机浏览器访问：`http://your-server:5173/mobile/ai-assistant/`
3. 或在PC端访问并切换到移动设备模式

### 对话示例

**用户**: "今天有多少个新订单？"
**AI**: "📊 订单统计信息：今日新增：3 个订单..."

**用户**: "查询订单号ABC123的详情"
**AI**: "订单详情：ABC123\n状态：处理中\n下单时间：2024-01-15 10:30..."

**用户**: "有哪些紧急交期的订单？"
**AI**: "找到 2 个紧急订单：\n• ORDER001 - 处理中，交期：2024-01-16\n• ORDER002 - 待处理，交期：2024-01-17"

### 快捷问题

界面提供了预设的快捷问题按钮：
- 今日订单
- 处理中订单
- 紧急订单
- 统计信息

---

## 🛠️ API接口

### 对话接口

```http
POST /api/conversation/chat/
Content-Type: application/json
X-CSRFToken: [csrf-token]

{
    "message": "今天有多少个新订单？"
}
```

响应：
```json
{
    "status": "success",
    "response": "📊 订单统计信息：...",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### 对话历史管理

```http
# 获取对话摘要
GET /api/conversation/history/

# 清除对话历史
DELETE /api/conversation/history/
```

### 测试接口

```http
# 测试对话功能
POST /api/conversation/test/
```

---

## 🔧 调试和测试

### 1. 测试API连接

在AI助手页面点击"🗣️ 测试对话API"按钮，查看调试信息：
- API响应状态
- 测试消息和AI回复
- 连接成功/失败状态

### 2. 查看日志

在开发模式下，AI对话的详细日志会显示在终端：
```bash
# Django服务器日志
INFO: 收到用户消息: 今天有多少个新订单？...
INFO: AI回复状态: success
```

### 3. 降级模式测试

如果API配置有问题，系统会自动降级到关键词匹配模式：
- 仍可查询基本订单信息
- 界面显示降级提示
- 建议用户使用快速操作按钮

---

## 🚨 常见问题

### Q: AI助手提示"暂时不可用"

**A**: 检查API配置：
1. 确认API密钥正确配置
2. 检查网络连接和API服务可用性
3. 查看终端日志中的错误信息

### Q: 聊天界面无响应

**A**: 检查以下项目：
1. CSRF Token是否正确
2. 用户是否有root权限
3. 浏览器控制台是否有JavaScript错误

### Q: AI回复不准确

**A**: 可能原因：
1. 数据库中订单数据不完整
2. 用户查询表达不够清晰
3. 可以尝试使用快捷问题或重新描述需求

### Q: 页面加载缓慢

**A**: 优化建议：
1. 确保Redis服务运行正常
2. 检查数据库查询效率
3. 考虑增加订单数据缓存

---

## 📈 支持的查询类型

### 1. 统计查询
- "今天有多少个新订单？"
- "总共有多少个订单？"
- "待处理的订单数量"

### 2. 状态查询
- "显示所有处理中的订单"
- "查看待处理的订单"
- "已完成的订单列表"

### 3. 时间范围查询
- "今天的订单"
- "昨天新增的订单"
- "本周的订单情况"

### 4. 订单详情查询
- "查询订单号ABC123的详情"
- "订单ORDER001的进度"
- "ABC123这个订单什么情况"

### 5. 紧急事项查询
- "有哪些紧急交期的订单？"
- "需要马上处理的订单"
- "交期在2天内的订单"

---

## 🔄 版本信息

- **LangChain版本**: 0.3.26
- **OpenAI版本**: 1.95.0
- **支持模型**: gpt-3.5-turbo
- **兼容性**: Django 4.2.8+

---

## 🤝 技术支持

如有问题请：
1. 查看调试信息和日志
2. 确认配置是否正确
3. 联系开发团队获取支持

**🎉 享受全新的AI对话体验！** 