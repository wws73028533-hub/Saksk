# -*- coding: utf-8 -*-
"""考试页面路由"""
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.core.utils.database import get_db
from app.core.utils.validators import parse_int

exam_pages_bp = Blueprint('exam_pages', __name__)


@exam_pages_bp.route('/exams')
def page_exams():
    """考试列表页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))
    
    subject = request.args.get('subject', 'all')
    page = parse_int(request.args.get('page'), 1, 1)
    size = parse_int(request.args.get('size'), 10, 5, 50)
    
    conn = get_db()
    
    # 科目列表
    subs = [r[0] for r in conn.execute('SELECT name FROM subjects ORDER BY id').fetchall()]
    
    # 进行中的考试
    ongoing = conn.execute(
        'SELECT * FROM exams WHERE user_id=? AND status="ongoing" ORDER BY started_at DESC',
        (uid,)
    ).fetchall()
    
    # 已提交的考试（支持筛选和分页）
    where = 'WHERE user_id=? AND status="submitted"'
    params = [uid]
    
    if subject != 'all':
        where += ' AND subject = ?'
        params.append(subject)
    
    total = conn.execute(f'SELECT COUNT(1) FROM exams {where}', params).fetchone()[0]
    offset = (page-1)*size
    
    submitted = conn.execute(
        f'SELECT * FROM exams {where} ORDER BY submitted_at DESC LIMIT ? OFFSET ?',
        params + [size, offset]
    ).fetchall()
    
    return render_template('exam/exams.html',
                         ongoing=[dict(r) for r in ongoing],
                         submitted=[dict(r) for r in submitted],
                         subjects=subs,
                         filter_subject=subject,
                         page=page,
                         size=size,
                         total=total)


@exam_pages_bp.route('/exams/<int:exam_id>')
def page_exam_detail(exam_id):
    """考试详情页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))
    
    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    # 管理员可查看任意用户的考试
    if not exam:
        return "考试不存在或无权限", 403
    if exam['user_id'] != uid and not session.get('is_admin'):
        return "考试不存在或无权限", 403
    
    # 统计每题对错
    rows = conn.execute('''
        SELECT eq.*, q.content, q.answer, q.q_type
        FROM exam_questions eq
        JOIN questions q ON q.id = eq.question_id
        WHERE eq.exam_id=?
        ORDER BY eq.order_index
    ''', (exam_id,)).fetchall()
    
    total = len(rows)
    correct = sum(1 for r in rows if (r['is_correct'] or 0) == 1)
    acc = round(correct*100.0/total, 1) if total else 0.0
    
    data = {
        'exam': dict(exam),
        'total': total,
        'correct': correct,
        'accuracy': acc,
        'items': [dict(r) for r in rows]
    }
    
    return render_template('exam/exam_detail.html', **data)


