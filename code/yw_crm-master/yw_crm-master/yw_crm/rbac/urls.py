"""
RBAC权限管理URL配置
"""
from django.urls import path
from rbac.views.menus import MenuView, MenuAddView, MenuEditView, MenuDelView
from rbac.views.roles import RoleView, RoleAddView, RoleEditView, RoleDelView
from rbac.views.permissions import PermissionAddView, PermissionEditView, PermissionDelView
from rbac.views import distribute_permissions
from rbac.views.step_permissions import (
    StepPermissionListView,
    StepPermissionCreateView, 
    StepPermissionEditView,
    RoleStepPermissionView,
    StepPermissionLogView,
    StepPermissionApiView
)

app_name = 'rbac'

urlpatterns = [
    # 原有的权限管理URL - 菜单管理
    path('menus/list/', MenuView.as_view(), name='menus_list'),
    path('menus/add/', MenuAddView.as_view(), name='menus_add'),
    path('menus/edit/<int:mid>/', MenuEditView.as_view(), name='menus_edit'),
    path('menus/del/<int:mid>/', MenuDelView.as_view(), name='menus_del'),
    
    # 权限管理
    path('permissions/add/', PermissionAddView.as_view(), name='permissions_add'),
    path('permissions/edit/<int:pid>/', PermissionEditView.as_view(), name='permissions_edit'),
    path('permissions/del/<int:pid>/', PermissionDelView.as_view(), name='permissions_del'),
    
    # 角色管理
    path('roles/list/', RoleView.as_view(), name='roles_list'),
    path('roles/add/', RoleAddView.as_view(), name='roles_add'),
    path('roles/edit/<int:rid>/', RoleEditView.as_view(), name='roles_edit'),
    path('roles/del/<int:rid>/', RoleDelView.as_view(), name='roles_del'),
    
    # 权限分配
    path('distribute/permissions/', distribute_permissions.distribute_permissions, name='distribute_permissions'),
    
    # 新增：工作流程步骤权限管理URL
    path('step-permission/', StepPermissionListView.as_view(), name='step_permission_list'),
    path('step-permission/create/', StepPermissionCreateView.as_view(), name='step_permission_create'),
    path('step-permission/edit/<int:permission_id>/', StepPermissionEditView.as_view(), name='step_permission_edit'),
    path('step-permission/delete/<int:permission_id>/', StepPermissionApiView.as_view(), name='step_permission_delete'),
    
    # 角色步骤权限分配
    path('role-step-permission/', RoleStepPermissionView.as_view(), name='role_step_permission'),
    
    # 步骤权限操作日志
    path('step-permission/logs/', StepPermissionLogView.as_view(), name='step_permission_logs'),
    
    # API接口
    path('api/step-permission/', StepPermissionApiView.as_view(), name='step_permission_api'),
]
