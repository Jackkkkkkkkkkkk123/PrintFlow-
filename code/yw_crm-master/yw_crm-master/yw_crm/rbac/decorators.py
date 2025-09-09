"""
工作流程步骤权限装饰器和检查工具
"""
import json
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone

from .models import WorkflowStepOperationLog
from crm.models import OrderProgress, UserInfo


def get_client_ip(request):
    """获取客户端IP地址"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_step_operation(order_no, step_name, print_type, operation_type, user, 
                      permission_used='', permission_check_result=True, 
                      permission_check_details='', success=True, 
                      error_message='', note='', request=None):
    """
    记录步骤操作日志
    """
    try:
        # 准备用户角色信息
        user_roles = [role.title for role in user.roles.all()] if hasattr(user, 'roles') else []
        
        # 创建日志记录
        log_data = {
            'order_no': order_no,
            'step_name': step_name,
            'print_type': print_type,
            'operation_type': operation_type,
            'operator_id': user.id,
            'operator_name': getattr(user, 'name', user.username),
            'operator_roles': json.dumps(user_roles, ensure_ascii=False),
            'permission_used': permission_used,
            'permission_check_result': permission_check_result,
            'permission_check_details': permission_check_details,
            'success': success,
            'error_message': error_message,
            'note': note,
        }
        
        if request:
            log_data.update({
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],  # 限制长度
            })
        
        WorkflowStepOperationLog.objects.create(**log_data)
        
    except Exception as e:
        # 日志记录失败不应该影响主要业务流程
        print(f"权限日志记录失败: {str(e)}")


def check_step_permission(user, step, operation_type, request=None):
    """
    检查用户是否有操作指定步骤的权限
    
    Args:
        user: 用户对象
        step: 步骤对象(OrderProgress)
        operation_type: 操作类型 ('start', 'complete', 'skip')
        request: 请求对象（可选，用于日志记录）
    
    Returns:
        tuple: (is_allowed: bool, error_message: str, permission_details: dict)
    """
    # 检查基本参数
    if not user or not step:
        return False, "用户或步骤信息无效", {}
    
    # 获取订单的印刷类型
    print_type = getattr(step.order, 'print_type', 'cover')
    
    # 权限检查详情
    permission_details = {
        'user_id': user.id,
        'user_name': getattr(user, 'name', user.username),
        'step_id': step.id,
        'step_name': step.step_name,
        'print_type': print_type,
        'operation_type': operation_type,
        'check_time': timezone.now().isoformat(),
        'checks_performed': []
    }
    
    try:
        # 1. 检查用户角色
        user_roles = user.roles.all()
        if not user_roles.exists():
            error_msg = "用户未分配任何角色"
            permission_details['checks_performed'].append({
                'check': 'user_roles',
                'result': False,
                'message': error_msg
            })
            log_step_operation(
                step.order.order_no, step.step_name, print_type, operation_type,
                user, '', False, json.dumps(permission_details, ensure_ascii=False),
                False, error_msg, '', request
            )
            return False, error_msg, permission_details
        
        permission_details['user_roles'] = [role.title for role in user_roles]
        permission_details['checks_performed'].append({
            'check': 'user_roles',
            'result': True,
            'message': f"用户拥有 {len(user_roles)} 个角色"
        })
        
        # 2. 检查是否有任何角色拥有此步骤的操作权限
        has_permission = False
        permission_used = ""
        
        for role in user_roles:
            if role.can_operate_step(step.step_name, print_type, operation_type):
                has_permission = True
                permission_used = f"角色[{role.title}]"
                break
        
        if not has_permission:
            error_msg = f"无权限执行操作：{operation_type} on {step.step_name} ({print_type})"
            permission_details['checks_performed'].append({
                'check': 'step_permission',
                'result': False,
                'message': error_msg
            })
            log_step_operation(
                step.order.order_no, step.step_name, print_type, operation_type,
                user, permission_used, False, json.dumps(permission_details, ensure_ascii=False),
                False, error_msg, '', request
            )
            return False, error_msg, permission_details
        
        permission_details['checks_performed'].append({
            'check': 'step_permission',
            'result': True,
            'message': f"通过 {permission_used} 获得权限"
        })
        
        # 3. 检查并发步骤限制（如果配置了的话）
        # TODO: 实现并发步骤检查
        
        # 4. 检查前置步骤完成情况（如果权限要求的话）
        # TODO: 根据权限配置检查前置步骤
        
        # 权限检查通过
        log_step_operation(
            step.order.order_no, step.step_name, print_type, operation_type,
            user, permission_used, True, json.dumps(permission_details, ensure_ascii=False),
            True, '', '', request
        )
        
        return True, "", permission_details
        
    except Exception as e:
        error_msg = f"权限检查异常: {str(e)}"
        permission_details['checks_performed'].append({
            'check': 'exception',
            'result': False,
            'message': error_msg
        })
        log_step_operation(
            step.order.order_no, step.step_name, print_type, operation_type,
            user, '', False, json.dumps(permission_details, ensure_ascii=False),
            False, error_msg, '', request
        )
        return False, error_msg, permission_details


def require_step_permission(operation_type):
    """
    装饰器：要求用户拥有特定步骤操作权限
    
    Args:
        operation_type: 操作类型 ('start', 'complete', 'skip')
    
    Usage:
        @require_step_permission('start')
        def start_step_view(request, step_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, step_id, *args, **kwargs):
            try:
                # 获取步骤对象
                step = get_object_or_404(OrderProgress, id=step_id)
                
                # 获取用户
                user_id = request.session.get('user_id')
                if not user_id:
                    return JsonResponse({
                        'status': False, 
                        'message': '用户未登录，请重新登录',
                        'error_code': 'NOT_LOGGED_IN'
                    })
                
                user = UserInfo.objects.filter(id=user_id).first()
                if not user:
                    return JsonResponse({
                        'status': False, 
                        'message': '用户信息不存在，请重新登录',
                        'error_code': 'USER_NOT_FOUND'
                    })
                
                # 检查权限
                is_allowed, error_message, permission_details = check_step_permission(
                    user, step, operation_type, request
                )
                
                if not is_allowed:
                    return JsonResponse({
                        'status': False,
                        'message': error_message,
                        'error_code': 'PERMISSION_DENIED',
                        'permission_details': permission_details if settings.DEBUG else {}
                    })
                
                # 将权限检查结果添加到request中，供视图函数使用
                request.permission_check_result = permission_details
                request.current_user = user
                request.current_step = step
                
                # 调用原始视图函数
                return view_func(request, step_id, *args, **kwargs)
                
            except Exception as e:
                return JsonResponse({
                    'status': False,
                    'message': f'权限检查失败: {str(e)}',
                    'error_code': 'PERMISSION_CHECK_ERROR'
                })
        
        return _wrapped_view
    return decorator


