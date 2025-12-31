# -*- coding: utf-8 -*-
"""管理后台API路由（向后兼容的旧路径）"""
from flask import Blueprint, request, jsonify
from app.core.utils.database import get_db
import json

# 创建一个额外的蓝图用于向后兼容
admin_api_legacy_bp = Blueprint('admin_api_legacy', __name__)


@admin_api_legacy_bp.route('/types', methods=['GET'])
def get_question_types():
    """获取题型列表（向后兼容路径：/admin/types）"""
    conn = get_db()
    types = [row[0] for row in conn.execute('SELECT DISTINCT q_type FROM questions').fetchall()]
    return jsonify(types)


@admin_api_legacy_bp.route('/questions', methods=['GET'])
def get_filtered_questions():
    """获取筛选后的题目列表（向后兼容路径：/admin/questions）"""
    subject_id = request.args.get('subject_id')
    q_type = request.args.get('type', 'all')
    
    conn = get_db()
    
    sql = '''
        SELECT q.id, q.subject_id, q.q_type, q.content, q.difficulty, q.tags, q.image_path, u.username as created_by, q.updated_at
        FROM questions q
        LEFT JOIN users u ON q.created_by = u.id
        WHERE 1=1
    '''
    params = []
    
    if subject_id:
        sql += ' AND q.subject_id = ?'
        params.append(subject_id)
    
    if q_type != 'all':
        sql += ' AND q.q_type = ?'
        params.append(q_type)
    
    sql += ' ORDER BY q.id DESC'
    
    rows = conn.execute(sql, params).fetchall()
    questions = []
    for row in rows:
        question_dict = dict(row)
        image_path = question_dict.get('image_path')
        # Compatibility: if it's a non-empty string and not a JSON array, wrap it
        if image_path and isinstance(image_path, str) and not image_path.strip().startswith('['):
            question_dict['image_path'] = json.dumps([image_path])
        # If it's an empty string or None, make it an empty JSON array
        elif not image_path:
             question_dict['image_path'] = '[]'
        questions.append(question_dict)
    
    return jsonify(questions)


