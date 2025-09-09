from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse, JsonResponse
from crm.models import PrintOrderFlat, OrderProgress
from django.utils import timezone
from datetime import timedelta
import os
from crm.utils import is_mobile_device, is_root_user, get_device_type, get_user_type
from crm.ai_assistant import ai_assistant
from crm.models import UserInfo
# 新增：导入权限装饰器
from rbac.decorators import require_step_permission, check_step_permission, log_step_operation
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class IndexView(View):

    def get(self, request):
        # 检测设备类型
        device_type = get_device_type(request)
        user_type = get_user_type(request)
        
        # 调试信息：记录当前请求的设备检测结果
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        print(f"🔍 设备检测调试:")
        print(f"   User-Agent: {user_agent}")
        print(f"   检测结果: {device_type}")
        print(f"   用户类型: {user_type}")
        
        # 如果是移动设备，重定向到手机端页面
        if device_type == 'mobile':
            print(f"   → 重定向到手机端: {'mobile_dashboard' if user_type == 'root' else 'mobile_orders'}")
            if user_type == 'root':
                return redirect('mobile_dashboard')
            else:
                return redirect('mobile_orders')
        
        print(f"   → 显示桌面端页面")
        
        # PC端首页逻辑
        user_id = request.session.get('user_id')
        context = {}
        
        # 统计信息
        total_orders = PrintOrderFlat.objects.filter(detail_type=None).count()
        pending_orders = PrintOrderFlat.objects.filter(detail_type=None, status=1).count()
        processing_orders = PrintOrderFlat.objects.filter(detail_type=None, status=2).count()
        
        # 获取当前需要处理的步骤（进行中的步骤）
        current_steps = OrderProgress.objects.filter(
            status=2,  # 进行中的步骤
            order__detail_type=None
        ).select_related('order', 'operator').order_by('-updated_time')[:5]
        
        # 获取即将开始的步骤（待开始的步骤）
        next_steps = OrderProgress.objects.filter(
            status=1,  # 待开始的步骤
            order__detail_type=None,
            order__status=2  # 订单处理中
        ).select_related('order').order_by('created_time')[:5]
        
        # 获取最近完成的步骤
        recent_completed = OrderProgress.objects.filter(
            status=3,  # 已完成的步骤
            order__detail_type=None
        ).select_related('order', 'confirm_user').order_by('-updated_time')[:5]
        
        # 获取需要紧急处理的订单（即将到期的处理中订单）
        urgent_orders = PrintOrderFlat.objects.filter(
            detail_type=None,
            status__in=[1, 2],
            delivery_date__isnull=False,
            delivery_date__lte=timezone.now() + timedelta(days=3)  # 3天内到期
        ).order_by('delivery_date')[:3]
        
        context.update({
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'current_steps': current_steps,
            'next_steps': next_steps,
            'recent_completed': recent_completed,
            'urgent_orders': urgent_orders,
            'device_type': device_type,
            'user_type': user_type,
        })

        return render(request, 'index.html', context)


# ======================
# 手机端视图类
# ======================

class MobileOrdersView(View):
    """手机端订单列表页面（普通用户）"""
    
    def get(self, request):
        # 检查用户登录状态
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')
        
        # 获取订单列表
        orders = PrintOrderFlat.objects.filter(
            detail_type=None
        ).select_related().order_by('-order_date')
        
        # 分页处理（手机端显示更少条目）
        from django.core.paginator import Paginator
        paginator = Paginator(orders, 10)  # 每页10条
        page = request.GET.get('page', 1)
        orders_page = paginator.get_page(page)
        
        # 获取订单统计
        total_orders = orders.count()
        pending_orders = orders.filter(status=1).count()
        processing_orders = orders.filter(status=2).count()
        completed_orders = orders.filter(status=3).count()
        
        context = {
            'orders': orders_page,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'completed_orders': completed_orders,
            'user_type': 'normal',
            'device_type': 'mobile',
        }
        
        return render(request, 'mobile/orders.html', context)


