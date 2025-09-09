from django.db import models
from rbac.models import UserInfo as RbacUserInfo
import random

# Create your models here.
from django.conf import settings

class AIAssistantMemory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    memory_type = models.CharField(max_length=32, default='chat')  # chat/report/habit等
    content = models.TextField()
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_time']
class UserInfo(RbacUserInfo):
    """
    员工表
    """
    name=models.CharField(max_length=32,verbose_name="真实姓名")
    phone=models.CharField(max_length=32,verbose_name='手机号')
    gender_choices=(
        (1,'男'),
        (2,'女')
    )
    gender=models.IntegerField(choices=gender_choices,verbose_name='性别')
    department=models.ForeignKey(to='DepartMent',verbose_name='所属部门',on_delete=models.CASCADE)

    def __str__(self):
        return "%s"%self.name


class DepartMent(models.Model):
    """
    部门表
    """
    name=models.CharField(max_length=32,verbose_name='部门')

    def __str__(self):
        return "%s"%self.name

class Customer(models.Model):
    """
    客户表
    """
    name=models.CharField(max_length=32,verbose_name='客户姓名')
    contact=models.CharField(max_length=32,verbose_name='联系方式',help_text='电话/微信等')
    status_choices=(
        (1,'已签合同'),
        (2,'未签合同')
    )
    status=models.IntegerField(choices=status_choices,verbose_name='状态',default=2)
    sales_choices=(
        (1,'官方网站'),
        (2,'销售宣传'),
        (3,'代理商')
    )
    source=models.IntegerField(choices=sales_choices,verbose_name='销售渠道',null=True,blank=True)
    referral_from=models.ForeignKey(to='self',
                                    verbose_name='自己内部顾客介绍',
                                    related_name='referral',
                                    null=True,
                                    blank=True,
                                    on_delete=models.CASCADE
                                   )
    product=models.ForeignKey(to='Product',verbose_name='咨询的产品',on_delete=models.CASCADE,null=True,blank=True)
    consultant=models.ForeignKey(to='UserInfo',verbose_name='咨询顾问',on_delete=models.CASCADE,limit_choices_to={'department__name':'项目部'})
    consultant_date=models.DateTimeField(verbose_name='咨询日期',null=True,blank=True)

    def __str__(self):
        return "%s"%self.name

class ConsultantRecord(models.Model):
    """
    客户跟进记录
    """
    customer = models.ForeignKey(verbose_name="所咨询客户", to='Customer',on_delete=models.CASCADE)
    consultant = models.ForeignKey(verbose_name="跟进人", to='UserInfo',limit_choices_to={'department__name':'项目部'},on_delete=models.CASCADE)
    date = models.DateTimeField(verbose_name="跟进日期", auto_now_add=True)
    content = models.TextField(verbose_name="跟进内容")

    def __str__(self):
        return "%s-%s"%(self.customer,self.content)

class Order(models.Model):
    customer = models.ForeignKey(verbose_name="客户", to='Customer',on_delete=models.CASCADE,null=True,blank=True)
    product = models.ForeignKey(to='Product',verbose_name='购买的产品',on_delete=models.CASCADE,null=True,blank=True)
    consultant = models.ForeignKey(verbose_name="咨询顾问", to='UserInfo',limit_choices_to={'department__name':'项目部'},on_delete=models.CASCADE,null=True,blank=True)
    quantity=models.IntegerField(verbose_name='产品数量',null=True,blank=True)
    check_date=models.DateTimeField(verbose_name='订单审核',null=True,blank=True)
    delivery_date=models.DateTimeField(verbose_name='交货日期',null=True,blank=True)
    note = models.TextField(verbose_name="备注", blank=True, null=True)

    def __str__(self):
        return "%s-%s-%s"%(self.customer,self.product,self.quantity)

