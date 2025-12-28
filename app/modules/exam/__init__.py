# -*- coding: utf-8 -*-
"""考试模块"""
import os
from flask import Flask, Blueprint

def init_exam_module(app: Flask):
    """初始化考试模块"""
    from .routes.pages import exam_pages_bp
    from .routes.api import exam_api_bp
    
    # 获取模块目录，用于设置模板路径
    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')
    
    # 创建主蓝图，指定模板文件夹
    exam_bp = Blueprint('exam', __name__, template_folder=template_dir)
    
    # 注册子蓝图
    exam_bp.register_blueprint(exam_pages_bp)
    exam_bp.register_blueprint(exam_api_bp, url_prefix='/api')
    
    # 注册主蓝图
    app.register_blueprint(exam_bp)


