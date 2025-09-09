"""
CRM工具函数
"""
import re
from django.http import HttpRequest


def is_mobile_device(request: HttpRequest) -> bool:
    """
    检测是否为移动设备
    
    Args:
        request: Django请求对象
        
    Returns:
        bool: True表示移动设备，False表示PC设备
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # 首先检查明确的桌面系统标识 - 如果匹配则直接返回False
    desktop_agents = [
        'windows nt', 'win64', 'win32', 'x86_64', 'amd64',
        'macintosh', 'mac os x', 'intel mac',
        'linux', 'x11', 'ubuntu', 'fedora', 'centos'
    ]
    
    for agent in desktop_agents:
        if agent in user_agent:
            # 额外检查：排除移动版本的桌面浏览器
            if 'mobile' not in user_agent and 'mobi' not in user_agent:
                return False
    
    # 移动设备User-Agent特征
    mobile_agents = [
        'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone',
        'mobile', 'mobi', 'samsung', 'huawei', 'xiaomi', 'oppo', 'vivo', 
        'oneplus', 'nokia', 'motorola', 'lg', 'htc', 'sony', 'meizu', 
        'lenovo', 'tablet', 'kindle', 'silk', 'opera mini', 'opera mobi',
        'webos', 'palm', 'symbian', 'fennec', 'maemo'
    ]
    
    # 检查User-Agent是否包含移动设备特征
    for agent in mobile_agents:
        if agent in user_agent:
            return True
    
    # 检查Accept头
    accept = request.META.get('HTTP_ACCEPT', '')
    if 'application/vnd.wap.xhtml+xml' in accept:
        return True
    
    # 检查屏幕尺寸相关（如果有）
    if 'screen' in user_agent:
        # 检查是否提到小屏幕
        small_screen_indicators = ['320x', '240x', '176x', '128x']
        for indicator in small_screen_indicators:
            if indicator in user_agent:
                return True
    
    return False


def is_root_user(request: HttpRequest) -> bool:
    """
    检测当前用户是否为root用户
    
    Args:
        request: Django请求对象
        
    Returns:
        bool: True表示root用户，False表示普通用户
    """
    # 兼容两种session格式
    # 方式1：老的RBAC系统 - user_info字典
    user_info = request.session.get('user_info', {})
    username = user_info.get('username', '')
    if username == 'root':
        return True
    
    # 方式2：新的移动端系统 - user_id
    user_id = request.session.get('user_id')
    if user_id:
        try:
            from crm.models import UserInfo
            user = UserInfo.objects.get(id=user_id)
            return user.username == 'root'
        except:
            pass
    
    return False


def get_user_info(request: HttpRequest) -> dict:
    """
    获取当前用户信息
    
    Args:
        request: Django请求对象
        
    Returns:
        dict: 用户信息字典
    """
    return request.session.get('user_info', {})


def get_device_type(request: HttpRequest) -> str:
    """
    获取设备类型
    
    Args:
        request: Django请求对象
        
    Returns:
        str: 'mobile' 或 'desktop'
    """
    return 'mobile' if is_mobile_device(request) else 'desktop'


def get_user_type(request: HttpRequest) -> str:
    """
    获取用户类型
    
    Args:
        request: Django请求对象
        
    Returns:
        str: 'root' 或 'normal'
    """
    return 'root' if is_root_user(request) else 'normal'


def format_order_status(status: int) -> str:
    """
    格式化订单状态显示
    
    Args:
        status: 状态数字
        
    Returns:
        str: 状态文本
    """
    status_map = {
        1: '待处理',
        2: '处理中', 
        3: '已完成',
        4: '已取消'
    }
    return status_map.get(status, '未知状态')


def format_progress_status(status: int) -> str:
    """
    格式化进度状态显示
    
    Args:
        status: 状态数字
        
    Returns:
        str: 状态文本
    """
    status_map = {
        1: '待开始',
        2: '进行中',
        3: '已完成',
        4: '已跳过'
    }
    return status_map.get(status, '未知状态')


def test_device_detection(user_agent_string: str) -> dict:
    """
    测试设备检测逻辑
    
    Args:
        user_agent_string: User-Agent字符串
        
    Returns:
        dict: 检测结果详情
    """
    from django.http import HttpRequest
    
    # 创建模拟请求对象
    request = HttpRequest()
    request.META['HTTP_USER_AGENT'] = user_agent_string
    
    user_agent_lower = user_agent_string.lower()
    
    # 检查桌面系统标识
    desktop_agents = [
        'windows nt', 'win64', 'win32', 'x86_64', 'amd64',
        'macintosh', 'mac os x', 'intel mac',
        'linux', 'x11', 'ubuntu', 'fedora', 'centos'
    ]
    
    desktop_matches = [agent for agent in desktop_agents if agent in user_agent_lower]
    
    # 检查移动设备标识
    mobile_agents = [
        'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone',
        'mobile', 'mobi', 'samsung', 'huawei', 'xiaomi', 'oppo', 'vivo', 
        'oneplus', 'nokia', 'motorola', 'lg', 'htc', 'sony', 'meizu', 
        'lenovo', 'tablet', 'kindle', 'silk', 'opera mini', 'opera mobi',
        'webos', 'palm', 'symbian', 'fennec', 'maemo'
    ]
    
    mobile_matches = [agent for agent in mobile_agents if agent in user_agent_lower]
    
    # 执行实际检测
    is_mobile = is_mobile_device(request)
    device_type = get_device_type(request)
    
    return {
        'user_agent': user_agent_string,
        'user_agent_lower': user_agent_lower,
        'desktop_matches': desktop_matches,
        'mobile_matches': mobile_matches,
        'has_mobile_keyword': 'mobile' in user_agent_lower or 'mobi' in user_agent_lower,
        'is_mobile_result': is_mobile,
        'device_type': device_type,
        'expected': 'mobile' if mobile_matches and not (desktop_matches and not ('mobile' in user_agent_lower or 'mobi' in user_agent_lower)) else 'desktop'
    } 