class PaymentRecord(models.Model):
    """
    费用记录
    """
    order=models.ForeignKey(verbose_name='订单',to='Order',on_delete=models.CASCADE,null=True,blank=True)
    payment_type_choices = [

        (1, "定金"),
        (2, "尾款"),
        (3, "其它"),
    ]
    payment=models.IntegerField(choices=payment_type_choices,verbose_name='付款类型')
    paid_fee=models.CharField(max_length=16,verbose_name='费用')
    confirm_date = models.DateTimeField(verbose_name="确认日期",null=True, blank=True)
    confirm_user = models.ForeignKey(verbose_name="确认人", to='UserInfo',limit_choices_to={'department__name':'财务部'}, related_name='confirms', null=True, blank=True,
                                     on_delete=models.CASCADE)
    note = models.TextField(verbose_name="备注", blank=True, null=True)

    def __str__(self):
        return "%s-%s"%(self.payment,self.paid_fee)

class Product(models.Model):
    """
    产品
    """
    name=models.CharField(max_length=32,verbose_name='产品名称')
    price=models.CharField(max_length=16,verbose_name='产品价格')
    paramters=models.TextField(verbose_name='产品参数',null=True,blank=True)

    def __str__(self):
        return "%s"%self.name

class WorkShop(models.Model):
    """
    生产车间
    """
    name = models.CharField(max_length=16, verbose_name='车间',null=True,blank=True)

    def __str__(self):
        return "%s"%self.name

class ProductParameter(models.Model):
    """
    产品生产参数
    """
    workshop=models.ForeignKey(verbose_name='车间',to='WorkShop',on_delete=models.CASCADE)
    product = models.ForeignKey(to='Product',verbose_name='产品',on_delete=models.CASCADE,null=True,blank=True)
    technology=models.TextField(verbose_name='工艺参数',null=True,blank=True)
    quality=models.TextField(verbose_name='品质参数',null=True,blank=True)

    def __str__(self):
        return "%s-%s-%s-%s"%(self.workshop,self.product,self.technology,self.quality)

class Procedure(models.Model):
    """
    生产流程表
    """
    order=models.ForeignKey(to='Order',verbose_name='订单',on_delete=models.CASCADE,null=True,blank=True)
    workshop=models.ForeignKey(to='WorkShop',verbose_name='生产车间',on_delete=models.CASCADE)
    name=models.CharField(max_length=32,verbose_name='生产流程名称')
    status_choices=(
        (1,'未准备好'),
        (2,'已准备好')
    )
    status=models.IntegerField(choices=status_choices,default=2,verbose_name='生产流程状态')
    parent=models.ForeignKey(to='self',verbose_name='上一个流程',on_delete=models.CASCADE,null=True,blank=True)
    reason=models.TextField(verbose_name='原因',null=True,blank=True,help_text='如果该流程出现问题，请说明原因')
    product_choices=(
        (1,'未完成'),
        (2,'已完成')
    )
    product_status=models.IntegerField(choices=product_choices,verbose_name='产品完成状态',default=1)
    scedule=models.TextField(verbose_name='产品完成情况',null=True,blank=True)
    start=models.DateTimeField(verbose_name='开始时间',null=True,blank=True)
    end=models.DateTimeField(verbose_name='结束时间',null=True,blank=True)

    def __str__(self):
        return "%s"%self.order

class ProductAudit(models.Model):
    """
    产品审核
    """
    procedure=models.ForeignKey(to='Procedure',verbose_name='订单-产品信息',on_delete=models.CASCADE,null=True,blank=True)
    user=models.ForeignKey(to='UserInfo',verbose_name='审核人',limit_choices_to={'department__name':'总经理办'},on_delete=models.CASCADE,null=True,blank=True)
    audit_choices=(
        (1,'审核通过'),
        (2,'审核未通过')
    )
    status=models.IntegerField(choices=audit_choices,verbose_name='审核状态',default=2)
    reason=models.TextField(verbose_name='未通过原因',null=True,blank=True)
    audit_date=models.DateTimeField(verbose_name='审核时间',null=True,blank=True)

    def __str__(self):
        return "%s-%s"%(self.procedure,self.status)

