from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

class LoginRequiredMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 白名单：登录页、重置页、验证码、静态资源、根路径
        white_list = [
            '/', '/login/', '/reset/', '/verify_code/'
        ]
        if request.path in white_list or request.path.startswith('/static/'):
            return None
        # 你项目用 session 判断登录
        if not request.session.get('user_id'):
            return redirect('/login/')
        return None 