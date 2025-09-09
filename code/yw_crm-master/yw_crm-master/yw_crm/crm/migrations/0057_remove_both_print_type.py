# Generated manually to remove 'both' print type

from django.db import migrations

def remove_both_print_type(apps, schema_editor):
    """删除'both'印刷类型的相关数据"""
    PrintOrderFlat = apps.get_model('crm', 'PrintOrderFlat')
    OrderProgressTemplate = apps.get_model('crm', 'OrderProgressTemplate')
    
    # 将现有的'both'类型订单改为'cover'类型
    updated_orders = PrintOrderFlat.objects.filter(print_type='both').update(print_type='cover')
    print(f"已将 {updated_orders} 个'both'类型订单改为'cover'类型")
    
    # 删除'both'类型的进度模板
    deleted_templates = OrderProgressTemplate.objects.filter(print_type='both').delete()[0]
    print(f"已删除 {deleted_templates} 个'both'类型的进度模板")

def reverse_remove_both_print_type(apps, schema_editor):
    """反向操作：恢复both类型（如果需要回滚）"""
    # 这里不做具体操作，因为数据已经转换了
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0056_init_real_progress_templates'),
    ]

    operations = [
        migrations.RunPython(remove_both_print_type, reverse_remove_both_print_type),
    ] 