# 新增印刷订单相关模型
class PrintOrder(models.Model):
    """
    印刷订单
    """
    order_no = models.CharField(max_length=32, verbose_name='订单编号', unique=True)
    work_order_no = models.CharField(max_length=64, verbose_name='工单号', blank=True, null=True)
    customer_name = models.CharField(max_length=100, verbose_name='客户名称')
    product_name = models.CharField(max_length=100, verbose_name='印品名称')
    quantity = models.IntegerField(verbose_name='订货数量')
    unit = models.CharField(max_length=20, verbose_name='订货单位', blank=True, null=True)
    order_date = models.DateTimeField(verbose_name='委印日期', null=True, blank=True)
    delivery_date = models.DateTimeField(verbose_name='交货日期', null=True, blank=True)
    salesman = models.CharField(max_length=50, verbose_name='业务员', blank=True, null=True)
    contact_person = models.CharField(max_length=64, verbose_name='联系人', blank=True, null=True)
    contact_phone = models.CharField(max_length=32, verbose_name='联系方式', blank=True, null=True)
    design_requirement = models.TextField(verbose_name='设计制作要求', blank=True, null=True)
    customer_supply = models.TextField(verbose_name='客户提供', blank=True, null=True)
    product_size = models.TextField(verbose_name='成品尺寸', blank=True, null=True)
    product_description = models.TextField(verbose_name='产品描述', blank=True, null=True)
    consumption_requirement = models.TextField(verbose_name='消耗要求', blank=True, null=True)
    print_tech_requirement = models.TextField(verbose_name='印刷工艺要求', blank=True, null=True)
    quality_requirement = models.TextField(verbose_name='质检要求', blank=True, null=True)
    delivery_pack_requirement = models.TextField(verbose_name='送货和包装要求', blank=True, null=True)
    note = models.TextField(verbose_name='备注', blank=True, null=True)
    footer_note = models.TextField(verbose_name='底部备注', blank=True, null=True)
    customer_signature = models.CharField(max_length=64, verbose_name='客户签字', blank=True, null=True)
    order_maker = models.CharField(max_length=64, verbose_name='制单员', blank=True, null=True)
    auditor = models.CharField(max_length=64, verbose_name='审核人', blank=True, null=True)
    status_choices = (
        (1, '待处理'),
        (2, '处理中'),
        (3, '已完成'),
        (4, '已取消')
    )
    status = models.IntegerField(choices=status_choices, verbose_name='订单状态', default=1)

    def __str__(self):
        return self.order_no

class PrintProcess(models.Model):
    """
    印刷流程
    """
    process_type_choices = (
        (1, '封面印刷'),
        (2, '内文印刷')
    )
    print_order = models.ForeignKey(to='PrintOrder', verbose_name='印刷订单', on_delete=models.CASCADE)
    process_type = models.IntegerField(choices=process_type_choices, verbose_name='流程类型')
    name = models.CharField(max_length=100, verbose_name='流程名称')
    status_choices = (
        (1, '待开始'),
        (2, '进行中'),
        (3, '已完成'),
        (4, '已暂停')
    )
    status = models.IntegerField(choices=status_choices, verbose_name='流程状态', default=1)
    start_time = models.DateTimeField(verbose_name='开始时间', null=True, blank=True)
    end_time = models.DateTimeField(verbose_name='结束时间', null=True, blank=True)
    operator = models.ForeignKey(to='UserInfo', verbose_name='操作员', on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.print_order.order_no}-{self.get_process_type_display()}"

