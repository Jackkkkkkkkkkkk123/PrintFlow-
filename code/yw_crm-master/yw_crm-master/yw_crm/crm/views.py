from django.shortcuts import render,redirect,HttpResponse, get_object_or_404
from django.views import View
from django.contrib.auth import login,authenticate
from crm import models
from utils.code import get_verify_code
from django.conf import settings
import os
from crm.forms.login import LoginForm
from crm.forms.reset import EmailForm
from django.urls import reverse
from rbac.services.init_permission_menu import InitPermission
import random,string
from django.core.mail import send_mail
import json
import pandas as pd
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import re
from datetime import datetime
import math

# 新增：导入权限装饰器
from rbac.decorators import require_step_permission, require_role, check_step_permission, log_step_operation

# 新增：导入需要的模型
from crm.models import PrintOrderFlat, OrderProgress, UserInfo


# Create your views here.

def verify_code(request):

    return get_verify_code(request)

class LoginView(View):

    def get(self,request):
        form = LoginForm()

        # with open(os.path.join(settings.BASE_DIR,'static/images/verifycode.png'),'wb') as f:
        #     f.write(verifycode_response.content)
        return render(request,'login.html',{'form':form})

    def post(self,request):
        is_checked=request.POST.get('is_checked')

        if is_checked:
            request.session.set_expiry(60*60*24*30)
        form=LoginForm(data=request.POST)
        form.request=request
        if form.is_valid():
            request.session['user_id'] = form.user.id  # 登录成功后设置 session
            InitPermission(request, form.user).init_permissions_dict()
            InitPermission(request, form.user).init_menu_dict()
            return redirect('/index/')
        return render(request,'login.html',{'form':form})

class LogoutView(View):

    def get(self,request):
        request.session.delete()
        return redirect('/login/')

class IndexView(View):

    def get(self,request):
        from crm.models import PrintOrderFlat, OrderProgress
        from django.utils import timezone
        from datetime import timedelta
        
        # 获取当前用户信息
        user_id = request.session.get('user_id')
        
        # 统计信息
        total_orders = PrintOrderFlat.objects.filter(detail_type=None).count()
        pending_orders = PrintOrderFlat.objects.filter(detail_type=None, status=1).count()
        processing_orders = PrintOrderFlat.objects.filter(detail_type=None, status=2).count()
        completed_orders = PrintOrderFlat.objects.filter(detail_type=None, status=3).count()
        
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
        
        context = {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'completed_orders': completed_orders,
            'current_steps': current_steps,
            'next_steps': next_steps,
            'recent_completed': recent_completed,
            'urgent_orders': urgent_orders,
        }

        return render(request,'index.html', context)

class ResetView(View):

    def get(self,request):
        form=EmailForm()
        return render(request,'reset.html',{'form':form})

    def post(self,request):
        print(request.POST)
        result = {'status':None,'message':None,'data':None}
        form=EmailForm(request.POST)
        if form.is_valid():
            email=form.cleaned_data.get('email')
            obj=models.UserInfo.objects.filter(email=email).first()
            if not obj:
                result['status']=False
                result['message']='邮箱不存在'
            else:
                str = '1234567890QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm'
                rand_str = ''
                for i in range(0, 6):
                    rand_str += str[random.randrange(0, len(str))]
                send_mail(
                    '重置密码',
                    '亲爱的用户，您的密码已经重置，新的密码为%s' % rand_str,
                    settings.EMAIL_HOST_USER,
                    [email, ],
                    fail_silently=False
                )
                models.UserInfo.objects.filter(id=obj.id).update(password=rand_str)
                result['status'] = True
                result['message'] = '邮件发送成功'

        return HttpResponse(json.dumps(result))

# 新增印刷订单管理视图
class PrintOrderListView(View):
    """印刷订单列表（改为从 PrintOrderFlat 读取主信息）"""
    def get(self, request):
        from crm.models import PrintOrderFlat
        # 只查主信息（detail_type=None），按日期倒序
        orders = PrintOrderFlat.objects.filter(detail_type=None).order_by('-order_date')
        return render(request, 'print_order_list.html', {'orders': orders})

