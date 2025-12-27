# -*- coding: utf-8 -*-
"""
API路由蓝图
"""
from flask import Blueprint, request, jsonify, session
from ..utils.database import get_db
from ..extensions import limiter

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/favorite', methods=['POST'])
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


@api_bp.route('/record_result', methods=['POST'])
@limiter.exempt  # 答题记录接口不限流
def record_result():
    """记录做题结果"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    data = request.json
    q_id = data.get('question_id')
    is_correct = data.get('is_correct')
    uid = session.get('user_id')
    
    if not q_id or is_correct is None:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
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
        
        conn.commit()
        return jsonify({"status": "success", "action": action})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "msg": str(e)}), 500


@api_bp.route('/questions/count')
@limiter.exempt  # 题目数量查询不限流
def api_questions_count():
    """获取题目数量"""
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', '').lower()
    source = request.args.get('source', '').lower()  # 兼容背题模式下的来源
    uid = session.get('user_id')
    
    conn = get_db()

    # 兼容新的 source 参数，优先使用 source，其次 mode
    target = source if source in ('favorites', 'mistakes') else mode
    
    if target == 'favorites':
        if not uid:
            return jsonify({'status':'success','count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN favorites f ON f.question_id = q.id AND f.user_id = ? WHERE 1=1"
        params = [uid]
    elif target == 'mistakes':
        if not uid:
            return jsonify({'status':'success','count': 0})
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id JOIN mistakes m ON m.question_id = q.id AND m.user_id = ? WHERE 1=1"
        params = [uid]
    else:
        base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE 1=1"
        params = []
    
    if subject != 'all':
        base_sql += " AND s.name = ?"
        params.append(subject)
    
    if q_type != 'all':
        base_sql += " AND q.q_type = ?"
        params.append(q_type)
    
    sql = "SELECT COUNT(1) " + base_sql
    cnt = conn.execute(sql, params).fetchone()[0]
    
    return jsonify({'status':'success','count': cnt})


@api_bp.route('/questions/user_counts')
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


@api_bp.route('/progress', methods=['GET', 'POST', 'DELETE'])
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


# 注意：用户侧“历史通知”功能使用 app/routes/notifications.py 中的接口：
#   GET  /api/notifications
#   GET  /api/notifications/<id>
#   POST /api/notifications/<id>/read
#   GET  /api/notifications/unread_count
# 这里原本也实现了 /api/notifications（返回 notifications 字段），
# 会与新接口产生冲突并导致前端拿到空列表。
# 为避免破坏首页等可能旧逻辑，改为旧接口走 /api/notifications_legacy。

@api_bp.route('/notifications_legacy', methods=['GET'])
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


@api_bp.route('/notifications_legacy/<int:nid>/dismiss', methods=['POST'])
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


@api_bp.route('/subjects', methods=['GET'])
@limiter.exempt

def api_subjects():
    """获取科目列表（给前端设置页使用）"""
    conn = get_db()
    try:
        rows = conn.execute('SELECT name FROM subjects ORDER BY id').fetchall()
        subjects = [r[0] for r in rows if r and r[0]]
        return jsonify({'status': 'success', 'subjects': subjects})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'subjects': []}), 500


@api_bp.route('/ai/explain', methods=['POST'])
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

    # 返回“模板化解析”（可替换为真实 AI）
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