class PrintProgress(models.Model):
    """
    印刷进度
    """
    print_process = models.ForeignKey(to='PrintProcess', verbose_name='印刷流程', on_delete=models.CASCADE)
    step_name = models.CharField(max_length=100, verbose_name='步骤名称')
    step_order = models.IntegerField(verbose_name='步骤顺序')
    status_choices = (
        (1, '待确认'),
        (2, '已确认'),
        (3, '已跳过')
    )
    status = models.IntegerField(choices=status_choices, verbose_name='步骤状态', default=1)
    confirm_time = models.DateTimeField(verbose_name='确认时间', null=True, blank=True)
    confirm_user = models.ForeignKey(to='UserInfo', verbose_name='确认人', on_delete=models.CASCADE, null=True, blank=True)
    note = models.TextField(verbose_name='备注', blank=True, null=True)
    
    class Meta:
        ordering = ['step_order']
    
    def __str__(self):
        return f"{self.print_process}-{self.step_name}"
    
    def confirm_step(self, user):
        """确认步骤"""
        from django.utils import timezone
        self.status = 2
        self.confirm_time = timezone.now()
        self.confirm_user = user
        self.save()
        
        # 检查是否所有步骤都已完成
        remaining_steps = PrintProgress.objects.filter(
            print_process=self.print_process,
            status=1
        ).exclude(id=self.id)
        
        if not remaining_steps.exists():
            # 所有步骤完成，更新流程状态
            self.print_process.status = 3
            self.print_process.end_time = timezone.now()
            self.print_process.save()
            
            # 检查是否所有流程都完成
            remaining_processes = PrintProcess.objects.filter(
                print_order=self.print_process.print_order,
                status__in=[1, 2]
            )
            
            if not remaining_processes.exists():
                # 所有流程完成，更新订单状态
                self.print_process.print_order.status = 3
                self.print_process.print_order.save()
    
    def get_next_random_step(self):
        """获取下一个随机步骤"""
        remaining_steps = PrintProgress.objects.filter(
            print_process=self.print_process,
            status=1
        ).exclude(id=self.id)
        
        if remaining_steps.exists():
            return random.choice(remaining_steps)
        return None

class PrintMaterial(models.Model):
    """
    用料明细
    """
    order = models.ForeignKey('PrintOrder', verbose_name='印刷订单', on_delete=models.CASCADE)
    serial_no = models.CharField(max_length=10, verbose_name='序号', blank=True, null=True)
    item = models.CharField(max_length=100, verbose_name='项目', blank=True, null=True)
    material_name = models.CharField(max_length=100, verbose_name='材料名称', blank=True, null=True)
    spec = models.CharField(max_length=100, verbose_name='规格', blank=True, null=True)
    page_number = models.CharField(max_length=20, verbose_name='页数', blank=True, null=True)
    open_number = models.CharField(max_length=20, verbose_name='开数', blank=True, null=True)
    fangshu = models.CharField(max_length=20, verbose_name='放数', blank=True, null=True)
    total = models.CharField(max_length=20, verbose_name='总数', blank=True, null=True)
    unit = models.CharField(max_length=20, verbose_name='单位', blank=True, null=True)
    unit_price = models.CharField(max_length=20, verbose_name='单价', blank=True, null=True)
    amount = models.CharField(max_length=20, verbose_name='金额', blank=True, null=True)

class PrintPrepress(models.Model):
    """
    印前明细
    """
    order = models.ForeignKey('PrintOrder', verbose_name='印刷订单', on_delete=models.CASCADE)
    serial_no = models.CharField(max_length=10, verbose_name='序号', blank=True, null=True)
    item = models.CharField(max_length=100, verbose_name='项目', blank=True, null=True)
    content = models.CharField(max_length=100, verbose_name='内容', blank=True, null=True)
    spec = models.CharField(max_length=100, verbose_name='规格', blank=True, null=True)
    plate_name = models.CharField(max_length=100, verbose_name='制版名称', blank=True, null=True)
    note = models.CharField(max_length=100, verbose_name='备注', blank=True, null=True)
    quantity = models.CharField(max_length=20, verbose_name='数量', blank=True, null=True)
    unit = models.CharField(max_length=20, verbose_name='单位', blank=True, null=True)
    unit_price = models.CharField(max_length=20, verbose_name='单价', blank=True, null=True)
    amount = models.CharField(max_length=20, verbose_name='金额', blank=True, null=True)

