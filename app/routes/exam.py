# -*- coding: utf-8 -*-
"""
考试路由蓝图
"""
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..utils.database import get_db
from ..utils.validators import parse_int
from ..models.exam import Exam

exam_bp = Blueprint('exam', __name__)


@exam_bp.route('/exams')
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
    
    return render_template('exams.html',
                         ongoing=[dict(r) for r in ongoing],
                         submitted=[dict(r) for r in submitted],
                         subjects=subs,
                         filter_subject=subject,
                         page=page,
                         size=size,
                         total=total)


@exam_bp.route('/exams/<int:exam_id>')
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
    
    return render_template('exam_detail.html', **data)


@exam_bp.route('/api/exams/create', methods=['POST'])
def api_exams_create():
    """创建考试API"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.json or {}
    subject = data.get('subject') or 'all'
    duration = data.get('duration') or 60
    types_cfg = data.get('types') or {}
    scores_cfg = data.get('scores') or {}

    exam_id = Exam.create(uid, subject, duration, types_cfg, scores_cfg)
    return jsonify({'status': 'success', 'exam_id': exam_id})


@exam_bp.route('/api/exams/submit', methods=['POST'])
def api_exams_submit():
    """提交考试API"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.json or {}
    exam_id = data.get('exam_id')
    answers = data.get('answers') or []

    if not exam_id:
        return jsonify({'status': 'error', 'message': '缺少 exam_id'}), 400

    result = Exam.submit(exam_id, uid, answers)
    if not result:
        return jsonify({'status': 'error', 'message': '考试不存在/无权限/已提交'}), 400

    return jsonify({
        'status': 'success',
        'exam_id': exam_id,
        **result
    })


@exam_bp.route('/api/exams/<int:exam_id>', methods=['DELETE'])
def api_delete_exam(exam_id):
    """删除考试"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    conn = get_db()
    ex = conn.execute('SELECT user_id FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    if not ex or ex['user_id'] != uid:
        return jsonify({'status':'error','message':'考试不存在或无权限'}), 403
    
    conn.execute('DELETE FROM exams WHERE id=?', (exam_id,))
    conn.commit()
    
    return jsonify({'status':'success'})


@exam_bp.route('/api/exams/save_draft', methods=['POST'])
def api_save_exam_draft():
    """保存考试草稿"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status':'unauthorized','message':'请先登录'}), 401
    
    data = request.json or {}
    exam_id = data.get('exam_id')
    answers = data.get('answers') or []
    
    if not exam_id:
        return jsonify({'status':'error','message':'缺少 exam_id'}), 400
    
    conn = get_db()
    exam = conn.execute('SELECT user_id, status FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    if not exam or exam['user_id'] != uid:
        return jsonify({'status':'error','message':'考试不存在或无权限'}), 403
    
    if exam['status'] == 'submitted':
        return jsonify({'status':'error','message':'考试已提交，不可保存草稿'}), 400
    
    for a in answers:
        try:
            qid = int(a.get('question_id'))
        except:
            continue
        ua = (a.get('user_answer') or '').strip()
        conn.execute(
            'UPDATE exam_questions SET user_answer=? WHERE exam_id=? AND question_id=?',
            (ua, exam_id, qid)
        )
    
    conn.commit()
    return jsonify({'status':'success'})


@exam_bp.route('/api/exams/<int:exam_id>/mistakes', methods=['POST'])
def api_exam_to_mistakes(exam_id):
    """将考试错题加入错题本"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status':'unauthorized','message':'请先登录'}), 401
    
    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    if not exam or exam['user_id'] != uid:
        return jsonify({'status':'error','message':'考试不存在或无权限'}), 403
    
    if exam['status'] != 'submitted':
        return jsonify({'status':'error','message':'请在提交考试后再加入错题本'}), 400
    
    wrongs = conn.execute(
        'SELECT question_id FROM exam_questions WHERE exam_id=? AND (is_correct IS NULL OR is_correct=0)',
        (exam_id,)
    ).fetchall()
    
    count = 0
    for r in wrongs:
        qid = r['question_id']
        conn.execute("""
            INSERT INTO mistakes (user_id, question_id, wrong_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, question_id) DO UPDATE SET wrong_count = wrong_count + 1
        """, (uid, qid))
        count += 1
    
    conn.commit()
    return jsonify({'status':'success','count': count})

