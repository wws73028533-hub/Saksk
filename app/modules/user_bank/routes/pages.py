# -*- coding: utf-8 -*-
"""用户题库页面路由"""
from flask import Blueprint, render_template, redirect, url_for, request, session
from app.core.utils.decorators import login_required

user_bank_pages_bp = Blueprint('user_bank_pages', __name__)


@user_bank_pages_bp.route('/')
@login_required
def banks_list():
    """我的题库列表页面"""
    return render_template('user_bank/banks.html')


@user_bank_pages_bp.route('/<int:bank_id>')
@login_required
def bank_detail(bank_id):
    """题库详情/题目管理页面"""
    return render_template('user_bank/bank_questions.html', bank_id=bank_id)


@user_bank_pages_bp.route('/add')
@login_required
def bank_add():
    """创建题库页面"""
    return render_template('user_bank/bank_edit.html', bank_id=None, mode='add')


@user_bank_pages_bp.route('/<int:bank_id>/edit')
@login_required
def bank_edit(bank_id):
    """编辑题库页面"""
    return render_template('user_bank/bank_edit.html', bank_id=bank_id, mode='edit')


@user_bank_pages_bp.route('/<int:bank_id>/questions/add')
@login_required
def question_add(bank_id):
    """添加题目页面"""
    return render_template('user_bank/question_edit.html', bank_id=bank_id, question_id=None, mode='add')


@user_bank_pages_bp.route('/<int:bank_id>/questions/<int:question_id>/edit')
@login_required
def question_edit(bank_id, question_id):
    """编辑题目页面"""
    return render_template('user_bank/question_edit.html', bank_id=bank_id, question_id=question_id, mode='edit')


@user_bank_pages_bp.route('/<int:bank_id>/shares')
@login_required
def shares_manage(bank_id):
    """分享管理页面"""
    return render_template('user_bank/shares.html', bank_id=bank_id)


@user_bank_pages_bp.route('/shared')
@login_required
def shared_banks():
    """收到的分享列表页面"""
    return render_template('user_bank/shared_banks.html')


@user_bank_pages_bp.route('/<int:bank_id>/quiz')
@login_required
def bank_quiz(bank_id):
    """题库刷题页面"""
    mode = request.args.get('mode', 'all')
    return render_template('user_bank/quiz.html', bank_id=bank_id, mode=mode)
