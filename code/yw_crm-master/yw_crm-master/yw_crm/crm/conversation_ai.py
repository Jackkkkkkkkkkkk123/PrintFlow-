"""
对话AI模块
使用LangChain和OpenAI API提供自然语言对话功能
能够理解用户问题并查询数据库的订单信息
"""
import os
import re
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count
from django.conf import settings

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from .models import PrintOrderFlat, OrderProgress, UserInfo
from .conversation_memory import ConversationMemory, ConversationFragment


class OrderQueryTool:
    """订单查询工具类"""
    
    def __init__(self):
        self.today = timezone.now().date()
    
    def search_orders(self, query_params: Dict[str, Any]) -> str:
        """
        根据参数搜索订单 - 优化查询性能
        """
        try:
            # 🚀 构建优化的查询集
            queryset = PrintOrderFlat.objects.filter(detail_type=None)
            
            # 组合所有过滤条件
            if 'order_no' in query_params:
                queryset = queryset.filter(order_no__icontains=query_params['order_no'])
            
            if 'status' in query_params:
                queryset = queryset.filter(status=query_params['status'])
            
            if 'date_range' in query_params:
                date_range = query_params['date_range']
                if date_range == 'today':
                    queryset = queryset.filter(order_date__date=self.today)
                elif date_range == 'yesterday':
                    yesterday = self.today - timedelta(days=1)
                    queryset = queryset.filter(order_date__date=yesterday)
                elif date_range == 'week':
                    week_ago = self.today - timedelta(days=7)
                    queryset = queryset.filter(order_date__date__gte=week_ago)
                elif date_range == 'month':
                    month_ago = self.today - timedelta(days=30)
                    queryset = queryset.filter(order_date__date__gte=month_ago)
            
            if query_params.get('delivery_urgent'):
                urgent_date = timezone.now() + timedelta(days=3)
                queryset = queryset.filter(
                    delivery_date__isnull=False,
                    delivery_date__lte=urgent_date,
                    status__in=[1, 2]
                )
            
            # 🚀 一次性获取结果和总数
            orders = queryset.order_by('-order_date')[:8]  # 减少返回数量
            filtered_count = queryset.count()
            
            if filtered_count == 0:
                if not PrintOrderFlat.objects.filter(detail_type=None).exists():
                    return "🔍 订单搜索：\n\n⚠️ 暂无订单数据"
                return f"🔍 订单搜索：\n\n没有找到符合条件的订单\n\n搜索条件：{query_params}"
            
            # 🚀 精简格式化结果
            status_map = {1: "待处理", 2: "处理中", 3: "已完成"}
            result = f"🔍 找到 {filtered_count} 个订单，显示前 {len(orders)} 个：\n\n"
            
            urgent_date = timezone.now() + timedelta(days=3)
            for order in orders:
                try:
                    status_text = status_map.get(order.status, "未知")
                    is_urgent = (order.delivery_date and order.delivery_date <= urgent_date and order.status in [1, 2]) if order.delivery_date else False
                    urgent_mark = "🚨" if is_urgent else ""
                    date_str = order.order_date.strftime('%m-%d') if order.order_date else "未知"
                    product_name = getattr(order, 'product_name', '') or "未命名产品"
                    result += f"• {product_name} ({order.order_no}) - {status_text}{urgent_mark} ({date_str})\n"
                except Exception:
                    result += f"• {order.order_no} - 数据错误\n"
            
            return result
            
        except Exception as e:
            return f"🔍 订单搜索：\n\n❌ 查询失败：{str(e)[:50]}...\n\n请稍后重试"
    
    def get_order_details(self, order_no: str) -> str:
        """获取指定订单的详细信息"""
        try:
            order = PrintOrderFlat.objects.filter(
                order_no=order_no,
                detail_type=None
            ).first()
            
            if not order:
                return f"未找到订单号为 {order_no} 的订单。"
            
            # 获取订单的进度信息
            progress_steps = OrderProgress.objects.filter(
                order=order
            ).order_by('step_order')
            
            status_text = {1: "待处理", 2: "处理中", 3: "已完成"}.get(order.status, "未知")
            
            product_name = getattr(order, 'product_name', '') or "未命名产品"
            result = f"产品详情：{product_name}\n"
            result += f"订单号：{order.order_no}\n"
            result += f"状态：{status_text}\n"
            result += f"下单时间：{order.order_date.strftime('%Y-%m-%d %H:%M')}\n"
            
            if order.delivery_date:
                result += f"交期：{order.delivery_date.strftime('%Y-%m-%d')}\n"
            
            result += f"客户：{getattr(order, 'customer_name', '未知') or '未知'}\n"
            result += f"联系人：{order.contact_person or '未知'}\n"
            
            if progress_steps.exists():
                result += "\n生产进度：\n"
                for step in progress_steps:
                    step_status = {1: "待开始", 2: "进行中", 3: "已完成", 4: "已跳过"}.get(step.status, "未知")
                    operator_info = f"，操作员：{step.operator.username}" if step.operator else ""
                    result += f"  {step.step_order}. {step.step_name} - {step_status}{operator_info}\n"
            
            return result
            
        except Exception as e:
            return f"获取订单详情时出错：{str(e)}"
    
    def get_statistics(self) -> str:
        """获取订单统计信息 - 优化单次查询"""
        try:
            # 🚀 使用单次聚合查询获取所有统计数据
            from django.db.models import Count, Case, When, IntegerField
            
            stats = PrintOrderFlat.objects.filter(detail_type=None).aggregate(
                total=Count('id'),
                pending=Count(Case(When(status=1, then=1), output_field=IntegerField())),
                processing=Count(Case(When(status=2, then=1), output_field=IntegerField())),
                completed=Count(Case(When(status=3, then=1), output_field=IntegerField())),
                today=Count(Case(When(order_date__date=self.today, then=1), output_field=IntegerField())),
                urgent=Count(Case(When(
                    status__in=[1, 2],
                    delivery_date__isnull=False,
                    delivery_date__lte=timezone.now() + timedelta(days=3),
                    then=1
                ), output_field=IntegerField()))
            )
            
            # 快速数据验证
            if stats['total'] == 0:
                return "📊 订单统计信息：\n\n⚠️ 暂无订单数据\n\n建议：检查数据导入或联系管理员"
            
            # 生成简洁的统计报告
            result = f"📊 订单统计（{timezone.now().strftime('%m-%d %H:%M')}）：\n\n"
            result += f"📈 总数：{stats['total']} 订单\n"
            result += f"⏳ 待处理：{stats['pending']}\n"
            result += f"🔄 处理中：{stats['processing']}\n"
            result += f"✅ 已完成：{stats['completed']}\n"
            result += f"🆕 今日新增：{stats['today']}\n"
            result += f"🚨 紧急订单：{stats['urgent']}\n"
            
            # 检查数据一致性
            other_status = stats['total'] - (stats['pending'] + stats['processing'] + stats['completed'])
            if other_status > 0:
                result += f"❓ 其他状态：{other_status}\n"
            
            return result
            
        except Exception as e:
            return f"📊 订单统计信息：\n\n❌ 获取失败：{str(e)[:100]}...\n\n请稍后重试或联系技术支持"


