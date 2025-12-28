# -*- coding: utf-8 -*-
"""通知模块"""
import os
from flask import Flask, Blueprint

def init_notifications_module(app: Flask):
    """初始化通知模块"""
    from .routes.pages import notifications_pages_bp
    from .routes.api import notifications_api_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    notifications_bp = Blueprint('notifications', __name__, template_folder=template_dir)
    notifications_bp.register_blueprint(notifications_pages_bp)
    notifications_bp.register_blueprint(notifications_api_bp, url_prefix='/api')
    app.register_blueprint(notifications_bp)

