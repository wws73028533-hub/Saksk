# -*- coding: utf-8 -*-
"""
路由蓝图模块
"""
from .auth import auth_bp
from .main import main_bp
from .api import api_bp
from .quiz import quiz_bp
from .exam import exam_bp
from .user import user_bp
from .admin import admin_bp


def register_all_routes(app):
    """注册所有路由蓝图"""
    # 注册认证蓝图
    app.register_blueprint(auth_bp)
    
    # 注册主页蓝图
    app.register_blueprint(main_bp)
    
    # 注册API蓝图
    app.register_blueprint(api_bp)
    
    # 注册刷题蓝图
    app.register_blueprint(quiz_bp)
    
    # 注册考试蓝图
    app.register_blueprint(exam_bp)
    
    # 注册用户蓝图
    app.register_blueprint(user_bp)
    
    # 注册管理后台蓝图
    app.register_blueprint(admin_bp)
    
    app.logger.info('所有路由蓝图已注册 (7个蓝图)')