class MobileDashboardView(View):
    """手机端仪表板页面（root用户）"""
    
    def get(self, request):
        # 检查用户权限
        if not is_root_user(request):
            return redirect('mobile_orders')
        
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')
        
        # 获取仪表板数据
        total_orders = PrintOrderFlat.objects.filter(detail_type=None).count()
        pending_orders = PrintOrderFlat.objects.filter(detail_type=None, status=1).count()
        processing_orders = PrintOrderFlat.objects.filter(detail_type=None, status=2).count()
        completed_orders = PrintOrderFlat.objects.filter(detail_type=None, status=3).count()
        
        # 获取当前进行中的步骤
        current_steps = OrderProgress.objects.filter(
            status=2,  # 进行中
            order__detail_type=None
        ).select_related('order', 'operator').order_by('-updated_time')[:10]
        
        # 获取待开始的步骤
        next_steps = OrderProgress.objects.filter(
            status=1,  # 待开始
            order__detail_type=None,
            order__status=2
        ).select_related('order').order_by('created_time')[:10]
        
        # 获取紧急订单
        urgent_orders = PrintOrderFlat.objects.filter(
            detail_type=None,
            status__in=[1, 2],
            delivery_date__isnull=False,
            delivery_date__lte=timezone.now() + timedelta(days=3)
        ).order_by('delivery_date')[:5]
        
        # 获取今日完成的步骤
        today = timezone.now().date()
        today_completed = OrderProgress.objects.filter(
            status=3,
            order__detail_type=None,
            updated_time__date=today
        ).count()
        
        context = {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'completed_orders': completed_orders,
            'current_steps': current_steps,
            'next_steps': next_steps,
            'urgent_orders': urgent_orders,
            'today_completed': today_completed,
            'user_type': 'root',
            'device_type': 'mobile',
        }
        
        return render(request, 'mobile/dashboard.html', context)