class CreatePrintOrderView(View):
    """从Excel文件创建印刷订单"""
    
    def get(self, request):
        return render(request, 'create_print_order.html')
    
    def post(self, request):
        import pandas as pd
        from django.utils import timezone
        from . import models
        import json
        
        # 根据样例文件定义的实际进度步骤模板
        PROGRESS_TEMPLATES = {
            'cover': [
                {'name': '印刷', 'description': '封面印刷', 'required': True, 'category': 'cover'},
                {'name': '覆膜', 'description': '覆膜工艺', 'required': False, 'category': 'cover'},
                {'name': '烫金', 'description': '烫金工艺', 'required': False, 'category': 'cover'},
                {'name': '压痕', 'description': '压痕工艺', 'required': False, 'category': 'cover'},
                {'name': '压纹', 'description': '压纹工艺', 'required': False, 'category': 'cover'},
                {'name': '模切', 'description': '模切工艺', 'required': False, 'category': 'cover'},
                {'name': '击凸', 'description': '击凸工艺', 'required': False, 'category': 'cover'},
                {'name': '过油', 'description': '过油工艺', 'required': False, 'category': 'cover'},
                {'name': '外调', 'description': '外调加工', 'required': False, 'category': 'cover'}
            ],
            'content': [
                {'name': '调图', 'description': '图像调整', 'required': True, 'category': 'content'},
                {'name': 'CTP', 'description': 'CTP制版', 'required': True, 'category': 'content'},
                {'name': '切纸', 'description': '切纸准备', 'required': True, 'category': 'content'},
                {'name': '印刷', 'description': '内文印刷', 'required': True, 'category': 'content'},
                {'name': '折页', 'description': '折页工序', 'required': False, 'category': 'content'},
                {'name': '锁线', 'description': '锁线装订', 'required': False, 'category': 'content'},
                {'name': '胶包', 'description': '胶装包书', 'required': False, 'category': 'content'},
                {'name': '马订', 'description': '马订装订', 'required': False, 'category': 'content'},
                {'name': '勒口', 'description': '勒口工艺', 'required': False, 'category': 'content'},
                {'name': '夹卡片', 'description': '夹卡片', 'required': False, 'category': 'content'},
                {'name': '配本(塑封)', 'description': '配本塑封', 'required': False, 'category': 'content'},
                {'name': '打包', 'description': '打包工序', 'required': True, 'category': 'content'},
                {'name': '送货', 'description': '送货配送', 'required': True, 'category': 'content'}
            ],
            'cover_content': [
                {'name': '印刷', 'description': '封面印刷', 'required': True, 'category': 'cover'},
                {'name': '覆膜', 'description': '覆膜工艺', 'required': False, 'category': 'cover'},
                {'name': '烫金', 'description': '烫金工艺', 'required': False, 'category': 'cover'},
                {'name': '压痕', 'description': '压痕工艺', 'required': False, 'category': 'cover'},
                {'name': '压纹', 'description': '压纹工艺', 'required': False, 'category': 'cover'},
                {'name': '模切', 'description': '模切工艺', 'required': False, 'category': 'cover'},
                {'name': '击凸', 'description': '击凸工艺', 'required': False, 'category': 'cover'},
                {'name': '过油', 'description': '过油工艺', 'required': False, 'category': 'cover'},
                {'name': '外调', 'description': '外调加工', 'required': False, 'category': 'cover'},
                {'name': '调图', 'description': '图像调整', 'required': True, 'category': 'content'},
                {'name': 'CTP', 'description': 'CTP制版', 'required': True, 'category': 'content'},
                {'name': '切纸', 'description': '切纸准备', 'required': True, 'category': 'content'},
                {'name': '印刷', 'description': '内文印刷', 'required': True, 'category': 'content'},
                {'name': '折页', 'description': '折页工序', 'required': False, 'category': 'content'},
                {'name': '锁线', 'description': '锁线装订', 'required': False, 'category': 'content'},
                {'name': '胶包', 'description': '胶装包书', 'required': False, 'category': 'content'},
                {'name': '马订', 'description': '马订装订', 'required': False, 'category': 'content'},
                {'name': '勒口', 'description': '勒口工艺', 'required': False, 'category': 'content'},
                {'name': '夹卡片', 'description': '夹卡片', 'required': False, 'category': 'content'},
                {'name': '配本(塑封)', 'description': '配本塑封', 'required': False, 'category': 'content'},
                {'name': '打包', 'description': '打包工序', 'required': True, 'category': 'content'},
                {'name': '送货', 'description': '送货配送', 'required': True, 'category': 'content'}
            ]

        }
        
        field_map = {
            '订单单号': 'order_no',
            '订单号': 'order_no',  # 订单号变体
            '工单号': 'work_order_no',
            '工单单号': 'work_order_no',  # 工单单号变体
            '委印日期': 'order_date',
            '工单日期': 'order_date',  # 工单日期和委印日期映射到同一个字段
            '下单日期': 'order_date',  # 下单日期也映射到委印日期
            '交货日期': 'delivery_date',
            '客户名称': 'customer_name',
            '客户': 'customer_name',  # 客户名称简写
            '印品名称': 'product_name',
            '产品名称': 'product_name',  # 产品名称变体
            '订单数量': 'quantity',
            '订货数量': 'quantity',
            '数量': 'quantity',  # 数量简写
            '拼晒要求': 'imposition_requirement',
            '单位': 'unit',
            '联系人': 'contact_person',
            '联系方式': 'contact_phone',
            '电话': 'contact_phone',  # 电话映射到联系方式
            '业务员': 'salesman',
            '设计制作要求': 'design_requirement',
            '客户提供': 'customer_supply',
            '成品尺寸': 'product_size',
            '产品尺寸': 'product_size',  # 产品尺寸变体
            '产品描述': 'product_description',
            '消耗要求': 'consumption_requirement',
            '印刷工艺要求': 'print_tech_requirement',
            '印后工艺要求': 'delivery_pack_requirement',
            '质检要求': 'quality_requirement',
            '送货和包装要求': 'delivery_pack_requirement',
            '备注': 'note',
            '客户签字': 'customer_signature',
            '制单员': 'order_maker',
            '审核人': 'auditor',
        }
        
        # 字段名标准化映射
        def clean_key(key):
            import re
            key = str(key)
            key = key.replace('\n', '').replace('\r', '').replace('\u3000', '').replace(' ', '').lower()
            key = key.replace('：', ':')
            key = re.sub(r'\s+', '', key)
            # 移除尾随的冒号
            key = key.rstrip(':')
            return key
        field_map_clean = {clean_key(k): v for k, v in field_map.items()}
        
        try:
            # 获取前端传递的参数
            print_type = request.POST.get('print_type', 'cover')
            selected_steps_json = request.POST.get('selected_steps', '[]')
            
            try:
                selected_step_indexes = json.loads(selected_steps_json)
            except:
                selected_step_indexes = []
            
            excel_file = request.FILES.get('excel_file')
            if not excel_file:
                return JsonResponse({'status': False, 'message': '请选择Excel文件'})
            
            df = pd.read_excel(excel_file, header=None)
            print('==== Excel 前20行内容 ====' )
            print(df.head(20))

            import re, json
            from crm.models import PrintOrderFlat, OrderProgress
            order_info = {}
            
            # 先处理"字段:值"格式
            for i in range(10):
                row = df.iloc[i]
                for cell in row:
                    if isinstance(cell, str):
                        # 处理"字段:值"格式，使用更宽松的正则表达式
                        match = re.match(r'([\u4e00-\u9fa5A-Za-z0-9_\s]+)[:：](.*)', cell)
                        if match:
                            raw_key = match.group(1).strip()
                            value = match.group(2).strip()
                            key = clean_key(raw_key)
                            if key in field_map_clean and value and key not in order_info:
                                order_info[key] = value
                                print(f'找到字段映射(冒号格式): {raw_key} -> {value}')
            
            # 特殊处理订单单号（可能包含在单元格文本中）
            for i in range(5):  # 只检查前5行
                row = df.iloc[i]
                for cell in row:
                    if isinstance(cell, str) and '订单单号' in cell:
                        # 提取订单号
                        order_match = re.search(r'订单单号[:：]\s*([A-Za-z0-9]+)', cell)
                        if order_match and 'order_no' not in [field_map_clean.get(k) for k in order_info.keys()]:
                            order_no = order_match.group(1)
                            order_info['订单单号'] = order_no
                            print(f'找到订单单号: {order_no}')
            
            # 定义字段优先级（数字越小优先级越高）
            field_priority = {
                'order_no': 1,
                'work_order_no': 2,
                'customer_name': 3,
                'product_name': 4,
                'product_size': 5,  # 成品尺寸优先级较高
                'quantity': 6,
                'unit': 7,
                'order_date': 8,
                'delivery_date': 9,
                'salesman': 10,
                'contact_person': 11,
                'contact_phone': 12,
                'imposition_requirement': 15,
                'consumption_requirement': 16,
                'quality_requirement': 17,
                'design_requirement': 20,  # 设计制作要求优先级较低
                'customer_supply': 21,     # 客户提供优先级较低
                'product_description': 22,
                'print_tech_requirement': 23,
                'delivery_pack_requirement': 24,
                'note': 25,
                'customer_signature': 26,
                'order_maker': 27,
                'auditor': 28,
            }
            
            # 再处理"字段/值分列"格式 - 修正逻辑，增加优先级处理
            value_assignments = {}  # 记录值和其分配情况 {value: [(field, priority), ...]}
            
            for i in range(10):
                row = df.iloc[i]
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and cell.strip():
                        key = clean_key(cell.strip())
                        print(f'行{i}列{j}: "{cell.strip()}" -> 清理后: "{key}" -> 在映射中: {key in field_map_clean}')
                        if key in field_map_clean:
                            model_field = field_map_clean[key]
                            # 向右找值，搜索整行而不是限制范围
                            for k in range(j+1, len(row)):
                                val = row[k]
                                if pd.notna(val) and str(val).strip():
                                    val_str = str(val).strip()
                                    val_clean = clean_key(val_str)
                                    # 如果这个值不是另一个字段名，则视为当前字段的值
                                    if val_clean not in field_map_clean:
                                        # 记录这个值的候选分配
                                        if val_str not in value_assignments:
                                            value_assignments[val_str] = []
                                        
                                        priority = field_priority.get(model_field, 999)
                                        value_assignments[val_str].append((key, model_field, priority))
                                        print(f'候选映射: {cell.strip()} -> {val_str} (优先级: {priority})')
                                        break
            
            # 根据优先级分配值
            for val_str, candidates in value_assignments.items():
                if len(candidates) == 1:
                    # 只有一个候选，直接分配
                    key, model_field, priority = candidates[0]
                    if key not in order_info:
                        order_info[key] = val_str
                        print(f'找到字段映射: {key} -> {val_str}')
                else:
                    # 多个候选，选择优先级最高的（数字最小）
                    candidates.sort(key=lambda x: x[2])  # 按优先级排序
                    best_key, best_model_field, best_priority = candidates[0]
                    
                    if best_key not in order_info:
                        order_info[best_key] = val_str
                        print(f'找到字段映射(优先级选择): {best_key} -> {val_str} (优先级: {best_priority})')
                        
                        # 显示被跳过的候选
                        for key, model_field, priority in candidates[1:]:
                            print(f'  跳过低优先级候选: {key} (优先级: {priority})')
            
            # 如果没有找到合适的值，检查是否是紧邻的值（同一列的下一行或相邻列）
            for i in range(10):
                row = df.iloc[i]
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and cell.strip():
                        key = clean_key(cell.strip())
                        if key in field_map_clean and key not in order_info:
                            model_field = field_map_clean[key]
                            if i+1 < len(df):
                                next_row = df.iloc[i+1]
                                if j < len(next_row):
                                    next_val = next_row[j]
                                    if pd.notna(next_val) and str(next_val).strip():
                                        next_val_str = str(next_val).strip()
                                        next_val_clean = clean_key(next_val_str)
                                        if next_val_clean not in field_map_clean:
                                            # 检查这个值是否已经被使用
                                            already_used = False
                                            for existing_key, existing_val in order_info.items():
                                                if existing_val == next_val_str:
                                                    already_used = True
                                                    break
                                            
                                            if not already_used:
                                                order_info[key] = next_val_str
                                                print(f'找到字段映射(下一行): {cell.strip()} -> {next_val_str}')
            
            print('修正后的 order_info:', order_info)
            print('field_map_clean包含的键:', list(field_map_clean.keys()))
            
            # 只写入数据库有的字段
            db_fields = [f.name for f in PrintOrderFlat._meta.fields]
            order_data = {}
            for k, v in order_info.items():
                model_field = field_map_clean.get(k, k)
                if model_field in db_fields:
                    order_data[model_field] = v
            
            # 修正明细区四个区域提取逻辑
            section_names = ['用料', '印前', '印刷', '印后']
            section_json_fields = ['material_json', 'prepress_json', 'process_json', 'postpress_json']
            
            # 找到各个分区的起始行 - 修正识别逻辑
            section_starts = {}
            for idx, row in df.iterrows():
                if idx < 8:  # 跳过前8行，避免把主信息区的"印刷工艺要求"等误识别为分区
                    continue
                    
                # 检查第一列是否恰好是分区名（用于识别独立的分区标题）
                first_cell = row.iloc[0] if len(row) > 0 else None
                if pd.notna(first_cell) and str(first_cell).strip() in section_names:
                    section_name = str(first_cell).strip()
                    if section_name not in section_starts:
                        section_starts[section_name] = idx
                        print(f'找到分区 "{section_name}" 在第 {idx} 行')
            
            print('修正后的分区起始位置:', section_starts)
            
            for i, name in enumerate(section_names):
                start_idx = section_starts.get(name)
                if start_idx is None:
                    print(f'未找到分区 "{name}"，设为空数组')
                    order_data[section_json_fields[i]] = json.dumps([])
                    continue
                
                # 找表头行（分区名所在行）
                header_row = df.iloc[start_idx]
                # 提取非空的列作为表头
                header_cols = []
                for col_idx, cell in enumerate(header_row):
                    if pd.notna(cell) and str(cell).strip() and str(cell).strip() != name:
                        header_cols.append((col_idx, str(cell).strip()))
                
                if not header_cols:
                    print(f'分区 "{name}" 没有找到有效表头')
                    order_data[section_json_fields[i]] = json.dumps([])
                    continue
                
                print(f'分区 "{name}" 表头: {[h[1] for h in header_cols]}')
                
                # 提取数据行（分区名下一行开始）
                detail_list = []
                data_start = start_idx + 1
                
                # 找到下一个分区的位置作为结束位置
                next_section_idx = len(df)
                for next_name in section_names:
                    next_idx = section_starts.get(next_name)
                    if next_idx and next_idx > start_idx and next_idx < next_section_idx:
                        next_section_idx = next_idx
                
                print(f'分区 "{name}" 数据范围: {data_start} 到 {next_section_idx-1}')
                
                for row_idx in range(data_start, min(next_section_idx, len(df))):
                    row = df.iloc[row_idx]
                    # 检查是否是有效数据行
                    if row.notna().sum() <= 1:  # 空行或只有一个非空值
                        continue
                    
                    # 过滤掉表头行（检查是否第一列是其他分区名或"序"）
                    first_cell = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                    if first_cell in section_names or first_cell == "序":
                        # 如果第一列是分区名，说明这是其他分区的表头，跳过
                        continue
                    
                    # 提取数据
                    row_data = {}
                    has_data = False
                    for col_idx, header in header_cols:
                        if col_idx < len(row):
                            cell_value = row[col_idx]
                            if pd.notna(cell_value) and str(cell_value).strip():
                                # 过滤掉明显的表头值
                                cell_str = str(cell_value).strip()
                                if cell_str not in ['序', '项目', '内容', '规格', '数量', '单位', '单价', '金额', '印色', '印刷尺寸', '印刷方式', '机台', '加工内容', '工序']:
                                    row_data[header] = cell_str
                                    has_data = True
                    
                    if has_data and len(row_data) >= 2:  # 至少要有2个有效字段
                        detail_list.append(row_data)
                        print(f'  数据行 {row_idx}: {row_data}')
                
                order_data[section_json_fields[i]] = json.dumps(detail_list, ensure_ascii=False)
                print(f'分区 "{name}" 提取到 {len(detail_list)} 行数据')
            
            # 特殊字段处理（如日期、数量等）
            def parse_date(date_str):
                if not date_str or pd.isna(date_str):
                    return None
                from django.utils import timezone
                import pytz
                for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        naive_dt = datetime.strptime(str(date_str).strip(), fmt)
                        # 转换为timezone-aware datetime
                        return timezone.make_aware(naive_dt, timezone.get_current_timezone())
                    except Exception:
                        continue
                return None
            
            if 'order_date' in order_data:
                order_data['order_date'] = parse_date(order_data['order_date'])
            if 'delivery_date' in order_data:
                order_data['delivery_date'] = parse_date(order_data['delivery_date'])
            if 'quantity' in order_data:
                try:
                    order_data['quantity'] = int(float(order_data['quantity']))
                except Exception:
                    order_data['quantity'] = 1
            
            # 设置印刷类型和状态
            order_data['print_type'] = print_type
            order_data['status'] = 1  # 待处理
            order_data['detail_type'] = None  # 主信息
            
            # 写入主信息
            print('\n==== 四个JSON字段内容 ====')
            print('1. 用料明细JSON:')
            print(order_data.get('material_json', '[]'))
            print('\n2. 印前明细JSON:')
            print(order_data.get('prepress_json', '[]'))
            print('\n3. 印刷明细JSON:')
            print(order_data.get('process_json', '[]'))
            print('\n4. 印后明细JSON:')
            print(order_data.get('postpress_json', '[]'))
            print('==== JSON字段打印完毕 ====\n')
            
            # 检查订单号是否已存在
            if 'order_no' in order_data and order_data['order_no']:
                existing_order = PrintOrderFlat.objects.filter(
                    order_no=order_data['order_no'], 
                    detail_type=None
                ).first()
                if existing_order:
                    return JsonResponse({
                        'status': False, 
                        'message': f'订单号 {order_data["order_no"]} 已存在，请检查后重新上传'
                    })
            
            # 创建订单
            order = PrintOrderFlat.objects.create(**order_data)
            
            # 创建进度步骤
            steps_template = PROGRESS_TEMPLATES.get(print_type, [])
            created_steps = []
            
            for step_index in selected_step_indexes:
                if 0 <= step_index < len(steps_template):
                    step_info = steps_template[step_index]
                    progress_step = OrderProgress.objects.create(
                        order=order,
                        step_name=step_info['name'],
                        step_order=step_index + 1,
                        status=1,  # 待开始
                        step_category=step_info.get('category', 'content')  # 设置步骤分类
                    )
                    created_steps.append(step_info['name'])
                    print(f'创建进度步骤: {step_info["name"]}')
            
            print(f'订单创建成功: {order.order_no}，创建了 {len(created_steps)} 个进度步骤')

            return JsonResponse({
                'status': True, 
                'message': f'订单创建成功，已设置 {len(created_steps)} 个进度步骤',
                'order_no': order.order_no,
                'steps': created_steps
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': False, 'message': f'创建订单失败: {str(e)}'})

class PrintOrderDetailView(View):
    """印刷订单详情（从JSON字段解析明细数据）"""
    def get(self, request, order_id):
        from crm.models import PrintOrderFlat
        import json

        try:
            # 查找主信息记录
            main = PrintOrderFlat.objects.filter(id=order_id, detail_type=None).first()
            if not main:
                main = PrintOrderFlat.objects.filter(order_no=order_id, detail_type=None).first()
            if not main:
                return redirect('/print-orders/')
            
            # 从JSON字段解析明细数据
            details = []
            
            # 解析用料明细
            try:
                material_data = json.loads(main.material_json or '[]')
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
                        # 其他类型字段设为空
                        'content': '',
                        'plate_name': '',
                        'note_detail': '',
                        'print_color': '',
                        'print_size': '',
                        'print_method': '',
                        'machine': '',
                        'process_content': '',
                        'process': '',
                        'quantity': ''
                    })()
                    details.append(detail_obj)
            except:
                pass
            
            # 解析印前明细
            try:
                prepress_data = json.loads(main.prepress_json or '[]')
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
                        # 其他类型字段设为空
                        'material_name': '',
                        'page_number': '',
                        'open_number': '',
                        'fangshu': '',
                        'total': '',
                        'dunjia': '',
                        'print_color': '',
                        'print_size': '',
                        'print_method': '',
                        'machine': '',
                        'process_content': '',
                        'process': ''
                    })()
                    details.append(detail_obj)
            except:
                pass
            
            # 解析印刷明细
            try:
                process_data = json.loads(main.process_json or '[]')
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
                        # 其他类型字段设为空
                        'material_name': '',
                        'spec': '',
                        'page_number': '',
                        'open_number': '',
                        'fangshu': '',
                        'total': '',
                        'dunjia': '',
                        'content': '',
                        'plate_name': '',
                        'note_detail': '',
                        'process_content': '',
                        'process': ''
                    })()
                    details.append(detail_obj)
            except:
                pass
            
            # 解析印后明细
            try:
                postpress_data = json.loads(main.postpress_json or '[]')
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
                        # 其他类型字段设为空
                        'material_name': '',
                        'page_number': '',
                        'open_number': '',
                        'fangshu': '',
                        'total': '',
                        'dunjia': '',
                        'content': '',
                        'plate_name': '',
                        'note_detail': '',
                        'print_color': '',
                        'print_size': '',
                        'print_method': '',
                        'unit': ''
                    })()
                    details.append(detail_obj)
            except:
                pass
            
            return render(request, 'print_order_detail.html', {
                'main': main,
                'details': details,
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render(request, 'print_order_detail.html', {'error': str(e)})

class PrintProgressView(View):
    """印刷进度管理"""
    
    def get(self, request, process_id):
        try:
            print_process = models.PrintProcess.objects.get(id=process_id)
            progress_steps = models.PrintProgress.objects.filter(print_process=print_process)
            
            # 获取当前待确认的步骤
            current_step = progress_steps.filter(status=1).first()
            
            return render(request, 'print_progress.html', {
                'print_process': print_process,
                'progress_steps': progress_steps,
                'current_step': current_step
            })
        except models.PrintProcess.DoesNotExist:
            return redirect('/print-orders/')

@method_decorator(csrf_exempt, name='dispatch')
class ConfirmStepView(View):
    """确认步骤"""
    
    def post(self, request, step_id):
        try:
            step = models.PrintProgress.objects.get(id=step_id)
            user = request.user
            
            # 确认步骤
            step.confirm_step(user)
            
            # 获取下一个随机步骤
            next_step = step.get_next_random_step()
            
            return JsonResponse({
                'status': True,
                'message': '步骤确认成功',
                'next_step': {
                    'id': next_step.id,
                    'name': next_step.step_name
                } if next_step else None
            })
            
        except models.PrintProgress.DoesNotExist:
            return JsonResponse({'status': False, 'message': '步骤不存在'})
        except Exception as e:
            return JsonResponse({'status': False, 'message': f'确认失败: {str(e)}'})

class PrintDashboardView(View):
    """印刷仪表板（改为从 PrintOrderFlat 统计）"""
    def get(self, request):
        from crm.models import PrintOrderFlat, OrderProgress
        
        # 获取筛选参数
        status_filter = request.GET.get('status', 'all')  # all, pending, processing, completed
        
        # 获取各状态订单数量统计
        total_orders = PrintOrderFlat.objects.filter(detail_type=None).count()
        pending_orders = PrintOrderFlat.objects.filter(detail_type=None, status=1).count()
        processing_orders = PrintOrderFlat.objects.filter(detail_type=None, status=2).count()
        completed_orders = PrintOrderFlat.objects.filter(detail_type=None, status=3).count()
        
        # 根据筛选条件获取订单
        orders_queryset = PrintOrderFlat.objects.filter(detail_type=None)
        
        if status_filter == 'pending':
            orders_queryset = orders_queryset.filter(status=1)
        elif status_filter == 'processing':
            orders_queryset = orders_queryset.filter(status=2)
        elif status_filter == 'completed':
            orders_queryset = orders_queryset.filter(status=3)
        
        # 获取最近订单并附加当前步骤信息（增加显示数量）
        recent_orders_queryset = orders_queryset.order_by('-order_date')[:20]
        recent_orders = []
        
        for order in recent_orders_queryset:
            # 为每个订单创建一个带有当前步骤信息的对象
            order_info = {
                'order': order,
                'current_step': None,
                'current_step_status': None,
                'progress_percentage': 0,
                'total_steps': 0,
                'completed_steps': 0,
                'next_step': None
            }
            
            # 获取订单的进度步骤
            progress_steps = OrderProgress.objects.filter(order=order).order_by('step_order')
            
            if progress_steps.exists():
                total_steps = progress_steps.count()
                completed_steps = progress_steps.filter(status=3).count()
                in_progress_steps = progress_steps.filter(status=2).count()
                skipped_steps = progress_steps.filter(status=4).count()
                
                order_info['total_steps'] = total_steps
                order_info['completed_steps'] = completed_steps
                
                # 计算进度百分比（包括跳过的步骤）
                finished_steps = completed_steps + skipped_steps
                order_info['progress_percentage'] = int((finished_steps / total_steps * 100)) if total_steps > 0 else 0
                
                # 查找当前进行中的步骤
                current_step = progress_steps.filter(status=2).first()
                if current_step:
                    order_info['current_step'] = current_step.step_name
                    order_info['current_step_status'] = '进行中'
                    # 找下一个待开始的步骤
                    next_step = progress_steps.filter(status=1).first()
                    if next_step:
                        order_info['next_step'] = next_step.step_name
                else:
                    # 如果没有进行中的步骤，查找下一个待开始的步骤
                    next_step = progress_steps.filter(status=1).first()
                    if next_step:
                        order_info['current_step'] = next_step.step_name
                        order_info['current_step_status'] = '待开始'
                    else:
                        # 所有步骤都完成了
                        if finished_steps == total_steps:
                            order_info['current_step'] = '全部完成'
                            order_info['current_step_status'] = '已完成'
                        else:
                            order_info['current_step'] = '步骤配置异常'
                            order_info['current_step_status'] = '异常'
            else:
                # 没有设置进度步骤的订单
                order_info['current_step'] = '未设置步骤'
                order_info['current_step_status'] = '无进度'
            
            recent_orders.append(order_info)
        
        # 获取一些快速统计信息
        urgent_orders = PrintOrderFlat.objects.filter(
            detail_type=None, 
            status__in=[1, 2]
        ).order_by('delivery_date')[:5]  # 即将到期的订单
        
        return render(request, 'print_dashboard.html', {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'completed_orders': completed_orders,
            'recent_orders': recent_orders,
            'urgent_orders': urgent_orders,
            'status_filter': status_filter,
            'current_filter_name': {
                'all': '全部订单',
                'pending': '待处理订单',
                'processing': '处理中订单',
                'completed': '已完成订单'
            }.get(status_filter, '全部订单')
        })

def test(request):
    from django.db.models import ForeignKey, ManyToManyField, OneToOneField
    from django.db.models.fields import DateField

    # obj=models.Customer.objects.filter(id=1).first()
    # # queryset=obj.product.all()
    # val=getattr(obj,'consultant')
    # m2m=getattr(obj,'product').all()
    # print(val)
    # print(m2m)


    # field_obj=models.Customer._meta.get_field('consultant_date')
    # print(type(field_obj))
    # if isinstance(field_obj,ManyToManyField):
    #     queryset=field_obj.remote_field.model.objects.all()
    #     print(queryset)

    # queryset=models.WorkShop.objects.values_list('name').distinct()
    # print(queryset)
    # print(type(queryset))
    # from django.db.models.query import QuerySet
    # for item in queryset:
    #     print(item[0])
    from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
    # val=getattr(models.Procedure,'product').get_queryset()
    # print(val)

    obj=models.PaymentRecord.objects.filter(id=2).first()
    field_obj=models.PaymentRecord._meta.get_field('confirm_user')
    print(field_obj.get_choices())#[('', '---------'), (7, '李杰'), (15, '李材')]
    # field_obj=models.Customer._meta.get_field('status')  #[('', '---------'), (1, '已签合同'), (2, '未签合同')]
    # print(field_obj.get_choices())
    # print(type(field_obj))
    # print(field_obj.remote_field.model)
    # print(getattr(obj,'confirm_user_id'
    #               ))
    # val=getattr(obj,'confirm_date')
    # m=getattr(obj,'confirm_user')
    # print(obj.confirm_user_id)
    # print(obj.confirm_user.id)
    return HttpResponse('...')

from django.db.models.fields.related import ForeignKey
from django.db.models.fields.reverse_related import ManyToOneRel

class DeletePrintOrderView(View):
    """删除印刷订单及其明细（改为只删 PrintOrderFlat）"""
    
    def get(self, request, order_id):
        """GET方法：显示删除确认页面"""
        from crm.models import PrintOrderFlat
        try:
            # 查找主信息记录
            main = PrintOrderFlat.objects.filter(id=order_id, detail_type=None).first()
            if not main:
                main = PrintOrderFlat.objects.filter(order_no=order_id, detail_type=None).first()
            if not main:
                return JsonResponse({'status': False, 'message': '订单不存在'})
            
            return render(request, 'delete_print_order.html', {'order': main})
        except Exception as e:
            return JsonResponse({'status': False, 'message': f'访问失败: {str(e)}'})
    
    def post(self, request, order_id):
        """POST方法：执行删除操作"""
        from django.http import JsonResponse, HttpResponseRedirect
        from django.urls import reverse
        from crm.models import PrintOrderFlat
        try:
            # 先查主信息
            main = PrintOrderFlat.objects.filter(id=order_id, detail_type=None).first()
            if not main:
                main = PrintOrderFlat.objects.filter(order_no=order_id, detail_type=None).first()
            if not main:
                return JsonResponse({'status': False, 'message': '订单不存在'})
            
            order_no = main.order_no
            # 删除所有同 order_no 的记录（包括主信息和相关明细）
            deleted_count = PrintOrderFlat.objects.filter(order_no=order_no).delete()[0]
            
            print(f'成功删除订单 {order_no}，共删除 {deleted_count} 条记录')
            
            # 检查请求类型返回对应响应
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('content-type') == 'application/json':
                return JsonResponse({'status': True, 'message': f'订单 {order_no} 删除成功'})
            else:
                return HttpResponseRedirect(reverse('print_order_list'))
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': False, 'message': f'删除失败: {str(e)}'})

class EditPrintOrderView(View):
    """编辑印刷订单（改为操作 PrintOrderFlat 主信息）"""
    def get(self, request, order_id):
        from crm.models import PrintOrderFlat
        order = get_object_or_404(PrintOrderFlat, id=order_id, detail_type=None)
        return render(request, 'edit_print_order.html', {'order': order})

    def post(self, request, order_id):
        from crm.models import PrintOrderFlat
        from datetime import datetime
        import json
        
        order = get_object_or_404(PrintOrderFlat, id=order_id, detail_type=None)
        
        # 获取模型所有字段名
        model_fields = [f.name for f in order._meta.get_fields() if not f.is_relation or f.one_to_one or (f.many_to_one and f.related_model)]
        
        # 允许编辑的字段（主信息区）
        editable_fields = [
            'order_no', 'work_order_no', 'customer_name', 'product_name', 'product_size', 'order_date', 'delivery_date', 'salesman',
            'contact_person', 'contact_phone', 'design_requirement', 'customer_supply', 'product_description',
            'imposition_requirement', 'consumption_requirement', 'print_tech_requirement', 'quality_requirement', 
            'delivery_pack_requirement', 'note', 'customer_signature', 'order_maker', 'auditor', 'quantity', 'unit'
        ]
        
        # 处理特殊字段
        def parse_date(date_str):
            if not date_str:
                return None
            from django.utils import timezone
            try:
                naive_dt = datetime.strptime(date_str, '%Y-%m-%d')
                # 转换为timezone-aware datetime
                return timezone.make_aware(naive_dt, timezone.get_current_timezone())
            except:
                return None
        
        # 处理主信息字段
        for field in editable_fields:
            if field in model_fields:
                value = request.POST.get(field, getattr(order, field))
                
                # 处理日期字段
                if field in ['order_date', 'delivery_date']:
                    value = parse_date(value)
                # 处理数量字段
                elif field == 'quantity':
                    try:
                        value = int(value) if value else None
                    except:
                        value = getattr(order, field)
                
                setattr(order, field, value)
        
        # 处理JSON明细数据
        def collect_detail_data(prefix):
            """收集明细数据并转换为JSON格式"""
            detail_data = []
            index = 0
            while True:
                # 检查是否存在当前索引的数据
                has_data = False
                row_data = {}
                
                # 遍历POST数据，查找匹配的字段
                for key, value in request.POST.items():
                    if key.startswith(f'{prefix}[{index}][') and value.strip():
                        # 提取字段名：如 material[0][序] -> 序
                        field_name = key.split('[')[2].rstrip(']')
                        row_data[field_name] = value.strip()
                        has_data = True
                
                if not has_data:
                    break
                    
                if row_data:  # 只添加非空行
                    detail_data.append(row_data)
                index += 1
            
            return detail_data
        
        # 收集四个明细区的数据
        material_data = collect_detail_data('material')
        prepress_data = collect_detail_data('prepress')
        process_data = collect_detail_data('process')
        postpress_data = collect_detail_data('postpress')
        
        # 更新JSON字段
        order.material_json = json.dumps(material_data, ensure_ascii=False)
        order.prepress_json = json.dumps(prepress_data, ensure_ascii=False)
        order.process_json = json.dumps(process_data, ensure_ascii=False)
        order.postpress_json = json.dumps(postpress_data, ensure_ascii=False)
        
        order.save()
        return redirect('print_order_detail', order_id=order.id)

class ViewJsonDataView(View):
    """查看PrintOrderFlat的四个JSON字段内容"""
    
    def get(self, request, order_id=None):
        from crm.models import PrintOrderFlat
        import json
        
        try:
            if order_id:
                # 查看指定订单的JSON数据
                order = PrintOrderFlat.objects.filter(id=order_id, detail_type=None).first()
                if not order:
                    order = PrintOrderFlat.objects.filter(order_no=order_id, detail_type=None).first()
                if not order:
                    return HttpResponse('订单不存在')
                orders = [order]
            else:
                # 查看所有订单的JSON数据
                orders = PrintOrderFlat.objects.filter(detail_type=None).order_by('-id')[:5]  # 最近5个订单
                
            result_html = '<html><head><meta charset="utf-8"><title>JSON字段查看</title></head><body>'
            result_html += '<h1>PrintOrderFlat 四个JSON字段内容</h1>'
            
            for order in orders:
                result_html += f'<h2>订单号: {order.order_no} (ID: {order.id})</h2>'
                
                # 用料明细JSON
                result_html += '<h3>1. 用料明细JSON (material_json):</h3>'
                try:
                    material_data = json.loads(order.material_json or '[]')
                    result_html += f'<pre>{json.dumps(material_data, ensure_ascii=False, indent=2)}</pre>'
                except:
                    result_html += f'<pre>{order.material_json or "空"}</pre>'
                
                # 印前明细JSON
                result_html += '<h3>2. 印前明细JSON (prepress_json):</h3>'
                try:
                    prepress_data = json.loads(order.prepress_json or '[]')
                    result_html += f'<pre>{json.dumps(prepress_data, ensure_ascii=False, indent=2)}</pre>'
                except:
                    result_html += f'<pre>{order.prepress_json or "空"}</pre>'
                
                # 印刷明细JSON
                result_html += '<h3>3. 印刷明细JSON (process_json):</h3>'
                try:
                    process_data = json.loads(order.process_json or '[]')
                    result_html += f'<pre>{json.dumps(process_data, ensure_ascii=False, indent=2)}</pre>'
                except:
                    result_html += f'<pre>{order.process_json or "空"}</pre>'
                
                # 印后明细JSON
                result_html += '<h3>4. 印后明细JSON (postpress_json):</h3>'
                try:
                    postpress_data = json.loads(order.postpress_json or '[]')
                    result_html += f'<pre>{json.dumps(postpress_data, ensure_ascii=False, indent=2)}</pre>'
                except:
                    result_html += f'<pre>{order.postpress_json or "空"}</pre>'
                
                result_html += '<hr>'
                
            result_html += '</body></html>'
            return HttpResponse(result_html)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return HttpResponse(f'查看失败: {str(e)}')
    
    def post(self, request):
        """通过POST打印所有JSON数据到控制台"""
        from crm.models import PrintOrderFlat
        import json
        
        try:
            orders = PrintOrderFlat.objects.filter(detail_type=None).order_by('-id')[:5]
            
            print('\n' + '='*50)
            print('打印PrintOrderFlat的四个JSON字段内容')
            print('='*50)
            
            for order in orders:
                print(f'\n订单号: {order.order_no} (ID: {order.id})')
                print('-'*30)
                
                print('1. 用料明细JSON:')
                try:
                    material_data = json.loads(order.material_json or '[]')
                    print(json.dumps(material_data, ensure_ascii=False, indent=2))
                except:
                    print(order.material_json or "空")
                
                print('\n2. 印前明细JSON:')
                try:
                    prepress_data = json.loads(order.prepress_json or '[]')
                    print(json.dumps(prepress_data, ensure_ascii=False, indent=2))
                except:
                    print(order.prepress_json or "空")
                
                print('\n3. 印刷明细JSON:')
                try:
                    process_data = json.loads(order.process_json or '[]')
                    print(json.dumps(process_data, ensure_ascii=False, indent=2))
                except:
                    print(order.process_json or "空")
                
                print('\n4. 印后明细JSON:')
                try:
                    postpress_data = json.loads(order.postpress_json or '[]')
                    print(json.dumps(postpress_data, ensure_ascii=False, indent=2))
                except:
                    print(order.postpress_json or "空")
                
                print('\n' + '='*50)
            
            return JsonResponse({'status': True, 'message': '已在控制台打印JSON数据'})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': False, 'message': f'打印失败: {str(e)}'})

class OrderProgressView(View):
    """订单进度管理页面"""
    
    def get(self, request, order_id):
        from crm.models import PrintOrderFlat, OrderProgress
        try:
            # 获取订单
            order = get_object_or_404(PrintOrderFlat, id=order_id, detail_type=None)
            
            # 获取所有进度步骤
            all_steps = OrderProgress.objects.filter(order=order).order_by('step_order')
            
            # 按步骤分类进行分组
            cover_steps = all_steps.filter(step_category='cover')
            content_steps = all_steps.filter(step_category='content')
            
            # 关键函数：判断一个分类内的步骤是否可以开始
            def get_step_list_with_can_start(steps, category):
                step_list = []
                for step in steps:
                    can_start = True  # 默认可以开始
                    if step.status == 1:  # 仅当步骤是“待开始”时才检查
                        # 检查在 *相同分类* 中，是否有排序在它之前的步骤还未完成
                        previous_incomplete = OrderProgress.objects.filter(
                            order=order,
                            step_category=category,  # 关键：限制在同分类
                            step_order__lt=step.step_order,
                            status__in=[1, 2]  # 状态为“待开始”或“进行中”
                        ).exists()
                        # 如果存在未完成的前置步骤，则不能开始
                        can_start = not previous_incomplete
                    step_list.append({'step': step, 'can_start': can_start})
                return step_list

            cover_step_list = get_step_list_with_can_start(cover_steps, 'cover')
            content_step_list = get_step_list_with_can_start(content_steps, 'content')

            # 为每个分类计算进度统计
            def get_progress_stats(steps):
                total = steps.count()
                if total == 0:
                    return None # 如果该分类没有步骤，则不返回统计信息
                completed = steps.filter(status=3).count()
                in_progress = steps.filter(status=2).count()
                pending = steps.filter(status=1).count()
                skipped = steps.filter(status=4).count()
                finished = completed + skipped
                percentage = int((finished / total * 100)) if total > 0 else 0
                return {
                    'total': total,
                    'completed': completed,
                    'in_progress': in_progress,
                    'pending': pending,
                    'percentage': percentage
                }

            cover_progress = get_progress_stats(cover_steps)
            content_progress = get_progress_stats(content_steps)
            
            context = {
                'order': order,
                'cover_step_list': cover_step_list,
                'content_step_list': content_step_list,
                'cover_progress': cover_progress,
                'content_progress': content_progress,
                'error': None
            }
            
            return render(request, 'order_progress.html', context)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render(request, 'order_progress.html', {'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class StartProgressStepView(View):
    """开始进度步骤"""
    
    def get(self, request, step_id):
        """GET方法用于测试"""
        print(f"=== StartProgressStepView GET 测试请求 ===")
        print(f"步骤ID: {step_id}")
        return JsonResponse({'status': True, 'message': 'GET测试成功', 'step_id': step_id})
    
    @method_decorator(require_step_permission('start'))
    def post(self, request, step_id):
        """开始步骤 - 已通过权限装饰器验证"""
        print(f"=== StartProgressStepView POST 请求开始 ===")
        print(f"步骤ID: {step_id}")
        print(f"权限检查已通过，用户: {request.current_user.name}")
        
        try:
            # 从装饰器获取已验证的对象
            step = request.current_step
            user = request.current_user
            
            print(f"找到步骤: {step.step_name}, 当前状态: {step.status} ({step.get_status_display()})")
            
            if step.status != 1:  # 只有待开始的步骤才能开始
                error_msg = '该步骤当前状态不允许开始'
                print(f"❌ 步骤状态不正确: {step.status}")
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '', True, '', False, error_msg, '', request
                )
                return JsonResponse({'status': False, 'message': error_msg})
            
            # 检查是否有前置步骤未完成
            previous_steps = OrderProgress.objects.filter(
                order=step.order,
                step_category=step.step_category,
                step_order__lt=step.step_order
            ).exclude(status__in=[3, 4])  # 排除已完成和已跳过的步骤
            
            if previous_steps.exists():
                incomplete_steps = [s.step_name for s in previous_steps]
                error_msg = f'请先完成前置步骤：{", ".join(incomplete_steps)}'
                print(f"❌ 有未完成的前置步骤: {incomplete_steps}")
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'start',
                    user, '', True, '', False, error_msg, '', request
                )
                return JsonResponse({'status': False, 'message': error_msg})
            
            # 检查上个步骤是否留下备注
            previous_step = OrderProgress.objects.filter(
                order=step.order,
                step_order__lt=step.step_order,
                status__in=[3, 4]  # 已完成或已跳过的步骤
            ).order_by('-step_order').first()
            
            if previous_step and previous_step.note and previous_step.note.strip():
                print(f"⚠️ 上个步骤 '{previous_step.step_name}' 有备注: {previous_step.note}")
                return JsonResponse({
                    'status': False,
                    'need_confirmation': True,
                    'previous_step_name': previous_step.step_name,
                    'previous_step_note': previous_step.note,
                    'message': f'上个步骤 "{previous_step.step_name}" 留下了备注，请注意查看'
                })
            
            print("✅ 所有验证通过，开始执行步骤")
            step.start_step(user)
            print(f"✅ 步骤开始成功，新状态: {step.status}")
            
            # 记录成功操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'start',
                user, '权限装饰器验证', True, '', True, '', f'步骤已开始', request
            )
            
            response_data = {
                'status': True,
                'message': f'步骤 "{step.step_name}" 已开始',
                'new_status': step.get_status_display(),
                'operator': user.name,
                'start_time': step.start_time.strftime('%Y-%m-%d %H:%M:%S') if step.start_time else ''
            }
            print(f"✅ 返回响应数据: {response_data}")
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            print(f"❌ 异常发生: {str(e)}")
            traceback.print_exc()
            error_message = str(e) if str(e) and str(e) != 'None' else '发生未知错误，请检查系统日志'
            
            # 记录失败操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'start',
                user, '权限装饰器验证', True, '', False, error_message, '', request
            )
            
            error_response = {'status': False, 'message': f'操作失败: {error_message}'}
            print(f"❌ 返回错误响应: {error_response}")
            return JsonResponse(error_response)

