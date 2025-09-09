from stark.service.base_stark import BaseStark, BaseModelForm
from crm import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.urls import re_path
from crm.permissions.permissios import Permissions

class PrintOrderFlatStark(Permissions, BaseStark):
    """
    新的印刷订单管理后台
    """

    def display_order_no(self, row=None, header_body=False, *args, **kwargs):
        if header_body:
            return "订单号"
        # 点击订单号跳转到详情页
        detail_url = reverse('print_order_detail', kwargs={'order_id': row.pk})
        return mark_safe(f'<a href="{detail_url}">{row.order_no}</a>')

    def display_progress(self, row=None, header_body=False, *args, **kwargs):
        if header_body:
            return "生产进度"
        # 跳转到进度管理页面
        progress_url = reverse('order_progress', kwargs={'order_id': row.pk})
        return mark_safe(f'<a href="{progress_url}">查看/管理</a>')

    def display_status(self, row=None, header_body=False, *args, **kwargs):
        if header_body:
            return "订单状态"
        return row.get_status_display()

    list_display = [
        BaseStark.display_checkbox,
        'id',
        display_order_no,
        'customer_name',
        'product_name',
        'quantity',
        display_status,
        'order_date',
        'delivery_date',
        'salesman',
        display_progress,
    ]

    search_fields = ['order_no', 'customer_name', 'product_name', 'salesman']
    list_filter = ['status', 'print_type', 'salesman', ('order_date', '日期范围'), ('delivery_date', '交期范围')]
    
    action_list = [BaseStark.muti_delete]

    def get_add_btn(self, request, *args, **kwargs):
        # 重写添加按钮，跳转到自定义的创建页面
        add_url = reverse('create_print_order')
        return mark_safe(f'<a href="{add_url}" class="btn btn-primary">创建新订单</a>')

    def get_urls(self):
        urlpatterns = [
            re_path(r'list/$', self.wrapper(self.changelist_view), name=self.get_list_url_name),
            re_path(r'add/$', self.wrapper(self.add_view), name=self.get_add_url_name),
            re_path(r'(?P<order_id>\d+)/change/$', self.wrapper(self.change_view), name=self.get_edit_url_name),
            re_path(r'(?P<order_id>\d+)/delete/$', self.wrapper(self.del_view), name=self.get_del_url_name),
        ]
        
        extra_urls = self.extra_urls()
        if extra_urls:
            urlpatterns.extend(extra_urls)
            
        return urlpatterns

    def get_queryset(self, request, *args, **kwargs):
        # 只显示主订单信息
        return self.model_class.objects.filter(detail_type__isnull=True)

    # 重写编辑和删除按钮的URL，使其指向我们的自定义视图
    def display_edit(self, row=None, header_body=False, *args, **kwargs):
        if header_body:
            return "编辑"
        edit_url = reverse('edit_print_order', kwargs={'order_id': row.pk})
        return mark_safe(f'<a href="{edit_url}"><i class="fa fa-edit"></i></a>')

    def display_del(self, row=None, header_body=False, *args, **kwargs):
        if header_body:
            return "删除"
        del_url = reverse('delete_print_order', kwargs={'order_id': row.pk})
        return mark_safe(f'<a href="{del_url}"><i class="fa fa-trash-o"></i></a>')
        
    # 将自定义的编辑和删除按钮加入list_display
    list_display.extend([display_edit, display_del])