class PrintProcessDetail(models.Model):
    """
    印刷明细
    """
    order = models.ForeignKey('PrintOrder', verbose_name='印刷订单', on_delete=models.CASCADE)
    serial_no = models.CharField(max_length=10, verbose_name='序号', blank=True, null=True)
    item = models.CharField(max_length=100, verbose_name='项目', blank=True, null=True)
    print_color = models.CharField(max_length=50, verbose_name='印色', blank=True, null=True)
    print_size = models.CharField(max_length=50, verbose_name='印刷尺寸', blank=True, null=True)
    print_method = models.CharField(max_length=50, verbose_name='印刷方式', blank=True, null=True)
    machine = models.CharField(max_length=50, verbose_name='机台', blank=True, null=True)
    quantity = models.CharField(max_length=20, verbose_name='数量', blank=True, null=True)
    unit = models.CharField(max_length=20, verbose_name='单位', blank=True, null=True)
    unit_price = models.CharField(max_length=20, verbose_name='单价', blank=True, null=True)
    amount = models.CharField(max_length=20, verbose_name='金额', blank=True, null=True)

class PrintPostpress(models.Model):
    """
    印后明细
    """
    order = models.ForeignKey('PrintOrder', verbose_name='印刷订单', on_delete=models.CASCADE)
    serial_no = models.CharField(max_length=10, verbose_name='序号', blank=True, null=True)
    item = models.CharField(max_length=100, verbose_name='项目', blank=True, null=True)
    process_content = models.CharField(max_length=100, verbose_name='加工内容', blank=True, null=True)
    process = models.CharField(max_length=100, verbose_name='工序', blank=True, null=True)
    spec = models.CharField(max_length=100, verbose_name='规格', blank=True, null=True)
    machine = models.CharField(max_length=50, verbose_name='机台', blank=True, null=True)
    quantity = models.CharField(max_length=20, verbose_name='数量', blank=True, null=True)
    unit = models.CharField(max_length=20, verbose_name='单位', blank=True, null=True)
    unit_price = models.CharField(max_length=20, verbose_name='单价', blank=True, null=True)
    amount = models.CharField(max_length=20, verbose_name='金额', blank=True, null=True)

class PrintStep(models.Model):
    """
    工作步骤/进度
    """
    order = models.ForeignKey('PrintOrder', verbose_name='印刷订单', on_delete=models.CASCADE)
    process_type = models.CharField(max_length=50, verbose_name='所属分区', blank=True, null=True)  # 如用料、印前、印刷、印后
    step_name = models.CharField(max_length=100, verbose_name='步骤名称')
    step_order = models.IntegerField(verbose_name='步骤顺序', blank=True, null=True)
    status_choices = (
        (1, '待确认'),
        (2, '已确认'),
        (3, '已跳过')
    )
    status = models.IntegerField(choices=status_choices, verbose_name='步骤状态', default=1)
    confirm_time = models.DateTimeField(verbose_name='确认时间', null=True, blank=True)
    confirm_user = models.ForeignKey('UserInfo', verbose_name='确认人', on_delete=models.CASCADE, null=True, blank=True)
    note = models.TextField(verbose_name='备注', blank=True, null=True)

    class Meta:
        ordering = ['step_order']

    def __str__(self):
        return f"{self.order}-{self.process_type}-{self.step_name}"

