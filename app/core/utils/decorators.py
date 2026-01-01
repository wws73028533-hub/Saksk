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
            return redirect(url_for('auth.auth_pages.login_page'))
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
            return redirect(url_for('auth.auth_pages.login_page'))
        
        if not session.get('is_admin'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员权限'}), 403
            return redirect(url_for('main.main_pages.index'))
        
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


def subject_admin_required(f):
    """
    科目管理员验证装饰器（允许管理员和科目管理员）
    
    用法:
        @subject_admin_required
        def subject_admin_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            return redirect(url_for('auth.auth_pages.login_page'))
        
        # 管理员和科目管理员都可以访问
        is_admin_user = session.get('is_admin')
        is_subject_admin_user = session.get('is_subject_admin')
        
        if not (is_admin_user or is_subject_admin_user):
            if request.path.startswith('/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403
            return redirect(url_for('main.main_pages.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def is_subject_admin():
    """判断当前用户是否是科目管理员"""
    return bool(session.get('is_subject_admin'))


def notification_admin_required(f):
    """
    通知管理员验证装饰器（允许管理员和通知管理员）
    
    用法:
        @notification_admin_required
        def notification_admin_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            return redirect(url_for('auth.auth_pages.login_page'))
        
        # 管理员和通知管理员都可以访问
        is_admin_user = session.get('is_admin')
        is_notification_admin_user = session.get('is_notification_admin')
        
        if not (is_admin_user or is_notification_admin_user):
            if request.path.startswith('/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员或通知管理员权限'}), 403
            return redirect(url_for('main.main_pages.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def is_notification_admin():
    """判断当前用户是否是通知管理员"""
    return bool(session.get('is_notification_admin'))
