# -*- coding: utf-8 -*-
"""认证页面路由"""
from flask import Blueprint, render_template, request

auth_pages_bp = Blueprint('auth_pages', __name__)


@auth_pages_bp.route('/login')
def login_page():
    """登录页面"""
    from_param = request.args.get('from', '')
    redirect_url = request.args.get('redirect', '')
    
    # 根据 from 参数设置提示信息
    tips = {
        'quiz': '刷题',
        'memo': '背题',
        '背题': '背题',
        'favorites': '收藏本',
        '收藏本': '收藏本',
        'mistakes': '错题本',
        '错题本': '错题本',
        'exam': '考试',
        '考试': '考试',
        'exams': '考试',
        'profile': '个人中心',
        'search': '搜索'
    }
    
    tip_message = tips.get(from_param, '')
    if tip_message:
        tip_message = f'使用{tip_message}功能需要先登录'
    
    return render_template('auth/login.html', 
                         mode='login',
                         from_param=from_param,
                         redirect_url=redirect_url,
                         tip_message=tip_message)


@auth_pages_bp.route('/register')
def register_page():
    """注册页面"""
    return render_template('auth/login.html', mode='register')