@method_decorator(csrf_exempt, name='dispatch')
class ConfirmStartProgressStepView(View):
    """确认开始进度步骤（当上个步骤有备注时）"""
    
    def post(self, request, step_id):
        from crm.models import OrderProgress, UserInfo
        print(f"=== ConfirmStartProgressStepView POST 请求开始 ===")
        print(f"步骤ID: {step_id}")
        
        try:
            step = get_object_or_404(OrderProgress, id=step_id)
            print(f"找到步骤: {step.step_name}, 当前状态: {step.status} ({step.get_status_display()})")
            
            # 从session获取当前登录用户
            user_id = request.session.get('user_id')
            print(f"从session获取的user_id: {user_id}")
            
            if not user_id:
                print("❌ 用户未登录")
                return JsonResponse({'status': False, 'message': '用户未登录，请重新登录'})
            
            user = UserInfo.objects.filter(id=user_id).first()
            if not user:
                print(f"❌ 用户ID {user_id} 不存在")
                return JsonResponse({'status': False, 'message': '用户信息不存在，请重新登录'})
            
            print(f"找到用户: {user.name} (ID: {user.id})")
            
            if step.status != 1:  # 只有待开始的步骤才能开始
                print(f"❌ 步骤状态不正确: {step.status}, 只能开始状态为1的步骤")
                return JsonResponse({'status': False, 'message': '该步骤当前状态不允许开始'})
            
            # 检查是否有前置步骤未完成
            previous_steps = OrderProgress.objects.filter(
                order=step.order,
                step_category=step.step_category,
                step_order__lt=step.step_order
            ).exclude(status__in=[3, 4])  # 排除已完成和已跳过的步骤
            
            if previous_steps.exists():
                incomplete_steps = [s.step_name for s in previous_steps]
                print(f"❌ 有未完成的前置步骤: {incomplete_steps}")
                return JsonResponse({
                    'status': False, 
                    'message': f'请先完成前置步骤：{", ".join(incomplete_steps)}'
                })
            
            print("✅ 用户确认开始步骤，执行步骤开始")
            step.start_step(user)
            print(f"✅ 步骤开始成功，新状态: {step.status}")
            
            response_data = {
                'status': True,
                'message': f'步骤 "{step.step_name}" 已开始',
                'new_status': step.get_status_display(),
                'operator': user.name,
                'start_time': step.start_time.strftime('%Y-%m-%d %H:%M:%S') if step.start_time else ''
            }
            print(f"✅ 返回响应数据: {response_data}")
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            print(f"❌ 异常发生: {str(e)}")
            traceback.print_exc()
            error_message = str(e) if str(e) and str(e) != 'None' else '发生未知错误，请检查系统日志'
            error_response = {'status': False, 'message': f'操作失败: {error_message}'}
            print(f"❌ 返回错误响应: {error_response}")
            return JsonResponse(error_response)

