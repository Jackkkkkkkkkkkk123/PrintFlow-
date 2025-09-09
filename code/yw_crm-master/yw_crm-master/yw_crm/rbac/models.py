from django.db import models


class Menu(models.Model):
    """
    菜单表
    """
    title = models.CharField(verbose_name='菜单名称', max_length=32, unique=True)
    icon = models.CharField(verbose_name='图标', max_length=128, blank=True, null=True)

    def __str__(self):
        return self.title


class Permission(models.Model):
    """
    权限表
    """
    title = models.CharField(verbose_name='权限标题', max_length=32)
    url = models.CharField(verbose_name='含正则的URL', max_length=128)
    name=models.CharField(verbose_name='url别名',max_length=64,unique=True) #控制权限到按钮
    parent=models.ForeignKey(verbose_name='父权限',to='self',null=True,blank=True,on_delete=models.CASCADE,limit_choices_to={'parent__isnull':True})#构建非菜单权限关系，菜单默认展开
    menu=models.ForeignKey(verbose_name='菜单',to='Menu',null=True,blank=True,on_delete=models.CASCADE)

    def __str__(self):
        return self.title


class WorkflowStepPermissionType(models.Model):
    """
    工作流程步骤权限类型
    定义可以对步骤执行的操作类型
    """
    name = models.CharField(max_length=50, verbose_name='权限类型名称', unique=True)
    description = models.CharField(max_length=200, verbose_name='权限描述')
    
    class Meta:
        verbose_name = '步骤权限类型'
        verbose_name_plural = '步骤权限类型'
    
    def __str__(self):
        return self.name


