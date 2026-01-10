# -*- coding: utf-8 -*-
"""刷题API路由"""
from flask import Blueprint, request, jsonify, session, g
from app.core.utils.database import get_db
from app.core.extensions import limiter
from app.core.utils.decorators import jwt_required, auth_required, current_user_id
from app.core.models.question import Question
from app.core.utils.options_parser import parse_options

quiz_api_bp = Blueprint('quiz_api', __name__)

def _get_uid_from_request():
    """获取用户ID（优先 session，其次 JWT header；无需强制登录）"""
    uid = session.get('user_id')
    if uid:
        return uid

    token = request.headers.get('Authorization') or request.headers.get('authorization')
    if not token:
        return None
    try:
        if token.startswith('Bearer '):
            token = token[7:]
        from app.core.utils.jwt_utils import decode_jwt_token
        payload = decode_jwt_token(token)
        if payload and payload.get('user_id'):
            return payload.get('user_id')
    except Exception:
        return None

    return None


@quiz_api_bp.route('/favorite', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.exempt  # 收藏接口不限流
def toggle_favorite():
    """切换收藏状态"""
    data = request.json
    q_id = data.get('question_id')
    uid = current_user_id()
    
    conn = get_db()
    exists = conn.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND question_id = ?",
        (uid, q_id)
    ).fetchone()
    
    if exists:
        conn.execute("DELETE FROM favorites WHERE user_id = ? AND question_id = ?", (uid, q_id))
    else:
        conn.execute("INSERT INTO favorites (user_id, question_id) VALUES (?, ?)", (uid, q_id))
    
    conn.commit()
    return jsonify({"status": "success"})


