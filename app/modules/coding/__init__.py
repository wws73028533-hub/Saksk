# -*- coding: utf-8 -*-
"""编程题模块"""
import os
from flask import Flask, Blueprint

def init_coding_module(app: Flask):
    """初始化编程题模块"""
    from .routes.pages import coding_pages_bp
    from .routes.api import coding_api_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    coding_bp = Blueprint('coding', __name__, url_prefix='/coding', template_folder=template_dir)
    coding_bp.register_blueprint(coding_pages_bp)
    coding_bp.register_blueprint(coding_api_bp, url_prefix='/api')
    app.register_blueprint(coding_bp)

