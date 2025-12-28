# -*- coding: utf-8 -*-
"""用户模块"""
import os
from flask import Flask, Blueprint

def init_user_module(app: Flask):
    """初始化用户模块"""
    from .routes.pages import user_pages_bp
    from .routes.api import user_api_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    user_bp = Blueprint('user', __name__, template_folder=template_dir)
    user_bp.register_blueprint(user_pages_bp)
    user_bp.register_blueprint(user_api_bp, url_prefix='/api')
    app.register_blueprint(user_bp)


