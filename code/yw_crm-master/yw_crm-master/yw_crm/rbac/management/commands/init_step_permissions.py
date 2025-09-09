"""
初始化工作流程步骤权限系统基础数据的管理命令
运行方式: python manage.py init_step_permissions
"""
import json
from django.core.management.base import BaseCommand
from rbac.models import (
    WorkflowStepPermissionType, 
    WorkflowStepPermission, 
    Role
)


class Command(BaseCommand):
    help = '初始化工作流程步骤权限系统的基础数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新初始化，删除现有数据',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化工作流程步骤权限系统...'))
        
        if options['force']:
            self.stdout.write(self.style.WARNING('删除现有权限数据...'))
            WorkflowStepPermission.objects.all().delete()
            WorkflowStepPermissionType.objects.all().delete()
        
        # 1. 创建权限类型
        self.stdout.write('创建权限类型...')
        permission_types = [
            {'name': 'start', 'description': '开始步骤'},
            {'name': 'complete', 'description': '完成步骤'},
            {'name': 'skip', 'description': '跳过步骤'},
            {'name': 'view', 'description': '查看步骤'},
            {'name': 'edit_note', 'description': '编辑备注'},
            {'name': 'approve', 'description': '审批步骤'},
        ]
        
        created_types = {}
        for type_data in permission_types:
            perm_type, created = WorkflowStepPermissionType.objects.get_or_create(
                name=type_data['name'],
                defaults={'description': type_data['description']}
            )
            created_types[type_data['name']] = perm_type
            if created:
                self.stdout.write(f"  ✓ 创建权限类型: {perm_type.name}")
            else:
                self.stdout.write(f"  - 权限类型已存在: {perm_type.name}")
        
        # 2. 创建预定义的步骤权限
        self.stdout.write('创建预定义步骤权限...')
        predefined_permissions = [
            {
                'name': '全权限',
                'description': '可以操作所有工作流程的所有步骤',
                'print_type': 'all',
                'allowed_steps': '[]',  # 空数组表示所有步骤
                'permission_types': ['start', 'complete', 'skip', 'view', 'edit_note', 'approve']
            },
            {
                'name': '印刷专员权限',
                'description': '只能操作印刷相关步骤',
                'print_type': 'all',
                'allowed_steps': '["印刷"]',
                'permission_types': ['start', 'complete', 'view', 'edit_note']
            },
            {
                'name': '封面印刷权限',
                'description': '可以操作封面印刷的所有步骤',
                'print_type': 'cover',
                'allowed_steps': '[]',
                'permission_types': ['start', 'complete', 'skip', 'view', 'edit_note']
            },
            {
                'name': '封面后处理权限',
                'description': '只能操作封面印刷的后处理步骤',
                'print_type': 'cover',
                'allowed_steps': '["覆膜", "烫金", "压痕", "压纹", "模切", "击凸", "过油"]',
                'permission_types': ['start', 'complete', 'skip', 'view', 'edit_note']
            },
            {
                'name': '内文印刷权限',
                'description': '可以操作内文印刷的所有步骤',
                'print_type': 'content',
                'allowed_steps': '[]',
                'permission_types': ['start', 'complete', 'skip', 'view', 'edit_note']
            },
            {
                'name': '内文装订权限',
                'description': '只能操作内文装订相关步骤',
                'print_type': 'content',
                'allowed_steps': '["折页", "锁线", "胶包", "马订", "勒口", "夹卡片"]',
                'permission_types': ['start', 'complete', 'view', 'edit_note']
            },
            {
                'name': '配送权限',
                'description': '只能操作配本打包和送货步骤',
                'print_type': 'all',
                'allowed_steps': '["配本(塑封)", "打包", "送货", "外调"]',
                'permission_types': ['start', 'complete', 'view', 'edit_note']
            },
            {
                'name': '质检权限',
                'description': '可以查看所有步骤，审批关键步骤',
                'print_type': 'all',
                'allowed_steps': '[]',
                'permission_types': ['view', 'approve']
            },
            {
                'name': '主管权限',
                'description': '可以操作和审批所有步骤',
                'print_type': 'all',
                'allowed_steps': '[]',
                'permission_types': ['start', 'complete', 'skip', 'view', 'edit_note', 'approve']
            },
        ]
        
        for perm_data in predefined_permissions:
            permission, created = WorkflowStepPermission.objects.get_or_create(
                name=perm_data['name'],
                defaults={
                    'description': perm_data['description'],
                    'print_type': perm_data['print_type'],
                    'allowed_steps': perm_data['allowed_steps'],
                }
            )
            
            # 设置权限类型
            permission_type_objs = [
                created_types[ptype] for ptype in perm_data['permission_types']
                if ptype in created_types
            ]
            permission.permission_types.set(permission_type_objs)
            
            if created:
                self.stdout.write(f"  ✓ 创建步骤权限: {permission.name}")
            else:
                self.stdout.write(f"  - 步骤权限已存在: {permission.name}")
        
        # 3. 为现有角色分配默认权限
        self.stdout.write('为现有角色分配默认权限...')
        
        # 角色权限映射
        role_permission_mapping = {
            '系统管理员': '全权限',
            '主管': '主管权限',
            '印刷员': '印刷专员权限',
            '质检员': '质检权限',
            '配送员': '配送权限',
        }
        
        for role_name, permission_name in role_permission_mapping.items():
            try:
                role = Role.objects.get(title=role_name)
                permission = WorkflowStepPermission.objects.get(name=permission_name)
                role.workflow_step_permissions.add(permission)
                self.stdout.write(f"  ✓ 为角色 '{role_name}' 分配权限 '{permission_name}'")
            except Role.DoesNotExist:
                self.stdout.write(f"  - 角色 '{role_name}' 不存在，跳过")
            except WorkflowStepPermission.DoesNotExist:
                self.stdout.write(f"  - 权限 '{permission_name}' 不存在，跳过")
        
        # 4. 输出权限配置总结
        self.stdout.write('\n权限配置总结:')
        self.stdout.write(f"权限类型数量: {WorkflowStepPermissionType.objects.count()}")
        self.stdout.write(f"步骤权限数量: {WorkflowStepPermission.objects.count()}")
        
        self.stdout.write('\n可用的步骤权限:')
        for permission in WorkflowStepPermission.objects.all():
            allowed_steps = json.loads(permission.allowed_steps) if permission.allowed_steps else []
            if not allowed_steps:
                step_desc = "所有步骤"
            else:
                step_desc = ", ".join(allowed_steps)
            
            perm_types = [pt.name for pt in permission.permission_types.all()]
            self.stdout.write(
                f"  - {permission.name} ({permission.get_print_type_display()}): "
                f"步骤[{step_desc}], 操作[{', '.join(perm_types)}]"
            )
        
        self.stdout.write('\n✅ 工作流程步骤权限系统初始化完成！')
        
        self.stdout.write('\n🔧 后续操作指南:')
        self.stdout.write('1. 运行数据库迁移: python manage.py migrate')
        self.stdout.write('2. 访问管理界面配置具体的权限分配')
        self.stdout.write('3. 运行测试脚本验证权限功能: python test_step_permissions.py') 