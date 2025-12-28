# -*- coding: utf-8 -*-
"""聊天模块"""
import os
from flask import Flask, Blueprint

def init_chat_module(app: Flask):
    """初始化聊天模块"""
    from .routes.pages import chat_pages_bp
    from .routes.api import chat_api_bp

    module_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(module_dir, 'templates')

    chat_bp = Blueprint('chat', __name__, template_folder=template_dir)
    chat_bp.register_blueprint(chat_pages_bp)
    chat_bp.register_blueprint(chat_api_bp, url_prefix='/api')
    app.register_blueprint(chat_bp)


