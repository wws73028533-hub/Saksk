# -*- coding: utf-8 -*-
"""
验证器工具函数
"""
import re


def validate_password(password):
    """
    验证密码强度
    
    Args:
        password: 密码字符串
        
    Returns:
        tuple: (是否有效, 错误消息)
    """
    if not password:
        return False, '密码不能为空'
    
    if len(password) < 8:
        return False, '密码至少8位'
    
    if not any(c.isalpha() for c in password):
        return False, '密码必须包含字母'
    
    if not any(c.isdigit() for c in password):
        return False, '密码必须包含数字'
    
    return True, ''


def validate_username(username):
    """
    验证用户名
    
    Args:
        username: 用户名字符串
        
    Returns:
        tuple: (是否有效, 错误消息)
    """
    if not username:
        return False, '用户名不能为空'
    
    if len(username) < 3:
        return False, '用户名至少3个字符'
    
    if len(username) > 20:
        return False, '用户名最多20个字符'
    
    if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$', username):
        return False, '用户名只能包含字母、数字、下划线和中文'
    
    return True, ''


def parse_int(value, default, min_val=None, max_val=None):
    """
    解析整数，带默认值和范围限制
    
    Args:
        value: 要解析的值
        default: 默认值
        min_val: 最小值
        max_val: 最大值
        
    Returns:
        int: 解析后的整数
    """
    try:
        result = int(value)
    except (ValueError, TypeError):
        result = default
    
    if min_val is not None:
        result = max(result, min_val)
    if max_val is not None:
        result = min(result, max_val)
    
    return result