@method_decorator(csrf_exempt, name='dispatch')
class CompleteProgressStepView(View):
    """完成进度步骤"""
    
    @method_decorator(require_step_permission('complete'))
    def post(self, request, step_id):
        """完成步骤 - 已通过权限装饰器验证"""
        import json
        print(f"=== CompleteProgressStepView POST 请求开始 ===")
        print(f"步骤ID: {step_id}")
        print(f"权限检查已通过，用户: {request.current_user.name}")
        
        try:
            # 从装饰器获取已验证的对象
            step = request.current_step
            user = request.current_user
            
            if step.status not in [1, 2]:  # 只有待开始或进行中的步骤才能完成
                error_msg = '该步骤当前状态不允许完成'
                print(f"❌ 步骤状态不正确: {step.status}")
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'complete',
                    user, '', True, '', False, error_msg, '', request
                )
                return JsonResponse({'status': False, 'message': error_msg})
            
            # 获取备注信息
            data = json.loads(request.body) if request.body else {}
            note = data.get('note', '')
            
            print(f"完成步骤: {step.step_name}, 备注: {note}")
            is_all_completed = step.complete_step(user, note)
            
            # 记录成功操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'complete',
                user, '权限装饰器验证', True, '', True, '', f'步骤已完成，备注: {note}', request
            )
            
            response_data = {
                'status': True,
                'message': f'步骤 "{step.step_name}" 已完成',
                'new_status': step.get_status_display(),
                'confirm_user': user.name,
                'end_time': step.end_time.strftime('%Y-%m-%d %H:%M:%S') if step.end_time else '',
                'all_completed': is_all_completed
            }
            
            if is_all_completed:
                response_data['message'] += '，所有步骤已完成！'
            
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_message = str(e) if str(e) and str(e) != 'None' else '发生未知错误，请检查系统日志'
            return JsonResponse({'status': False, 'message': f'操作失败: {error_message}'})

