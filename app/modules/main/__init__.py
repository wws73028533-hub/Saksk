# -*- coding: utf-8 -*-
"""主页面模块"""
import os
from flask import Flask, Blueprint

def init_main_module(app: Flask):
    """初始化主页面模块"""
    from .routes.pages import main_pages_bp
    
    # 获取模块目录，用于设置模板路径
    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')
    
    # 创建主蓝图，指定模板文件夹
    main_bp = Blueprint('main', __name__, template_folder=template_dir)
    
    # 注册子蓝图
    main_bp.register_blueprint(main_pages_bp)
    
    # 注册主蓝图
    app.register_blueprint(main_bp)



