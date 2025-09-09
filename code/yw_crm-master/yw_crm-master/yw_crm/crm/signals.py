from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import PrintOrderFlat, OrderProgress
from django.utils import timezone
import json


def send_websocket_notification(group_name, notification_type, data):
    """
    发送WebSocket通知的辅助函数
    """
    try:
        print(f"🚀 准备发送WebSocket通知: {notification_type} 到 {group_name}")
        channel_layer = get_channel_layer()
        if channel_layer:
            message = {
                'type': notification_type,
                'data': data
            }
            print(f"📨 发送消息: {message}")
            async_to_sync(channel_layer.group_send)(group_name, message)
            print(f"✅ WebSocket通知发送成功: {notification_type}")
        else:
            print("❌ 通道层为空，无法发送WebSocket通知")
    except Exception as e:
        print(f"❌ WebSocket通知发送失败: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=PrintOrderFlat)
def print_order_updated(sender, instance, created, **kwargs):
    """
    当PrintOrderFlat模型被保存时触发
    """
    # 仅处理主订单信息（detail_type为None）
    if instance.detail_type is not None:
        return
    
    # 准备通知数据
    notification_data = {
        'order_id': instance.id,
        'order_no': instance.order_no,
        'customer_name': instance.customer_name,
        'product_name': instance.product_name,
        'status': instance.status,
        'status_display': instance.get_status_display(),
        'created': created,
        'timestamp': timezone.now().isoformat(),
        'action': 'created' if created else 'updated'
    }
    
    # 发送订单通知
    send_websocket_notification(
        'notifications',
        'order_notification',
        notification_data
    )
    
    # 发送仪表板更新通知
    dashboard_data = calculate_dashboard_stats()
    send_websocket_notification(
        'notifications',
        'dashboard_update',
        dashboard_data
    )


@receiver(post_delete, sender=PrintOrderFlat)
def print_order_deleted(sender, instance, **kwargs):
    """
    当PrintOrderFlat模型被删除时触发
    """
    # 仅处理主订单信息（detail_type为None）
    if instance.detail_type is not None:
        return
    
    # 准备通知数据
    notification_data = {
        'order_id': instance.id,
        'order_no': instance.order_no,
        'customer_name': instance.customer_name,
        'action': 'deleted',
        'timestamp': timezone.now().isoformat(),
    }
    
    # 发送订单通知
    send_websocket_notification(
        'notifications',
        'order_notification',
        notification_data
    )
    
    # 发送仪表板更新通知
    dashboard_data = calculate_dashboard_stats()
    send_websocket_notification(
        'notifications',
        'dashboard_update',
        dashboard_data
    )


@receiver(post_save, sender=OrderProgress)
def order_progress_updated(sender, instance, created, **kwargs):
    """
    当OrderProgress模型被保存时触发
    """
    print(f"🔥 信号触发: OrderProgress {instance.id} ({instance.step_name}) - {'创建' if created else '更新'}")
    print(f"   订单: {instance.order.order_no}, 状态: {instance.status} ({instance.get_status_display()})")
    
    # 准备通知数据
    notification_data = {
        'progress_id': instance.id,
        'order_id': instance.order.id,
        'order_no': instance.order.order_no,
        'step_name': instance.step_name,
        'step_order': instance.step_order,
        'status': instance.status,
        'status_display': instance.get_status_display(),
        'operator': instance.operator.name if instance.operator else None,
        'operator_id': instance.operator.id if instance.operator else None,
        'confirm_user': instance.confirm_user.name if instance.confirm_user else None,
        'confirm_user_id': instance.confirm_user.id if instance.confirm_user else None,
        'created': created,
        'timestamp': timezone.now().isoformat(),
        'action': 'created' if created else 'updated'
    }
    
    # 发送进度通知
    send_websocket_notification(
        'notifications',
        'progress_notification',
        notification_data
    )
    
    # 发送仪表板更新通知
    dashboard_data = calculate_dashboard_stats()
    send_websocket_notification(
        'notifications',
        'dashboard_update',
        dashboard_data
    )


@receiver(post_delete, sender=OrderProgress)
def order_progress_deleted(sender, instance, **kwargs):
    """
    当OrderProgress模型被删除时触发
    """
    # 准备通知数据
    notification_data = {
        'progress_id': instance.id,
        'order_id': instance.order.id,
        'order_no': instance.order.order_no,
        'step_name': instance.step_name,
        'action': 'deleted',
        'timestamp': timezone.now().isoformat(),
    }
    
    # 发送进度通知
    send_websocket_notification(
        'notifications',
        'progress_notification',
        notification_data
    )
    
    # 发送仪表板更新通知
    dashboard_data = calculate_dashboard_stats()
    send_websocket_notification(
        'notifications',
        'dashboard_update',
        dashboard_data
    )


def calculate_dashboard_stats():
    """
    计算仪表板统计数据
    """
    try:
        from datetime import timedelta
        
        # 统计信息
        total_orders = PrintOrderFlat.objects.filter(detail_type=None).count()
        pending_orders = PrintOrderFlat.objects.filter(detail_type=None, status=1).count()
        processing_orders = PrintOrderFlat.objects.filter(detail_type=None, status=2).count()
        completed_orders = PrintOrderFlat.objects.filter(detail_type=None, status=3).count()
        
        # 获取当前需要处理的步骤数量
        current_steps_count = OrderProgress.objects.filter(
            status=2,  # 进行中的步骤
            order__detail_type=None
        ).count()
        
        # 获取即将开始的步骤数量
        next_steps_count = OrderProgress.objects.filter(
            status=1,  # 待开始的步骤
            order__detail_type=None,
            order__status=2  # 订单处理中
        ).count()
        
        # 获取需要紧急处理的订单数量
        urgent_orders_count = PrintOrderFlat.objects.filter(
            detail_type=None,
            status__in=[1, 2],
            delivery_date__isnull=False,
            delivery_date__lte=timezone.now() + timedelta(days=3)  # 3天内到期
        ).count()
        
        return {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'completed_orders': completed_orders,
            'current_steps_count': current_steps_count,
            'next_steps_count': next_steps_count,
            'urgent_orders_count': urgent_orders_count,
            'timestamp': timezone.now().isoformat(),
        }
    except Exception as e:
        print(f"计算仪表板统计数据失败: {e}")
        return {
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        }


def send_general_notification(message, notification_type='info'):
    """
    发送一般通知
    """
    notification_data = {
        'message': message,
        'type': notification_type,
        'timestamp': timezone.now().isoformat(),
    }
    
    send_websocket_notification(
        'notifications',
        'general_notification',
        notification_data
    ) 