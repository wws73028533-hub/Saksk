# -*- coding: utf-8 -*-
"""弹窗模块"""
import os
from flask import Flask, Blueprint

def init_popups_module(app: Flask):
    """初始化弹窗模块"""
    from .routes.api import popups_api_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    popups_bp = Blueprint('popups', __name__, template_folder=template_dir)
    popups_bp.register_blueprint(popups_api_bp, url_prefix='/api')
    app.register_blueprint(popups_bp)