class ConversationAI:
    """对话AI主类"""
    
    def __init__(self):
        # 从环境变量或配置中获取API配置
        import os
        from django.conf import settings
        
        # 使用DeepSeek API配置
        self.api_key = getattr(settings, 'DEEPSEEK_API_KEY', 'sk-a1ba808bda0442308d951ba0856ebce1')
        self.base_url = getattr(settings, 'DEEPSEEK_BASE_URL', "https://api.deepseek.com/v1")
        self.model = getattr(settings, 'DEEPSEEK_MODEL', "deepseek-chat")
        
        # 如果Django设置中没有配置，再尝试环境变量
        if self.api_key == 'sk-a1ba808bda0442308d951ba0856ebce1':
            env_key = os.getenv('DEEPSEEK_API_KEY')
            if env_key:
                self.api_key = env_key
        
        # 检查API key是否已配置
        if not self.api_key or self.api_key == 'sk-替换为你的key':
            print("⚠️  警告：请在环境变量或Django设置中配置DEEPSEEK_API_KEY")
            print("   可以在settings.py中添加：DEEPSEEK_API_KEY = 'your-actual-api-key'")
            print("   或设置环境变量：export DEEPSEEK_API_KEY='your-actual-api-key'")
        
        print(f"🤖 DeepSeek配置:")
        print(f"   模型: {self.model}")
        print(f"   API地址: {self.base_url}")
        print(f"   API密钥: {self.api_key[:10]}...")
        
        try:
            # 使用DeepSeek API配置（兼容OpenAI格式）
            self.llm = ChatOpenAI(
                model=self.model,
                temperature=0.7,
                api_key=self.api_key,
                base_url=self.base_url,
                max_tokens=1200,
                timeout=30,  # 添加超时设置
                max_retries=2  # 添加重试设置
            )
        except Exception as e:
            print(f"❌ 初始化DeepSeek API失败: {e}")
            print("   请检查API key和base_url配置是否正确")
            # 创建一个备用的虚拟LLM，避免程序崩溃
            self.llm = None
        
        self.order_tool = OrderQueryTool()
        self.conversation_history = []
        self.today = timezone.now().date()
        
        # 初始化RAG对话记忆
        try:
            self.memory = ConversationMemory()
            print("🧠 对话记忆系统初始化成功")
        except Exception as e:
            print(f"⚠️ 对话记忆系统初始化失败: {e}")
            self.memory = None
        
        # 创建系统提示
        self.system_prompt = """你是华龙印务管理系统的AI助手。你可以帮助用户查询和了解华龙印务的订单信息。

你的主要功能包括：
1. 基于提供的订单数据回答用户问题
2. 分析订单统计信息
3. 识别紧急订单和异常情况
4. 提供订单状态和进度查询
5. 记住用户的对话历史，提供连续性服务

订单状态说明：
- 1/待处理: 刚接收的新订单，等待开始处理
- 2/处理中: 正在生产或处理的订单
- 3/已完成: 已完成交付的订单

数据上下文说明：
- 你会收到最新的订单数据上下文
- 你可能会收到相关的历史对话记录，用于理解用户的持续需求
- 历史对话以<conversation_history>标签包围

重要提示：
- 请始终基于提供的数据回答问题，不要编造信息
- 如果数据中没有相关信息，请明确说明
- 对于紧急订单（🚨标记），请特别关注并提醒用户
- 利用历史对话信息提供个性化和连续性的服务
- 如果用户之前询问过类似问题，可以适当关联提及

回答风格：
- 使用友好、专业的语气
- 提供清晰、有组织的信息
- 使用适当的emoji来增强可读性
- 根据具体问题提供相关建议
- 体现对用户历史需求的理解"""
    
    def _get_order_context_data(self) -> str:
        """
        获取订单上下文数据 - 优化数据库查询性能
        """
        try:
            # 🚀 优化：使用单次查询获取所有需要的统计数据
            from django.db.models import Count, Case, When, IntegerField
            
            # 一次性获取所有统计数据
            stats = PrintOrderFlat.objects.filter(detail_type=None).aggregate(
                total=Count('id'),
                pending=Count(Case(When(status=1, then=1), output_field=IntegerField())),
                processing=Count(Case(When(status=2, then=1), output_field=IntegerField())),
                completed=Count(Case(When(status=3, then=1), output_field=IntegerField())),
                today=Count(Case(When(order_date__date=self.today, then=1), output_field=IntegerField())),
                urgent=Count(Case(When(
                    status__in=[1, 2],
                    delivery_date__isnull=False,
                    delivery_date__lte=timezone.now() + timedelta(days=3),
                    then=1
                ), output_field=IntegerField()))
            )
            
            # 快速检查数据可用性
            if stats['total'] == 0:
                return f"<order_data_context>\n⚠️ 暂无订单数据\n</order_data_context>\n"
            
            # 🚀 优化：使用select_related减少查询次数，只获取前5条最近订单
            recent_orders = PrintOrderFlat.objects.filter(detail_type=None).order_by('-order_date')[:5]
            
            # 构建精简的上下文数据
            context_text = f"""<order_data_context>
📊 订单统计：总数{stats['total']} | 待处理{stats['pending']} | 处理中{stats['processing']} | 已完成{stats['completed']} | 今日{stats['today']} | 紧急{stats['urgent']}

📋 最近订单："""
            
            # 添加最近订单（简化格式）
            if recent_orders.exists():
                urgent_date = timezone.now() + timedelta(days=3)
                for order in recent_orders:
                    try:
                        status_text = {1: "待处理", 2: "处理中", 3: "已完成"}.get(order.status, "未知")
                        is_urgent = (order.delivery_date and order.delivery_date <= urgent_date and order.status in [1, 2]) if order.delivery_date else False
                        urgent_mark = "🚨" if is_urgent else ""
                        date_str = order.order_date.strftime('%m-%d') if order.order_date else "未知"
                        product_name = getattr(order, 'product_name', '') or "未命名产品"
                        context_text += f"\n- {product_name}({order.order_no}){urgent_mark} {status_text} {date_str}"
                    except Exception:
                        context_text += f"\n- {order.order_no}(数据错误)"
            else:
                context_text += "\n暂无订单"
            
            context_text += "\n</order_data_context>\n"
            return context_text
            
        except Exception as e:
            return f"<order_data_context>\n❌ 数据获取失败：{str(e)[:50]}...\n</order_data_context>\n"
    
    def chat(self, user_message: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        处理用户消息并返回AI回复 - 精简版
        """
        try:
            # 🚀 优先处理简单查询
            simple_response = self._handle_simple_queries(user_message)
            if simple_response:
                return {
                    'status': 'success',
                    'response': simple_response,
                    'timestamp': timezone.now().isoformat()
                }
            
            # 检查LLM可用性
            if self.llm is None:
                return {
                    'status': 'error',
                    'response': '抱歉，DeepSeek AI助手暂时不可用。您可以尝试使用快速查询功能（如：输入「统计」、「今天」、「紧急」等）。',
                    'timestamp': timezone.now().isoformat()
                }
            
            # 🚀 快速获取上下文并构建消息
            order_context = self._get_order_context_data()
            
            # 简化的历史对话检索
            conversation_context = ""
            if self.memory:
                try:
                    relevant_conversations = self.memory.retrieve_relevant_conversations(
                        user_message, user_id=user_id, limit=2, similarity_threshold=0.2
                    )
                    if relevant_conversations:
                        conversation_context = f"\n<history>最近相关对话：{relevant_conversations[0].user_message[:30]}...</history>\n"
                except Exception:
                    pass
            
            enhanced_message = f"{order_context}{conversation_context}\n用户问题：{user_message}\n\n请简洁回答。"
            
            # 更新对话历史
            self.conversation_history.append(HumanMessage(content=user_message))
            if len(self.conversation_history) > 12:
                self.conversation_history = self.conversation_history[-12:]
            
            # 调用LLM
            messages = [
                SystemMessage(content=self.system_prompt),
                *self.conversation_history[:-1],
                HumanMessage(content=enhanced_message)
            ]
            
            response = self.llm.invoke(messages)
            ai_response = response.content
            
            # 更新历史记录
            self.conversation_history.append(AIMessage(content=ai_response))
            
            # 异步存储对话（不阻塞）
            if self.memory and ai_response:
                try:
                    context_type = self._determine_context_type(user_message, ai_response)
                    self.memory.store_conversation(user_message, ai_response, user_id, context_type)
                except Exception:
                    pass
            
            return {
                'status': 'success',
                'response': ai_response,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            # 🚀 简化的错误处理 - 尝试降级
            fallback_response = self._handle_simple_queries(user_message)
            if fallback_response:
                return {
                    'status': 'success',
                    'response': f"{fallback_response}\n\n（注：AI对话功能暂时不可用）",
                    'timestamp': timezone.now().isoformat()
                }
            
            # 提供基本的帮助信息
            return {
                'status': 'error',
                'response': f'AI服务暂时不可用。您可以尝试：\n• 输入「统计」查看数据\n• 输入「今天」查看今日订单\n• 输入「紧急」查看急单\n• 直接输入订单号查询\n\n错误：{str(e)[:50]}...',
                'timestamp': timezone.now().isoformat()
            }
    
    
    
    def chat_stream(self, user_message: str, user_id: Optional[int] = None):
        """
        优化的流式对话处理 - 简化流程，加快响应速度
        """
        try:
            # 🚀 优先处理简单查询 - 最快路径
            simple_response = self._handle_simple_queries(user_message)
            if simple_response:
                # 直接流式输出简单查询结果，无需状态更新
                yield from self._stream_text_chunks(simple_response, delay=0.015)
                yield {'type': 'complete', 'timestamp': timezone.now().isoformat()}
                return
            
            # 检查LLM可用性
            if self.llm is None:
                yield {
                    'type': 'error',
                    'message': '抱歉，DeepSeek AI助手暂时不可用。您可以尝试使用快速查询功能。',
                    'timestamp': timezone.now().isoformat()
                }
                return
            
            # 📊 快速获取数据上下文（减少日志开销）
            order_context = self._get_order_context_data()
            
            # 🧠 检索历史对话（简化处理）
            conversation_context = ""
            if self.memory:
                try:
                    relevant_conversations = self.memory.retrieve_relevant_conversations(
                        user_message, user_id=user_id, limit=2, similarity_threshold=0.2
                    )
                    if relevant_conversations:
                        conversation_context = f"\n<conversation_history>\n相关历史对话：\n"
                        for i, conv in enumerate(relevant_conversations, 1):
                            time_desc = "今天" if (timezone.now() - conv.timestamp.replace(tzinfo=timezone.get_current_timezone())).days == 0 else "最近"
                            conversation_context += f"{i}. {time_desc}: {conv.user_message[:50]}\n"
                        conversation_context += "</conversation_history>\n"
                except Exception:
                    pass  # 静默处理历史对话错误
            
            # 🤖 构建AI消息
            enhanced_message = f"{order_context}{conversation_context}\n用户问题：{user_message}\n\n请基于以上数据简洁回答。"
            
            # 更新对话历史
            self.conversation_history.append(HumanMessage(content=user_message))
            if len(self.conversation_history) > 16:  # 减少历史记录长度
                self.conversation_history = self.conversation_history[-16:]
            
            messages = [
                SystemMessage(content=self.system_prompt),
                *self.conversation_history[:-1],
                HumanMessage(content=enhanced_message)
            ]
            
            # 🌊 流式AI调用 - 简化重试逻辑
            ai_response_chunks = []
            try:
                for chunk in self.llm.stream(messages):
                    if hasattr(chunk, 'content') and chunk.content:
                        ai_response_chunks.append(chunk.content)
                        yield {
                            'type': 'content',
                            'content': chunk.content,
                            'timestamp': timezone.now().isoformat()
                        }
                        time.sleep(0.02)  # 减少延迟
                
                # 成功完成
                ai_response = ''.join(ai_response_chunks)
                self.conversation_history.append(AIMessage(content=ai_response))
                
                # 异步存储对话（不阻塞响应）
                if self.memory and ai_response:
                    try:
                        context_type = self._determine_context_type(user_message, ai_response)
                        self.memory.store_conversation(user_message, ai_response, user_id, context_type)
                    except Exception:
                        pass  # 静默处理存储错误
                
                yield {'type': 'complete', 'timestamp': timezone.now().isoformat()}
                
            except Exception as e:
                # 简化的错误处理 - 直接降级到非流式
                try:
                    response = self.llm.invoke(messages)
                    ai_response = response.content
                    self.conversation_history.append(AIMessage(content=ai_response))
                    
                    # 快速流式输出降级结果
                    yield from self._stream_text_chunks(ai_response, delay=0.025)
                    yield {'type': 'complete', 'timestamp': timezone.now().isoformat()}
                    
                except Exception:
                    yield {
                        'type': 'error',
                        'message': '抱歉，DeepSeek服务暂时不可用。请尝试使用快速查询功能。',
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            yield {
                'type': 'error',
                'message': f'系统繁忙，请稍后重试。错误信息：{str(e)[:50]}',
                'timestamp': timezone.now().isoformat()
            }
    
    def _stream_text_chunks(self, text: str, delay: float = 0.02):
        """
        优化的文本流式输出 - 智能分块，自然节奏
        """
        if not text:
            return
        
        # 🚀 智能分块策略 - 按语义单位分割
        # 优先按句子分割，再按词组分割
        chunks = []
        
        # 首先按句子分割
        sentences = re.split(r'([。！？；])', text)
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]
            
            if sentence.strip():
                # 如果句子太长，按逗号再次分割
                if len(sentence) > 50:
                    sub_chunks = re.split(r'([，、：])', sentence)
                    for j in range(0, len(sub_chunks), 2):
                        if j + 1 < len(sub_chunks):
                            chunk = sub_chunks[j] + sub_chunks[j + 1]
                        else:
                            chunk = sub_chunks[j]
                        if chunk.strip():
                            chunks.append(chunk)
                else:
                    chunks.append(sentence)
        
        # 🌊 流式输出
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            
            yield {
                'type': 'content',
                'content': chunk,
                'timestamp': timezone.now().isoformat()
            }
            
            # 🎯 智能延迟 - 根据内容调整
            if chunk.endswith(('。', '！', '？')):
                time.sleep(delay * 3)  # 句子结尾较长停顿
            elif chunk.endswith(('，', '、', '：', '；')):
                time.sleep(delay * 2)  # 短语结尾中等停顿
            elif len(chunk) > 20:
                time.sleep(delay * 1.5)  # 长内容稍慢
            else:
                time.sleep(delay)  # 标准延迟
    
    def _handle_simple_queries(self, user_message: str) -> Optional[str]:
        """
        超高速简单查询处理 - 目标: 0.01-0.05秒内返回结果
        """
        start_time = time.time()
        message_cleaned = user_message.strip().lower()
        
        try:
            # 🚀 最高优先级：精确匹配（最快路径）
            exact_commands = {
                '统计': 'stats', '数据': 'stats', '概况': 'stats', '总览': 'stats',
                '今天': 'today', '今日': 'today', '昨天': 'yesterday', '本周': 'week', '本月': 'month',
                '待处理': 'pending', '处理中': 'processing', '已完成': 'completed',
                '紧急': 'urgent', '急单': 'urgent', '交期': 'urgent',
                '帮助': 'help', 'help': 'help', '你好': 'hello', 'hi': 'hello'
            }
            
            command = exact_commands.get(message_cleaned)
            if command:
                result = self._execute_quick_command(command)
                elapsed = time.time() - start_time
                return f"{result}\n\n⚡ 快速查询 ({elapsed:.3f}s)"
            
            # 🎯 高效模糊匹配（单次遍历）
            if len(message_cleaned) <= 20:  # 只对短消息进行模糊匹配
                command = self._fuzzy_match_command(message_cleaned)
                if command:
                    result = self._execute_quick_command(command)
                    elapsed = time.time() - start_time
                    return f"{result}\n\n⚡ 智能匹配 ({elapsed:.3f}s)"
            
            # 🔢 订单号快速检测
            if any(c.isdigit() for c in user_message[:10]):  # 只检查前10个字符
                order_match = re.search(r'\b[A-Za-z]*\d{3,}[A-Za-z0-9]*\b', user_message)
                if order_match:
                    order_no = order_match.group()
                    result = self.order_tool.get_order_details(order_no)
                    elapsed = time.time() - start_time
                    return f"{result}\n\n⚡ 订单查询 ({elapsed:.3f}s)"
            
            return None  # 未匹配，交给AI处理
            
        except Exception:
            return None  # 静默处理错误，交给AI处理
    
    def _execute_quick_command(self, command: str) -> str:
        """执行预定义的快速命令"""
        command_actions = {
            'stats': lambda: self.order_tool.get_statistics(),
            'today': lambda: self.order_tool.search_orders({'date_range': 'today'}),
            'yesterday': lambda: self.order_tool.search_orders({'date_range': 'yesterday'}),
            'week': lambda: self.order_tool.search_orders({'date_range': 'week'}),
            'month': lambda: self.order_tool.search_orders({'date_range': 'month'}),
            'pending': lambda: self.order_tool.search_orders({'status': 1}),
            'processing': lambda: self.order_tool.search_orders({'status': 2}),
            'completed': lambda: self.order_tool.search_orders({'status': 3}),
            'urgent': lambda: self.order_tool.search_orders({'delivery_urgent': True}),
            'help': lambda: "🤖 快速查询指南：\n📊 说「统计」查看概览\n📅 说「今天」查看今日订单\n⚡ 说「处理中」查看进行中订单\n🚨 说「紧急」查看急单\n💬 说具体问题让AI详细回答",
            'hello': lambda: "👋 您好！我是订单管理AI助手\n\n💡 快速提示：\n• 「统计」- 查看数据概览\n• 「今天」- 今日订单\n• 「紧急」- 查看急单\n• 直接说订单号查询详情"
        }
        
        action = command_actions.get(command)
        return action() if action else "❓ 命令未识别"
    
    def _fuzzy_match_command(self, message: str) -> Optional[str]:
        """高效的模糊匹配 - 单次扫描"""
        # 关键词到命令的映射
        keyword_map = {
            # 统计相关
            ('多少', '几个', '数量', '总数', '汇总'): 'stats',
            ('新增', '新订单'): 'today',
            
            # 时间相关
            ('当天', '本日'): 'today',
            ('昨日',): 'yesterday',
            ('这周', '一周', '七天'): 'week',
            ('这月', '一月', '30天'): 'month',
            
            # 状态相关
            ('未处理', '新订单'): 'pending',
            ('进行中', '正在处理'): 'processing',
            ('完成', '完成的'): 'completed',
            
            # 紧急相关
            ('加急', '截止', '到期', '延期', '逾期', '超期'): 'urgent',
            
            # 其他
            ('功能', '指令'): 'help'
        }
        
        # 快速遍历匹配
        for keywords, command in keyword_map.items():
            if any(kw in message for kw in keywords):
                return command
        
        return None
    
    def _determine_context_type(self, user_message: str, ai_response: str) -> str:
        """确定对话的上下文类型"""
        message_lower = user_message.lower()
        response_lower = ai_response.lower()
        
        # 订单详情查询
        if any(keyword in message_lower for keyword in ['订单', '详情', '状态', '进度']) and any(keyword in response_lower for keyword in ['订单详情', '订单号', '状态']):
            return 'order_details'
        
        # 统计信息查询
        if any(keyword in message_lower for keyword in ['统计', '多少', '数量', '总共', '汇总']) and '统计信息' in response_lower:
            return 'statistics'
        
        # 紧急订单查询
        if any(keyword in message_lower for keyword in ['紧急', '交期', '急单']) and any(keyword in response_lower for keyword in ['紧急', '交期']):
            return 'urgent_orders'
        
        # 订单搜索
        if any(keyword in message_lower for keyword in ['今天', '昨天', '处理中', '待处理', '已完成']) and '找到' in response_lower:
            return 'order_search'
        
        # 日期相关查询
        if any(keyword in message_lower for keyword in ['今天', '今日', '昨天', '本周', '本月']):
            return 'date_query'
        
        # 状态相关查询  
        if any(keyword in message_lower for keyword in ['待处理', '处理中', '已完成']):
            return 'status_query'
        
        # 默认为一般对话
        return 'general'
    
    def clear_history(self):
        """清除对话历史"""
        self.conversation_history = []
    
    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        if not self.conversation_history:
            return "暂无对话历史"
        
        # 简单的对话摘要
        human_messages = [msg.content for msg in self.conversation_history if isinstance(msg, HumanMessage)]
        return f"共进行了 {len(human_messages)} 轮对话，最近询问了：{human_messages[-1] if human_messages else '无'}"


# 全局实例
conversation_ai = ConversationAI() 