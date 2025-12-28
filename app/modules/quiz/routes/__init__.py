# -*- coding: utf-8 -*-
"""刷题路由"""
from flask import Blueprint
from .pages import quiz_pages_bp

# 创建主蓝图（不指定template_folder，在模块初始化时处理）
quiz_bp = Blueprint('quiz', __name__)

# 注册子蓝图
quiz_bp.register_blueprint(quiz_pages_bp)


