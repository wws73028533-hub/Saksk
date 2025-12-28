# -*- coding: utf-8 -*-
"""管理后台模块"""
import os
from flask import Flask, Blueprint

def init_admin_module(app: Flask):
    """初始化管理后台模块"""
    from .routes.pages import admin_pages_bp
    from .routes.api import admin_api_bp
    from .routes.api_legacy import admin_api_legacy_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder=template_dir)
    admin_bp.register_blueprint(admin_pages_bp)
    admin_bp.register_blueprint(admin_api_bp, url_prefix='/api')
    # 向后兼容：注册旧路径的路由（/admin/types, /admin/questions）
    admin_bp.register_blueprint(admin_api_legacy_bp)
    app.register_blueprint(admin_bp)

