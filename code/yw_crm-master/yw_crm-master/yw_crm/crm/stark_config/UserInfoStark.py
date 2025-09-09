from stark.service.base_stark import BaseStark,BaseModelForm,Option,BaseForm
from django import forms
from crm import models
from django.forms import ValidationError
from django.shortcuts import HttpResponse,render,redirect
from django.urls import re_path
from django.utils.safestring import mark_safe
# 新增导入
from rbac.models import Role, WorkflowStepPermission
from django.contrib import messages


class UserInfoAddModelForm(BaseModelForm):
    confirm_password = forms.CharField(label='确认密码', widget=forms.PasswordInput)
    
    # 添加角色选择字段
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='分配角色',
        help_text='选择用户的角色，角色决定了用户的权限'
    )

    class Meta:
        model = models.UserInfo
        fields='__all__'

    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        
        # 美化表单字段
        self.fields['name'].widget.attrs.update({
            'placeholder': '请输入真实姓名',
            'class': 'form-control'
        })
        self.fields['username'].widget.attrs.update({
            'placeholder': '请输入用户名',
            'class': 'form-control'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': '请输入邮箱地址',
            'class': 'form-control'
        })
        self.fields['phone'].widget.attrs.update({
            'placeholder': '请输入手机号',
            'class': 'form-control'
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': '请输入密码',
            'class': 'form-control'
        })
        self.fields['confirm_password'].widget.attrs.update({
            'placeholder': '请确认密码',
            'class': 'form-control'
        })

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password != confirm_password:
            raise ValidationError('密码输入不一致')
        return confirm_password
    
    def clean_roles(self):
        """验证角色选择的合理性"""
        roles = self.cleaned_data.get('roles', [])
        
        # 检查角色冲突
        role_names = [role.title for role in roles]
        
        # 检查是否有冲突的角色组合
        if '唐师' in role_names and '邓师' in role_names:
            raise ValidationError('唐师和邓师角色不能同时分配给一个用户')
        
        return roles
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # 设置用户角色
            user.roles.set(self.cleaned_data['roles'])
        return user

class UserInfoChangeModelForm(BaseModelForm):
    """增强的用户编辑表单，包含权限设置"""
    
    # 添加角色选择字段
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='分配角色',
        help_text='选择用户的角色，角色决定了用户的权限'
    )
    
    class Meta:
        model = models.UserInfo
        fields = '__all__'

    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        
        # 设置角色字段的初始值
        if self.instance and self.instance.pk:
            self.fields['roles'].initial = self.instance.roles.all()
            
        # 美化表单字段
        self.fields['name'].widget.attrs.update({
            'placeholder': '请输入真实姓名',
            'class': 'form-control'
        })
        self.fields['username'].widget.attrs.update({
            'placeholder': '请输入用户名',
            'class': 'form-control'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': '请输入邮箱地址',
            'class': 'form-control'
        })
        self.fields['phone'].widget.attrs.update({
            'placeholder': '请输入手机号',
            'class': 'form-control'
        })

    def clean(self):
        password = self.cleaned_data['password']
        self.cleaned_data['password'] = password
        return self.cleaned_data
    
    def clean_roles(self):
        """验证角色选择的合理性"""
        roles = self.cleaned_data.get('roles', [])
        
        # 检查角色冲突
        role_names = [role.title for role in roles]
        
        # 检查是否有冲突的角色组合
        if '唐师' in role_names and '邓师' in role_names:
            raise ValidationError('唐师和邓师角色不能同时分配给一个用户')
        
        return roles
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # 更新用户角色
            user.roles.set(self.cleaned_data['roles'])
        return user

class ResetPasswordForm(BaseForm):
    password = forms.CharField(label='密码', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='确认密码', widget=forms.PasswordInput)

    def clean_confirm_password(self):
        password = self.cleaned_data['password']
        confirm_password = self.cleaned_data['confirm_password']
        if password != confirm_password:
            raise ValidationError('密码输入不一致')
        return confirm_password

    def clean(self):
        password = self.cleaned_data['password']
        self.cleaned_data['password'] = password
        return self.cleaned_data