class MobileOrderDetailView(View):
    """手机端订单详情页面"""
    def get(self, request, order_id):
        try:
            import json
            from django.shortcuts import get_object_or_404
            order = get_object_or_404(PrintOrderFlat, id=order_id, detail_type=None)
            
            # 解析明细数据
            details = []
            # 解析用料明细
            try:
                material_data = json.loads(order.material_json or '[]')
                for item in material_data:
                    detail_obj = type('DetailObj', (), {
                        'detail_type': '用料',
                        'serial_no': item.get('序', ''),
                        'item': item.get('项目', ''),
                        'material_name': item.get('材料名称', ''),
                        'spec': item.get('规格', ''),
                        'page_number': item.get('页数', ''),
                        'open_number': item.get('开数', ''),
                        'fangshu': item.get('放数', ''),
                        'total': item.get('总数', ''),
                        'dunjia': item.get('吨价', ''),
                        'unit_price': item.get('单价', ''),
                        'amount': item.get('金额', ''),
                    })()
                    details.append(detail_obj)
            except:
                pass

            # 解析印前明细
            try:
                prepress_data = json.loads(order.prepress_json or '[]')
                for item in prepress_data:
                    detail_obj = type('DetailObj', (), {
                        'detail_type': '印前',
                        'serial_no': item.get('序', ''),
                        'item': item.get('项目', ''),
                        'content': item.get('内    容', item.get('内容', '')),
                        'spec': item.get('规格', ''),
                        'plate_name': item.get('制版名称', ''),
                        'note_detail': item.get('备注', ''),
                        'quantity': item.get('数量', ''),
                        'unit': item.get('单位', ''),
                        'unit_price': item.get('单价', ''),
                        'amount': item.get('金额', ''),
                    })()
                    details.append(detail_obj)
            except:
                pass

            # 解析印刷明细
            try:
                process_data = json.loads(order.process_json or '[]')
                for item in process_data:
                    detail_obj = type('DetailObj', (), {
                        'detail_type': '印刷',
                        'serial_no': item.get('序', ''),
                        'item': item.get('项目', ''),
                        'print_color': item.get('印色', ''),
                        'print_size': item.get('印刷尺寸', ''),
                        'print_method': item.get('印刷方式', ''),
                        'machine': item.get('机台', ''),
                        'quantity': item.get('数量', ''),
                        'unit': item.get('单位', ''),
                        'unit_price': item.get('单价', ''),
                        'amount': item.get('金额', ''),
                    })()
                    details.append(detail_obj)
            except:
                pass

            # 解析印后明细
            try:
                postpress_data = json.loads(order.postpress_json or '[]')
                for item in postpress_data:
                    detail_obj = type('DetailObj', (), {
                        'detail_type': '印后',
                        'serial_no': item.get('序', ''),
                        'item': item.get('项目', ''),
                        'process_content': item.get('加工内容', ''),
                        'process': item.get('工序', ''),
                        'spec': item.get('规格', ''),
                        'machine': item.get('机台', ''),
                        'quantity': item.get('数量', ''),
                        'unit_price': item.get('单价', ''),
                        'amount': item.get('金额', ''),
                    })()
                    details.append(detail_obj)
            except:
                pass

            # 步骤进度相关
            progress_steps = OrderProgress.objects.filter(order=order).order_by('step_order')
            cover_steps = progress_steps.filter(step_category='cover')
            content_steps = progress_steps.filter(step_category='content')
            step_list = []
            total_steps = progress_steps.count()
            completed_steps = progress_steps.filter(status=3).count()
            in_progress_steps = progress_steps.filter(status=2).count()
            pending_steps = progress_steps.filter(status=1).count()
            skipped_steps = progress_steps.filter(status=4).count()
            progress_percentage = int(((completed_steps + skipped_steps) / total_steps * 100)) if total_steps > 0 else 0

            # 新增：获取当前用户
            from crm.models import UserInfo
            user = UserInfo.objects.filter(id=request.session.get('user_id')).first()

            # 计算每个步骤是否可开始，并检查权限
            for step in progress_steps:
                can_start = False
                if step.status == 1:  # 待开始
                    # 只检查同类别的前置步骤
                    previous_steps = progress_steps.filter(
                        step_category=step.step_category,
                        step_order__lt=step.step_order
                    ).exclude(status__in=[3, 4])
                    if not previous_steps.exists():
                        can_start = True
                # 检查权限
                can_start_permission = check_step_permission(user, step, 'start') if user else False
                can_complete_permission = check_step_permission(user, step, 'complete') if user else False
                can_skip_permission = check_step_permission(user, step, 'skip') if user else False

                step_list.append({
                    'step': step,
                    'can_start': can_start,
                    'can_start_permission': can_start_permission,
                    'can_complete_permission': can_complete_permission,
                    'can_skip_permission': can_skip_permission,
                })

            context = {
                'order': order,
                'details': details,  # 添加details数据
                'progress_steps': progress_steps,
                'step_list': step_list,  # 添加包含can_start信息的步骤列表
                'user_type': get_user_type(request),
                'device_type': 'mobile',
                # 进度统计
                'total_steps': total_steps,
                'completed_steps': completed_steps,
                'in_progress_steps': in_progress_steps,
                'pending_steps': pending_steps,
                'skipped_steps': skipped_steps,
                'progress_percentage': progress_percentage,
                'cover_steps': cover_steps,
                'content_steps': content_steps,
            }
            return render(request, 'mobile/order_detail.html', context)
        except Exception as e:
            return render(request, 'mobile/order_detail.html', {'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class MobileAIAssistantView(View):
    """手机端AI助手页面（仅root用户）"""
    
    def get(self, request):
        # 检查权限
        if not is_root_user(request):
            return JsonResponse({'error': '权限不足'}, status=403)
        
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')
        
        context = {
            'user_type': 'root',
            'device_type': 'mobile',
        }
        
        return render(request, 'mobile/ai_assistant.html', context)
    
    def post(self, request):
        """处理AI助手请求"""
        if not is_root_user(request):
            return JsonResponse({'error': '权限不足'}, status=403)
        
        # 这里后续会接入AI助手功能
        return JsonResponse({
            'status': 'success',
            'message': 'AI助手功能开发中...'
        })


# ======================
# API视图（用于AJAX请求）
# ======================

class MobileOrderStatusAPI(View):
    """手机端订单状态API"""
    
    def get(self, request, order_id):
        try:
            order = PrintOrderFlat.objects.get(id=order_id, detail_type=None)
            progress_steps = OrderProgress.objects.filter(
                order=order
            ).order_by('step_order')
            
            steps_data = []
            for step in progress_steps:
                steps_data.append({
                    'id': step.id,
                    'step_name': step.step_name,
                    'status': step.status,
                    'status_display': step.get_status_display(),
                    'operator': step.operator.username if step.operator else None,
                    'start_time': step.start_time.strftime('%Y-%m-%d %H:%M') if step.start_time else None,
                    'complete_time': step.complete_time.strftime('%Y-%m-%d %H:%M') if step.complete_time else None,
                })
            
            return JsonResponse({
                'status': 'success',
                'order': {
                    'id': order.id,
                    'order_no': order.order_no,
                    'status': order.status,
                    'status_display': order.get_status_display(),
                },
                'steps': steps_data
            })
            
        except PrintOrderFlat.DoesNotExist:
            return JsonResponse({'error': '订单不存在'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class MobileStartStepAPI(View):
    """手机端开始步骤API"""
    
    @method_decorator(require_step_permission('start'))
    def post(self, request, step_id):
        """开始步骤 - 已通过权限装饰器验证"""
        try:
            # 从装饰器获取已验证的对象
            step = request.current_step
            user = request.current_user
            
            print(f"🔧 移动端开始步骤: {step.step_name}, 用户: {user.name}, 权限检查已通过")
            
            # 检查步骤状态
            if step.status != 1:  # 只能开始待开始的步骤
                error_msg = '步骤状态不允许开始'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 检查订单状态
            if step.order.status not in [1, 2]:
                error_msg = '订单状态不允许操作'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 检查是否有前置步骤未完成
            previous_steps = OrderProgress.objects.filter(
                order=step.order,
                step_category=step.step_category,
                step_order__lt=step.step_order
            ).exclude(status__in=[3, 4])  # 只查同类别，排除已完成和已跳过的步骤
            
            if previous_steps.exists():
                incomplete_steps = [s.step_name for s in previous_steps]
                error_msg = f'请先完成前置步骤：{", ".join(incomplete_steps)}'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 检查上个步骤是否有备注
            previous_step = OrderProgress.objects.filter(
                order=step.order,
                step_order__lt=step.step_order,
                status__in=[3, 4],  # 已完成或已跳过
                note__isnull=False
            ).exclude(note='').order_by('-step_order').first()
            
            if previous_step and previous_step.note:
                # 需要用户确认上个步骤的备注
                return JsonResponse({
                    'status': 'need_confirmation',
                    'message': '请先查看上个步骤的备注',
                    'previous_step_name': previous_step.step_name,
                    'previous_step_note': previous_step.note,
                    'step_id': step.id
                })
            
            # 直接开始步骤
            return self._start_step_directly(step, user, request)
            
        except Exception as e:
            print(f"❌ 移动端开始步骤错误: {str(e)}")
            return JsonResponse({'error': f'操作失败：{str(e)}'}, status=500)
    
    def _start_step_directly(self, step, user, request):
        """直接开始步骤的内部方法"""
        try:
            # 使用模型的start_step方法，确保与PC版本逻辑一致
            step.start_step(user)
            
            # 记录成功操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'start',
                user, '移动端权限装饰器验证', True, '', True, '', f'移动端步骤已开始', request
            )
            
            return JsonResponse({
                'status': 'success',
                'message': '步骤已开始',
                'step_id': step.id,
                'step_name': step.step_name
            })
        except Exception as e:
            error_msg = f'开始步骤失败：{str(e)}'
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'start',
                user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
            )
            return JsonResponse({'error': error_msg}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MobileSkipStepAPI(View):
    """手机端跳过步骤API"""
    
    @method_decorator(require_step_permission('skip'))
    def post(self, request, step_id):
        """跳过步骤 - 已通过权限装饰器验证"""
        try:
            import json
            data = json.loads(request.body)
            reason = data.get('reason', '').strip()
            
            if not reason:
                return JsonResponse({'error': '跳过原因不能为空'}, status=400)
            
            # 从装饰器获取已验证的对象
            step = request.current_step
            user = request.current_user
            
            print(f"🔧 移动端跳过步骤: {step.step_name}, 用户: {user.name}, 权限检查已通过")
            
            # 检查步骤状态
            if step.status != 2:  # 只能跳过进行中的步骤
                error_msg = '只能跳过进行中的步骤'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'skip',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 更新步骤状态
            step.status = 4  # 已跳过
            step.end_time = timezone.now()
            step.updated_time = timezone.now()
            step.note = f'跳过原因: {reason}'
            step.confirm_user = user
            step.save()
            
            # 记录成功操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'skip',
                user, '移动端权限装饰器验证', True, '', True, '', f'移动端步骤已跳过，原因: {reason}', request
            )
            
            return JsonResponse({
                'status': 'success',
                'message': '步骤已跳过',
                'step_id': step.id,
                'step_name': step.step_name
            })
            
        except Exception as e:
            print(f"❌ 移动端跳过步骤错误: {str(e)}")
            return JsonResponse({'error': f'操作失败：{str(e)}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MobileConfirmStartStepAPI(View):
    """手机端确认开始步骤API（用户已查看备注）"""
    
    @method_decorator(require_step_permission('start'))
    def post(self, request, step_id):
        """确认开始步骤 - 已通过权限装饰器验证"""
        try:
            # 从装饰器获取已验证的对象
            step = request.current_step
            user = request.current_user
            
            print(f"🔧 移动端确认开始步骤: {step.step_name}, 用户: {user.name}, 权限检查已通过")
            
            # 检查步骤状态
            if step.status != 1:  # 只能开始待开始的步骤
                error_msg = '步骤状态不允许开始'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 检查订单状态
            if step.order.status not in [1, 2]:
                error_msg = '订单状态不允许操作'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 检查是否有前置步骤未完成
            previous_steps = OrderProgress.objects.filter(
                order=step.order,
                step_category=step.step_category,
                step_order__lt=step.step_order
            ).exclude(status__in=[3, 4])  # 只查同类别，排除已完成和已跳过的步骤
            
            if previous_steps.exists():
                incomplete_steps = [s.step_name for s in previous_steps]
                error_msg = f'请先完成前置步骤：{", ".join(incomplete_steps)}'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 直接开始步骤（用户已确认查看备注）
            return self._start_step_directly(step, user, request)
            
        except Exception as e:
            print(f"❌ 移动端确认开始步骤错误: {str(e)}")
            return JsonResponse({'error': f'操作失败：{str(e)}'}, status=500)
    
    def _start_step_directly(self, step, user, request):
        """直接开始步骤的内部方法"""
        try:
            # 使用模型的start_step方法，确保与PC版本逻辑一致
            step.start_step(user)
            
            # 记录成功操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'start',
                user, '移动端权限装饰器验证', True, '', True, '', f'移动端确认开始步骤', request
            )
            
            return JsonResponse({
                'status': 'success',
                'message': '步骤已开始',
                'step_id': step.id,
                'step_name': step.step_name
            })
        except Exception as e:
            error_msg = f'开始步骤失败：{str(e)}'
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'start',
                user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
            )
            return JsonResponse({'error': error_msg}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class MobileCompleteStepAPI(View):
    """手机端完成步骤API"""
    
    @method_decorator(require_step_permission('complete'))
    def post(self, request, step_id):
        """完成步骤 - 已通过权限装饰器验证"""
        try:
            import json
            data = json.loads(request.body) if request.body else {}
            note = data.get('note', '').strip()
            
            # 从装饰器获取已验证的对象
            step = request.current_step
            user = request.current_user
            
            print(f"🔧 移动端完成步骤: {step.step_name}, 用户: {user.name}, 权限检查已通过")
            
            # 检查步骤状态
            if step.status != 2:  # 只能完成进行中的步骤
                error_msg = '步骤状态不允许完成'
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'complete',
                    user, '移动端权限装饰器验证', True, '', False, error_msg, '', request
                )
                return JsonResponse({'error': error_msg}, status=400)
            
            # 更新步骤状态
            step.status = 3  # 已完成
            step.end_time = timezone.now()
            step.updated_time = timezone.now()
            step.confirm_user = user
            
            # 添加备注
            if note:
                step.note = note
            
            step.save()
            
            # 检查是否所有步骤都完成了，如果是则更新订单状态
            remaining_steps = OrderProgress.objects.filter(
                order=step.order,
                status__in=[1, 2]  # 待开始或进行中
            ).count()
            
            if remaining_steps == 0:
                step.order.status = 3  # 已完成
                step.order.save()
            
            # 记录成功操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'complete',
                user, '移动端权限装饰器验证', True, '', True, '', f'移动端步骤已完成，备注: {note}', request
            )
            
            return JsonResponse({
                'status': 'success',
                'message': '步骤已完成',
                'step_id': step.id,
                'step_name': step.step_name,
                'order_completed': remaining_steps == 0
            })
            
        except Exception as e:
            print(f"❌ 移动端完成步骤错误: {str(e)}")
            return JsonResponse({'error': f'操作失败：{str(e)}'}, status=500)


# ======================
# AI助手API视图
# ======================

class AIGenerateDailyReportAPI(View):
    """AI生成日报API"""
    
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 检查权限
            if not is_root_user(request):
                logger.warning(f"AI日报权限不足: {request.session.get('user_id')}")
                return JsonResponse({'error': '权限不足'}, status=403)
            
            logger.info("开始生成AI日报...")
            result = ai_assistant.generate_daily_report()
            logger.info(f"AI日报生成结果: {result.get('status')}")
            return JsonResponse(result)
        except Exception as e:
            import traceback
            logger.error(f"AI日报生成失败: {str(e)}")
            logger.error(f"完整错误信息: {traceback.format_exc()}")
            return JsonResponse({
                'status': 'error',
                'message': f'生成日报失败：{str(e)}'
            })


class AIAnalyzeAnomaliesAPI(View):
    """AI异常分析API"""
    
    def post(self, request):
        # 检查权限
        if not is_root_user(request):
            return JsonResponse({'error': '权限不足'}, status=403)
        
        try:
            result = ai_assistant.analyze_anomalies()
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'异常分析失败：{str(e)}'
            })


