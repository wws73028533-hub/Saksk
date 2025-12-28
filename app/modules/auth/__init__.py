# -*- coding: utf-8 -*-
"""认证模块"""
import os
from flask import Flask, Blueprint

def init_auth_module(app: Flask):
    """初始化认证模块"""
    from .routes.pages import auth_pages_bp
    from .routes.api import auth_api_bp
    
    # 获取模块目录，用于设置模板路径
    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')
    
    # 创建主蓝图，指定模板文件夹
    auth_bp = Blueprint('auth', __name__, template_folder=template_dir)
    
    # 注册子蓝图
    auth_bp.register_blueprint(auth_pages_bp)
    auth_bp.register_blueprint(auth_api_bp, url_prefix='/api')
    
    # 注册主蓝图
    app.register_blueprint(auth_bp)

