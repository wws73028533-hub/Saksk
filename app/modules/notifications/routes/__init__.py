# -*- coding: utf-8 -*-
"""通知路由"""
from flask import Blueprint
from .pages import notifications_pages_bp
from .api import notifications_api_bp

notifications_bp = Blueprint('notifications', __name__)
notifications_bp.register_blueprint(notifications_pages_bp)
notifications_bp.register_blueprint(notifications_api_bp, url_prefix='/api')