class UserInfoStark(BaseStark):

    def display_reset_pwd(self, row=None, header_body=False,*args,**kwargs):
        if not header_body:
            return '重置密码'
        reset_url = self.reverse_common_url\
            (self.get_url_name('reset_pwd'), pk=row.pk)
        return mark_safe("<a href='%s'>重置密码</a>" % reset_url)

    def display_user_roles(self, row=None, header_body=False, *args, **kwargs):
        """显示用户角色"""
        if not header_body:
            return '角色权限'
        
        roles = row.roles.all()
        if not roles.exists():
            return mark_safe("<span style='color: #999; font-style: italic;'>未分配角色</span>")
        
        role_names = []
        for role in roles:
            role_names.append(f"<span class='label label-primary'>{role.title}</span>")
        
        return mark_safe(" ".join(role_names))
    
    def display_user_permissions(self, row=None, header_body=False, *args, **kwargs):
        """显示用户权限摘要"""
        if not header_body:
            return '权限摘要'
        
        roles = row.roles.all()
        if not roles.exists():
            return mark_safe("<span style='color: #999;'>无权限</span>")
        
        # 统计权限
        all_permissions = set()
        step_permissions = set()
        
        for role in roles:
            # 基础权限
            perms = role.permissions.all()
            all_permissions.update([p.title for p in perms])
            
            # 工序权限
            step_perms = role.workflow_step_permissions.all()
            for sp in step_perms:
                steps = sp.get_allowed_steps_list()
                if steps:
                    step_permissions.update(steps)
                else:
                    step_permissions.add("所有工序")
        
        permission_summary = []
        if all_permissions:
            permission_summary.append(f"<small>基础权限: {len(all_permissions)}个</small>")
        if step_permissions:
            if "所有工序" in step_permissions:
                permission_summary.append(f"<small>工序权限: 所有工序</small>")
            else:
                permission_summary.append(f"<small>工序权限: {len(step_permissions)}个</small>")
        
        if not permission_summary:
            return mark_safe("<span style='color: #999;'>无权限</span>")
        
        return mark_safe("<br>".join(permission_summary))
    
    def display_permission_check(self, row=None, header_body=False, *args, **kwargs):
        """权限检查操作"""
        if not header_body:
            return '权限检查'
        
        check_url = self.reverse_common_url(
            self.get_url_name('permission_check'), pk=row.pk)
        return mark_safe(f"<a href='{check_url}' class='btn btn-xs btn-info'>检查权限</a>")

    # 增强的列表显示字段
    list_display = ['username', 'name', 'gender', 'phone', 'email', 'department', 
                   display_user_roles, display_user_permissions, display_permission_check, display_reset_pwd]

    search_list = ['username', 'name']

    list_filter = [
        Option(field='department'),
        Option(field='gender', text_func=lambda x: x[1], is_choice=True),
    ]
    
    def get_add_btn(self, request, *args, **kwargs):
        """重写获取添加按钮的方法，添加批量权限检查按钮"""
        add_btn = super().get_add_btn(request, *args, **kwargs)
        
        batch_check_url = self.reverse_common_url(
            self.get_url_name('batch_permission_check'))
        
        batch_check_btn = mark_safe(
            f'<a href="{batch_check_url}" class="btn btn-info" style="margin-left: 10px;">'
            f'<i class="fa fa-search"></i> 批量权限检查</a>'
        )
        
        return add_btn + batch_check_btn

    def get_model_form_class(self, is_add, pk, request, *args,**kwargs):
        if is_add:
            return UserInfoAddModelForm
        return UserInfoChangeModelForm

    def reset_password(self, request, pk):
        """
        重置密码的视图函数
        :param request:
        :param pk:
        :return:
        """
        userinfo_object = models.UserInfo.objects.filter(id=pk).first()
        if not userinfo_object:
            return HttpResponse('用户不存在，无法进行密码重置！')
        if request.method == 'GET':
            form = ResetPasswordForm(request)
            return render(request, 'stark/change.html', {'form': form})
        form = ResetPasswordForm(data=request.POST,request=request)
        if form.is_valid():
            userinfo_object.password = form.cleaned_data['password']
            userinfo_object.save() #赋值后再进行保存
            return redirect(self.reverse_changelist_url())
        return render(request, 'stark/change.html', {'form': form})

    def permission_check(self, request, pk):
        """
        权限检查视图函数
        :param request:
        :param pk:
        :return:
        """
        userinfo_object = models.UserInfo.objects.filter(id=pk).first()
        if not userinfo_object:
            return HttpResponse('用户不存在！')
        
        # 获取用户权限详情
        context = {
            'user': userinfo_object,
            'roles': userinfo_object.roles.all(),
            'all_roles': Role.objects.all(),
        }
        
        # 分析权限
        basic_permissions = []
        step_permissions = []
        permission_issues = []
        
        for role in userinfo_object.roles.all():
            # 基础权限
            perms = role.permissions.all()
            for perm in perms:
                basic_permissions.append({
                    'role': role.title,
                    'permission': perm.title,
                    'url': perm.url,
                })
            
            # 工序权限
            step_perms = role.workflow_step_permissions.all()
            for sp in step_perms:
                steps = sp.get_allowed_steps_list()
                operations = [pt.description for pt in sp.permission_types.all()]
                step_permissions.append({
                    'role': role.title,
                    'permission_name': sp.name,
                    'print_type': sp.get_print_type_display(),
                    'allowed_steps': steps if steps else ['所有工序'],
                    'operations': operations,
                    'time_restriction': sp.get_time_restriction_display(),
                    'is_active': sp.is_active,
                })
                
                # 检查权限配置问题
                if not sp.is_active:
                    permission_issues.append({
                        'type': 'warning',
                        'title': '权限未激活',
                        'description': f'工序权限 "{sp.name}" 未激活，用户无法使用此权限'
                    })
                
                if not operations:
                    permission_issues.append({
                        'type': 'error',
                        'title': '权限操作为空',
                        'description': f'工序权限 "{sp.name}" 没有配置任何操作类型'
                    })
        
        # 权限冲突检查
        role_names = [role.title for role in userinfo_object.roles.all()]
        if '唐师' in role_names and '邓师' in role_names:
            permission_issues.append({
                'type': 'error',
                'title': '角色冲突',
                'description': '用户同时拥有唐师和邓师角色，可能导致权限冲突'
            })
        
        # 权限覆盖检查
        all_steps = set()
        for perm in step_permissions:
            if perm['allowed_steps'] == ['所有工序']:
                all_steps.add('*')
            else:
                all_steps.update(perm['allowed_steps'])
        
        if len(all_steps) > 10:  # 如果权限过多，可能存在重复
            permission_issues.append({
                'type': 'info',
                'title': '权限可能重复',
                'description': f'用户拥有 {len(all_steps)} 个工序权限，建议检查是否存在重复权限'
            })
        
        context.update({
            'basic_permissions': basic_permissions,
            'step_permissions': step_permissions,
            'permission_issues': permission_issues,
        })
        
        return render(request, 'stark/user_permission_check.html', context)
    
    def batch_permission_check(self, request):
        """
        批量权限检查视图函数
        """
        # 获取所有用户
        all_users = models.UserInfo.objects.all()
        
        # 分析每个用户的权限状态
        user_analysis = []
        
        for user in all_users:
            roles = user.roles.all()
            
            # 权限统计
            basic_perm_count = 0
            step_perm_count = 0
            issues = []
            
            for role in roles:
                basic_perm_count += role.permissions.count()
                step_perm_count += role.workflow_step_permissions.count()
            
            # 检查问题
            if not roles.exists():
                issues.append('未分配角色')
            
            if basic_perm_count == 0 and step_perm_count == 0:
                issues.append('无有效权限')
            
            role_names = [role.title for role in roles]
            if '唐师' in role_names and '邓师' in role_names:
                issues.append('角色冲突')
            
            user_analysis.append({
                'user': user,
                'roles': roles,
                'basic_perm_count': basic_perm_count,
                'step_perm_count': step_perm_count,
                'issues': issues,
                'status': 'normal' if not issues else 'warning'
            })
        
        # 统计信息
        total_users = len(user_analysis)
        users_with_issues = sum(1 for u in user_analysis if u['issues'])
        users_without_roles = sum(1 for u in user_analysis if not u['roles'].exists())
        normal_users = total_users - users_with_issues
        
        context = {
            'user_analysis': user_analysis,
            'total_users': total_users,
            'users_with_issues': users_with_issues,
            'users_without_roles': users_without_roles,
            'normal_users': normal_users,
        }
        
        return render(request, 'stark/batch_permission_check.html', context)

    def extra_urls(self):
        patterns = [
            re_path(r'reset/password/(?P<pk>\d+)/$', self.wrapper(self.reset_password),
                name=self.get_url_name('reset_pwd')),
            re_path(r'permission/check/(?P<pk>\d+)/$', self.wrapper(self.permission_check),
                name=self.get_url_name('permission_check')),
            re_path(r'batch/permission/check/$', self.wrapper(self.batch_permission_check),
                name=self.get_url_name('batch_permission_check')),
        ]
        return patterns