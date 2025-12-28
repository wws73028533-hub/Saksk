# -*- coding: utf-8 -*-
"""编程题路由"""
from flask import Blueprint
from .pages import coding_pages_bp
from .api import coding_api_bp

coding_bp = Blueprint('coding', __name__, url_prefix='/coding')
coding_bp.register_blueprint(coding_pages_bp)
coding_bp.register_blueprint(coding_api_bp, url_prefix='/api')

