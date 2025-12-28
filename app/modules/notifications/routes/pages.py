# -*- coding: utf-8 -*-
"""通知页面路由"""
from flask import Blueprint, render_template, session, redirect, url_for

notifications_pages_bp = Blueprint('notifications_pages', __name__)


@notifications_pages_bp.route('/notifications')
def notifications_page():
    if not session.get('user_id'):
        return redirect(url_for('auth.auth_pages.login_page'))

    return render_template(
        'notifications/notifications.html',
        logged_in=True,
        username=session.get('username'),
        is_admin=bool(session.get('is_admin')),
    )

