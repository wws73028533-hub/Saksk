# -*- coding: utf-8 -*-
"""用户侧通知页面路由

页面：
- GET /notifications ：历史通知列表（详情弹层在前端实现）

API 在 notifications.py 中。
"""

from flask import Blueprint, render_template, session, redirect

notifications_page_bp = Blueprint('notifications_page', __name__)


@notifications_page_bp.route('/notifications')
def notifications_page():
    if not session.get('user_id'):
        return redirect('/login')

    return render_template(
        'notifications.html',
        logged_in=True,
        username=session.get('username'),
        is_admin=bool(session.get('is_admin')),
    )