@admin_api_legacy_bp.route('/questions', methods=['POST'])
def add_question_legacy():
    """添加题目（向后兼容路径：/admin/questions）"""
    from flask import request, session
    from app.core.utils.options_parser import parse_options
    
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400
    
    try:
        q_type = data.get('q_type')
        answer = (data.get('answer') or '').strip()
        options_str = data.get('options', '[]')
        
        # 多选题验证：确保答案至少有两个选项
        if q_type == '多选题':
            if len(answer) < 2:
                return jsonify({'status':'error','message':'多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
            # 验证答案中的所有字母是否在选项范围内
            try:
                options_list = json.loads(options_str) if isinstance(options_str, str) else options_str
                if isinstance(options_list, list) and len(options_list) > 0:
                    parsed_options = parse_options(options_list)
                    valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                    answer_keys = set(answer.upper())
                    invalid_keys = answer_keys - valid_keys
                    if invalid_keys:
                        return jsonify({'status':'error','message':f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'}), 400
            except Exception:
                pass  # 如果解析选项失败，跳过验证
        
        conn = get_db()
        conn.execute('''
            INSERT INTO questions (subject_id, q_type, content, options, answer, explanation, difficulty, tags, image_path, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (
            data.get('subject_id'),
            q_type,
            data.get('content'),
            options_str,
            answer,
            data.get('explanation',''),
            data.get('difficulty', 1),
            data.get('tags'),
            data.get('image_path'),
            session.get('user_id')
        ))
        conn.commit()
        
        return jsonify({'status':'success','message':'题目添加成功'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/questions/<int:question_id>', methods=['GET'])
def get_single_question(question_id):
    """获取单个题目（向后兼容路径：/admin/questions/<id>）"""
    conn = get_db()
    row = conn.execute('SELECT * FROM questions WHERE id=?', (question_id,)).fetchone()
    
    if row:
        question_dict = dict(row)
        image_path = question_dict.get('image_path')
        # Compatibility: if it's a non-empty string and not a JSON array, wrap it
        if image_path and isinstance(image_path, str) and not image_path.strip().startswith('['):
            question_dict['image_path'] = json.dumps([image_path])
        # If it's an empty string or None, make it an empty JSON array
        elif not image_path:
             question_dict['image_path'] = '[]'
        return jsonify(question_dict)
    return jsonify({'error': 'not found'}), 404


@admin_api_legacy_bp.route('/questions/<int:question_id>', methods=['PUT'])
def edit_question_legacy(question_id):
    """编辑题目（向后兼容路径：/admin/questions/<id>）"""
    from flask import request
    from app.core.utils.options_parser import parse_options
    
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': '请求数据不能为空'}), 400
    
    try:
        q_type = data.get('q_type')
        answer = (data.get('answer') or '').strip()
        options_str = data.get('options', '[]')
        
        # 多选题验证：确保答案至少有两个选项
        if q_type == '多选题':
            if len(answer) < 2:
                return jsonify({'status':'error','message':'多选题答案至少需要两个选项，例如：AB 或 ABC'}), 400
            # 验证答案中的所有字母是否在选项范围内
            try:
                options_list = json.loads(options_str) if isinstance(options_str, str) else options_str
                if isinstance(options_list, list) and len(options_list) > 0:
                    parsed_options = parse_options(options_list)
                    valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                    answer_keys = set(answer.upper())
                    invalid_keys = answer_keys - valid_keys
                    if invalid_keys:
                        return jsonify({'status':'error','message':f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'}), 400
            except Exception:
                pass  # 如果解析选项失败，跳过验证
        
        conn = get_db()
        conn.execute('''
            UPDATE questions SET
                subject_id=?, q_type=?, content=?, options=?, answer=?, explanation=?,
                difficulty=?, tags=?, image_path=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (
            data.get('subject_id'),
            q_type,
            data.get('content'),
            options_str,
            answer,
            data.get('explanation',''),
            data.get('difficulty', 1),
            data.get('tags'),
            data.get('image_path'),
            question_id
        ))
        conn.commit()
        
        return jsonify({'status':'success','message':'题目修改成功'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/questions/<int:question_id>', methods=['DELETE'])
def delete_question_legacy(question_id):
    """删除题目（向后兼容路径：/admin/questions/<id>）"""
    conn = get_db()
    try:
        conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        conn.commit()
        return jsonify({'status': 'success', 'message': '题目删除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/questions/import', methods=['POST'])
def import_questions_api():
    """导入题目（向后兼容路径：/admin/questions/import）"""
    from flask import request, session
    from app.core.utils.options_parser import parse_options
    from app.core.utils.fill_blank_parser import parse_fill_blank
    
    data = request.json
    subject_id = data.get('subject_id')
    questions = data.get('questions', [])
    
    if not subject_id or not questions:
        return jsonify({'status': 'error', 'message': '缺少科目或题库数据'}), 400
    
    conn = get_db()
    count = 0
    
    try:
        for item in questions:
            q_type = item.get('题型', '未知')
            content = item.get('题干', '')
            answer = item.get('答案', '')
            explanation = item.get('解析', '')
            opts_json = '[]'
            
            if q_type == '选择题' or q_type == '多选题':
                opts_json = json.dumps(item.get('选项', []), ensure_ascii=False)
                # 多选题验证：确保答案至少有两个选项
                if q_type == '多选题':
                    answer = (answer or '').strip()
                    if len(answer) < 2:
                        # 跳过该题目，继续处理下一题，而不是中断整个导入
                        continue
                    # 验证答案中的所有字母是否在选项范围内
                    try:
                        options_list = item.get('选项', [])
                        if isinstance(options_list, list) and len(options_list) > 0:
                            parsed_options = parse_options(options_list)
                            valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                            answer_keys = set(answer.upper())
                            invalid_keys = answer_keys - valid_keys
                            if invalid_keys:
                                # 跳过该题目，继续处理下一题
                                continue
                    except Exception:
                        pass  # 如果解析选项失败，跳过验证，继续导入
            elif q_type == '填空题':
                # 支持题干中用 {答案} 标记空位，并自动提取答案
                # 例："...{答案1}...{答案2}..." -> content="...__...__...", answer="答案1;;答案2"
                new_content, new_answer, _blank_count = parse_fill_blank(content)
                if new_answer:
                    content = new_content
                    answer = new_answer
            
            conn.execute('''
                INSERT INTO questions (subject_id, q_type, content, options, answer, explanation, created_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                subject_id,
                q_type,
                content,
                opts_json,
                answer,
                explanation,
                session.get('user_id')
            ))
            count += 1
        
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功导入{count}道题'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/questions/batch_delete', methods=['POST'])
def batch_delete_questions():
    """批量删除题目（向后兼容路径：/admin/questions/batch_delete）"""
    data = request.json
    ids = data.get('ids', [])
    
    if not ids:
        return jsonify({'status': 'error', 'message': '未提供要删除的题目 ID'}), 400
    
    conn = get_db()
    try:
        conn.executemany('DELETE FROM questions WHERE id = ?', [(id,) for id in ids])
        conn.commit()
        return jsonify({'status': 'success', 'message': '批量删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'批量删除失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/questions/batch_change_type', methods=['POST'])
def batch_change_type():
    """批量修改题型（向后兼容路径：/admin/questions/batch_change_type）"""
    data = request.json
    ids = data.get('ids', [])
    target_type = data.get('target_type', '')
    
    if not ids or not target_type:
        return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
    
    conn = get_db()
    try:
        conn.executemany('UPDATE questions SET q_type = ? WHERE id = ?', [(target_type, id) for id in ids])
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功修改 {len(ids)} 道题目的题型'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'批量修改失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/questions/batch_move_subject', methods=['POST'])
def batch_move_subject():
    """批量移动科目（向后兼容路径：/admin/questions/batch_move_subject）"""
    data = request.json
    ids = data.get('ids', [])
    target_subject_id = data.get('target_subject_id')
    
    if not ids or not target_subject_id:
        return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
    
    conn = get_db()
    try:
        conn.executemany('UPDATE questions SET subject_id = ? WHERE id = ?', [(target_subject_id, id) for id in ids])
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功移动 {len(ids)} 道题目'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'批量移动失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/questions/batch_set_difficulty', methods=['POST'])
def batch_set_difficulty():
    """批量设置难度（向后兼容路径：/admin/questions/batch_set_difficulty）"""
    data = request.json
    ids = data.get('ids', [])
    difficulty = data.get('difficulty', '')
    
    if not ids or not difficulty:
        return jsonify({'status': 'error', 'message': '缺少必要参数'}), 400
    
    conn = get_db()
    try:
        conn.executemany('UPDATE questions SET difficulty = ? WHERE id = ?', [(difficulty, id) for id in ids])
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功设置 {len(ids)} 道题目的难度'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': f'批量设置失败: {str(e)}'}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
def toggle_admin(user_id):
    """切换管理员权限（向后兼容路径：/admin/users/<id>/toggle_admin）"""
    from flask import session, request, current_app
    
    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '管理员不能对自己进行操作'}), 400
    
    conn = get_db()
    try:
        row = conn.execute('SELECT is_admin, username FROM users WHERE id=?', (user_id,)).fetchone()
        
        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        target_is_admin = bool(row['is_admin'])
        
        if target_is_admin:
            admin_count = conn.execute('SELECT COUNT(1) FROM users WHERE is_admin = 1').fetchone()[0]
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能取消最后一个管理员的权限'}), 400
        
        conn.execute('UPDATE users SET is_admin = NOT is_admin WHERE id = ?', (user_id,))
        conn.execute('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=?', (user_id,))
        conn.commit()
        
        current_app.logger.info(f'管理员权限切换 - 目标用户: {row["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/toggle_subject_admin', methods=['POST'])
def toggle_subject_admin(user_id):
    """切换科目管理员权限（向后兼容路径：/admin/users/<id>/toggle_subject_admin）"""
    from flask import session, request, current_app
    
    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能对自己进行操作'}), 400
    
    conn = get_db()
    try:
        row = conn.execute('SELECT is_subject_admin, username FROM users WHERE id=?', (user_id,)).fetchone()
        
        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        conn.execute('UPDATE users SET is_subject_admin = NOT is_subject_admin WHERE id = ?', (user_id,))
        conn.execute('UPDATE users SET session_version = COALESCE(session_version,0) + 1 WHERE id=?', (user_id,))
        conn.commit()
        
        current_app.logger.info(f'科目管理员权限切换 - 目标用户: {row["username"]}, 操作者: {session.get("username")}, IP: {request.remote_addr}')
        return jsonify({'status': 'success', 'message': '科目管理员权限已切换（已强制刷新目标用户会话）'})
    except Exception as e:
        current_app.logger.error(f'切换科目管理员权限失败 - 用户ID: {user_id}, 错误: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/toggle_lock', methods=['POST'])
def toggle_lock(user_id):
    """切换用户锁定状态（向后兼容路径：/admin/users/<id>/toggle_lock）"""
    from flask import session
    
    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400

    conn = get_db()
    try:
        # 切换锁定状态，增加会话版本，清空 last_active 使其立即显示离线
        conn.execute(
            'UPDATE users SET is_locked = CASE WHEN COALESCE(is_locked,0)=1 THEN 0 ELSE 1 END, session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id=?',
            (user_id,)
        )
        if conn.total_changes == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        conn.commit()

        return jsonify({'status':'success','message':'锁定状态已切换，并已强制下线'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
def reset_password(user_id):
    """重置用户密码（向后兼容路径：/admin/users/<id>/reset_password）"""
    from flask import session, request
    from werkzeug.security import generate_password_hash
    from app.core.utils.validators import validate_password
    
    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400
    
    payload = request.json or {}
    new = payload.get('new_password') or payload.get('password') or ''
    
    valid, msg = validate_password(new)
    if not valid:
        return jsonify({'status':'error','message':msg}), 400
    
    ph = generate_password_hash(new)
    
    conn = get_db()
    try:
        conn.execute(
            'UPDATE users SET password_hash=?, session_version = COALESCE(session_version,0) + 1 WHERE id=?',
            (ph, user_id)
        )
        if conn.total_changes == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        conn.commit()
        
        return jsonify({'status':'success','message':'重置密码成功（已强制下线）'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/users/export')
def export_users():
    """导出用户CSV（向后兼容路径：/admin/users/export）"""
    conn = get_db()
    rows = conn.execute(
        'SELECT id, username, is_admin, is_locked, created_at FROM users ORDER BY id'
    ).fetchall()
    
    def csv_escape(s):
        s = '' if s is None else str(s)
        if any(c in s for c in [',','"','\n','\r']):
            s = '"' + s.replace('"','""') + '"'
        return s
    
    out = '\ufeff' + 'id,username,is_admin,is_locked,created_at\n'
    for r in rows:
        out += ','.join([
            str(r['id']),
            csv_escape(r['username']),
            '1' if r['is_admin'] else '0',
            '1' if (r['is_locked'] or 0) else '0',
            csv_escape(r['created_at'])
        ]) + '\n'
    
    from flask import Response
    return Response(
        out,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=users.csv'}
    )


@admin_api_legacy_bp.route('/users/create', methods=['POST'])
def create_user():
    """创建用户（向后兼容路径：/admin/users/create）"""
    from flask import request
    from werkzeug.security import generate_password_hash
    from app.core.utils.validators import validate_password
    import sqlite3
    
    payload = request.json or {}
    username = (payload.get('username') or '').strip()
    password = payload.get('password') or ''
    is_admin = 1 if payload.get('is_admin') in (1, True, '1', 'true') else 0
    
    if not username or not password:
        return jsonify({'status':'error','message':'用户名和密码不能为空'}), 400
    
    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'status':'error','message':msg}), 400
    
    ph = generate_password_hash(password)
    
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO users (username, password_hash, is_admin, is_locked, session_version) VALUES (?, ?, ?, 0, 0)',
            (username, ph, is_admin)
        )
        conn.commit()
        return jsonify({'status':'success','message':'用户创建成功'})
    except sqlite3.IntegrityError:
        return jsonify({'status':'error','message':'用户名已存在'}), 409
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_legacy_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户（向后兼容路径：/admin/users/<id>）"""
    from flask import session
    import sqlite3
    
    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能删除自己'}), 400

    conn = get_db()
    try:
        u = conn.execute('SELECT id, is_admin, username FROM users WHERE id=?', (user_id,)).fetchone()

        if not u:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        if u['is_admin']:
            admin_count = conn.execute('SELECT COUNT(1) FROM users WHERE is_admin = 1').fetchone()[0]
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能删除最后一个管理员'}), 400

        # 级联清理（仅清理我们明确知道的表；其余若还有外键引用，会被 IntegrityError 拦住）
        conn.execute('DELETE FROM favorites WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM mistakes WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_answers WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_progress WHERE user_id=?', (user_id,))
        conn.execute('UPDATE questions SET created_by=NULL WHERE created_by=?', (user_id,))
        conn.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()

        return jsonify({'status': 'success', 'message': '用户已删除'})

    except sqlite3.IntegrityError as e:
        # 外键约束失败：返回友好的错误信息
        msg = str(e)
        if 'FOREIGN KEY constraint failed' in msg:
            return jsonify({
                'status': 'error',
                'message': '删除失败：该用户仍有关联数据（外键约束），请先删除/转移其相关记录后再删除。'
            }), 400
        return jsonify({'status': 'error', 'message': msg}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_legacy_bp.route('/download_template')
def download_template():
    """下载Excel模板文件（向后兼容路径：/admin/download_template）"""
    from flask import send_from_directory, current_app
    import os
    
    # 模板文件目录：项目根目录的instance文件夹
    # current_app.root_path 是 app/ 目录，需要向上两级到项目根目录
    directory = os.path.join(current_app.root_path, '..', 'instance')
    directory = os.path.abspath(directory)
    
    return send_from_directory(directory, 'question_import_template.xlsx', as_attachment=True)


@admin_api_legacy_bp.route('/questions/export', methods=['GET'])
def export_questions_api():
    """导出题目（向后兼容路径：/admin/questions/export）"""
    subject_id = request.args.get('subject_id')
    
    conn = get_db()
    sql = '''
        SELECT q.id, s.name as subject, q.q_type, q.content, q.options, q.answer, q.explanation
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE 1=1
    '''
    params = []
    
    if subject_id:
        sql += ' AND q.subject_id = ?'
        params.append(subject_id)
    
    sql += ' ORDER BY q.id'
    rows = conn.execute(sql, params).fetchall()
    
    items = []
    for r in rows:
        opts = []
        if r['options']:
            try:
                opts = json.loads(r['options'])
            except:
                opts = []
        
        items.append({
            '科目': r['subject'] or '默认科目',
            '题型': r['q_type'],
            '题干': r['content'],
            '选项': opts,
            '答案': r['answer'],
            '解析': r['explanation'] or ''
        })
    
    return jsonify({'status':'success','count': len(items), 'questions': items})


@admin_api_legacy_bp.route('/questions/export_package', methods=['GET'])
def export_questions_package():
    """导出题目包（向后兼容路径：/admin/questions/export_package）"""
    from flask import request, send_file, current_app
    import zipfile
    import io
    import datetime
    import os
    
    subject_id = request.args.get('subject_id')
    q_type = request.args.get('type')
    
    conn = get_db()
    
    # 1. 获取科目名称
    subject_name = "all_subjects"
    if subject_id:
        subject_row = conn.execute('SELECT name FROM subjects WHERE id = ?', (subject_id,)).fetchone()
        if subject_row:
            subject_name = subject_row['name']

    # 2. 查询题目数据
    sql = '''
        SELECT q.*, s.name as subject_name 
        FROM questions q 
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE 1=1
    '''
    params = []
    if subject_id:
        sql += ' AND subject_id = ?'
        params.append(subject_id)
    if q_type and q_type != 'all':
        sql += ' AND q_type = ?'
        params.append(q_type)
    
    sql += ' ORDER BY id'
    rows = conn.execute(sql, params).fetchall()
    
    questions_data = [dict(row) for row in rows]
    
    # 3. 创建 ZIP 文件
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 3.1 写入 data.json
        # 使用能够处理 datetime 对象的 JSON encoder
        def json_default(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
        zf.writestr('data.json', json.dumps(questions_data, indent=4, ensure_ascii=False, default=json_default))
        
        # 3.2 收集并写入图片
        image_paths = {q['image_path'] for q in questions_data if q.get('image_path')}
        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))
        
        for image_path in image_paths:
            # image_path is like 'question_images/1766...png'
            if not image_path:
                continue
            full_image_path = os.path.join(upload_folder, *image_path.split('/'))
            if os.path.exists(full_image_path):
                # 写入 zip 时保持目录结构, e.g., images/question_images/....png
                arcname = 'images/' + image_path.replace('\\', '/')
                zf.write(full_image_path, arcname)

    memory_file.seek(0)
    
    # 4. 生成文件名并发送文件
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"questions_export_{subject_name}_{timestamp}.zip"
    
    return send_file(
        memory_file,
        as_attachment=True,
        download_name=filename,
        mimetype='application/zip'
    )


@admin_api_legacy_bp.route('/questions/import_package', methods=['POST'])
def import_questions_package():
    """导入题目包（向后兼容路径：/admin/questions/import_package）"""
    # 直接使用api.py中的实现，但需要导入必要的模块
    from flask import current_app
    import zipfile
    import datetime
    import os
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有文件部分'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({'status': 'error', 'message': '请上传有效的 .zip 文件'}), 400

    conn = get_db()
    
    # 获取现有的科目 name -> id 映射
    subjects = conn.execute('SELECT id, name FROM subjects').fetchall()
    subject_map = {s['name']: s['id'] for s in subjects}

    imported_count = 0
    errors = []
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))

    try:
        with zipfile.ZipFile(file, 'r') as zf:
            if 'data.json' not in zf.namelist():
                return jsonify({'status': 'error', 'message': '压缩包中缺少 data.json 文件'}), 400
            
            with zf.open('data.json') as f:
                questions_data = json.load(f)
            
            for q in questions_data:
                try:
                    # 1. 处理科目
                    subject_name = q.get('subject_name')
                    if not subject_name:
                        errors.append(f"题目ID {q.get('id')} 缺少科目名称，已跳过。")
                        continue

                    if subject_name not in subject_map:
                        cursor = conn.execute('INSERT INTO subjects (name) VALUES (?)', (subject_name,))
                        subject_id = cursor.lastrowid
                        subject_map[subject_name] = subject_id
                    else:
                        subject_id = subject_map[subject_name]

                    # 2. 处理图片
                    new_image_path = q.get('image_path')
                    if new_image_path:
                        arcname = 'images/' + new_image_path.replace('\\', '/')
                        if arcname in zf.namelist():
                            # 生成新的唯一文件名以避免冲突
                            ext = os.path.splitext(new_image_path)[1]
                            unique_filename = f"{int(datetime.datetime.now().timestamp())}_{imported_count}{ext}"
                            image_save_dir = os.path.join(upload_folder, 'question_images')
                            os.makedirs(image_save_dir, exist_ok=True)
                            image_save_path = os.path.join(image_save_dir, unique_filename)
                            
                            with zf.open(arcname) as source, open(image_save_path, 'wb') as target:
                                target.write(source.read())
                            
                            new_image_path = f'question_images/{unique_filename}'
                        else:
                            new_image_path = None # 图片在zip中不存在

                    # 3. 插入题目数据 (忽略原始ID)
                    from flask import session
                    conn.execute('''
                        INSERT INTO questions (subject_id, q_type, content, options, answer, explanation, difficulty, tags, image_path, created_by, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        subject_id,
                        q.get('q_type'),
                        q.get('content'),
                        q.get('options'),
                        q.get('answer'),
                        q.get('explanation'),
                        q.get('difficulty'),
                        q.get('tags'),
                        new_image_path,
                        session.get('user_id') or q.get('created_by'),
                        q.get('created_at'),
                        q.get('updated_at')
                    ))
                    imported_count += 1
                except Exception as e:
                    errors.append(f"导入题目ID {q.get('id', 'N/A')} 时出错: {str(e)}")

        conn.commit()

        message = f'成功导入 {imported_count} 道题。'
        if errors:
            message += f' 遇到 {len(errors)} 个问题。'
        
        return jsonify({
            'status': 'success' if not errors else 'warning',
            'message': message,
            'imported_count': imported_count,
            'errors': errors
        })

    except zipfile.BadZipFile:
        return jsonify({'status': 'error', 'message': '文件不是一个有效的ZIP压缩包'}), 400
    except Exception as e:
        conn.rollback() # 如果发生意外错误，回滚事务
        return jsonify({'status': 'error', 'message': f'处理文件时发生未知错误: {str(e)}'}), 500

