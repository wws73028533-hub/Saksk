# -*- coding: utf-8 -*-
"""刷题模块"""
import os
from flask import Flask, Blueprint

def init_quiz_module(app: Flask):
    """初始化刷题模块"""
    from .routes.pages import quiz_pages_bp
    from .routes.api import quiz_api_bp, toggle_favorite, record_result, progress_api, api_questions_count, api_user_counts
    
    # 获取模块目录，用于设置模板路径
    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')
    
    # 创建主蓝图，指定模板文件夹
    quiz_bp = Blueprint('quiz', __name__, template_folder=template_dir)
    
    # 注册子蓝图（子蓝图已经在创建时指定了template_folder）
    quiz_bp.register_blueprint(quiz_pages_bp)
    # API蓝图直接注册到app，使用 /api/quiz 前缀以匹配小程序API路径
    app.register_blueprint(quiz_api_bp, url_prefix='/api/quiz')

    # Web 端历史代码使用 /api/*（不带 /quiz 前缀）；这里加别名确保互通与兼容
    app.add_url_rule('/api/favorite', endpoint='api_favorite', view_func=toggle_favorite, methods=['POST'])
    app.add_url_rule('/api/record_result', endpoint='api_record_result', view_func=record_result, methods=['POST'])
    app.add_url_rule('/api/progress', endpoint='api_progress', view_func=progress_api, methods=['GET', 'POST', 'DELETE'])
    app.add_url_rule('/api/questions/count', endpoint='api_questions_count', view_func=api_questions_count, methods=['GET'])
    app.add_url_rule('/api/questions/user_counts', endpoint='api_questions_user_counts', view_func=api_user_counts, methods=['GET'])
    
    # 注册主蓝图（用于页面路由）
    app.register_blueprint(quiz_bp)
