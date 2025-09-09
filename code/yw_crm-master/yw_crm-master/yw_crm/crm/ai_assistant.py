"""
AI助手模块
负责生成日报、分析异常数据、检查交期等智能分析功能
"""
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
from .models import PrintOrderFlat, OrderProgress
import json
from crm.models import AIAssistantMemory


class AIAssistant:
    """AI助手类，提供智能分析功能"""
    
    def __init__(self):
        self.today = timezone.now().date()
        self.yesterday = self.today - timedelta(days=1)
        self.week_ago = self.today - timedelta(days=7)
        
    def generate_daily_report(self):
        """生成每日工作报告"""
        try:
            # 获取今日数据
            today_orders = PrintOrderFlat.objects.filter(
                detail_type=None,
                order_date__date=self.today
            )
            
            # 获取今日完成的步骤
            today_completed_steps = OrderProgress.objects.filter(
                status=3,  # 已完成
                end_time__date=self.today,
                order__detail_type=None
            )
            
            # 获取今日开始的步骤
            today_started_steps = OrderProgress.objects.filter(
                status__in=[2, 3],  # 进行中或已完成
                start_time__date=self.today,
                order__detail_type=None
            )
            
            # 统计数据
            stats = {
                'new_orders': today_orders.count(),
                'completed_steps': today_completed_steps.count(),
                'started_steps': today_started_steps.count(),
                'pending_orders': PrintOrderFlat.objects.filter(
                    detail_type=None, status=1
                ).count(),
                'processing_orders': PrintOrderFlat.objects.filter(
                    detail_type=None, status=2
                ).count(),
            }
            
            # 生成报告内容
            report_content = self._format_daily_report(stats, today_completed_steps, today_started_steps)
            
            return {
                'status': 'success',
                'report': report_content,
                'data': stats,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'生成日报时发生错误：{str(e)}'
            }
    
    def _format_daily_report(self, stats, completed_steps, started_steps):
        """格式化日报内容"""
        current_time = timezone.now().strftime('%Y年%m月%d日 %H:%M')
        
        html_content = f"""
        <div style="text-align: left;">
            <h4 style="color: #667eea; margin-bottom: 15px;">📊 {current_time} 工作报告</h4>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <div style="font-weight: bold; margin-bottom: 10px;">📈 今日数据概览</div>
                <div style="margin-bottom: 5px;">• 新增订单：<span style="color: #28a745; font-weight: bold;">{stats['new_orders']}</span> 个</div>
                <div style="margin-bottom: 5px;">• 完成步骤：<span style="color: #17a2b8; font-weight: bold;">{stats['completed_steps']}</span> 个</div>
                <div style="margin-bottom: 5px;">• 开始步骤：<span style="color: #ffc107; font-weight: bold;">{stats['started_steps']}</span> 个</div>
                <div style="margin-bottom: 5px;">• 待处理订单：<span style="color: #dc3545; font-weight: bold;">{stats['pending_orders']}</span> 个</div>
                <div>• 处理中订单：<span style="color: #6c757d; font-weight: bold;">{stats['processing_orders']}</span> 个</div>
            </div>
        """
        
        # 添加完成步骤详情
        if completed_steps.exists():
            html_content += """
            <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <div style="font-weight: bold; margin-bottom: 10px; color: #155724;">✅ 今日完成步骤</div>
            """
            for step in completed_steps[:5]:  # 只显示前5个
                html_content += f'<div style="margin-bottom: 3px; font-size: 12px;">• {step.order.order_no} - {step.step_name}</div>'
            
            if completed_steps.count() > 5:
                html_content += f'<div style="margin-top: 8px; font-size: 11px; color: #666;">...还有 {completed_steps.count() - 5} 个步骤</div>'
            html_content += "</div>"
        
        # 添加效率分析
        efficiency_analysis = self._analyze_efficiency()
        html_content += f"""
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px;">
                <div style="font-weight: bold; margin-bottom: 10px; color: #856404;">⚡ 效率分析</div>
                {efficiency_analysis}
            </div>
        </div>
        """
        
        return html_content
    
    def _analyze_efficiency(self):
        """分析工作效率"""
        # 计算平均完成时间
        completed_today = OrderProgress.objects.filter(
            status=3,
            end_time__date=self.today,
            order__detail_type=None
        )
        
        if not completed_today.exists():
            return "<div style='font-size: 12px;'>今日暂无完成的步骤数据</div>"
        
        # 简单的效率分析
        total_steps = completed_today.count()
        avg_per_hour = round(total_steps / max(timezone.now().hour, 1), 1) if timezone.now().hour > 0 else 0
        
        return f"""
        <div style="font-size: 12px;">
            <div>• 平均每小时完成：{avg_per_hour} 个步骤</div>
            <div>• 总体进度：{"良好" if total_steps >= 5 else "一般" if total_steps >= 2 else "较慢"}</div>
        </div>
        """
    
    def analyze_anomalies(self):
        """分析异常数据"""
        try:
            anomalies = []
            
            # 1. 检查长期未处理的订单
            overdue_orders = PrintOrderFlat.objects.filter(
                detail_type=None,
                status=1,  # 待处理
                order_date__lte=timezone.now() - timedelta(days=3)
            )
            
            if overdue_orders.exists():
                anomalies.append({
                    'type': 'overdue_orders',
                    'title': '⚠️ 长期未处理订单',
                    'count': overdue_orders.count(),
                    'description': f'发现 {overdue_orders.count()} 个订单超过3天未开始处理'
                })
            
            # 2. 检查长时间停滞的步骤
            stalled_steps = OrderProgress.objects.filter(
                status=2,  # 进行中
                start_time__lte=timezone.now() - timedelta(days=2),
                order__detail_type=None
            )
            
            if stalled_steps.exists():
                anomalies.append({
                    'type': 'stalled_steps',
                    'title': '🔄 停滞的生产步骤',
                    'count': stalled_steps.count(),
                    'description': f'发现 {stalled_steps.count()} 个步骤超过2天未完成'
                })
            
            # 3. 检查即将逾期的订单
            urgent_orders = PrintOrderFlat.objects.filter(
                detail_type=None,
                status__in=[1, 2],
                delivery_date__isnull=False,
                delivery_date__lte=timezone.now() + timedelta(days=2)
            )
            
            if urgent_orders.exists():
                anomalies.append({
                    'type': 'urgent_orders',
                    'title': '🚨 紧急交期订单',
                    'count': urgent_orders.count(),
                    'description': f'发现 {urgent_orders.count()} 个订单将在2天内到期'
                })
            
            # 格式化异常报告
            if anomalies:
                content = self._format_anomalies_report(anomalies)
            else:
                content = """
                <div style="text-align: center; color: #28a745; padding: 20px;">
                    <div style="font-size: 24px; margin-bottom: 10px;">✅</div>
                    <div>未发现异常数据</div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;">所有订单和步骤运行正常</div>
                </div>
                """
            
            return {
                'status': 'success',
                'anomalies': content,
                'count': len(anomalies)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'异常分析时发生错误：{str(e)}'
            }
    
    def _format_anomalies_report(self, anomalies):
        """格式化异常报告"""
        html_content = ""
        
        for anomaly in anomalies:
            color = "#dc3545" if anomaly['type'] == 'urgent_orders' else "#ffc107"
            html_content += f"""
            <div style="border-left: 3px solid {color}; padding: 15px; margin-bottom: 15px; background: #f8f9fa; border-radius: 5px;">
                <div style="font-weight: bold; color: {color}; margin-bottom: 8px;">{anomaly['title']}</div>
                <div style="font-size: 12px; color: #666;">{anomaly['description']}</div>
                <div style="font-size: 11px; color: #999; margin-top: 5px;">建议：尽快处理相关订单</div>
            </div>
            """
        
        return html_content
    
    def check_deadlines(self):
        """检查交期情况"""
        try:
            now = timezone.now()
            
            # 获取不同时间段的交期订单
            deadline_data = {
                'overdue': PrintOrderFlat.objects.filter(
                    detail_type=None,
                    status__in=[1, 2],
                    delivery_date__lt=now
                ),
                'today': PrintOrderFlat.objects.filter(
                    detail_type=None,
                    status__in=[1, 2],
                    delivery_date__date=now.date()
                ),
                'tomorrow': PrintOrderFlat.objects.filter(
                    detail_type=None,
                    status__in=[1, 2],
                    delivery_date__date=now.date() + timedelta(days=1)
                ),
                'this_week': PrintOrderFlat.objects.filter(
                    detail_type=None,
                    status__in=[1, 2],
                    delivery_date__range=[
                        now.date() + timedelta(days=2),
                        now.date() + timedelta(days=7)
                    ]
                )
            }
            
            # 格式化交期分析报告
            content = self._format_deadline_report(deadline_data)
            
            return {
                'status': 'success',
                'deadline_analysis': content
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'交期检查时发生错误：{str(e)}'
            }
    
    def _format_deadline_report(self, deadline_data):
        """格式化交期报告"""
        html_content = f"""
        <div style="text-align: left;">
            <h4 style="color: #667eea; margin-bottom: 15px;">⏰ 交期分析报告</h4>
        """
        
        # 逾期订单
        if deadline_data['overdue'].exists():
            html_content += f"""
            <div style="background: #f8d7da; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid #dc3545;">
                <div style="font-weight: bold; color: #721c24; margin-bottom: 10px;">🚨 已逾期订单 ({deadline_data['overdue'].count()}个)</div>
            """
            for order in deadline_data['overdue'][:3]:
                days_overdue = (timezone.now().date() - order.delivery_date.date()).days
                html_content += f'<div style="font-size: 12px; margin-bottom: 3px;">• {order.order_no} (逾期{days_overdue}天)</div>'
            html_content += "</div>"
        
        # 今日交期
        if deadline_data['today'].exists():
            html_content += f"""
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid #ffc107;">
                <div style="font-weight: bold; color: #856404; margin-bottom: 10px;">📅 今日交期 ({deadline_data['today'].count()}个)</div>
            """
            for order in deadline_data['today']:
                html_content += f'<div style="font-size: 12px; margin-bottom: 3px;">• {order.order_no}</div>'
            html_content += "</div>"
        
        # 明日交期
        if deadline_data['tomorrow'].exists():
            html_content += f"""
            <div style="background: #d1ecf1; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid #17a2b8;">
                <div style="font-weight: bold; color: #0c5460; margin-bottom: 10px;">📋 明日交期 ({deadline_data['tomorrow'].count()}个)</div>
            """
            for order in deadline_data['tomorrow']:
                html_content += f'<div style="font-size: 12px; margin-bottom: 3px;">• {order.order_no}</div>'
            html_content += "</div>"
        
        # 本周交期
        if deadline_data['this_week'].exists():
            html_content += f"""
            <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 3px solid #28a745;">
                <div style="font-weight: bold; color: #155724; margin-bottom: 10px;">📊 本周交期 ({deadline_data['this_week'].count()}个)</div>
                <div style="font-size: 12px; color: #666;">本周内需要完成的订单数量</div>
            </div>
            """
        
        # 如果没有任何交期订单
        if not any(data.exists() for data in deadline_data.values()):
            html_content += """
            <div style="text-align: center; color: #28a745; padding: 20px;">
                <div style="font-size: 24px; margin-bottom: 10px;">✅</div>
                <div>暂无紧急交期订单</div>
                <div style="font-size: 12px; color: #666; margin-top: 5px;">所有订单交期充裕</div>
            </div>
            """
        
        html_content += "</div>"
        return html_content
    
    def get_auto_report_time(self):
        """获取自动报告时间（每天下午5:30）"""
        today = timezone.now().date()
        report_time = timezone.make_aware(
            datetime.combine(today, datetime.min.time().replace(hour=17, minute=30))
        )
        return report_time

    def save_memory(self, user, content, memory_type='chat'):
        """保存一条记忆，只用user本身，并加user.id有效性判断"""
        import logging
        logger = logging.getLogger(__name__)
        print('正在写入')
        print('user类型:', type(user))
        try:
            if user is None or not getattr(user, 'id', None):
                logger.error("记忆写入失败: user为None或user.id为None")
                return
            AIAssistantMemory.objects.create(user=user, content=content, memory_type=memory_type)
            logger.info(f"记忆写入成功: user={user}, content={content[:20]}")
        except Exception as e:
            logger.error(f"记忆写入失败: {e}")

    def get_memories(self, user, memory_type='chat', limit=20):
        """获取用户最近的记忆"""
        return AIAssistantMemory.objects.filter(user=user, memory_type=memory_type)[:limit]

    def clear_memories(self, user, memory_type='chat'):
        """清空用户记忆"""
        AIAssistantMemory.objects.filter(user=user, memory_type=memory_type).delete()


# 全局AI助手实例
ai_assistant = AIAssistant() 