@method_decorator(csrf_exempt, name='dispatch')
class SkipProgressStepView(View):
    """跳过进度步骤"""
    
    @method_decorator(require_step_permission('skip'))
    def post(self, request, step_id):
        """跳过步骤 - 已通过权限装饰器验证"""
        import json
        print(f"=== SkipProgressStepView POST 请求开始 ===")
        print(f"步骤ID: {step_id}")
        print(f"权限检查已通过，用户: {request.current_user.name}")
        
        try:
            # 从装饰器获取已验证的对象
            step = request.current_step
            user = request.current_user
            
            if step.status not in [1, 2]:  # 只有待开始或进行中的步骤才能跳过
                error_msg = '该步骤当前状态不允许跳过'
                print(f"❌ 步骤状态不正确: {step.status}")
                log_step_operation(
                    step.order.order_no, step.step_name, 
                    getattr(step.order, 'print_type', 'cover'), 'skip',
                    user, '', True, '', False, error_msg, '', request
                )
                return JsonResponse({'status': False, 'message': error_msg})
            
            # 获取跳过原因
            data = json.loads(request.body) if request.body else {}
            reason = data.get('reason', '')
            
            print(f"跳过步骤: {step.step_name}, 原因: {reason}")
            step.skip_step(user, reason)
            
            # 记录成功操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'skip',
                user, '权限装饰器验证', True, '', True, '', f'步骤已跳过，原因: {reason}', request
            )
            
            response_data = {
                'status': True,
                'message': f'步骤 "{step.step_name}" 已跳过',
                'new_status': step.get_status_display(),
                'confirm_user': user.name,
                'end_time': step.end_time.strftime('%Y-%m-%d %H:%M:%S') if step.end_time else ''
            }
            
            print(f"✅ 步骤跳过成功: {response_data}")
            return JsonResponse(response_data)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_message = str(e) if str(e) and str(e) != 'None' else '发生未知错误，请检查系统日志'
            
            # 记录失败操作日志
            log_step_operation(
                step.order.order_no, step.step_name, 
                getattr(step.order, 'print_type', 'cover'), 'skip',
                user, '权限装饰器验证', True, '', False, error_message, '', request
            )
            
            return JsonResponse({'status': False, 'message': f'操作失败: {error_message}'})