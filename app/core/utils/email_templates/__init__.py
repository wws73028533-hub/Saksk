# -*- coding: utf-8 -*-
"""
邮件模板模块
提供现代化的邮件模板，采用iOS 18风格设计
"""
from typing import Dict, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# 获取模板目录路径
TEMPLATE_DIR = Path(__file__).parent

# 创建Jinja2环境
env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)


def render_template(template_name: str, **kwargs: Any) -> str:
    """
    渲染邮件模板
    
    Args:
        template_name: 模板文件名（不含扩展名）
        **kwargs: 模板变量
        
    Returns:
        渲染后的HTML字符串
    """
    template = env.get_template(f'{template_name}.html')
    return template.render(**kwargs)


def get_email_subject(template_type: str) -> str:
    """
    获取邮件主题
    
    Args:
        template_type: 模板类型
        
    Returns:
        邮件主题
    """
    subjects = {
        'bind_code': '邮箱绑定验证码',
        'login_code': '登录验证码',
        'reset_password': '密码重置验证码'
    }
    return subjects.get(template_type, '系统通知')