class AICheckDeadlinesAPI(View):
    """AI交期检查API"""
    
    def post(self, request):
        # 检查权限
        if not is_root_user(request):
            return JsonResponse({'error': '权限不足'}, status=403)
        
        try:
            result = ai_assistant.check_deadlines()
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'交期检查失败：{str(e)}'
            })


class DeviceDetectionTestAPI(View):
    """设备检测测试API"""
    
    def get(self, request):
        from crm.utils import test_device_detection
        
        # 获取当前请求的检测结果
        current_user_agent = request.META.get('HTTP_USER_AGENT', '')
        current_result = test_device_detection(current_user_agent)
        
        # 测试用例
        test_cases = [
            # 桌面设备
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            # 手机设备
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 10; Huawei P30) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
        ]
        
        test_results = []
        for ua in test_cases:
            test_results.append(test_device_detection(ua))
        
        return JsonResponse({
            'current_request': current_result,
            'test_cases': test_results,
            'device_type': get_device_type(request),
            'user_type': get_user_type(request)
        }, json_dumps_params={'ensure_ascii': False, 'indent': 2})


# ======================
# 对话AI API视图
# ======================

class ConversationStreamAPI(View):
    """流式对话AI API - 使用Server-Sent Events"""
    
    def get(self, request):
        import json
        import logging
        import asyncio
        from django.http import StreamingHttpResponse
        
        logger = logging.getLogger(__name__)
        
        try:
            # 检查权限 - 目前只允许root用户使用
            if not is_root_user(request):
                logger.warning(f"流式对话AI权限不足: {request.session.get('user_id')}")
                return JsonResponse({'error': '权限不足，只有管理员可以使用对话功能'}, status=403)
            
            # 从查询参数获取消息
            user_message = request.GET.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': '消息内容不能为空'}, status=400)
            
            logger.info(f"收到流式对话请求: {user_message[:50]}...")
            
            # 导入对话AI模块
            from crm.conversation_ai import conversation_ai
            
            # 获取用户ID
            user_id = request.session.get('user_id')
            
            def generate_stream():
                """生成SSE数据流 - 使用同步方式避免异步数据库调用问题"""
                try:
                    # 发送开始事件
                    yield "data: " + json.dumps({
                        'type': 'start',
                        'message': '开始处理您的问题...',
                        'timestamp': timezone.now().isoformat()
                    }, ensure_ascii=False) + "\n\n"
                    
                    # 调用同步流式处理（避免异步数据库调用问题）
                    for event_data in conversation_ai.chat_stream(user_message, user_id):
                        # 格式化为SSE格式
                        event_json = json.dumps(event_data, ensure_ascii=False)
                        yield f"data: {event_json}\n\n"
                        
                        # 如果是完成事件，准备结束
                        if event_data.get('type') in ['complete', 'error']:
                            break
                    
                    # 确保发送结束信号
                    yield "event: close\ndata: " + json.dumps({
                        'type': 'end',
                        'message': '流式响应结束'
                    }, ensure_ascii=False) + "\n\n"
                    
                except Exception as e:
                    logger.error(f"流式对话生成错误: {e}")
                    error_event = {
                        'type': 'error',
                        'message': f'抱歉，AI助手遇到了技术问题：{str(e)}',
                        'error': str(e),
                        'timestamp': timezone.now().isoformat()
                    }
                    yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                    yield "event: close\ndata: {}\n\n"
            
            # 创建流式响应
            response = StreamingHttpResponse(
                generate_stream(),
                content_type='text/event-stream; charset=utf-8'
            )
            response['Cache-Control'] = 'no-cache'
            response['Connection'] = 'keep-alive'
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'Cache-Control'
            response['X-Accel-Buffering'] = 'no'  # 禁用nginx缓冲
            
            return response
            
        except Exception as e:
            logger.error(f"流式对话API错误: {e}")
            return JsonResponse({
                'error': '服务器内部错误',
                'message': str(e)
            }, status=500)
    
    def post(self, request):
        """POST方法用于启动流式对话"""
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # 检查权限
            if not is_root_user(request):
                return JsonResponse({'error': '权限不足'}, status=403)
            
            # 解析请求数据
            if not request.body:
                return JsonResponse({'error': '请求数据为空'}, status=400)
            
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': '消息内容不能为空'}, status=400)
            
            # 重定向到GET方法处理SSE
            from urllib.parse import quote
            encoded_message = quote(user_message)
            sse_url = f"/api/conversation/stream/?message={encoded_message}"
            
            return JsonResponse({
                'status': 'redirect',
                'sse_url': sse_url,
                'message': '请使用SSE连接'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': '请求数据格式错误'}, status=400)
        except Exception as e:
            logger.error(f"流式对话POST错误: {e}")
            return JsonResponse({
                'error': '服务器内部错误',
                'message': str(e)
            }, status=500)

class ConversationChatAPI(View):
    """对话AI聊天API"""
    
    def post(self, request):
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # 检查权限 - 目前只允许root用户使用
            if not is_root_user(request):
                logger.warning(f"对话AI权限不足: {request.session.get('user_id')}")
                return JsonResponse({'error': '权限不足，只有管理员可以使用对话功能'}, status=403)
            
            # 解析请求数据
            if not request.body:
                return JsonResponse({'error': '请求数据为空'}, status=400)
            
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': '消息内容不能为空'}, status=400)
            
            logger.info(f"收到用户消息: {user_message[:50]}...")
            
            # 导入对话AI模块
            from crm.conversation_ai import conversation_ai
            from crm.ai_assistant import ai_assistant
            from crm.models import UserInfo
            # 获取用户ID
            user_id = request.session.get('user_id')
            user = UserInfo.objects.filter(id=user_id).first()
            # 查询最近20条记忆，按created_time正序
            memories = ai_assistant.get_memories(user, memory_type='chat', limit=20)
            memories = list(memories)[::-1]  # 反转为正序（最早的在前）
            mcp_messages = []
            for idx, m in enumerate(memories):
                role = 'user' if idx % 2 == 0 else 'AI'
                mcp_messages.append({'role': role, 'content': m.content})
            # 加入本轮用户消息
            mcp_messages.append({'role': 'user', 'content': user_message})
            # 传递给AI
            result = conversation_ai.chat(mcp_messages, user_id)
            logger.info(f"AI回复状态: {result.get('status')}")
            # 写入记忆（用户消息和AI回复）
            print('写入记忆：')
            ai_assistant.save_memory(user, user_message, memory_type='chat')
            if result.get('response'):
                ai_assistant.save_memory(user, result['response'], memory_type='chat')
            if user:
                ai_assistant.save_memory(user, user_message, memory_type='chat')
                if result.get('response'):
                    ai_assistant.save_memory(user, result['response'], memory_type='chat')
            return JsonResponse(result)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': '请求数据格式错误，请发送有效的JSON'}, status=400)
        except Exception as e:
            import traceback
            logger.error(f"对话AI处理失败: {str(e)}")
            logger.error(f"完整错误信息: {traceback.format_exc()}")
            return JsonResponse({
                'status': 'error',
                'response': '抱歉，AI助手遇到了技术问题，请稍后重试。',
                'error': str(e)
            })


class ConversationHistoryAPI(View):
    """对话历史API"""
    
    def get(self, request):
        """获取对话摘要"""
        try:
            # 检查权限
            if not is_root_user(request):
                return JsonResponse({'error': '权限不足'}, status=403)
            
            from crm.conversation_ai import conversation_ai
            
            summary = conversation_ai.get_conversation_summary()
            
            return JsonResponse({
                'status': 'success',
                'summary': summary
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'获取对话历史失败：{str(e)}'
            })
    
    def delete(self, request):
        """清除对话历史"""
        try:
            # 检查权限
            if not is_root_user(request):
                return JsonResponse({'error': '权限不足'}, status=403)
            
            from crm.conversation_ai import conversation_ai
            
            conversation_ai.clear_history()
            
            return JsonResponse({
                'status': 'success',
                'message': '对话历史已清除'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'清除对话历史失败：{str(e)}'
            })


class ConversationTestAPI(View):
    """对话AI测试API"""
    
    def post(self, request):
        """测试对话AI连接"""
        try:
            # 检查权限
            if not is_root_user(request):
                return JsonResponse({'error': '权限不足'}, status=403)
            
            from crm.conversation_ai import conversation_ai
            
            # 测试简单对话
            test_message = "你好，请告诉我当前有多少个订单？"
            result = conversation_ai.chat(test_message)
            
            return JsonResponse({
                'status': 'success',
                'test_message': test_message,
                'ai_response': result.get('response', ''),
                'test_successful': result.get('status') == 'success'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'对话AI测试失败：{str(e)}',
                'test_successful': False
            })

 