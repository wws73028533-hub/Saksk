# -*- coding: utf-8 -*-
"""刷题模块"""
import os
from flask import Flask, Blueprint

def init_quiz_module(app: Flask):
    """初始化刷题模块"""
    from .routes.pages import quiz_pages_bp
    from .routes.api import quiz_api_bp
    
    # 获取模块目录，用于设置模板路径
    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')
    
    # 创建主蓝图，指定模板文件夹
    quiz_bp = Blueprint('quiz', __name__, template_folder=template_dir)
    
    # 注册子蓝图（子蓝图已经在创建时指定了template_folder）
    quiz_bp.register_blueprint(quiz_pages_bp)
    quiz_bp.register_blueprint(quiz_api_bp, url_prefix='/api')
    
    # 注册主蓝图
    app.register_blueprint(quiz_bp)

