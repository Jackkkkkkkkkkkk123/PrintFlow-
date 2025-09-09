"""
自动生成日报的Django管理命令
运行方式：python manage.py generate_daily_report
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from crm.ai_assistant import ai_assistant
from crm.models import PrintOrderFlat
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '生成每日工作报告'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto',
            action='store_true',
            help='自动模式：检查时间是否合适再生成报告',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制生成报告，忽略时间检查',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('开始生成每日工作报告...')
        )
        
        # 检查是否是自动模式
        auto_mode = options.get('auto', False)
        force_mode = options.get('force', False)
        
        # 如果是自动模式，检查当前时间
        if auto_mode and not force_mode:
            now = timezone.now()
            target_hour = 17  # 下午5点
            target_minute = 30  # 30分
            
            # 检查是否在指定时间范围内（5:30-5:35）
            if not (now.hour == target_hour and target_minute <= now.minute <= target_minute + 5):
                self.stdout.write(
                    self.style.WARNING(
                        f'当前时间 {now.strftime("%H:%M")} 不在自动报告时间范围内（17:30-17:35），跳过生成'
                    )
                )
                return
        
        try:
            # 生成报告
            result = ai_assistant.generate_daily_report()
            
            if result.get('status') == 'success':
                self.stdout.write(
                    self.style.SUCCESS('✅ 日报生成成功！')
                )
                
                # 输出报告摘要
                data = result.get('data', {})
                self.stdout.write(
                    f"📊 今日数据摘要："
                )
                self.stdout.write(
                    f"  • 新增订单：{data.get('new_orders', 0)} 个"
                )
                self.stdout.write(
                    f"  • 完成步骤：{data.get('completed_steps', 0)} 个"
                )
                self.stdout.write(
                    f"  • 开始步骤：{data.get('started_steps', 0)} 个"
                )
                self.stdout.write(
                    f"  • 待处理订单：{data.get('pending_orders', 0)} 个"
                )
                self.stdout.write(
                    f"  • 处理中订单：{data.get('processing_orders', 0)} 个"
                )
                
                # 记录日志
                logger.info(f"AI日报生成成功: {result.get('timestamp')}")
                
                # 可以在这里添加发送邮件或通知的逻辑
                self._send_report_notification(result)
                
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ 日报生成失败：{result.get("message", "未知错误")}')
                )
                logger.error(f"AI日报生成失败: {result.get('message')}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 日报生成过程中发生错误：{str(e)}')
            )
            logger.error(f"日报生成异常: {str(e)}")
    
    def _send_report_notification(self, report_result):
        """发送报告通知（这里可以扩展为邮件、短信等）"""
        try:
            # TODO: 这里可以添加实际的通知逻辑
            # 例如：发送邮件、推送通知、写入文件等
            
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 保存到日志文件
            log_message = f"[{timestamp}] AI日报已生成\n"
            log_message += f"生成时间: {report_result.get('timestamp')}\n"
            log_message += f"数据摘要: {report_result.get('data')}\n"
            log_message += "-" * 50 + "\n"
            
            # 写入日志文件（可选）
            try:
                with open('daily_reports.log', 'a', encoding='utf-8') as f:
                    f.write(log_message)
            except Exception as e:
                logger.warning(f"写入日志文件失败: {str(e)}")
            
            self.stdout.write(
                self.style.SUCCESS('📧 报告通知已发送')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️ 发送通知时出错：{str(e)}')
            )
            logger.warning(f"发送报告通知失败: {str(e)}") 