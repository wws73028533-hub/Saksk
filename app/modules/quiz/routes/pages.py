# -*- coding: utf-8 -*-
"""刷题页面路由"""
import json
import random
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.core.utils.database import get_db
from app.core.utils.options_parser import parse_options

# 子蓝图需要指定template_folder（Flask子蓝图不会自动继承父蓝图的template_folder）
import os
# __file__ 是 app/modules/quiz/routes/pages.py
# 需要向上两级到quiz模块目录：routes -> quiz
module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
template_dir = os.path.join(module_dir, 'templates')
quiz_pages_bp = Blueprint('quiz_pages', __name__, template_folder=template_dir)


@quiz_pages_bp.route('/quiz')
def quiz_page():
    """刷题页面"""
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', 'quiz').lower()
    source = request.args.get('source', '').lower()  # 兼容背题来源（收藏/错题）
    tag = (request.args.get('tag') or '').strip()
    exam_id = request.args.get('exam_id', type=int)
    bank_id = request.args.get('bank_id', type=int)
    
    # 获取打乱设置
    shuffle_questions = request.args.get('shuffle_questions', '0') == '1'
    shuffle_options = request.args.get('shuffle_options', '0') == '1'
    
    uid = session.get('user_id') or -1
    conn = get_db()

    # ====================================================
    # 个人题库（user_question_banks / user_bank_questions）
    # 复用共有刷题模板：/quiz?bank_id=<id>
    # ====================================================
    if bank_id and mode != 'exam':
        # 个人题库不支持未登录访问
        if uid == -1:
            return redirect(url_for('auth.auth_pages.login_page'))

        from app.modules.user_bank.routes.api import check_bank_access, _load_bank_tag_store

        has_access, _permission, _access_type = check_bank_access(uid, int(bank_id))
        if not has_access:
            return render_template(
                'quiz/quiz.html',
                questions=[],
                mode=mode,
                source=source,
                exam_id=None,
                user_answers_json='{}',
                logged_in=True,
                user_id=uid,
                username=session.get('username'),
                is_admin=bool(session.get('is_admin')),
                is_subject_admin=bool(session.get('is_subject_admin')),
                duration=0,
                submitted=False,
            )

        # tag 过滤：bank_<bank_id>_tags 存储在 user_progress
        tag_question_ids = None
        if tag and str(tag).lower() != 'all':
            try:
                store = _load_bank_tag_store(conn, int(bank_id), uid)
                question_tags = store.get('question_tags', {}) or {}
                tag_question_ids = []
                for q_id, tags in question_tags.items():
                    if not isinstance(tags, list):
                        continue
                    if tag in tags:
                        try:
                            tag_question_ids.append(int(q_id))
                        except Exception:
                            continue
            except Exception:
                tag_question_ids = []

            if not tag_question_ids:
                return render_template(
                    'quiz/quiz.html',
                    questions=[],
                    mode=mode,
                    source=source,
                    exam_id=None,
                    user_answers_json='{}',
                    logged_in=True,
                    user_id=uid,
                    username=session.get('username'),
                    is_admin=bool(session.get('is_admin')),
                    is_subject_admin=bool(session.get('is_subject_admin')),
                    duration=0,
                    submitted=False,
                )

        # scope：复用 source=favorites/mistakes
        sql = "SELECT q.* FROM user_bank_questions q"
        params = []
        if source == 'mistakes':
            sql += " JOIN user_bank_mistakes m ON q.id = m.question_id AND m.user_id = ?"
            params.append(uid)
        elif source == 'favorites':
            sql += " JOIN user_bank_favorites f ON q.id = f.question_id AND f.user_id = ?"
            params.append(uid)

        sql += " WHERE q.bank_id = ?"
        params.append(int(bank_id))

        if q_type != 'all':
            sql += " AND q.q_type = ?"
            params.append(q_type)

        if tag_question_ids is not None:
            tag_question_ids = sorted(set(tag_question_ids))
            if len(tag_question_ids) <= 900:
                placeholders = ",".join(["?"] * len(tag_question_ids))
                sql += f" AND q.id IN ({placeholders})"
                params.extend(tag_question_ids)
            else:
                sql += " AND q.id IN ({})".format(",".join(str(i) for i in tag_question_ids))

        if source == 'mistakes':
            sql += " ORDER BY m.wrong_count DESC, m.updated_at DESC"
        elif source == 'favorites':
            sql += " ORDER BY f.created_at DESC"
        else:
            sql += " ORDER BY q.sort_order ASC, q.id ASC"

        rows = conn.execute(sql, params).fetchall()
        q_ids = [int(r['id']) for r in rows] if rows else []

        # 收藏/错题状态
        fav_set = set()
        mis_set = set()
        if q_ids:
            placeholders = ",".join(["?"] * len(q_ids))
            fav_rows = conn.execute(
                f"SELECT question_id FROM user_bank_favorites WHERE user_id = ? AND question_id IN ({placeholders})",
                [uid] + q_ids,
            ).fetchall()
            fav_set = {int(r['question_id']) for r in fav_rows}

            mis_rows = conn.execute(
                f"SELECT question_id FROM user_bank_mistakes WHERE user_id = ? AND question_id IN ({placeholders})",
                [uid] + q_ids,
            ).fetchall()
            mis_set = {int(r['question_id']) for r in mis_rows}

        # 历史答案回显
        ua_map = {}
        if q_ids:
            placeholders = ",".join(["?"] * len(q_ids))
            ua_rows = conn.execute(
                f"SELECT question_id, user_answer FROM user_bank_answers WHERE user_id = ? AND bank_id = ? AND question_id IN ({placeholders})",
                [uid, int(bank_id)] + q_ids,
            ).fetchall()
            ua_map = {int(r['question_id']): (r['user_answer'] or '') for r in ua_rows}

        questions = []
        for row in rows:
            q = dict(row)
            q['is_fav'] = 1 if int(q.get('id') or 0) in fav_set else 0
            q['is_mistake'] = 1 if int(q.get('id') or 0) in mis_set else 0

            # 统一 image_path_json（个人题库当前不存图时也保持兼容字段）
            image_path = q.get('image_path')
            image_path_json = '[]'
            if image_path and isinstance(image_path, str):
                if image_path.strip().startswith('[') and image_path.strip().endswith(']'):
                    image_path_json = image_path
                else:
                    image_path_json = json.dumps([image_path])
            q['image_path_json'] = image_path_json

            # options 统一解析
            if q.get('options'):
                try:
                    q['options'] = parse_options(q['options'])
                except Exception:
                    q['options'] = []
            else:
                q['options'] = []

            # 答案格式兼容：选择/多选支持 "A,B" / "AB"；判断兼容 对/错/true/false 等
            try:
                qtype = str(q.get('q_type') or '')
                ans_raw = str(q.get('answer') or '').strip()

                if qtype in ('选择题', '多选题'):
                    q['answer'] = ''.join([c for c in ans_raw if c.isalpha()]).upper()
                elif qtype == '判断题':
                    v = ans_raw.strip().lower()
                    if v in ('对', '正确', 'true', 't', '1', 'yes', 'y'):
                        q['answer'] = '正确'
                    elif v in ('错', '错误', 'false', 'f', '0', 'no', 'n'):
                        q['answer'] = '错误'
            except Exception:
                pass

            questions.append(q)

        return render_template(
            'quiz/quiz.html',
            questions=questions,
            mode=mode,
            source=source,
            exam_id=None,
            user_answers_json=json.dumps(ua_map, ensure_ascii=False),
            logged_in=True,
            user_id=uid,
            username=session.get('username'),
            is_admin=bool(session.get('is_admin')),
            is_subject_admin=bool(session.get('is_subject_admin')),
            duration=0,
            submitted=False,
        )
    
    # 获取用户可访问的科目ID列表（用于权限过滤）
    accessible_subject_ids = None
    if uid and uid != -1 and mode != 'exam':
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        accessible_subject_ids = get_user_accessible_subjects(uid)
        # 如果没有可访问的科目，直接返回空题目列表
        if not accessible_subject_ids:
            return render_template('quiz/quiz.html',
                                 questions=[],
                                 mode=mode,
                                 source=source,
                                 exam_id=exam_id,
                                 user_answers_json='{}',
                                 logged_in=bool(uid),
                                 user_id=uid,
                                 username=session.get('username'),
                                 is_admin=bool(session.get('is_admin')),
                                 is_subject_admin=bool(session.get('is_subject_admin')),
                                 duration=0,
                                 submitted=False)
    
    exam_meta = None
    exam_source = 'public'
    if mode == 'exam' and exam_id:
        exam_meta = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
        if not exam_meta:
            return "考试不存在或无权限", 404
        if exam_meta['user_id'] != uid and not session.get('is_admin'):
            return "考试不存在或无权限", 403

        try:
            cfg = json.loads(exam_meta['config_json'] or '{}')
            if not isinstance(cfg, dict):
                cfg = {}
        except Exception:
            cfg = {}

        exam_source = (cfg.get('source') or 'public').strip().lower()
        if exam_source not in ('public', 'user_bank'):
            exam_source = 'public'

    # 根据不同模式获取题目
    target = source if source in ('favorites', 'mistakes') else mode
    if mode == 'exam' and exam_id:
        # 考试模式：获取考试题目
        if exam_source == 'user_bank':
            sql = """
                SELECT q.*, ? as subject, eq.user_answer, eq.score_val,
                       CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                       CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
                FROM exam_questions eq
                JOIN user_bank_questions q ON eq.question_id = q.id
                LEFT JOIN user_bank_favorites f ON q.id = f.question_id AND f.user_id = ?
                LEFT JOIN user_bank_mistakes m ON q.id = m.question_id AND m.user_id = ?
                WHERE eq.exam_id = ?
                ORDER BY eq.order_index
            """
            rows = conn.execute(sql, (exam_meta['subject'] or '', uid, uid, exam_id)).fetchall()
        else:
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
        # 收藏模式（过滤掉锁定科目和被限制科目的题目）
        sql = """
            SELECT q.*, s.name as subject,
                   1 as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid, uid]
        
        # 添加权限过滤
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.q_type = ?"
            params.append(q_type)
        
        rows = conn.execute(sql, params).fetchall()

    # 标签筛选（仅对当前用户生效）
    if tag and str(tag).lower() != 'all' and uid and uid != -1 and mode != 'exam':
        from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            rows = []
        else:
            rows = [r for r in rows if int(r['id']) in tag_ids]
    elif target == 'mistakes':
        # 错题模式（过滤掉锁定科目和被限制科目的题目）
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   1 as is_mistake
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid, uid]
        
        # 添加权限过滤
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            sql += " AND q.q_type = ?"
            params.append(q_type)
        
        rows = conn.execute(sql, params).fetchall()
    else:
        # 普通刷题/背题模式（过滤掉锁定科目和被限制科目的题目）
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid, uid]
        
        # 添加权限过滤
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        elif uid == -1:
            # 未登录用户：返回空结果
            sql += " AND 1=0"
        
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
            f"tag{tag}" if tag and str(tag).lower() != 'all' else None,
            f"q{1 if shuffle_questions else 0}",
            f"o{1 if shuffle_options else 0}"
        ]
        p_key = "_".join([p for p in key_parts if p])
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

                # 打乱选项顺序（使用确定性随机，确保同一用户同一题目的选项顺序一致）
                if shuffle_options and q['options'] and q.get('q_type') in ('选择题', '多选题'):
                    # 1. 保存原始正确答案的文本
                    orig_answer_keys = str(q.get('answer') or '')
                    correct_texts = []
                    options_map = {opt['key']: opt['value'] for opt in q['options']}
                    for key in orig_answer_keys:
                        if key in options_map:
                            correct_texts.append(options_map[key])
                    
                    # 2. 使用确定性随机打乱选项
                    # 种子 = 用户ID + 题目ID，确保同一用户同一题目的选项顺序永远一致
                    shuffle_seed = (uid if uid != -1 else 0) * 1000000 + q['id']
                    rng = random.Random(shuffle_seed)
                    rng.shuffle(q['options'])
                    
                    # 3. 根据打乱后的顺序，重新分配 A,B,C,D 并找到新答案
                    abcd = 'ABCD'
                    new_answer_keys = []
                    for i, option in enumerate(q['options']):
                        if i < len(abcd):
                            option['key'] = abcd[i]  # 重新分配key
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
                    f"tag{tag}" if tag and str(tag).lower() != 'all' else None,
                    f"q{1 if shuffle_questions else 0}",
                    f"o{1 if shuffle_options else 0}"
                ]
                p_key = "_".join([p for p in key_parts if p])
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
        if exam_meta:
            duration = exam_meta['duration_minutes']
            submitted = (exam_meta['status'] == 'submitted')
        else:
            exam_row = conn.execute('SELECT duration_minutes, status FROM exams WHERE id=?', (exam_id,)).fetchone()
            if exam_row:
                duration = exam_row['duration_minutes']
                submitted = (exam_row['status'] == 'submitted')
    
    return render_template('quiz/quiz.html',
                         questions=questions,
                         mode=mode,
                         source=source,
                         exam_id=exam_id,
                         user_answers_json=user_answers_json,
                         logged_in=bool(uid),
                         user_id=uid,
                         username=session.get('username'),
                         is_admin=bool(session.get('is_admin')),
                         is_subject_admin=bool(session.get('is_subject_admin')),
                         duration=duration,
                         submitted=submitted)
