# -*- coding: utf-8 -*-
"""
刷题路由蓝图
"""
import json
import random
from flask import Blueprint, render_template, request, session
from ..utils.database import get_db
from ..utils.options_parser import parse_options

quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route('/quiz')
def quiz_page():
    """刷题页面"""
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', 'quiz').lower()
    source = request.args.get('source', '').lower()  # 兼容背题来源（收藏/错题）
    exam_id = request.args.get('exam_id', type=int)
    
    # 获取打乱设置
    shuffle_questions = request.args.get('shuffle_questions', '0') == '1'
    shuffle_options = request.args.get('shuffle_options', '0') == '1'
    
    uid = session.get('user_id') or -1
    conn = get_db()
    
    # 根据不同模式获取题目
    target = source if source in ('favorites', 'mistakes') else mode
    if mode == 'exam' and exam_id:
        # 考试模式：获取考试题目
        sql = """
            SELECT q.*, s.name as subject, eq.user_answer, eq.score_val,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM exam_questions eq
            JOIN questions q ON eq.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE eq.exam_id = ?
            ORDER BY eq.order_index
        """
        rows = conn.execute(sql, (uid, uid, exam_id)).fetchall()
    elif target == 'favorites':
        # 收藏模式
        sql = """
            SELECT q.*, s.name as subject,
                   1 as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE f.user_id = ?
        """
        params = [uid, uid]
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.q_type = ?"
            params.append(q_type)
        
        rows = conn.execute(sql, params).fetchall()
    elif target == 'mistakes':
        # 错题模式
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   1 as is_mistake
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            WHERE m.user_id = ?
        """
        params = [uid, uid]
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.q_type = ?"
            params.append(q_type)
        
        rows = conn.execute(sql, params).fetchall()
    else:
        # 普通刷题/背题模式
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE 1=1
        """
        params = [uid, uid]
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.q_type = ?"
            params.append(q_type)
        
        rows = conn.execute(sql, params).fetchall()
    
    # 读取已保存的做题顺序（如果是打乱题目模式且已保存）
    saved_order = None
    if shuffle_questions and mode != 'exam' and uid != -1:
        # 生成进度key，与前端 progressKey 保持一致
        data_scope = target if target in ('favorites', 'mistakes') else 'all'
        key_parts = [
            f"quiz_progress_{uid}",
            mode,
            subject,
            q_type,
            data_scope,
            f"q{1 if shuffle_questions else 0}",
            f"o{1 if shuffle_options else 0}"
        ]
        p_key = "_".join(key_parts)
        try:
            saved = conn.execute('SELECT data FROM user_progress WHERE user_id=? AND p_key=?', (uid, p_key)).fetchone()
            if saved and saved['data']:
                saved_json = json.loads(saved['data'])
                if isinstance(saved_json, dict) and isinstance(saved_json.get('order'), list):
                    saved_order = saved_json['order']
        except Exception:
            saved_order = None

    # 处理题目数据
    questions = []
    question_ids = []
    for row in rows:
        q = dict(row)
        image_path = q.get('image_path')
        image_path_json = '[]'
        if image_path and isinstance(image_path, str):
            # Check if it's already a JSON array string
            if image_path.strip().startswith('[') and image_path.strip().endswith(']'):
                image_path_json = image_path
            else:
                # It's a single path string, wrap it in an array
                image_path_json = json.dumps([image_path])
        q['image_path_json'] = image_path_json

        if q.get('options'):
            try:
                # 统一 options 解析（兼容有/无 A/B 前缀、数字列表、结构化等）
                q['options'] = parse_options(q['options'])

                # 打乱选项顺序
                if shuffle_options and q['options'] and q.get('q_type') == '选择题':
                    # 1. 保存原始正确答案的文本
                    orig_answer_keys = str(q.get('answer') or '')
                    correct_texts = []
                    options_map = {opt['key']: opt['value'] for opt in q['options']}
                    for key in orig_answer_keys:
                        if key in options_map:
                            correct_texts.append(options_map[key])
                    
                    # 2. 打乱选项列表
                    random.shuffle(q['options'])
                    
                    # 3. 根据打乱后的顺序，重新分配 A,B,C,D 并找到新答案
                    abcd = 'ABCD'
                    new_answer_keys = []
                    for i, option in enumerate(q['options']):
                        if i < len(abcd):
                            # original_key = option['key']  # 保存原始key（当前逻辑未使用，保留注释）
                            option['key'] = abcd[i] # 重新分配key
                            if option['value'] in correct_texts:
                                new_answer_keys.append(option['key'])
                    
                    # 4. 更新答案
                    q['answer'] = ''.join(sorted(new_answer_keys))
            except Exception:
                q['options'] = []
        questions.append(q)
        question_ids.append(q['id'])
    
    # 打乱题目顺序后，生成最终的题目ID列表，用于传递给前端
    question_ids_for_template = [q['id'] for q in questions]

    # 打乱题目顺序(考试模式除外,考试模式需要保持order_index顺序)
    if shuffle_questions and mode != 'exam':
        if saved_order:
            # 如果有已保存的顺序，则按此顺序排序
            q_map = {q['id']: q for q in questions}
            ordered_questions = []
            for qid in saved_order:
                if qid in q_map:
                    ordered_questions.append(q_map.pop(qid))
            # 追加剩余的题目（如果有新增题目）
            if q_map:
                ordered_questions.extend(q_map.values())
            questions = ordered_questions
        else:
            # 否则，随机打乱并保存新的顺序
            random.shuffle(questions)
            if uid != -1:
                new_order = [q['id'] for q in questions]
                # 生成进度key
                data_scope = target if target in ('favorites', 'mistakes') else 'all'
                key_parts = [
                    f"quiz_progress_{uid}",
                    mode,
                    subject,
                    q_type,
                    data_scope,
                    f"q{1 if shuffle_questions else 0}",
                    f"o{1 if shuffle_options else 0}"
                ]
                p_key = "_".join(key_parts)
                # 尝试获取现有进度数据
                try:
                    existing_data = conn.execute('SELECT data FROM user_progress WHERE user_id=? AND p_key=?', (uid, p_key)).fetchone()
                    if existing_data and existing_data['data']:
                        progress_json = json.loads(existing_data['data'])
                    else:
                        progress_json = {}
                except Exception:
                    progress_json = {}
                # 更新顺序并写回数据库
                progress_json['order'] = new_order
                progress_json['timestamp'] = progress_json.get('timestamp', 0) # 保留原有时间戳
                data_to_save = json.dumps(progress_json, ensure_ascii=False)
                conn.execute(
                    "INSERT INTO user_progress (user_id, p_key, data) VALUES (?, ?, ?) ON CONFLICT(user_id, p_key) DO UPDATE SET data = excluded.data",
                    (uid, p_key, data_to_save)
                )
                conn.commit()
    
    # 获取用户的答题记录（用于恢复答题状态）
    user_answers_json = '{}'
    uid = session.get('user_id')
    
    # 考试模式：从 exam_questions 表获取用户答案
    if mode == 'exam' and exam_id:
        user_answers = {}
        for q in questions:
            if q.get('user_answer'):
                user_answers[str(q['id'])] = q['user_answer']
        user_answers_json = json.dumps(user_answers, ensure_ascii=False)
    # 其他模式：从 user_answers 表获取答题记录
    elif uid and question_ids:
        try:
            # 获取用户对这些题目的最新答题记录
            placeholders = ','.join(['?'] * len(question_ids))
            answer_rows = conn.execute(
                f'''SELECT question_id, is_correct 
                   FROM user_answers 
                   WHERE user_id = ? AND question_id IN ({placeholders})
                   ORDER BY created_at DESC''',
                [uid] + question_ids
            ).fetchall()
            
            # 构建答题记录字典（每道题只保留最新的一条记录）
            user_answers = {}
            seen_questions = set()
            for row in answer_rows:
                q_id = row['question_id']
                if q_id not in seen_questions:
                    user_answers[str(q_id)] = {
                        'is_correct': bool(row['is_correct'])
                    }
                    seen_questions.add(q_id)
            
            user_answers_json = json.dumps(user_answers, ensure_ascii=False)
        except Exception as e:
            # 如果出错，使用空字典
            user_answers_json = '{}'
    
    # 考试模式：获取考试信息(时长、状态等)
    duration = 0
    submitted = False
    if mode == 'exam' and exam_id:
        exam_row = conn.execute('SELECT duration_minutes, status FROM exams WHERE id=?', (exam_id,)).fetchone()
        if exam_row:
            duration = exam_row['duration_minutes']
            submitted = (exam_row['status'] == 'submitted')
    
    return render_template('quiz.html',
                         questions=questions,
                         mode=mode,
                         source=source,
                         exam_id=exam_id,
                         user_answers_json=user_answers_json,
                         logged_in=bool(uid),
                         user_id=uid,
                         username=session.get('username'),
                         duration=duration,
                         submitted=submitted)

