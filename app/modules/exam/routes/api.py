# -*- coding: utf-8 -*-
"""考试API路由"""
from flask import Blueprint, request, jsonify, session
from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id
from app.core.models.exam import Exam
from app.core.utils.options_parser import parse_options

exam_api_bp = Blueprint('exam_api', __name__)


@exam_api_bp.route('/exams/create', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_exams_create():
    """创建考试API（添加科目权限检查）"""
    from app.core.utils.subject_permissions import can_user_access_subject
    
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.json or {}
    subject = data.get('subject') or 'all'
    duration = data.get('duration') or 60
    types_cfg = data.get('types') or {}
    scores_cfg = data.get('scores') or {}
    
    # 如果指定了科目，检查用户是否有权限访问该科目
    if subject != 'all':
        conn = get_db()
        subject_row = conn.execute(
            'SELECT id FROM subjects WHERE name = ?',
            (subject,)
        ).fetchone()
        
        if subject_row:
            subject_id = subject_row['id']
            if not can_user_access_subject(uid, subject_id):
                return jsonify({
                    'status': 'error',
                    'message': '您没有权限访问该科目'
                }), 403

    exam_id = Exam.create(uid, subject, duration, types_cfg, scores_cfg)
    return jsonify({'status': 'success', 'exam_id': exam_id})


@exam_api_bp.route('/exams/submit', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_exams_submit():
    """提交考试API"""
    uid = current_user_id()
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


@exam_api_bp.route('/exams/<int:exam_id>', methods=['GET', 'DELETE'])
@auth_required  # 支持session和JWT（小程序）
def api_exam_detail_or_delete(exam_id):
    """获取/删除考试（JSON）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    if request.method == 'DELETE':
        conn = get_db()
        ex = conn.execute('SELECT user_id FROM exams WHERE id=?', (exam_id,)).fetchone()

        if not ex or ex['user_id'] != uid:
            return jsonify({'status': 'error', 'message': '考试不存在或无权限'}), 403

        conn.execute('DELETE FROM exams WHERE id=?', (exam_id,))
        conn.commit()

        return jsonify({'status': 'success'})

    # GET：返回考试详情（含题目）
    data = Exam.get_by_id(exam_id, uid)
    if not data:
        return jsonify({'status': 'error', 'message': '考试不存在或无权限'}), 404

    exam = data.get('exam') or {}
    questions = data.get('questions') or []

    formatted_questions = []
    for q in questions:
        q_type_val = q.get('q_type', '')
        options = parse_options(q.get('options'))
        if q_type_val == '判断题' and not options:
            options = [
                {'key': '正确', 'value': '正确'},
                {'key': '错误', 'value': '错误'},
            ]

        formatted_questions.append({
            'id': q.get('id'),
            'content': q.get('content', ''),
            'q_type': q_type_val,
            'options': options,
            'answer': q.get('answer', ''),
            'explanation': q.get('explanation', ''),
            'image_path': q.get('image_path'),
            'subject': q.get('subject', ''),
            'score_val': q.get('score_val', 1),
            'order_index': q.get('order_index', 0),
            'user_answer': q.get('user_answer', ''),
            'is_correct': q.get('is_correct')
        })

    # 降噪返回（避免把 config_json 原封不动传太大）
    exam_info = {
        'id': exam.get('id'),
        'subject': exam.get('subject'),
        'duration_minutes': exam.get('duration_minutes'),
        'status': exam.get('status'),
        'started_at': exam.get('started_at'),
        'submitted_at': exam.get('submitted_at'),
        'total_score': exam.get('total_score', 0)
    }

    return jsonify({'status': 'success', 'data': {'exam': exam_info, 'questions': formatted_questions}})


@exam_api_bp.route('/exams/save_draft', methods=['POST'])
@auth_required  # 支持session和JWT（小程序）
def api_save_exam_draft():
    """保存考试草稿"""
    uid = current_user_id()
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
@auth_required  # 支持session和JWT（小程序）
def api_exam_to_mistakes(exam_id):
    """将考试错题加入错题本"""
    uid = current_user_id()
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

