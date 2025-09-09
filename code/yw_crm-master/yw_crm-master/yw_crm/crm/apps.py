from django.apps import AppConfig


class CrmConfig(AppConfig):
    name = 'crm'
    
    def ready(self):
        """
        应用准备就绪时导入信号处理器
        """
        import crm.signals
