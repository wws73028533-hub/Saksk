# -*- coding: utf-8 -*-
"""弹窗路由"""
from flask import Blueprint
from .api import popups_api_bp

popups_bp = Blueprint('popups', __name__)
popups_bp.register_blueprint(popups_api_bp)


