# -*- coding: utf-8 -*-
"""用户路由"""
from flask import Blueprint
from .pages import user_pages_bp
from .api import user_api_bp

user_bp = Blueprint('user', __name__)
user_bp.register_blueprint(user_pages_bp)
user_bp.register_blueprint(user_api_bp, url_prefix='/api')