class WorkflowStepPermission(models.Model):
    """
    工作流程步骤权限表
    细粒度控制用户可以操作哪些具体的工作流程步骤
    """
    # 基本权限信息
    name = models.CharField(max_length=100, verbose_name='权限名称', unique=True)
    description = models.CharField(max_length=200, verbose_name='权限描述', blank=True)
    
    # 工作流程限制
    print_type_choices = (
        ('cover', '封面印刷'),
        ('content', '内文印刷'),
        ('both', '封面+内文'),
        ('all', '所有类型')
    )
    print_type = models.CharField(
        max_length=20, 
        choices=print_type_choices, 
        verbose_name='适用印刷类型',
        default='all'
    )
    
    # 步骤限制（JSON格式存储步骤名称列表）
    allowed_steps = models.TextField(
        verbose_name='允许操作的步骤',
        help_text='JSON格式存储允许操作的步骤名称列表，如["印刷", "覆膜"]',
        blank=True,
        null=True
    )
    
    # 操作类型限制
    permission_types = models.ManyToManyField(
        WorkflowStepPermissionType,
        verbose_name='允许的操作类型',
        help_text='选择用户可以执行的操作，如开始、完成、跳过等'
    )
    
    # 时间限制
    time_restriction_choices = (
        ('none', '无时间限制'),
        ('working_hours', '仅工作时间'),
        ('specific_hours', '指定时间段')
    )
    time_restriction = models.CharField(
        max_length=20,
        choices=time_restriction_choices,
        verbose_name='时间限制',
        default='none'
    )
    
    start_time = models.TimeField(verbose_name='开始时间', null=True, blank=True)
    end_time = models.TimeField(verbose_name='结束时间', null=True, blank=True)
    
    # 其他限制
    max_concurrent_steps = models.IntegerField(
        verbose_name='最大并发步骤数',
        default=0,
        help_text='0表示无限制，大于0表示用户同时最多能操作的步骤数'
    )
    
    require_previous_complete = models.BooleanField(
        verbose_name='要求前置步骤完成',
        default=True,
        help_text='是否要求前面的步骤必须完成才能操作当前步骤'
    )
    
    # 审批要求
    require_approval = models.BooleanField(
        verbose_name='需要审批',
        default=False,
        help_text='某些重要步骤是否需要上级审批'
    )
    
    approver_roles = models.ManyToManyField(
        'Role',
        verbose_name='审批者角色',
        blank=True,
        help_text='有权审批此操作的角色'
    )
    
    # 系统字段
    is_active = models.BooleanField(verbose_name='是否启用', default=True)
    created_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    updated_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '工作流程步骤权限'
        verbose_name_plural = '工作流程步骤权限'
        ordering = ['print_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_print_type_display()})"
    
    def get_allowed_steps_list(self):
        """获取允许操作的步骤列表"""
        if not self.allowed_steps:
            return []
        try:
            import json
            return json.loads(self.allowed_steps)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_allowed_steps_list(self, steps_list):
        """设置允许操作的步骤列表"""
        import json
        self.allowed_steps = json.dumps(steps_list, ensure_ascii=False)

    def can_operate_step(self, step_name, print_type, operation_type):
        """
        检查是否可以操作指定步骤
        
        Args:
            step_name: 步骤名称
            print_type: 印刷类型 ('cover', 'content')
            operation_type: 操作类型 ('start', 'complete', 'skip')
        
        Returns:
            bool: 是否允许操作
        """
        if not self.is_active:
            return False
        
        # 检查印刷类型权限
        if self.print_type != 'all' and self.print_type != print_type:
            return False
        
        # 检查步骤权限
        allowed_steps = self.get_allowed_steps_list()
        if allowed_steps and step_name not in allowed_steps:
            return False
        
        # 检查操作类型权限
        allowed_operations = [pt.name for pt in self.permission_types.all()]
        if operation_type not in allowed_operations:
            return False
        
        # 检查时间限制
        if not self._check_time_restriction():
            return False
        
        return True
    
    def _check_time_restriction(self):
        """检查时间限制"""
        if self.time_restriction == 'none':
            return True
        
        from datetime import datetime
        now = datetime.now().time()
        
        if self.time_restriction == 'working_hours':
            # 工作时间：8:00-18:00
            from datetime import time
            return time(8, 0) <= now <= time(18, 0)
        
        if self.time_restriction == 'specific_hours':
            if self.start_time and self.end_time:
                return self.start_time <= now <= self.end_time
        
        return True


class Role(models.Model):
    """
    角色
    """
    title = models.CharField(verbose_name='角色名称', max_length=32)
    permissions = models.ManyToManyField(verbose_name='拥有的所有权限', to='Permission', blank=True)
    
    # 新增：工作流程步骤权限
    workflow_step_permissions = models.ManyToManyField(
        WorkflowStepPermission,
        verbose_name='工作流程步骤权限',
        blank=True,
        help_text='角色拥有的具体工作流程步骤操作权限'
    )

    def __str__(self):
        return self.title
    
    def can_operate_step(self, step_name, print_type, operation_type):
        """
        检查角色是否可以操作指定步骤
        """
        for perm in self.workflow_step_permissions.filter(is_active=True):
            if perm.can_operate_step(step_name, print_type, operation_type):
                return True
        return False


class UserInfo(models.Model):
    """
    用户表
    """
    username = models.CharField(verbose_name='用户名', max_length=32)
    password = models.CharField(verbose_name='密码', max_length=64)
    email = models.CharField(verbose_name='邮箱', max_length=32)
    roles = models.ManyToManyField(verbose_name='拥有的所有角色', to=Role, blank=True)

    class Meta:
        abstract=True

    def __str__(self):
        return self.username
    
    def can_operate_step(self, step_name, print_type, operation_type):
        """
        检查用户是否可以操作指定步骤
        """
        for role in self.roles.all():
            if role.can_operate_step(step_name, print_type, operation_type):
                return True
        return False


class WorkflowStepOperationLog(models.Model):
    """
    工作流程步骤操作日志
    记录所有的步骤操作，用于审计和分析
    """
    # 操作基本信息
    order_no = models.CharField(max_length=32, verbose_name='订单号')
    step_name = models.CharField(max_length=100, verbose_name='步骤名称')
    print_type = models.CharField(max_length=20, verbose_name='印刷类型')
    
    # 操作详情
    operation_choices = (
        ('start', '开始步骤'),
        ('complete', '完成步骤'),
        ('skip', '跳过步骤'),
        ('approve', '审批操作'),
        ('reject', '拒绝操作')
    )
    operation_type = models.CharField(
        max_length=20,
        choices=operation_choices,
        verbose_name='操作类型'
    )
    
    # 操作者信息
    operator_id = models.IntegerField(verbose_name='操作员ID')
    operator_name = models.CharField(max_length=50, verbose_name='操作员姓名')
    operator_roles = models.TextField(verbose_name='操作员角色', help_text='JSON格式存储')
    
    # 权限验证信息
    permission_used = models.CharField(max_length=100, verbose_name='使用的权限', blank=True)
    permission_check_result = models.BooleanField(verbose_name='权限检查结果')
    permission_check_details = models.TextField(
        verbose_name='权限检查详情',
        blank=True,
        help_text='JSON格式存储权限检查的详细信息'
    )
    
    # 操作结果
    success = models.BooleanField(verbose_name='操作是否成功')
    error_message = models.TextField(verbose_name='错误信息', blank=True)
    note = models.TextField(verbose_name='操作备注', blank=True)
    
    # 时间信息
    operation_time = models.DateTimeField(verbose_name='操作时间', auto_now_add=True)
    ip_address = models.GenericIPAddressField(verbose_name='IP地址', null=True, blank=True)
    user_agent = models.TextField(verbose_name='用户代理', blank=True)
    
    class Meta:
        verbose_name = '步骤操作日志'
        verbose_name_plural = '步骤操作日志'
        ordering = ['-operation_time']
        indexes = [
            models.Index(fields=['order_no', 'operation_time']),
            models.Index(fields=['operator_id', 'operation_time']),
            models.Index(fields=['step_name', 'print_type']),
        ]
    
    def __str__(self):
        return f"{self.order_no} - {self.step_name} - {self.get_operation_type_display()}"
