# -*- coding: utf-8 -*-
"""编程题页面路由"""
from flask import Blueprint, render_template, session

coding_pages_bp = Blueprint('coding_pages', __name__)


@coding_pages_bp.route('/')
@coding_pages_bp.route('/index')
def coding_index():
    """编程题主页"""
    uid = session.get('user_id')
    
    return render_template(
        'coding/index.html',
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )

