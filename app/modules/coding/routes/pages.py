# -*- coding: utf-8 -*-
"""编程题页面路由"""
from flask import Blueprint, render_template, session, redirect, url_for, request

coding_pages_bp = Blueprint('coding_pages', __name__)


@coding_pages_bp.route('/home')
def coding_home():
    """编程题首页（科目选择页）"""
    uid = session.get('user_id')
    
    return render_template(
        'coding/home.html',
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )


@coding_pages_bp.route('/', strict_slashes=False)
@coding_pages_bp.route('/index')
def coding_index():
    """编程题列表页"""
    uid = session.get('user_id')
    
    return render_template(
        'coding/index.html',
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )


@coding_pages_bp.route('/subject/<int:subject_id>')
def coding_subject_overview(subject_id: int):
    """题目集（科目）概述页"""
    uid = session.get('user_id')
    
    return render_template(
        'coding/subject_overview.html',
        subject_id=subject_id,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )


@coding_pages_bp.route('/questions')
def coding_questions():
    """题目列表页（按科目筛选）"""
    uid = session.get('user_id')
    subject_id = request.args.get('subject', type=int)
    
    return render_template(
        'coding/questions.html',
        subject_id=subject_id or 0,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )


@coding_pages_bp.route('/<int:question_id>')
def coding_detail(question_id: int):
    """编程题详情页"""
    uid = session.get('user_id')
    
    return render_template(
        'coding/detail.html',
        question_id=question_id,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )


@coding_pages_bp.route('/submissions')
def coding_submissions():
    """提交历史页"""
    uid = session.get('user_id')
    question_id = request.args.get('question', type=int)
    subject_id = request.args.get('subject', type=int)
    
    return render_template(
        'coding/submissions.html',
        question_id=question_id or 0,
        subject_id=subject_id or 0,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )


@coding_pages_bp.route('/statistics')
def coding_statistics():
    """排名页"""
    uid = session.get('user_id')
    question_id = request.args.get('question', type=int)
    subject_id = request.args.get('subject', type=int)
    
    return render_template(
        'coding/statistics.html',
        question_id=question_id or 0,
        subject_id=subject_id or 0,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        user_id=uid or 0
    )
