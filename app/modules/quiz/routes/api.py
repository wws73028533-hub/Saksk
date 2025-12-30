# -*- coding: utf-8 -*-
"""刷题API路由"""
from flask import Blueprint, request, jsonify, session
from app.core.utils.database import get_db
from app.core.extensions import limiter

quiz_api_bp = Blueprint('quiz_api', __name__)


@quiz_api_bp.route('/favorite', methods=['POST'])
@limiter.exempt  # 收藏接口不限流
def toggle_favorite():
    """切换收藏状态"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    data = request.json
    q_id = data.get('question_id')
    uid = session.get('user_id')
    
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
@limiter.exempt  # 答题记录接口不限流
def record_result():
    """记录做题结果（添加刷题限制检查）"""
    from app.core.utils.subject_permissions import (
        check_quiz_limit, 
        increment_user_quiz_count,
        get_user_quiz_count,
        get_quiz_limit_count
    )
    
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    data = request.json
    q_id = data.get('question_id')
    is_correct = data.get('is_correct')
    uid = session.get('user_id')
    
    if not q_id or is_correct is None:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
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
            # 答对了，从错题本中移除
            conn.execute("DELETE FROM mistakes WHERE user_id = ? AND question_id = ?", (uid, q_id))
            action = "removed_mistake"
        
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
    
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', '').lower()
    source = request.args.get('source', '').lower()  # 兼容背题模式下的来源
    uid = session.get('user_id')
    
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
    elif not uid:
        # 未登录用户：返回0
        return jsonify({'status':'success','count': 0})
    
    if subject != 'all':
        base_sql += " AND s.name = ?"
        params.append(subject)
    
    if q_type != 'all':
        base_sql += " AND q.q_type = ?"
        params.append(q_type)
    
    sql = "SELECT COUNT(1) " + base_sql
    cnt = conn.execute(sql, params).fetchone()[0]
    
    return jsonify({'status':'success','count': cnt})


@quiz_api_bp.route('/questions/user_counts')
@limiter.exempt  # 用户计数查询不限流
def api_user_counts():
    """获取用户的收藏和错题数量"""
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    uid = session.get('user_id')
    
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
@limiter.exempt  # 进度同步接口不限流
def progress_api():
    """用户答题进度同步API"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
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
@limiter.exempt
def api_subjects():
    """获取科目列表（添加权限过滤）"""
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    
    try:
        user_id = session.get('user_id')
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


@quiz_api_bp.route('/ai/explain', methods=['POST'])
@limiter.exempt
def api_ai_explain():
    """AI 解析占位接口：返回基于题目信息的模板化解析。

    说明：
    - 本项目默认不集成真实大模型（避免泄露密钥/部署复杂度）。
    - 你可以后续把这里替换为 OpenAI/Claude/自建模型调用。
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录后使用 AI 解析'}), 401

    data = request.json or {}
    question_id = data.get('question_id')
    content = (data.get('content') or '').strip()
    q_type = (data.get('q_type') or '').strip()
    options = data.get('options')  # 可选

    # 简单校验
    if not question_id and not content:
        return jsonify({'status': 'error', 'message': '缺少题目信息'}), 400

    # 返回"模板化解析"（可替换为真实 AI）
    text_lines = []
    text_lines.append('AI 解析（占位）：')
    if q_type:
        text_lines.append(f'- 题型：{q_type}')
    if question_id:
        text_lines.append(f'- 题目ID：{question_id}')
    if content:
        preview = content.replace('\n', ' ').strip()
        if len(preview) > 80:
            preview = preview[:80] + '…'
        text_lines.append(f'- 题干要点：{preview}')

    if isinstance(options, list) and options:
        # options 可能是 [{key,value}]，也可能是字符串
        try:
            opt_preview = []
            for opt in options[:6]:
                if isinstance(opt, dict):
                    opt_preview.append(f"{opt.get('key','')}. {opt.get('value','')}")
                else:
                    opt_preview.append(str(opt))
            text_lines.append('- 选项：' + ' / '.join(opt_preview))
        except Exception:
            pass

    text_lines.append('')
    text_lines.append('建议解题思路：')
    text_lines.append('1) 先圈出关键词与限定条件。')
    text_lines.append('2) 把题干转为可验证的结论/公式/步骤。')
    text_lines.append('3) 对选择题：用排除法 + 代入验证。')
    text_lines.append('4) 对填空/问答题：列步骤，逐步推导，最后回代检查。')

    return jsonify({
        'status': 'success',
        'data': {
            'explain': '\n'.join(text_lines)
        }
    })


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

