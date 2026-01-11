# -*- coding: utf-8 -*-
"""用户私人题库模块"""
import os
from flask import Flask, Blueprint


def init_user_bank_module(app: Flask):
    """初始化用户题库模块"""
    from .routes.pages import user_bank_pages_bp
    from .routes.api import user_bank_api_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    user_bank_bp = Blueprint('user_bank', __name__, url_prefix='/user/banks', template_folder=template_dir)
    user_bank_bp.register_blueprint(user_bank_pages_bp)
    user_bank_bp.register_blueprint(user_bank_api_bp, url_prefix='/api')
    app.register_blueprint(user_bank_bp)

    # 小程序/API 前缀兼容：
    # 小程序端基础路径通常为 /api，若复用 Web 的 /user/banks/api/*，
    # 最终请求会变为 /api/user/banks/api/*，这里将同一套 API 再挂载一份到该前缀下。
    api_root_bp = Blueprint('user_bank_api_root', __name__, url_prefix='/api')
    api_root_bp.register_blueprint(user_bank_api_bp, url_prefix='/user/banks/api')
    app.register_blueprint(api_root_bp)

    # 注册公开题库广场的路由（无需 /user 前缀）
    from .routes.public import public_bank_bp
    app.register_blueprint(public_bank_bp)