def check_user_role_permissions(user, role_names=None):
    """
    检查用户是否拥有指定角色
    
    Args:
        user: 用户对象
        role_names: 角色名称列表，None表示只要有角色即可
    
    Returns:
        bool: 是否拥有指定角色
    """
    if not user:
        return False
    
    user_roles = user.roles.all()
    if not user_roles.exists():
        return False
    
    if role_names is None:
        return True
    
    user_role_names = [role.title for role in user_roles]
    return any(role_name in user_role_names for role_name in role_names)


def require_role(role_names):
    """
    装饰器：要求用户拥有指定角色
    
    Args:
        role_names: 角色名称列表或单个角色名称
    
    Usage:
        @require_role(['老板', '办公室'])
        def admin_view(request):
            ...
        
        @require_role('操作员')
        def operator_view(request):
            ...
    """
    if isinstance(role_names, str):
        role_names = [role_names]
    
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                # 获取用户
                user_id = request.session.get('user_id')
                if not user_id:
                    return JsonResponse({
                        'status': False, 
                        'message': '用户未登录，请重新登录',
                        'error_code': 'NOT_LOGGED_IN'
                    })
                
                user = UserInfo.objects.filter(id=user_id).first()
                if not user:
                    return JsonResponse({
                        'status': False, 
                        'message': '用户信息不存在，请重新登录',
                        'error_code': 'USER_NOT_FOUND'
                    })
                
                # 检查角色权限
                if not check_user_role_permissions(user, role_names):
                    return JsonResponse({
                        'status': False,
                        'message': f'需要以下角色之一: {", ".join(role_names)}',
                        'error_code': 'ROLE_REQUIRED'
                    })
                
                # 将用户添加到request中
                request.current_user = user
                
                # 调用原始视图函数
                return view_func(request, *args, **kwargs)
                
            except Exception as e:
                return JsonResponse({
                    'status': False,
                    'message': f'角色检查失败: {str(e)}',
                    'error_code': 'ROLE_CHECK_ERROR'
                })
        
        return _wrapped_view
    return decorator 