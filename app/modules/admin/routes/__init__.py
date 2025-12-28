# -*- coding: utf-8 -*-
"""管理后台路由"""
from flask import Blueprint
from .pages import admin_pages_bp
from .api import admin_api_bp

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
admin_bp.register_blueprint(admin_pages_bp)
admin_bp.register_blueprint(admin_api_bp, url_prefix='/api')

