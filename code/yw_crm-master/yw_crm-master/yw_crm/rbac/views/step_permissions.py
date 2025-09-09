"""
工作流程步骤权限管理视图
"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from django.utils.module_loading import import_string

from rbac.models import (
    WorkflowStepPermission, 
    WorkflowStepPermissionType, 
    WorkflowStepOperationLog,
    Role
)


class StepPermissionListView(View):
    """步骤权限列表页面"""
    
    def get(self, request):
        # 获取所有步骤权限
        permissions = WorkflowStepPermission.objects.all().order_by('print_type', 'name')
        permission_types = WorkflowStepPermissionType.objects.all()
        
        # 分组显示
        grouped_permissions = {
            'cover': [],
            'content': [],
            'both': [],
            'all': []
        }
        
        for permission in permissions:
            grouped_permissions[permission.print_type].append(permission)
        
        context = {
            'grouped_permissions': grouped_permissions,
            'permission_types': permission_types,
            'print_type_choices': WorkflowStepPermission.print_type_choices
        }
        
        return render(request, 'rbac/step_permission_list.html', context)


class StepPermissionCreateView(View):
    """创建步骤权限"""
    
    def get(self, request):
        permission_types = WorkflowStepPermissionType.objects.all()
        roles = Role.objects.all()
        
        # 预定义的步骤选项
        step_options = {
            'cover': ['印刷', '覆膜', '烫金', '压痕', '压纹', '模切', '击凸', '过油', '外调'],
            'content': ['调图', 'CTP', '切纸', '印刷', '折页', '锁线', '胶包', '马订', '勒口', '夹卡片', '配本(塑封)', '打包', '送货']
        }
        
        context = {
            'permission_types': permission_types,
            'roles': roles,
            'step_options': step_options,
            'print_type_choices': WorkflowStepPermission.print_type_choices,
            'time_restriction_choices': WorkflowStepPermission.time_restriction_choices
        }
        
        return render(request, 'rbac/step_permission_form.html', context)
    
    def post(self, request):
        try:
            with transaction.atomic():
                # 基本信息
                permission = WorkflowStepPermission.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description', ''),
                    print_type=request.POST.get('print_type', 'all'),
                    time_restriction=request.POST.get('time_restriction', 'none'),
                    max_concurrent_steps=int(request.POST.get('max_concurrent_steps', 0)),
                    require_previous_complete=request.POST.get('require_previous_complete') == 'on',
                    require_approval=request.POST.get('require_approval') == 'on'
                )
                
                # 时间限制
                if permission.time_restriction == 'specific_hours':
                    start_time = request.POST.get('start_time')
                    end_time = request.POST.get('end_time')
                    if start_time:
                        permission.start_time = start_time
                    if end_time:
                        permission.end_time = end_time
                
                # 允许的步骤
                selected_steps = request.POST.getlist('allowed_steps')
                if selected_steps:
                    permission.set_allowed_steps_list(selected_steps)
                
                permission.save()
                
                # 权限类型
                permission_types = request.POST.getlist('permission_types')
                if permission_types:
                    permission.permission_types.set(permission_types)
                
                # 审批者角色
                approver_roles = request.POST.getlist('approver_roles')
                if approver_roles:
                    permission.approver_roles.set(approver_roles)
                
                messages.success(request, f'步骤权限 "{permission.name}" 创建成功')
                return redirect('rbac:step_permission_list')
                
        except Exception as e:
            messages.error(request, f'创建失败：{str(e)}')
            return self.get(request)


class StepPermissionEditView(View):
    """编辑步骤权限"""
    
    def get(self, request, permission_id):
        permission = get_object_or_404(WorkflowStepPermission, id=permission_id)
        permission_types = WorkflowStepPermissionType.objects.all()
        roles = Role.objects.all()
        
        # 预定义的步骤选项
        step_options = {
            'cover': ['印刷', '覆膜', '烫金', '压痕', '压纹', '模切', '击凸', '过油', '外调'],
            'content': ['调图', 'CTP', '切纸', '印刷', '折页', '锁线', '胶包', '马订', '勒口', '夹卡片', '配本(塑封)', '打包', '送货']
        }
        
        context = {
            'permission': permission,
            'permission_types': permission_types,
            'roles': roles,
            'step_options': step_options,
            'selected_steps': permission.get_allowed_steps_list(),
            'selected_permission_types': [pt.id for pt in permission.permission_types.all()],
            'selected_approver_roles': [role.id for role in permission.approver_roles.all()],
            'print_type_choices': WorkflowStepPermission.print_type_choices,
            'time_restriction_choices': WorkflowStepPermission.time_restriction_choices
        }
        
        return render(request, 'rbac/step_permission_form.html', context)
    
    def post(self, request, permission_id):
        permission = get_object_or_404(WorkflowStepPermission, id=permission_id)
        
        try:
            with transaction.atomic():
                # 更新基本信息
                permission.name = request.POST.get('name')
                permission.description = request.POST.get('description', '')
                permission.print_type = request.POST.get('print_type', 'all')
                permission.time_restriction = request.POST.get('time_restriction', 'none')
                permission.max_concurrent_steps = int(request.POST.get('max_concurrent_steps', 0))
                permission.require_previous_complete = request.POST.get('require_previous_complete') == 'on'
                permission.require_approval = request.POST.get('require_approval') == 'on'
                permission.is_active = request.POST.get('is_active') == 'on'
                
                # 时间限制
                if permission.time_restriction == 'specific_hours':
                    start_time = request.POST.get('start_time')
                    end_time = request.POST.get('end_time')
                    permission.start_time = start_time if start_time else None
                    permission.end_time = end_time if end_time else None
                else:
                    permission.start_time = None
                    permission.end_time = None
                
                # 允许的步骤
                selected_steps = request.POST.getlist('allowed_steps')
                permission.set_allowed_steps_list(selected_steps)
                
                permission.save()
                
                # 权限类型
                permission_types = request.POST.getlist('permission_types')
                permission.permission_types.set(permission_types)
                
                # 审批者角色
                approver_roles = request.POST.getlist('approver_roles')
                permission.approver_roles.set(approver_roles)
                
                messages.success(request, f'步骤权限 "{permission.name}" 更新成功')
                return redirect('rbac:step_permission_list')
                
        except Exception as e:
            messages.error(request, f'更新失败：{str(e)}')
            return self.get(request, permission_id)


class RoleStepPermissionView(View):
    """角色步骤权限分配"""
    
    def get(self, request):
        # 获取所有角色和步骤权限
        roles = Role.objects.all()
        step_permissions = WorkflowStepPermission.objects.filter(is_active=True).order_by('print_type', 'name')
        
        # 分组权限
        grouped_permissions = {
            'cover': [],
            'content': [],
            'both': [],
            'all': []
        }
        
        for permission in step_permissions:
            grouped_permissions[permission.print_type].append(permission)
        
        # 获取选中的角色和权限信息
        selected_role_id = request.GET.get('role_id')
        selected_role = None
        if selected_role_id:
            selected_role = Role.objects.filter(id=selected_role_id).first()
        
        context = {
            'roles': roles,
            'grouped_permissions': grouped_permissions,
            'selected_role': selected_role,
            'selected_role_permissions': [p.id for p in selected_role.workflow_step_permissions.all()] if selected_role else []
        }
        
        return render(request, 'rbac/role_step_permission.html', context)
    
    def post(self, request):
        role_id = request.POST.get('role_id')
        if not role_id:
            messages.error(request, '请选择角色')
            return redirect('rbac:role_step_permission')
        
        role = get_object_or_404(Role, id=role_id)
        
        try:
            # 获取选中的权限
            selected_permissions = request.POST.getlist('step_permissions')
            
            # 更新角色的步骤权限
            role.workflow_step_permissions.set(selected_permissions)
            
            messages.success(request, f'角色 "{role.title}" 的步骤权限更新成功')
            
        except Exception as e:
            messages.error(request, f'权限分配失败：{str(e)}')
        
        return redirect(f"{request.path}?role_id={role_id}")


class StepPermissionLogView(View):
    """步骤权限操作日志"""
    
    def get(self, request):
        # 获取查询参数
        order_no = request.GET.get('order_no', '')
        operator_name = request.GET.get('operator_name', '')
        operation_type = request.GET.get('operation_type', '')
        step_name = request.GET.get('step_name', '')
        
        # 构建查询
        logs = WorkflowStepOperationLog.objects.all()
        
        if order_no:
            logs = logs.filter(order_no__icontains=order_no)
        if operator_name:
            logs = logs.filter(operator_name__icontains=operator_name)
        if operation_type:
            logs = logs.filter(operation_type=operation_type)
        if step_name:
            logs = logs.filter(step_name__icontains=step_name)
        
        # 分页
        from django.core.paginator import Paginator
        paginator = Paginator(logs, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'operation_choices': WorkflowStepOperationLog.operation_choices,
            'query_params': {
                'order_no': order_no,
                'operator_name': operator_name,
                'operation_type': operation_type,
                'step_name': step_name,
            }
        }
        
        return render(request, 'rbac/step_permission_log.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class StepPermissionApiView(View):
    """步骤权限API接口"""
    
    def post(self, request):
        """批量操作API"""
        action = request.POST.get('action')
        permission_ids = request.POST.getlist('permission_ids')
        
        if not action or not permission_ids:
            return JsonResponse({'status': False, 'message': '参数不完整'})
        
        try:
            with transaction.atomic():
                permissions = WorkflowStepPermission.objects.filter(id__in=permission_ids)
                
                if action == 'activate':
                    permissions.update(is_active=True)
                    message = f'成功激活 {len(permission_ids)} 个权限'
                elif action == 'deactivate':
                    permissions.update(is_active=False)
                    message = f'成功停用 {len(permission_ids)} 个权限'
                elif action == 'delete':
                    permissions.delete()
                    message = f'成功删除 {len(permission_ids)} 个权限'
                else:
                    return JsonResponse({'status': False, 'message': '未知操作'})
                
                return JsonResponse({'status': True, 'message': message})
                
        except Exception as e:
            return JsonResponse({'status': False, 'message': f'操作失败：{str(e)}'})
    
    def get(self, request):
        """获取步骤选项API"""
        print_type = request.GET.get('print_type', 'cover')
        
        step_options = {
            'cover': ['印刷', '覆膜', '烫金', '压痕', '压纹', '模切', '击凸', '过油', '外调'],
            'content': ['调图', 'CTP', '切纸', '印刷', '折页', '锁线', '胶包', '马订', '勒口', '夹卡片', '配本(塑封)', '打包', '送货'],
            'both': ['印刷', '覆膜', '烫金', '压痕', '压纹', '模切', '击凸', '过油', '外调', '调图', 'CTP', '切纸', '折页', '锁线', '胶包', '马订', '勒口', '夹卡片', '配本(塑封)', '打包', '送货'],
            'all': ['印刷', '覆膜', '烫金', '压痕', '压纹', '模切', '击凸', '过油', '外调', '调图', 'CTP', '切纸', '折页', '锁线', '胶包', '马订', '勒口', '夹卡片', '配本(塑封)', '打包', '送货']
        }
        
        return JsonResponse({
            'status': True,
            'steps': step_options.get(print_type, [])
        }) 