class PrintOrderFlat(models.Model):
    # 主信息区
    order_no = models.CharField(max_length=32, verbose_name='订单编号', unique=True)
    work_order_no = models.CharField(max_length=64, verbose_name='工单号', blank=True, null=True)
    customer_name = models.CharField(max_length=100, verbose_name='客户名称', blank=True, null=True)
    imposition_requirement = models.TextField(verbose_name='拼晒要求', blank=True, null=True)
    product_name = models.CharField(max_length=100, verbose_name='印品名称', blank=True, null=True)
    product_size = models.TextField(verbose_name='成品尺寸', blank=True, null=True)
    order_date = models.DateTimeField(verbose_name='委印日期', null=True, blank=True)
    delivery_date = models.DateTimeField(verbose_name='交货日期', null=True, blank=True)
    salesman = models.CharField(max_length=50, verbose_name='业务员', blank=True, null=True)
    contact_person = models.CharField(max_length=64, verbose_name='联系人', blank=True, null=True)
    contact_phone = models.CharField(max_length=32, verbose_name='联系方式', blank=True, null=True)
    design_requirement = models.TextField(verbose_name='设计制作要求', blank=True, null=True)
    customer_supply = models.TextField(verbose_name='客户提供', blank=True, null=True)
    product_description = models.TextField(verbose_name='产品描述', blank=True, null=True)
    consumption_requirement = models.TextField(verbose_name='消耗要求', blank=True, null=True)
    print_tech_requirement = models.TextField(verbose_name='印刷工艺要求', blank=True, null=True)
    quality_requirement = models.TextField(verbose_name='质检要求', blank=True, null=True)
    delivery_pack_requirement = models.TextField(verbose_name='送货和包装要求', blank=True, null=True)
    note = models.TextField(verbose_name='备注', blank=True, null=True)
    customer_signature = models.CharField(max_length=64, verbose_name='客户签字', blank=True, null=True)
    order_maker = models.CharField(max_length=64, verbose_name='制单员', blank=True, null=True)
    auditor = models.CharField(max_length=64, verbose_name='审核人', blank=True, null=True)
    quantity = models.CharField(max_length=20, verbose_name='订货数量', blank=True, null=True)
    unit = models.CharField(max_length=20, verbose_name='订货单位', blank=True, null=True)
    
    # 新增字段：印刷类型和订单状态
    print_type_choices = (
        ('cover', '封面印刷'),
        ('content', '内文印刷'),
        ('cover_content', '封面+内文')
    )
    print_type = models.CharField(max_length=20, choices=print_type_choices, verbose_name='印刷类型', default='cover')
    
    status_choices = (
        (1, '待处理'),
        (2, '处理中'),
        (3, '已完成'),
        (4, '已取消')
    )
    status = models.IntegerField(choices=status_choices, verbose_name='订单状态', default=1)
    
    # 明细区类型标识
    detail_type = models.CharField(max_length=20, verbose_name='明细类型', blank=True, null=True)  # 用料/印前/印刷/印后，None表示主信息
    
    # 明细区JSON存储
    material_json = models.TextField(verbose_name='用料明细JSON', blank=True, null=True)
    prepress_json = models.TextField(verbose_name='印前明细JSON', blank=True, null=True)
    process_json = models.TextField(verbose_name='印刷明细JSON', blank=True, null=True)
    postpress_json = models.TextField(verbose_name='印后明细JSON', blank=True, null=True)

    class Meta:
        verbose_name = '订单全信息大表'
        verbose_name_plural = '订单全信息大表'

    def __str__(self):
        return f"{self.order_no}-{self.detail_type or '主信息'}"

class OrderProgressTemplate(models.Model):
    """
    订单进度模板（预定义的进度步骤）- 基于实际印刷流程
    """
    print_type_choices = (
        ('cover', '封面印刷'),
        ('content', '内文印刷'),
        ('cover_content', '封面+内文')
    )
    print_type = models.CharField(max_length=20, choices=print_type_choices, verbose_name='印刷类型')
    step_name = models.CharField(max_length=100, verbose_name='步骤名称')
    step_order = models.IntegerField(verbose_name='步骤顺序')
    description = models.TextField(verbose_name='步骤描述', blank=True, null=True)
    is_required = models.BooleanField(default=True, verbose_name='是否必需步骤')
    estimated_hours = models.IntegerField(verbose_name='预计耗时(小时)', default=1)

    class Meta:
        ordering = ['print_type', 'step_order']
        unique_together = ['print_type', 'step_order']
        verbose_name = '进度模板'
        verbose_name_plural = '进度模板'

    def __str__(self):
        return f"{self.get_print_type_display()}-{self.step_name}"

