# -*- coding: utf-8 -*-
"""
Flask扩展初始化
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 初始化限流器（不绑定app）
limiter = Limiter(
    key_func=get_remote_address,
    headers_enabled=False
)


def init_extensions(app):
    """初始化所有扩展"""
    limiter.init_app(app)

