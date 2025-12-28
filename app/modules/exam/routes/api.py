# -*- coding: utf-8 -*-
"""考试API路由"""
from flask import Blueprint, request, jsonify, session
from app.core.utils.database import get_db
from app.core.models.exam import Exam

exam_api_bp = Blueprint('exam_api', __name__)


@exam_api_bp.route('/exams/create', methods=['POST'])
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


@exam_api_bp.route('/exams/submit', methods=['POST'])
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


@exam_api_bp.route('/exams/<int:exam_id>', methods=['DELETE'])
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


@exam_api_bp.route('/exams/save_draft', methods=['POST'])
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


@exam_api_bp.route('/exams/<int:exam_id>/mistakes', methods=['POST'])
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


