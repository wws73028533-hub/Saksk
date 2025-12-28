# -*- coding: utf-8 -*-
"""聊天路由"""
from flask import Blueprint
from .pages import chat_pages_bp
from .api import chat_api_bp

chat_bp = Blueprint('chat', __name__)
chat_bp.register_blueprint(chat_pages_bp)
chat_bp.register_blueprint(chat_api_bp, url_prefix='/api')


