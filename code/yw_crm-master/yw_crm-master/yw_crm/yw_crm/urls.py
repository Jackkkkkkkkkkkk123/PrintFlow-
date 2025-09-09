"""yw_crm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from stark.service.stark import site
from crm import views as crm_views
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
import sys
import os

# 添加项目根目录到Python路径，以便导入views.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import views  # 导入根目录的views.py（包含移动端视图）

def root_redirect(request):
    """根路径重定向：未登录跳转到登录页，已登录跳转到首页"""
    if not request.session.get('user_id'):
        return redirect('/login/')
    return redirect('/index/')

urlpatterns = [
    path('', root_redirect, name='root'),  # 添加根路径重定向
    path('verify_code/', crm_views.verify_code),
    path('admin/', admin.site.urls),
    path('stark/',site.urls),
    path('rbac/', include('rbac.urls',namespace='rbac')),
    path('login/',crm_views.LoginView.as_view(),name='login'),
    path('logout/', crm_views.LogoutView.as_view(), name='logout'),

    path('index/', views.IndexView.as_view(), name='index'),

    path('reset/', crm_views.ResetView.as_view(), name='reset'),
    # path('reset/', views.reset,name='reset'),

    path('test/', crm_views.test),

    # 印刷订单管理URL
    path('print-orders/', crm_views.PrintOrderListView.as_view(), name='print_order_list'),
    path('print-orders/create/', crm_views.CreatePrintOrderView.as_view(), name='create_print_order'),
    path('print-orders/<int:order_id>/', crm_views.PrintOrderDetailView.as_view(), name='print_order_detail'),
    path('print-orders/delete/<int:order_id>/', crm_views.DeletePrintOrderView.as_view(), name='delete_print_order'),
    path('print-orders/edit/<int:order_id>/', crm_views.EditPrintOrderView.as_view(), name='edit_print_order'),
    path('print-orders/<int:order_id>/progress/', crm_views.OrderProgressView.as_view(), name='order_progress'),
    path('progress/start/<int:step_id>/', crm_views.StartProgressStepView.as_view(), name='start_progress_step'),
    path('progress/confirm-start/<int:step_id>/', crm_views.ConfirmStartProgressStepView.as_view(), name='confirm_start_progress_step'),
    path('progress/complete/<int:step_id>/', crm_views.CompleteProgressStepView.as_view(), name='complete_progress_step'),
    path('progress/skip/<int:step_id>/', crm_views.SkipProgressStepView.as_view(), name='skip_progress_step'),
    path('print-progress/<int:process_id>/', crm_views.PrintProgressView.as_view(), name='print_progress'),
    path('confirm-step/<int:step_id>/', crm_views.ConfirmStepView.as_view(), name='confirm_step'),
    path('print-dashboard/', crm_views.PrintDashboardView.as_view(), name='print_dashboard'),
    # 查看JSON数据
    path('view-json/', crm_views.ViewJsonDataView.as_view(), name='view_json_data'),
    path('view-json/<int:order_id>/', crm_views.ViewJsonDataView.as_view(), name='view_json_data_detail'),

    # ==================
    # 手机端URL路由
    # ==================
    # 手机端订单页面（普通用户）
    path('mobile/orders/', views.MobileOrdersView.as_view(), name='mobile_orders'),
    # 手机端仪表板（root用户）
    path('mobile/dashboard/', views.MobileDashboardView.as_view(), name='mobile_dashboard'),
    # 手机端订单详情
    path('mobile/orders/<int:order_id>/', views.MobileOrderDetailView.as_view(), name='mobile_order_detail'),
    # 手机端AI助手（root用户）
    path('mobile/ai-assistant/', views.MobileAIAssistantView.as_view(), name='mobile_ai_assistant'),
    
    # ==================
    # 手机端API接口
    # ==================
    # 订单状态API
    path('api/mobile/orders/<int:order_id>/status/', views.MobileOrderStatusAPI.as_view(), name='mobile_order_status_api'),
    
    # ==================
    # AI助手API接口
    # ==================
    # AI生成日报
    path('api/ai/daily-report/', views.AIGenerateDailyReportAPI.as_view(), name='ai_daily_report'),
    # AI异常分析
    path('api/ai/analyze-anomalies/', views.AIAnalyzeAnomaliesAPI.as_view(), name='ai_analyze_anomalies'),
    # AI交期检查
    path('api/ai/check-deadlines/', views.AICheckDeadlinesAPI.as_view(), name='ai_check_deadlines'),
    
    # ==================
    # 对话AI API接口
    # ==================
    # 流式对话（推荐，更快响应）
    path('api/conversation/stream/', views.ConversationStreamAPI.as_view(), name='conversation_stream'),
    # 对话聊天
    path('api/conversation/chat/', views.ConversationChatAPI.as_view(), name='conversation_chat'),
    # 对话历史
    path('api/conversation/history/', views.ConversationHistoryAPI.as_view(), name='conversation_history'),
    # 对话测试
    path('api/conversation/test/', views.ConversationTestAPI.as_view(), name='conversation_test'),
    
    # ==================
    # 设备检测测试API
    # ==================
    # 设备检测测试
    path('api/test/device-detection/', views.DeviceDetectionTestAPI.as_view(), name='test_device_detection'),
    
    # ==================
    # 手机端步骤操作API
    # ==================
    # 开始步骤
    path('api/mobile/start-step/<int:step_id>/', views.MobileStartStepAPI.as_view(), name='mobile_start_step'),
    # 确认开始步骤（已查看备注）
    path('api/mobile/confirm-start-step/<int:step_id>/', views.MobileConfirmStartStepAPI.as_view(), name='mobile_confirm_start_step'),
    # 完成步骤
    path('api/mobile/complete-step/<int:step_id>/', views.MobileCompleteStepAPI.as_view(), name='mobile_complete_step'),
    # 跳过步骤
    path('api/mobile/skip-step/<int:step_id>/', views.MobileSkipStepAPI.as_view(), name='mobile_skip_step'),

]

# 在开发环境下提供静态文件服务
if settings.DEBUG:
    from django.contrib.staticfiles.views import serve
    from django.views.static import serve as static_serve
    from django.urls import re_path
    
    # 使用Django内置的静态文件服务
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve),
    ]
