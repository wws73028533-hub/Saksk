# -*- coding: utf-8 -*-
"""考试路由"""
from flask import Blueprint
from .pages import exam_pages_bp
from .api import exam_api_bp

# 创建主蓝图（不指定template_folder，在模块初始化时处理）
exam_bp = Blueprint('exam', __name__)

# 注册子蓝图
exam_bp.register_blueprint(exam_pages_bp)
exam_bp.register_blueprint(exam_api_bp, url_prefix='/api')