class OrderProgress(models.Model):
    """
    订单进度实例（具体订单的进度跟踪）
    """
    order = models.ForeignKey('PrintOrderFlat', verbose_name='印刷订单', on_delete=models.CASCADE, related_name='progress_steps')
    step_name = models.CharField(max_length=100, verbose_name='步骤名称')
    step_order = models.IntegerField(verbose_name='步骤顺序')
    step_category_choices = (
        ('cover', '封面'),
        ('content', '内文')
    )
    step_category = models.CharField(max_length=20, choices=step_category_choices, verbose_name='步骤分类', default='content')
    
    status_choices = (
        (1, '待开始'),
        (2, '进行中'),
        (3, '已完成'),
        (4, '已跳过')
    )
    status = models.IntegerField(choices=status_choices, verbose_name='步骤状态', default=1)
    
    start_time = models.DateTimeField(verbose_name='开始时间', null=True, blank=True)
    end_time = models.DateTimeField(verbose_name='完成时间', null=True, blank=True)
    operator = models.ForeignKey('UserInfo', verbose_name='操作员', on_delete=models.CASCADE, null=True, blank=True, related_name='operated_steps')
    confirm_user = models.ForeignKey('UserInfo', verbose_name='确认人', on_delete=models.CASCADE, null=True, blank=True, related_name='confirmed_steps')
    note = models.TextField(verbose_name='备注', blank=True, null=True)
    
    created_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    updated_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)

    class Meta:
        ordering = ['step_order']
        unique_together = ['order', 'step_order', 'step_category']

    def __str__(self):
        return f"{self.order.order_no}-{self.step_name}-{self.get_status_display()}"
    
    def start_step(self, user):
        """开始步骤"""
        from django.utils import timezone
        print(f'=== 模型start_step方法开始 ===')
        print(f'步骤: {self.step_name}, 当前状态: {self.status}')
        print(f'用户: {user.name} (ID: {user.id})')
        print(f'订单: {self.order.order_no} (当前状态: {self.order.status})')
        
        # 更新步骤状态
        old_status = self.status
        self.status = 2
        self.start_time = timezone.now()
        self.operator = user
        
        print(f'步骤状态更新: {old_status} -> {self.status}')
        print(f'开始时间: {self.start_time}')
        
        try:
            self.save()
            print('✅ 步骤保存成功')
        except Exception as e:
            print(f'❌ 步骤保存失败: {e}')
            raise
        
        # 更新订单状态为处理中
        if self.order.status == 1:
            old_order_status = self.order.status
            self.order.status = 2
            print(f'订单状态更新: {old_order_status} -> {self.order.status}')
            try:
                self.order.save()
                print('✅ 订单状态保存成功')
            except Exception as e:
                print(f'❌ 订单状态保存失败: {e}')
                raise
        else:
            print(f'订单状态无需更新 (当前状态: {self.order.status})')
        
        print(f'=== 模型start_step方法完成 ===')
    
    def complete_step(self, user, note=None):
        """完成步骤"""
        from django.utils import timezone
        self.status = 3
        self.end_time = timezone.now()
        self.confirm_user = user
        if note:
            self.note = note
        self.save()
        
        # 检查是否所有步骤都已完成
        remaining_steps = OrderProgress.objects.filter(
            order=self.order,
            status__in=[1, 2]
        ).exclude(id=self.id)
        
        if not remaining_steps.exists():
            # 所有步骤完成，更新订单状态
            self.order.status = 3
            self.order.save()
            
        return not remaining_steps.exists()  # 返回是否全部完成
    
    def skip_step(self, user, reason=None):
        """跳过步骤"""
        from django.utils import timezone
        self.status = 4
        self.end_time = timezone.now()
        self.confirm_user = user
        if reason:
            self.note = f"跳过原因: {reason}"
        self.save()