@quiz_api_bp.route('/record_result', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.exempt  # 答题记录接口不限流
def record_result():
    """记录做题结果（添加刷题限制检查）"""
    from app.core.utils.subject_permissions import (
        check_quiz_limit, 
        increment_user_quiz_count,
        get_user_quiz_count,
        get_quiz_limit_count
    )
    
    data = request.json or {}
    q_id = data.get('question_id')
    is_correct = data.get('is_correct')
    clear_mistake_on_correct = data.get('clear_mistake_on_correct', True)
    uid = current_user_id()
    
    if not q_id or is_correct is None:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400

    # 兼容 clear_mistake_on_correct 可能为 string/int/bool；默认 True（保持旧行为）
    try:
        if isinstance(clear_mistake_on_correct, str):
            v = clear_mistake_on_correct.strip().lower()
            if v in ('0', 'false', 'no', 'off'):
                clear_mistake_on_correct = False
            elif v in ('1', 'true', 'yes', 'on'):
                clear_mistake_on_correct = True
            else:
                clear_mistake_on_correct = True
        elif isinstance(clear_mistake_on_correct, (int, float)):
            clear_mistake_on_correct = bool(clear_mistake_on_correct)
        else:
            clear_mistake_on_correct = bool(clear_mistake_on_correct)
    except Exception:
        clear_mistake_on_correct = True
    
    # 检查刷题限制
    is_limited, limit_message = check_quiz_limit(uid)
    if is_limited:
        return jsonify({
            'status': 'error',
            'message': limit_message,
            'code': 'QUIZ_LIMIT_REACHED',
            'data': {
                'current_count': get_user_quiz_count(uid),
                'limit_count': get_quiz_limit_count(),
                'contact_admin_url': '/contact_admin'
            }
        }), 403
    
    conn = get_db()
    try:
        # 更新错题本（只记录错误题目）
        if not is_correct:
            conn.execute(
                "INSERT INTO mistakes (user_id, question_id, wrong_count) VALUES (?, ?, 1) ON CONFLICT(user_id, question_id) DO UPDATE SET wrong_count = wrong_count + 1",
                (uid, q_id)
            )
            action = "added_mistake"
        else:
            if clear_mistake_on_correct:
                # 答对了，从错题本中移除（默认行为）
                conn.execute("DELETE FROM mistakes WHERE user_id = ? AND question_id = ?", (uid, q_id))
                action = "removed_mistake"
            else:
                # 答对但不清除：保留在错题本
                action = "kept_mistake"
        
        # 记录答题历史（每次答题都记录，用于统计）
        # 先删除旧记录，再插入新记录，确保每个用户对每道题只保留最新的一条记录
        conn.execute(
            'DELETE FROM user_answers WHERE user_id = ? AND question_id = ?',
            (uid, q_id)
        )
        conn.execute(
            """INSERT INTO user_answers 
               (user_id, question_id, is_correct, created_at) 
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
            (uid, q_id, 1 if is_correct else 0)
        )
        
        # 增加刷题数（如果功能开启）
        increment_user_quiz_count(uid)
        
        conn.commit()
        return jsonify({"status": "success", "action": action})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "msg": str(e)}), 500


@quiz_api_bp.route('/questions/count')
@limiter.exempt  # 题目数量查询不限流
def api_questions_count():
    """获取题目数量（添加权限过滤）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
    
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', '').lower()
    source = request.args.get('source', '').lower()  # 兼容背题模式下的来源
    tag = (request.args.get('tag') or '').strip()
    uid = _get_uid_from_request()
    
    conn = get_db()
    
    # 获取用户可访问的科目ID列表（用于权限过滤）
    accessible_subject_ids = None
    if uid:
        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return jsonify({'status':'success','count': 0})

    # 兼容新的 source 参数，优先使用 source，其次 mode
    target = source if source in ('favorites', 'mistakes') else mode
    
    if target == 'favorites':
        if not uid:
            return jsonify({'status':'success','count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN favorites f ON f.question_id = q.id AND f.user_id = ? WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = [uid]
    elif target == 'mistakes':
        if not uid:
            return jsonify({'status':'success','count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN mistakes m ON m.question_id = q.id AND m.user_id = ? WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = [uid]
    else:
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE (s.is_locked=0 OR s.is_locked IS NULL)"
        params = []
    
    # 添加权限过滤
    if accessible_subject_ids is not None:
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        base_sql += f" AND q.subject_id IN ({placeholders})"
        params.extend(accessible_subject_ids)
    # 未登录用户：不添加权限过滤，显示所有未锁定科目的题目数（已在base_sql中过滤了is_locked）
    
    if subject != 'all':
        base_sql += " AND s.name = ?"
        params.append(subject)
    
    if q_type != 'all':
        base_sql += " AND q.q_type = ?"
        params.append(q_type)

    # 标签筛选：无登录 / 无命中直接返回 0（标签是用户私有）
    if tag and str(tag).lower() != 'all':
        if not uid:
            return jsonify({'status': 'success', 'count': 0})
        tag_ids = get_question_ids_by_tag(conn, uid, tag)
        if not tag_ids:
            return jsonify({'status': 'success', 'count': 0})

        # 变量过多时避免 IN 触发 SQLite 参数上限：回退为取ID后求交集
        if len(tag_ids) > 900:
            id_rows = conn.execute("SELECT q.id " + base_sql, params).fetchall()
            base_ids = {int(r[0]) for r in id_rows if r and r[0] is not None}
            return jsonify({'status': 'success', 'count': len(base_ids & set(tag_ids))})

        placeholders = ','.join(['?'] * len(tag_ids))
        sql = "SELECT COUNT(1) " + base_sql + f" AND q.id IN ({placeholders})"
        cnt = conn.execute(sql, params + list(tag_ids)).fetchone()[0]
        return jsonify({'status': 'success', 'count': cnt})

    sql = "SELECT COUNT(1) " + base_sql
    cnt = conn.execute(sql, params).fetchone()[0]
    return jsonify({'status': 'success', 'count': cnt})


@quiz_api_bp.route('/questions/user_counts')
@limiter.exempt  # 用户计数查询不限流
def api_user_counts():
    """获取用户的收藏和错题数量"""
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    uid = _get_uid_from_request()
    
    if not uid:
        return jsonify({'status': 'success', 'favorites': 0, 'mistakes': 0})
    
    conn = get_db()
    
    fav_sql = """
        SELECT COUNT(1)
        FROM favorites f
        JOIN questions q ON q.id = f.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE f.user_id = ?
    """
    mis_sql = """
        SELECT COUNT(1)
        FROM mistakes m
        JOIN questions q ON q.id = m.question_id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE m.user_id = ?
    """
    
    fav_params = [uid]
    mis_params = [uid]
    
    if subject != 'all':
        fav_sql += " AND s.name = ?"
        mis_sql += " AND s.name = ?"
        fav_params.append(subject)
        mis_params.append(subject)
    
    if q_type != 'all':
        fav_sql += " AND q.q_type = ?"
        mis_sql += " AND q.q_type = ?"
        fav_params.append(q_type)
        mis_params.append(q_type)
    
    fav_cnt = conn.execute(fav_sql, fav_params).fetchone()[0]
    mis_cnt = conn.execute(mis_sql, mis_params).fetchone()[0]
    
    return jsonify({'status': 'success', 'favorites': fav_cnt, 'mistakes': mis_cnt})


@quiz_api_bp.route('/progress', methods=['GET', 'POST', 'DELETE'])
@auth_required  # 支持session和JWT（小程序/网页共用 user_progress）
@limiter.exempt  # 进度同步接口不限流
def progress_api():
    """用户答题进度同步API"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    conn = get_db()
    
    if request.method == 'GET':
        # 获取进度
        key = request.args.get('key', '').strip()
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400
        
        try:
            row = conn.execute(
                'SELECT data FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, key)
            ).fetchone()
            
            if row:
                import json
                data = json.loads(row['data'])
                return jsonify({'status': 'success', 'data': data})
            else:
                return jsonify({'status': 'success', 'data': None})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    elif request.method == 'POST':
        # 保存进度
        data = request.json
        key = data.get('key', '').strip()
        progress_data = data.get('data')
        
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400
        
        try:
            import json
            data_json = json.dumps(progress_data, ensure_ascii=False)
            
            # 先检查是否存在，存在则更新，不存在则插入
            existing = conn.execute(
                'SELECT id FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, key)
            ).fetchone()
            
            if existing:
                conn.execute(
                    """UPDATE user_progress 
                       SET data = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE user_id = ? AND p_key = ?""",
                    (data_json, uid, key)
                )
            else:
                # 检查是否有created_at字段
                try:
                    conn.execute(
                        """INSERT INTO user_progress (user_id, p_key, data, updated_at, created_at) 
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                        (uid, key, data_json)
                    )
                except:
                    # 如果created_at字段不存在,则不包含它
                    conn.execute(
                        """INSERT INTO user_progress (user_id, p_key, data, updated_at) 
                           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                        (uid, key, data_json)
                    )
            conn.commit()
            
            return jsonify({'status': 'success', 'message': '进度已保存'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    elif request.method == 'DELETE':
        # 删除进度
        key = request.args.get('key', '').strip()
        if not key:
            return jsonify({'status': 'error', 'message': '缺少key参数'}), 400
        
        try:
            conn.execute(
                'DELETE FROM user_progress WHERE user_id = ? AND p_key = ?',
                (uid, key)
            )
            conn.commit()
            return jsonify({'status': 'success', 'message': '进度已删除'})
        except Exception as e:
            conn.rollback()
            return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/tags', methods=['GET', 'POST', 'DELETE'])
@auth_required  # 支持session和JWT
@limiter.exempt
def tags_api():
    """用户题目标签（存储于 user_progress，不改DB结构）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    from app.modules.quiz.services.question_tags_service import (
        list_user_tags,
        create_user_tag,
        delete_user_tag,
    )

    conn = get_db()

    if request.method == 'GET':
        tags = list_user_tags(conn, uid)
        return jsonify({'status': 'success', 'data': {'tags': tags}})

    data = request.json or {}
    name = data.get('name') or data.get('tag') or data.get('tag_name')

    if request.method == 'POST':
        ok, msg, tag = create_user_tag(conn, uid, name)
        if not ok:
            conn.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        conn.commit()
        tags = list_user_tags(conn, uid)
        return jsonify({'status': 'success', 'data': {'tag': tag, 'tags': tags}})

    if request.method == 'DELETE':
        ok, msg = delete_user_tag(conn, uid, name)
        if not ok:
            conn.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        conn.commit()
        tags = list_user_tags(conn, uid)
        return jsonify({'status': 'success', 'data': {'tags': tags}})

    return jsonify({'status': 'error', 'message': '不支持的请求方式'}), 405


@quiz_api_bp.route('/questions/<int:question_id>/tags', methods=['GET', 'POST'])
@auth_required  # 支持session和JWT
@limiter.exempt
def question_tags_api(question_id: int):
    """题目标签管理（对当前用户生效）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    # 校验题目存在 + 权限
    question = Question.get_by_id(question_id)
    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    from app.core.utils.subject_permissions import can_user_access_subject
    if question.get('subject_id') and not can_user_access_subject(uid, question['subject_id']):
        return jsonify({'status': 'error', 'message': '无权限访问该题目'}), 403

    from app.modules.quiz.services.question_tags_service import (
        get_question_tags,
        set_question_tags,
        update_question_tags,
    )

    conn = get_db()

    if request.method == 'GET':
        tags = get_question_tags(conn, uid, question_id)
        return jsonify({'status': 'success', 'data': {'question_id': question_id, 'tags': tags}})

    data = request.json or {}
    try:
        if 'tags' in data:
            ok, msg, tags = set_question_tags(conn, uid, question_id, data.get('tags'))
        else:
            ok, msg, tags = update_question_tags(
                conn,
                uid,
                question_id,
                add=data.get('add'),
                remove=data.get('remove'),
            )
        if not ok:
            conn.rollback()
            return jsonify({'status': 'error', 'message': msg}), 400
        conn.commit()
        return jsonify({'status': 'success', 'data': {'question_id': question_id, 'tags': tags}})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/notifications_legacy', methods=['GET'])
@limiter.exempt
def get_notifications_legacy():
    """[兼容] 获取当前用户可见的通知列表（旧接口）"""
    uid = session.get('user_id')
    conn = get_db()

    if uid:
        # 登录用户：排除已关闭的通知（旧逻辑：关闭=不显示）
        sql = '''
            SELECT n.id, n.title, n.content, n.n_type, n.priority
            FROM notifications n
            LEFT JOIN notification_dismissals d
                ON d.notification_id = n.id AND d.user_id = ?
            WHERE n.is_active = 1
              AND d.id IS NULL
              AND (n.start_at IS NULL OR replace(n.start_at, 'T', ' ') <= datetime('now', 'localtime'))
              AND (n.end_at IS NULL OR replace(n.end_at, 'T', ' ') >= datetime('now', 'localtime'))
            ORDER BY n.priority DESC, n.created_at DESC
        '''
        rows = conn.execute(sql, (uid,)).fetchall()
    else:
        # 游客：显示所有活跃通知
        sql = '''
            SELECT id, title, content, n_type, priority
            FROM notifications
            WHERE is_active = 1
              AND (start_at IS NULL OR replace(start_at, 'T', ' ') <= datetime('now', 'localtime'))
              AND (end_at IS NULL OR replace(end_at, 'T', ' ') >= datetime('now', 'localtime'))
            ORDER BY priority DESC, created_at DESC
        '''
        rows = conn.execute(sql).fetchall()

    return jsonify({
        'status': 'success',
        'notifications': [dict(row) for row in rows]
    })


@quiz_api_bp.route('/notifications_legacy/<int:nid>/dismiss', methods=['POST'])
@limiter.exempt
def dismiss_notification_legacy(nid):
    """[兼容] 关闭/隐藏指定通知（旧接口）"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401

    conn = get_db()
    try:
        conn.execute(
            'INSERT OR IGNORE INTO notification_dismissals (user_id, notification_id) VALUES (?, ?)',
            (uid, nid)
        )
        conn.commit()
        return jsonify({'status': 'success', 'message': '通知已关闭'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/subjects', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_subjects():
    """获取科目列表（添加权限过滤）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    
    try:
        user_id = current_user_id()
        conn = get_db()
        
        if user_id:
            # 获取用户可访问的科目
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids:
                return jsonify({'status': 'success', 'subjects': []})
            
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            rows = conn.execute(
                f'''SELECT DISTINCT s.name 
                    FROM subjects s 
                    WHERE s.id IN ({placeholders}) AND (s.is_locked=0 OR s.is_locked IS NULL)
                    ORDER BY s.id''',
                accessible_subject_ids
            ).fetchall()
        else:
            # 未登录用户：返回空列表
            rows = []
        
        subjects = [row[0] for row in rows if row and row[0]]
        return jsonify({'status': 'success', 'subjects': subjects})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'subjects': []}), 500


@quiz_api_bp.route('/subjects/<subject>/info', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_subject_info(subject):
    """获取科目详情信息"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    
    try:
        user_id = current_user_id()
        conn = get_db()
        
        # 获取科目信息
        subject_row = conn.execute(
            'SELECT id, name FROM subjects WHERE name = ? AND (is_locked=0 OR is_locked IS NULL)',
            (subject,)
        ).fetchone()
        
        if not subject_row:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404
        
        subject_id = subject_row['id']
        
        # 检查用户权限
        if user_id:
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids or subject_id not in accessible_subject_ids:
                return jsonify({'status': 'error', 'message': '无权限访问该科目'}), 403
        
        # 获取题目总数
        total_count = conn.execute(
            'SELECT COUNT(*) FROM questions WHERE subject_id = ?',
            (subject_id,)
        ).fetchone()[0]

        # 获取该科目实际拥有的题型（用于小程序动态渲染）
        type_rows = conn.execute(
            "SELECT DISTINCT q_type FROM questions WHERE subject_id = ? AND q_type IS NOT NULL AND TRIM(q_type) != '' ORDER BY q_type",
            (subject_id,)
        ).fetchall()
        available_types = [r['q_type'] for r in type_rows if r and r['q_type']]
        
        # 获取作者信息（暂时设为空，后续可以从其他表获取）
        author = ''
        
        # 获取用户统计信息
        user_stats = {
            'done_count': 0,
            'wrong_count': 0,
            'favorite_count': 0,
            'note_count': 0,
            'last_activity': None
        }
        
        if user_id:
            # 已做题数（从user_answers表统计）
            done_count = conn.execute(
                'SELECT COUNT(DISTINCT question_id) FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()[0]
            
            # 错题数
            wrong_count = conn.execute(
                'SELECT COUNT(*) FROM mistakes m JOIN questions q ON m.question_id = q.id WHERE m.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()[0]
            
            # 收藏数
            favorite_count = conn.execute(
                'SELECT COUNT(*) FROM favorites f JOIN questions q ON f.question_id = q.id WHERE f.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()[0]
            
            # 最后活动时间（从user_answers表获取最新的created_at）
            last_activity_row = conn.execute(
                'SELECT MAX(ua.created_at) as last_activity FROM user_answers ua JOIN questions q ON ua.question_id = q.id WHERE ua.user_id = ? AND q.subject_id = ?',
                (user_id, subject_id)
            ).fetchone()
            
            last_activity = last_activity_row['last_activity'] if last_activity_row and last_activity_row['last_activity'] else None
            
            user_stats = {
                'done_count': done_count,
                'wrong_count': wrong_count,
                'favorite_count': favorite_count,
                'note_count': 0,  # 笔记功能暂未实现
                'last_activity': last_activity
            }
        
        return jsonify({
            'status': 'success',
            'data': {
                'subject': subject,
                'total_count': total_count,
                'author': author,
                'available_types': available_types,
                'user_stats': user_stats
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@quiz_api_bp.route('/search', methods=['GET'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_search_questions():
    """题目搜索（JSON，用于小程序）

    Query:
    - keyword: 搜索关键词（必填）
    - subject: 科目名称（可选，默认 all）
    - q_type/type: 题型（可选，默认 all）
    - page/per_page: 分页
    """
    import re
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    keyword = (request.args.get('keyword', '') or '').strip()
    subject = (request.args.get('subject', 'all') or 'all').strip()
    q_type = (request.args.get('q_type') or request.args.get('type') or 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)

    uid = current_user_id()
    conn = get_db()

    # 无关键词：直接返回空结果（前端可做实时输入）
    if not keyword:
        return jsonify({
            'status': 'success',
            'data': {'questions': [], 'total': 0, 'page': page, 'per_page': per_page}
        })

    # 权限过滤：仅搜索可访问科目
    accessible_subject_ids = get_user_accessible_subjects(uid) if uid else []
    if not accessible_subject_ids:
        return jsonify({
            'status': 'success',
            'data': {'questions': [], 'total': 0, 'page': page, 'per_page': per_page}
        })

    search_term = f'%{keyword}%'
    sql_base = """
        SELECT q.id, q.content, q.q_type, s.name as subject,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
        LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
        WHERE (s.is_locked=0 OR s.is_locked IS NULL)
          AND (q.content LIKE ? OR q.explanation LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)
    """
    params = [uid, uid, search_term, search_term, search_term, search_term]

    placeholders = ','.join(['?'] * len(accessible_subject_ids))
    sql_base += f" AND q.subject_id IN ({placeholders})"
    params.extend(accessible_subject_ids)

    if subject and subject != 'all':
        sql_base += " AND s.name = ?"
        params.append(subject)

    if q_type and q_type != 'all':
        sql_base += " AND q.q_type = ?"
        params.append(q_type)

    # 统计总数
    count_sql = f"SELECT COUNT(*) FROM ({sql_base})"
    total = conn.execute(count_sql, params).fetchone()[0]

    if page < 1:
        page = 1
    offset = (page - 1) * per_page

    sql = sql_base + " ORDER BY q.id DESC LIMIT ? OFFSET ?"
    rows = conn.execute(sql, params + [per_page, offset]).fetchall()

    questions = []
    for row in rows:
        q = dict(row)
        content = q.get('content') or ''
        try:
            text = re.sub(r'<[^>]+>', '', str(content)).replace('\n', ' ').strip()
        except Exception:
            text = str(content).replace('\n', ' ').strip()
        if len(text) > 80:
            text = text[:80] + '...'
        questions.append({
            'id': q.get('id'),
            'content': q.get('content', ''),
            'content_preview': text,
            'q_type': q.get('q_type', ''),
            'subject': q.get('subject', ''),
            'is_fav': q.get('is_fav', 0),
            'is_mistake': q.get('is_mistake', 0)
        })

    return jsonify({
        'status': 'success',
        'data': {
            'questions': questions,
            'total': total,
            'page': page,
            'per_page': per_page
        }
    })


@quiz_api_bp.route('/ai/explain', methods=['POST'])
@auth_required  # 支持session和JWT
@limiter.exempt
def api_ai_explain():
    """AI 解析接口（阿里云百炼 DashScope OpenAI 兼容接口）。

    环境变量（推荐写入项目根目录 .env）：
    - DASHSCOPE_API_KEY: 百炼 API-KEY
    - DASHSCOPE_BASE_URL: 可选，北京默认 https://dashscope.aliyuncs.com/compatible-mode/v1
    - DASHSCOPE_MODEL: 可选，默认 qwen-plus
    """
    from flask import current_app
    from app.core.utils.subject_permissions import can_user_access_subject
    from app.modules.quiz.services.ai_explain_service import generate_ai_explain

    uid = current_user_id()
    data = request.json or {}

    # 允许前端仅传 question_id；后端优先用库内题目，避免前端篡改
    raw_qid = data.get('question_id')
    qid = None
    try:
        qid = int(raw_qid) if raw_qid is not None and str(raw_qid).strip() else None
    except Exception:
        qid = None

    payload = {
        'question_id': qid,
        'content': (data.get('content') or '').strip(),
        'q_type': (data.get('q_type') or '').strip(),
        'options': data.get('options'),
        'answer': (data.get('answer') or '').strip(),
    }

    if qid:
        q = Question.get_by_id(qid)
        if q:
            subject_id = q.get('subject_id')
            if subject_id and uid and not can_user_access_subject(uid, subject_id):
                return jsonify({'status': 'forbidden', 'message': '无权限访问该题目'}), 403

            payload['content'] = (q.get('content') or '').strip()
            payload['q_type'] = (q.get('q_type') or '').strip()
            payload['options'] = q.get('options')
            payload['answer'] = (q.get('answer') or '').strip()

    if not payload.get('content') and not payload.get('question_id'):
        return jsonify({'status': 'error', 'message': '缺少题目信息'}), 400

    api_key = (current_app.config.get('DASHSCOPE_API_KEY') or '').strip()
    base_url = (current_app.config.get('DASHSCOPE_BASE_URL') or '').strip()
    model = (current_app.config.get('DASHSCOPE_MODEL') or '').strip()
    timeout = int(current_app.config.get('DASHSCOPE_TIMEOUT') or 25)

    # 未配置密钥：保留旧行为，返回“占位解析”，同时提示如何配置
    if not api_key:
        tip = '（未配置 DASHSCOPE_API_KEY，当前为模板解析；配置后将自动使用百炼模型）'
        lines = [tip, '', '建议解题思路：', '1) 先圈出关键词与限定条件。', '2) 把题干转为可验证的结论/公式/步骤。', '3) 对选择题：用排除法 + 代入验证。', '4) 对填空/问答题：列步骤，逐步推导，最后回代检查。']
        return jsonify({'status': 'success', 'data': {'explain': '\n'.join(lines), 'provider': 'placeholder'}})

    try:
        explain = generate_ai_explain(
            api_key=api_key,
            base_url=base_url,
            model=model or 'qwen-plus',
            payload=payload,
            timeout=timeout,
        )
        return jsonify({'status': 'success', 'data': {'explain': explain, 'provider': 'dashscope', 'model': model or 'qwen-plus'}})
    except Exception as e:
        current_app.logger.error('AI解析失败: %s', str(e), exc_info=True)
        return jsonify({'status': 'error', 'message': 'AI解析失败，请检查 DASHSCOPE_API_KEY / 计费状态 / 地域 Base URL 配置'}), 502


@quiz_api_bp.route('/coding/execute', methods=['POST'])
@limiter.limit("10 per minute")  # 限制执行频率：每分钟最多10次
def api_coding_execute():
    """
    代码执行接口（符合开发文档要求的路径：/api/coding/execute）
    
    Request Body:
    {
        "code": "print('Hello')",
        "language": "python",
        "input": "1\n2",  // 可选
        "time_limit": 5,  // 可选
        "memory_limit": 128  // 可选
    }
    
    Response:
    {
        "status": "success",
        "output": "Hello\n",
        "error": null,
        "execution_time": 0.05,
        "status_code": "success"
    }
    """
    if not session.get('user_id'):
        return jsonify({
            'status': 'unauthorized',
            'message': '请先登录'
        }), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        code = data.get('code', '').strip()
        language = data.get('language', 'python').lower()
        input_data = data.get('input', '')
        time_limit = data.get('time_limit', 5)
        memory_limit = data.get('memory_limit', 128)
        
        # 验证参数
        if not code:
            return jsonify({
                'status': 'error',
                'message': '代码不能为空'
            }), 400
        
        if language not in ['python']:  # 第一阶段只支持 Python
            return jsonify({
                'status': 'error',
                'message': f'不支持的编程语言: {language}'
            }), 400
        
        # 验证时间限制和内存限制
        if not isinstance(time_limit, (int, float)) or time_limit < 1 or time_limit > 30:
            time_limit = 5
        if not isinstance(memory_limit, int) or memory_limit < 64 or memory_limit > 512:
            memory_limit = 128
        
        # 执行代码
        from app.modules.coding.services.code_executor import PythonExecutor
        executor = PythonExecutor(time_limit=int(time_limit), memory_limit=memory_limit)
        result = executor.execute(code, input_data)
        
        # 限制输出长度（避免过长输出）
        if result.get('output') and len(result['output']) > 10000:
            result['output'] = result['output'][:10000] + '\n... (输出过长，已截断)'
        
        return jsonify({
            'status': 'success',
            'output': result.get('output', ''),
            'error': result.get('error'),
            'execution_time': result.get('execution_time', 0),
            'status_code': result.get('status', 'success')
        }), 200
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'服务器错误: {str(e)}'
        }), 500


@quiz_api_bp.route('/questions', methods=['GET'])
@jwt_required
def api_get_questions():
    """获取题目列表（JSON格式，用于小程序）"""
    try:
        # 获取查询参数
        subject = request.args.get('subject', 'all')
        q_type = request.args.get('q_type', 'all')
        mode = request.args.get('mode', 'quiz')
        tag = (request.args.get('tag') or '').strip()
        shuffle_options = request.args.get('shuffle_options', '0') in ('1', 'true', 'True')
        page = request.args.get('page', 1, type=int)
        # 小程序刷题页支持一次性加载较多题目（用于离线/顺滑切题）
        per_page = min(request.args.get('per_page', 20, type=int), 1000)
        
        # 从JWT token获取用户ID
        user_id = g.current_user_id
        
        # 获取题目列表
        questions = Question.get_list(
            subject=subject,
            q_type=q_type,
            mode=mode,
            user_id=user_id
        )

        # 标签筛选（用户私有）
        if tag and str(tag).lower() != 'all':
            from app.modules.quiz.services.question_tags_service import get_question_ids_by_tag
            conn = get_db()
            tag_ids = get_question_ids_by_tag(conn, user_id, tag)
            if not tag_ids:
                questions = []
            else:
                questions = [q for q in questions if int(q.get('id') or 0) in tag_ids]
        
        # 分页处理
        total = len(questions)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_questions = questions[start:end]
        
        # 格式化题目数据（转换为小程序需要的格式）
        formatted_questions = []
        for q in paginated_questions:
            q_type_val = q.get('q_type', '')
            options = parse_options(q.get('options'))
            # 判断题历史数据常为 []，小程序端需要可选项用于作答
            if q_type_val == '判断题' and not options:
                options = [
                    {'key': '正确', 'value': '正确'},
                    {'key': '错误', 'value': '错误'},
                ]

            # 打乱选项（确定性随机，与 Web 端保持一致；会同步重算答案字母）
            answer = q.get('answer', '') or ''
            if shuffle_options and options and q_type_val in ('选择题', '多选题'):
                try:
                    import random

                    orig_answer_keys = str(answer)
                    options_map = {opt.get('key'): opt.get('value') for opt in options}
                    correct_texts = []
                    for key in orig_answer_keys:
                        if key in options_map:
                            correct_texts.append(options_map[key])

                    shuffle_seed = int(user_id) * 1000000 + int(q.get('id') or 0)
                    rng = random.Random(shuffle_seed)
                    rng.shuffle(options)

                    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    new_answer_keys = []
                    for i, option in enumerate(options):
                        if i < len(letters):
                            option['key'] = letters[i]
                            if option.get('value') in correct_texts:
                                new_answer_keys.append(option['key'])

                    answer = ''.join(sorted(new_answer_keys))
                except Exception:
                    # 选项打乱失败时兜底：保持原 options/answer
                    pass
            
            formatted_q = {
                'id': q.get('id'),
                'content': q.get('content', ''),
                'q_type': q_type_val,
                'options': options,
                'answer': answer,
                'explanation': q.get('explanation', ''),
                'image_path': q.get('image_path'),
                'subject': q.get('subject', ''),
                'is_fav': q.get('is_fav', 0),
                'is_mistake': q.get('is_mistake', 0)
            }
            formatted_questions.append(formatted_q)
        
        return jsonify({
            'status': 'success',
            'data': {
                'questions': formatted_questions,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'获取题目列表失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'获取题目列表失败: {str(e)}'
        }), 500


@quiz_api_bp.route('/questions/<int:question_id>', methods=['GET'])
@jwt_required
def api_get_question_detail(question_id):
    """获取题目详情（JSON格式，用于小程序）"""
    try:
        shuffle_options = request.args.get('shuffle_options', '0') in ('1', 'true', 'True')
        # 从JWT token获取用户ID
        user_id = g.current_user_id
        
        # 获取题目详情
        question = Question.get_by_id(question_id)
        if not question:
            return jsonify({
                'status': 'error',
                'message': '题目不存在'
            }), 404
        
        # 检查用户权限（通过科目权限过滤）
        from app.core.utils.subject_permissions import can_user_access_subject
        if question.get('subject_id') and not can_user_access_subject(user_id, question['subject_id']):
            return jsonify({
                'status': 'error',
                'message': '无权限访问该题目'
            }), 403
        
        # 获取收藏和错题状态
        conn = get_db()
        fav_row = conn.execute(
            'SELECT id FROM favorites WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        ).fetchone()
        mistake_row = conn.execute(
            'SELECT id FROM mistakes WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        ).fetchone()
        
        q_type_val = question.get('q_type', '')
        options = parse_options(question.get('options'))
        if q_type_val == '判断题' and not options:
            options = [
                {'key': '正确', 'value': '正确'},
                {'key': '错误', 'value': '错误'},
            ]

        answer = question.get('answer', '') or ''
        if shuffle_options and options and q_type_val in ('选择题', '多选题'):
            try:
                import random

                orig_answer_keys = str(answer)
                options_map = {opt.get('key'): opt.get('value') for opt in options}
                correct_texts = []
                for key in orig_answer_keys:
                    if key in options_map:
                        correct_texts.append(options_map[key])

                shuffle_seed = int(user_id) * 1000000 + int(question_id)
                rng = random.Random(shuffle_seed)
                rng.shuffle(options)

                letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                new_answer_keys = []
                for i, option in enumerate(options):
                    if i < len(letters):
                        option['key'] = letters[i]
                        if option.get('value') in correct_texts:
                            new_answer_keys.append(option['key'])

                answer = ''.join(sorted(new_answer_keys))
            except Exception:
                pass
        
        # 格式化题目数据
        formatted_question = {
            'id': question.get('id'),
            'content': question.get('content', ''),
            'q_type': q_type_val,
            'options': options,
            'answer': answer,
            'explanation': question.get('explanation', ''),
            'image_path': question.get('image_path'),
            'subject': question.get('subject', ''),
            'is_fav': 1 if fav_row else 0,
            'is_mistake': 1 if mistake_row else 0
        }
        
        return jsonify({
            'status': 'success',
            'data': formatted_question
        }), 200
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'获取题目详情失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'获取题目详情失败: {str(e)}'
        }), 500


@quiz_api_bp.route('/questions/<int:question_id>', methods=['PUT'])
@auth_required  # 支持 session 和 JWT
@limiter.exempt
def api_update_question(question_id: int):
    """编辑题目（管理员/科目管理员：答题页内弹窗编辑）"""
    uid = current_user_id()
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    data = request.json or {}
    content = data.get('content')
    q_type = data.get('q_type')
    answer = data.get('answer')
    explanation = data.get('explanation')
    options_in = data.get('options', None)

    # 基础校验
    if content is not None and not isinstance(content, str):
        return jsonify({'status': 'error', 'message': 'content 必须为字符串'}), 400
    if q_type is not None and not isinstance(q_type, str):
        return jsonify({'status': 'error', 'message': 'q_type 必须为字符串'}), 400
    if answer is not None and not isinstance(answer, str):
        return jsonify({'status': 'error', 'message': 'answer 必须为字符串'}), 400
    if explanation is not None and not isinstance(explanation, str):
        return jsonify({'status': 'error', 'message': 'explanation 必须为字符串'}), 400

    conn = get_db()

    # 权限：管理员/科目管理员
    try:
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    except Exception:
        user_cols = []
    role_fields = ['is_admin']
    if 'is_subject_admin' in user_cols:
        role_fields.append('is_subject_admin')
    role_row = conn.execute(
        f"SELECT {', '.join(role_fields)} FROM users WHERE id = ?",
        (int(uid),)
    ).fetchone()
    if not role_row:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404
    role_row = dict(role_row)
    can_edit = bool(role_row.get('is_admin')) or bool(role_row.get('is_subject_admin'))
    if not can_edit:
        return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403

    # 读取旧题目（用于默认值/不存在校验）
    old_row = conn.execute(
        'SELECT id, subject_id, q_type, content, options, answer, explanation, image_path FROM questions WHERE id = ?',
        (int(question_id),)
    ).fetchone()
    if not old_row:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404
    old = dict(old_row)

    next_q_type = (q_type if q_type is not None else (old.get('q_type') or '')).strip()
    next_content = (content if content is not None else (old.get('content') or '')).strip()
    next_answer = (answer if answer is not None else (old.get('answer') or '')).strip()
    next_explanation = (explanation if explanation is not None else (old.get('explanation') or '')).strip()

    # options：允许数组/对象（前端结构化）或字符串（JSON/纯文本）
    options_str = None
    options_list = None
    if options_in is None:
        options_str = old.get('options')
        options_list = old.get('options')
    else:
        if isinstance(options_in, str):
            options_str = options_in
            options_list = options_in
        else:
            try:
                import json
                options_str = json.dumps(options_in, ensure_ascii=False)
                options_list = options_in
            except Exception:
                return jsonify({'status': 'error', 'message': 'options 格式错误'}), 400

    # 多选题校验：答案至少两个选项，且必须在选项范围内
    if next_q_type == '多选题':
        if len(next_answer) < 2:
            return jsonify({'status': 'error', 'message': '多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
        try:
            import json
            options_parsed = options_list
            if isinstance(options_parsed, str):
                options_parsed = json.loads(options_parsed) if options_parsed.strip() else []
            parsed_options = parse_options(options_parsed)
            valid_keys = {opt.get('key') for opt in parsed_options if opt.get('key')}
            answer_keys = set(next_answer.upper())
            invalid_keys = answer_keys - valid_keys
            if invalid_keys:
                return jsonify({
                    'status': 'error',
                    'message': f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'
                }), 400
        except Exception:
            # 解析失败时不阻塞（保持兼容旧数据），由题库管理页进一步校验
            pass

    try:
        conn.execute(
            '''
            UPDATE questions SET
                q_type = ?,
                content = ?,
                options = ?,
                answer = ?,
                explanation = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''',
            (next_q_type, next_content, options_str, next_answer, next_explanation, int(question_id))
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'保存失败: {str(e)}'}), 500

    # 返回更新后的题目（沿用小程序详情接口格式）
    try:
        row = conn.execute(
            '''
            SELECT q.*, s.name as subject
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.id = ?
            ''',
            (int(question_id),)
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': '题目不存在'}), 404
        q = dict(row)

        fav_row = conn.execute(
            'SELECT id FROM favorites WHERE user_id = ? AND question_id = ?',
            (int(uid), int(question_id))
        ).fetchone()
        mistake_row = conn.execute(
            'SELECT id FROM mistakes WHERE user_id = ? AND question_id = ?',
            (int(uid), int(question_id))
        ).fetchone()

        q_type_val = q.get('q_type', '')
        options = parse_options(q.get('options'))
        if q_type_val == '判断题' and not options:
            options = [
                {'key': '正确', 'value': '正确'},
                {'key': '错误', 'value': '错误'},
            ]

        formatted_question = {
            'id': q.get('id'),
            'content': q.get('content', ''),
            'q_type': q_type_val,
            'options': options,
            'answer': q.get('answer', '') or '',
            'explanation': q.get('explanation', ''),
            'image_path': q.get('image_path'),
            'subject': q.get('subject', '') or '',
            'is_fav': 1 if fav_row else 0,
            'is_mistake': 1 if mistake_row else 0
        }

        return jsonify({'status': 'success', 'data': formatted_question}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'题目更新成功但返回数据失败: {str(e)}'}), 500
