# -*- coding: utf-8 -*-
"""认证路由"""
from flask import Blueprint
from .pages import auth_pages_bp
from .api import auth_api_bp

# 创建主蓝图（不指定template_folder，在模块初始化时处理）
auth_bp = Blueprint('auth', __name__)

# 注册子蓝图
auth_bp.register_blueprint(auth_pages_bp)
auth_bp.register_blueprint(auth_api_bp, url_prefix='/api')

