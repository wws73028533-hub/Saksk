# -*- coding: utf-8 -*-
"""聊天页面路由"""
from flask import Blueprint, render_template, session

chat_pages_bp = Blueprint('chat_pages', __name__)


@chat_pages_bp.route('/chat')
def chat_page():
    if not session.get('user_id'):
        return ("请先登录", 401)
    return render_template(
        'chat/chat.html',
        logged_in=True,
        username=session.get('username'),
        user_id=session.get('user_id'),
        is_admin=bool(session.get('is_admin')),
    )


