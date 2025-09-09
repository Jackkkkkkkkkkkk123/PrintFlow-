#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
印刷订单管理系统安装脚本
"""

import os
import sys
import subprocess
import platform

def run_command(command):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_python_version():
    """检查Python版本"""
    print("检查Python版本...")
    if sys.version_info < (3, 6):
        print("错误: 需要Python 3.6或更高版本")
        return False
    print(f"Python版本: {sys.version}")
    return True

def install_dependencies():
    """安装依赖包"""
    print("安装依赖包...")
    success, stdout, stderr = run_command("pip install -r requirements.txt")
    if success:
        print("依赖包安装成功")
        return True
    else:
        print(f"依赖包安装失败: {stderr}")
        return False

def setup_database():
    """设置数据库"""
    print("设置数据库...")
    
    # 创建迁移文件
    success, stdout, stderr = run_command("python manage.py makemigrations")
    if not success:
        print(f"创建迁移文件失败: {stderr}")
        return False
    
    # 执行迁移
    success, stdout, stderr = run_command("python manage.py migrate")
    if not success:
        print(f"数据库迁移失败: {stderr}")
        return False
    
    print("数据库设置完成")
    return True

def create_superuser():
    """创建超级用户"""
    print("创建超级用户...")
    print("请按照提示输入用户名、邮箱和密码")
    
    success, stdout, stderr = run_command("python manage.py createsuperuser --noinput")
    if not success:
        print("创建超级用户失败，请手动运行: python manage.py createsuperuser")
        return False
    
    print("超级用户创建成功")
    return True

def main():
    """主安装流程"""
    print("=" * 50)
    print("印刷订单管理系统安装程序")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return
    
    # 安装依赖
    if not install_dependencies():
        return
    
    # 设置数据库
    if not setup_database():
        return
    
    # 创建超级用户
    create_superuser()
    
    print("=" * 50)
    print("安装完成！")
    print("启动系统: python manage.py runserver")
    print("访问地址: http://127.0.0.1:5173")
    print("=" * 50)

if __name__ == '__main__':
    main() 