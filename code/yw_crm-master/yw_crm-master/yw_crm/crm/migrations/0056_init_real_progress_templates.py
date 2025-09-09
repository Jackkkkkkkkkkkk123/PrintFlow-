# Generated manually to initialize real printing progress templates

from django.db import migrations


def create_progress_templates(apps, schema_editor):
    """创建基于实际印刷流程的进度模板"""
    OrderProgressTemplate = apps.get_model('crm', 'OrderProgressTemplate')
    
    # 清除旧的模板数据
    OrderProgressTemplate.objects.all().delete()
    
    # 封面印刷步骤（基于样例文件）
    cover_steps = [
        {'name': '印刷', 'description': '封面印刷', 'required': True},
        {'name': '覆膜', 'description': '覆膜工艺', 'required': False},
        {'name': '烫金', 'description': '烫金工艺', 'required': False},
        {'name': '压痕', 'description': '压痕工艺', 'required': False},
        {'name': '压纹', 'description': '压纹工艺', 'required': False},
        {'name': '模切', 'description': '模切工艺', 'required': False},
        {'name': '击凸', 'description': '击凸工艺', 'required': False},
        {'name': '过油', 'description': '过油工艺', 'required': False},
        {'name': '外调', 'description': '外调加工', 'required': False}
    ]
    
    # 内文印刷步骤（基于样例文件）
    content_steps = [
        {'name': '调图', 'description': '图像调整', 'required': True},
        {'name': 'CTP', 'description': 'CTP制版', 'required': True},
        {'name': '切纸', 'description': '切纸准备', 'required': True},
        {'name': '印刷', 'description': '内文印刷', 'required': True},
        {'name': '折页', 'description': '折页工序', 'required': False},
        {'name': '锁线', 'description': '锁线装订', 'required': False},
        {'name': '胶包', 'description': '胶装包书', 'required': False},
        {'name': '马订', 'description': '马订装订', 'required': False},
        {'name': '勒口', 'description': '勒口工艺', 'required': False},
        {'name': '夹卡片', 'description': '夹卡片', 'required': False},
        {'name': '配本(塑封)', 'description': '配本塑封', 'required': False},
        {'name': '打包', 'description': '打包工序', 'required': True},
        {'name': '送货', 'description': '送货配送', 'required': True}
    ]
    
    # 封面+内文步骤（合并）
    both_steps = [
        # 封面步骤
        {'name': '封面印刷', 'description': '封面印刷', 'required': True},
        {'name': '覆膜', 'description': '封面覆膜工艺', 'required': False},
        {'name': '烫金', 'description': '封面烫金工艺', 'required': False},
        {'name': '压痕', 'description': '封面压痕工艺', 'required': False},
        {'name': '压纹', 'description': '封面压纹工艺', 'required': False},
        {'name': '模切', 'description': '封面模切工艺', 'required': False},
        {'name': '击凸', 'description': '封面击凸工艺', 'required': False},
        {'name': '过油', 'description': '封面过油工艺', 'required': False},
        # 内文步骤
        {'name': '调图', 'description': '内文图像调整', 'required': True},
        {'name': 'CTP', 'description': '内文CTP制版', 'required': True},
        {'name': '切纸', 'description': '内文切纸准备', 'required': True},
        {'name': '内文印刷', 'description': '内文印刷', 'required': True},
        {'name': '折页', 'description': '内文折页工序', 'required': False},
        {'name': '锁线', 'description': '锁线装订', 'required': False},
        {'name': '胶包', 'description': '胶装包书', 'required': False},
        {'name': '马订', 'description': '马订装订', 'required': False},
        {'name': '勒口', 'description': '勒口工艺', 'required': False},
        {'name': '夹卡片', 'description': '夹卡片', 'required': False},
        {'name': '配本(塑封)', 'description': '配本塑封', 'required': False},
        {'name': '打包', 'description': '打包工序', 'required': True},
        {'name': '送货', 'description': '送货配送', 'required': True}
    ]
    
    # 创建封面印刷模板
    for i, step in enumerate(cover_steps, 1):
        OrderProgressTemplate.objects.create(
            print_type='cover',
            step_name=step['name'],
            step_order=i,
            description=step['description'],
            is_required=step['required'],
            estimated_hours=1
        )
    
    # 创建内文印刷模板
    for i, step in enumerate(content_steps, 1):
        OrderProgressTemplate.objects.create(
            print_type='content',
            step_name=step['name'],
            step_order=i,
            description=step['description'],
            is_required=step['required'],
            estimated_hours=1
        )
    
    # 创建封面+内文模板
    for i, step in enumerate(both_steps, 1):
        OrderProgressTemplate.objects.create(
            print_type='both',
            step_name=step['name'],
            step_order=i,
            description=step['description'],
            is_required=step['required'],
            estimated_hours=1
        )


def remove_progress_templates(apps, schema_editor):
    """删除进度模板"""
    OrderProgressTemplate = apps.get_model('crm', 'OrderProgressTemplate')
    OrderProgressTemplate.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0055_printorderflat_print_type_printorderflat_status_and_more'),
    ]

    operations = [
        migrations.RunPython(create_progress_templates, remove_progress_templates),
    ] 