# -*- coding: utf-8 -*-
"""
JWT工具函数
用于生成和验证JWT token
"""
import jwt
from datetime import datetime, timedelta
from flask import current_app
from typing import Dict, Any, Optional


def generate_jwt_token(
    user_id: int,
    openid: str,
    expires_in: int = 7 * 24 * 60 * 60,
    session_version: Optional[int] = None,
) -> str:
    """
    生成JWT token
    
    Args:
        user_id: 用户ID
        openid: 微信openid
        expires_in: token过期时间（秒），默认7天
    
    Returns:
        JWT token字符串
    """
    payload = {
        'user_id': user_id,
        'openid': openid,
        'session_version': int(session_version or 0),
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow()
    }
    
    secret_key = current_app.config.get('SECRET_KEY')
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    # jwt.encode在PyJWT 2.0+返回字符串，旧版本返回bytes
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码JWT token
    
    Args:
        token: JWT token字符串
    
    Returns:
        包含user_id和openid的字典，如果token无效返回None
    """
    try:
        secret_key = current_app.config.get('SECRET_KEY')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        # token已过期
        return None
    except jwt.InvalidTokenError:
        # token无效
        return None


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证JWT token（decode_jwt_token的别名，保持一致性）
    
    Args:
        token: JWT token字符串
    
    Returns:
        包含user_id和openid的字典，如果token无效返回None
    """
    return decode_jwt_token(token)

