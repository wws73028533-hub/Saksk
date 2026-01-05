# -*- coding: utf-8 -*-
"""
Flask扩展初始化
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

# 初始化限流器（不绑定app）
limiter = Limiter(
    key_func=get_remote_address,
    headers_enabled=False
)


def init_extensions(app):
    """初始化所有扩展"""
    limiter.init_app(app)
    
    # CORS配置（允许小程序域名）
    CORS(app, resources={
        r"/api/*": {
            "origins": ["https://servicewechat.com", "*"],  # 微信小程序域名，开发环境允许所有来源
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False
        }
    })

