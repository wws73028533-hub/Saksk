# -*- coding: utf-8 -*-
"""编程题模块"""
import os
from flask import Flask, Blueprint

def init_coding_module(app: Flask):
    """初始化编程题模块"""
    from .routes.pages import coding_pages_bp
    from .routes.api import coding_api_bp
    from .routes.admin import coding_admin_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    # 添加重定向：/coding -> /coding/ 
    # 注意：必须在蓝图注册之前注册，避免路由冲突
    @app.route('/coding', methods=['GET'], strict_slashes=False)
    def coding_redirect():
        from flask import redirect, url_for
        # 使用 url_for 生成正确的 URL，确保重定向到正确的路由
        return redirect(url_for('coding.coding_pages.coding_index'))
    
    # 用户端蓝图
    coding_bp = Blueprint('coding', __name__, url_prefix='/coding', template_folder=template_dir)
    coding_bp.register_blueprint(coding_pages_bp)
    coding_bp.register_blueprint(coding_api_bp, url_prefix='/api')
    app.register_blueprint(coding_bp)

    # 管理端蓝图
    admin_bp = Blueprint('coding_admin', __name__, url_prefix='/admin/coding')
    admin_bp.register_blueprint(coding_admin_bp)
    app.register_blueprint(admin_bp)

