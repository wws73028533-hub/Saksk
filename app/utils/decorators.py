# -*- coding: utf-8 -*-
"""
装饰器工具函数
"""
from functools import wraps
from flask import session, redirect, url_for, jsonify, request


def login_required(f):
    """
    登录验证装饰器
    
    用法:
        @login_required
        def my_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            # API请求返回JSON
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            # 页面请求重定向到登录页
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    管理员验证装饰器
    
    用法:
        @admin_required
        def admin_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            return redirect(url_for('auth.login'))
        
        if not session.get('is_admin'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员权限'}), 403
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def current_user_id():
    """获取当前用户ID"""
    return session.get('user_id')


def current_username():
    """获取当前用户名"""
    return session.get('username')


def is_admin():
    """判断当前用户是否是管理员"""
    return bool(session.get('is_admin'))

