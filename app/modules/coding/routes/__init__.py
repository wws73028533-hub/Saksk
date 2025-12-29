# -*- coding: utf-8 -*-
"""编程题路由"""
# 注意：蓝图在 app/modules/coding/__init__.py 中注册
# 这里只导出子蓝图，不创建主蓝图
from .pages import coding_pages_bp
from .api import coding_api_bp

__all__ = ['coding_pages_bp', 'coding_api_bp']

