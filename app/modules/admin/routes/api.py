# -*- coding: utf-8 -*-
"""
管理后台路由蓝图
"""
import json
import sqlite3
import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app, send_from_directory, send_file
from werkzeug.utils import secure_filename
import zipfile
import io
import datetime
from werkzeug.security import generate_password_hash
from app.core.utils.database import get_db
from app.core.utils.validators import parse_int, validate_password
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.extensions import limiter
import pandas as pd

admin_api_bp = Blueprint('admin_api', __name__)

ALLOWED_EXTENSIONS = {'json'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 页面路由已迁移到pages.py


@admin_api_bp.route('/subjects', methods=['GET'])
def api_get_subjects():
    """获取科目列表（管理后台，包含锁定状态）"""
    conn = get_db()
    rows = conn.execute('''
        SELECT s.id, s.name, s.is_locked, COUNT(q.id) as question_count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id, s.name, s.is_locked
        ORDER BY s.id
    ''').fetchall()
    
    subjects = [dict(row) for row in rows]
    return jsonify(subjects)


@admin_api_bp.route('/types', methods=['GET'])
def get_question_types():
    """获取题型列表"""
    conn = get_db()
    types = [row[0] for row in conn.execute('SELECT DISTINCT q_type FROM questions').fetchall()]
    return jsonify(types)


@admin_api_bp.route('/questions', methods=['GET'])
def get_filtered_questions():
    """获取筛选后的题目列表"""
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


@admin_api_bp.route('/questions/<int:question_id>', methods=['GET'])
def get_single_question(question_id):
    """获取单个题目"""
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


@admin_api_bp.route('/questions', methods=['POST'])
def add_question():
    """添加题目"""
    data = request.json
    uid = session.get('user_id')
    
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
                    from app.core.utils.options_parser import parse_options
                    parsed_options = parse_options(options_list)
                    valid_keys = {opt['key'] for opt in parsed_options if opt.get('key')}
                    answer_keys = set(answer.upper())
                    invalid_keys = answer_keys - valid_keys
                    if invalid_keys:
                        return jsonify({'status':'error','message':f'多选题答案中包含无效选项：{", ".join(sorted(invalid_keys))}。有效选项为：{", ".join(sorted(valid_keys))}'}), 400
            except Exception:
                pass  # 如果解析选项失败，跳过验证
        
        conn = get_db()
        cursor = conn.execute('''
            INSERT INTO questions (subject_id, q_type, content, options, answer, explanation, difficulty, tags, image_path, created_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
            uid
        ))
        new_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({'status':'success','message':'题目新增成功', 'id': new_id})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_api_bp.route('/questions/<int:question_id>', methods=['PUT'])
def edit_question(question_id):
    """编辑题目"""
    data = request.json
    
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
                    from app.core.utils.options_parser import parse_options
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


@admin_api_bp.route('/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """删除题目"""
    conn = get_db()
    conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    conn.commit()
    
    return jsonify({'status': 'success', 'message': '题目删除成功'})


@admin_api_bp.route('/questions/batch_delete', methods=['POST'])
def batch_delete_questions():
    """批量删除题目"""
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
        return jsonify({'status': 'error', 'message': f'批量删除失败: {str(e)}'}), 500


@admin_api_bp.route('/questions/batch_change_type', methods=['POST'])
def batch_change_type():
    """批量修改题型"""
    data = request.json
    ids = data.get('ids', [])
    target_type = data.get('target_type')

    if not ids or not target_type:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400

    conn = get_db()
    try:
        # 验证题型是否有效 (可选，但推荐)
        valid_types = [row[0] for row in conn.execute('SELECT DISTINCT q_type FROM questions').fetchall()]
        if target_type not in valid_types:
            return jsonify({'status': 'error', 'message': '无效的目标题型'}), 400

        conn.executemany('UPDATE questions SET q_type = ? WHERE id = ?', 
                        [(target_type, id) for id in ids])
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功将 {len(ids)} 道题目修改为 "{target_type}"'}) 
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量修改题型失败: {str(e)}'}), 500


@admin_api_bp.route('/questions/batch_move_subject', methods=['POST'])
def batch_move_subject():
    """批量移动题目到其他科目"""
    data = request.json
    ids = data.get('ids', [])
    target_subject_id = data.get('target_subject_id')
    
    if not ids or not target_subject_id:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
    conn = get_db()
    try:
        conn.executemany('UPDATE questions SET subject_id = ? WHERE id = ?', 
                        [(target_subject_id, id) for id in ids])
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功移动 {len(ids)} 道题目'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量移动失败: {str(e)}'}), 500


@admin_api_bp.route('/questions/batch_set_difficulty', methods=['POST'])
def batch_set_difficulty():
    """批量设置题目难度"""
    data = request.json
    ids = data.get('ids', [])
    difficulty = data.get('difficulty')
    
    if not ids or difficulty is None:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
    conn = get_db()
    try:
        conn.executemany('UPDATE questions SET difficulty = ? WHERE id = ?', 
                        [(difficulty, id) for id in ids])
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功设置 {len(ids)} 道题目的难度'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量设置难度失败: {str(e)}'}), 500


@admin_api_bp.route('/questions/batch_tags', methods=['POST'])
def batch_tags():
    """批量操作标签"""
    data = request.json
    ids = data.get('ids', [])
    action = data.get('action')  # 'add', 'remove', 'set'
    tags = data.get('tags', '')
    
    if not ids or not action:
        return jsonify({'status': 'error', 'message': '参数不完整'}), 400
    
    conn = get_db()
    try:
        for qid in ids:
            row = conn.execute('SELECT tags FROM questions WHERE id = ?', (qid,)).fetchone()
            if not row:
                continue
            
            current_tags = row['tags'] or ''
            current_set = set(t.strip() for t in current_tags.split(',') if t.strip())
            new_tags_set = set(t.strip() for t in tags.split(',') if t.strip())
            
            if action == 'add':
                current_set.update(new_tags_set)
            elif action == 'remove':
                current_set -= new_tags_set
            elif action == 'set':
                current_set = new_tags_set
            
            new_tags_str = ','.join(sorted(current_set))
            conn.execute('UPDATE questions SET tags = ? WHERE id = ?', (new_tags_str, qid))
        
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功处理 {len(ids)} 道题目的标签'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'批量操作标签失败: {str(e)}'}), 500


@admin_api_bp.route('/subjects', methods=['POST'])
def api_add_subject():
    """添加科目"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'status': 'error', 'message': '科目名不能为空'}), 400
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO subjects (name) VALUES (?)', (name,))
        conn.commit()
        return jsonify({'status': 'success', 'message': '科目添加成功'})
    except sqlite3.IntegrityError as e:
        # 常见原因：该用户仍被其它表外键引用（例如聊天消息、通知、考试记录等）
        msg = str(e)
        if 'FOREIGN KEY constraint failed' in msg:
            return jsonify({'status': 'error', 'message': '删除失败：该用户仍有关联数据（外键约束），请先删除/转移其相关记录后再删除。'}), 400
        return jsonify({'status': 'error', 'message': msg}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/subjects/<int:subject_id>', methods=['PUT'])
def api_edit_subject(subject_id):
    """编辑科目"""
    data = request.json
    name = data.get('name')
    
    if not name:
        return jsonify({'status': 'error', 'message': '科目名不能为空'}), 400
    
    conn = get_db()
    try:
        conn.execute('UPDATE subjects SET name=? WHERE id=?', (name, subject_id))
        conn.commit()
        return jsonify({'status': 'success', 'message': '科目修改成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/subjects/<int:subject_id>', methods=['DELETE'])
def api_delete_subject(subject_id):
    """删除科目"""
    force = request.args.get('force') in ('1','true','yes')
    
    conn = get_db()
    try:
        qcount = conn.execute('SELECT COUNT(1) FROM questions WHERE subject_id=?', (subject_id,)).fetchone()[0]
        
        if qcount > 0 and not force:
            return jsonify({'status': 'error', 'message': f'该科目下仍有 {qcount} 道题，无法直接删除'}), 400
        
        if qcount > 0 and force:
            conn.execute('DELETE FROM favorites WHERE question_id IN (SELECT id FROM questions WHERE subject_id=?)', (subject_id,))
            conn.execute('DELETE FROM mistakes WHERE question_id IN (SELECT id FROM questions WHERE subject_id=?)', (subject_id,))
            conn.execute('DELETE FROM questions WHERE subject_id=?', (subject_id,))
        
        conn.execute('DELETE FROM subjects WHERE id=?', (subject_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': '科目删除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/subjects/<int:subject_id>/lock', methods=['POST'])
def api_lock_subject(subject_id):
    """锁定科目"""
    conn = get_db()
    try:
        # 检查科目是否存在
        subject = conn.execute('SELECT id, name FROM subjects WHERE id=?', (subject_id,)).fetchone()
        if not subject:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404
        
        conn.execute('UPDATE subjects SET is_locked=1 WHERE id=?', (subject_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': f'科目"{dict(subject)["name"]}"已锁定'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/subjects/<int:subject_id>/unlock', methods=['POST'])
def api_unlock_subject(subject_id):
    """解锁科目"""
    conn = get_db()
    try:
        # 检查科目是否存在
        subject = conn.execute('SELECT id, name FROM subjects WHERE id=?', (subject_id,)).fetchone()
        if not subject:
            return jsonify({'status': 'error', 'message': '科目不存在'}), 404
        
        conn.execute('UPDATE subjects SET is_locked=0 WHERE id=?', (subject_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': f'科目"{dict(subject)["name"]}"已解锁'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/users')
@limiter.exempt
def admin_api_users():
    """用户列表API"""
    try:
        search = (request.args.get('search') or '').strip()
        page = parse_int(request.args.get('page'), 1, 1)
        size = parse_int(request.args.get('size'), 10, 5, 100)
        sort = (request.args.get('sort') or 'created_at').lower()
        order = (request.args.get('order') or 'desc').lower()
        
        sort_map = {'created_at':'created_at', 'username':'username', 'id':'id'}
        if sort not in sort_map:
            sort = 'created_at'
        if order not in ('asc','desc'):
            order = 'desc'
        
        offset = (page-1)*size
        
        conn = get_db()
        where = 'WHERE 1=1'
        params = []
        
        if search:
            where += ' AND username LIKE ?'
            params.append(f'%{search}%')
        
        total = conn.execute(f'SELECT COUNT(1) FROM users {where}', params).fetchone()[0]
        
        # 检查 is_subject_admin 字段是否存在，如果不存在则自动添加
        has_subject_admin_field = False
        try:
            user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            has_subject_admin_field = 'is_subject_admin' in user_cols
            
            # 如果字段不存在，尝试添加
            if not has_subject_admin_field:
                try:
                    conn.execute('ALTER TABLE users ADD COLUMN is_subject_admin INTEGER DEFAULT 0')
                    conn.commit()
                    has_subject_admin_field = True
                    current_app.logger.info('已自动添加 is_subject_admin 字段')
                except Exception as e:
                    current_app.logger.warning(f'添加 is_subject_admin 字段失败（可能已存在）: {e}')
                    # 即使添加失败，也尝试查询，可能字段已经存在
                    try:
                        test_row = conn.execute('SELECT is_subject_admin FROM users LIMIT 1').fetchone()
                        has_subject_admin_field = True
                    except Exception:
                        has_subject_admin_field = False
        except Exception as e:
            current_app.logger.warning(f'检查 is_subject_admin 字段失败: {e}')
            # 如果检查失败，尝试直接查询，如果失败则使用不包含该字段的查询
            try:
                test_row = conn.execute('SELECT is_subject_admin FROM users LIMIT 1').fetchone()
                has_subject_admin_field = True
            except Exception:
                has_subject_admin_field = False
        
        # 根据字段是否存在构建查询
        if has_subject_admin_field:
            select_fields = 'id, username, is_admin, is_subject_admin, is_locked, created_at, last_active'
        else:
            select_fields = 'id, username, is_admin, is_locked, created_at, last_active'
        
        rows = conn.execute(
            f'SELECT {select_fields} FROM users {where} ORDER BY {sort_map[sort]} {order} LIMIT ? OFFSET ?',
            params + [size, offset]
        ).fetchall()
        
        from datetime import datetime, timedelta
        
        data = []
        for r in rows:
            # 判断在线状态：5分钟内有活动视为在线
            is_online = False
            last_active_val = r['last_active'] if 'last_active' in r.keys() else None
            if last_active_val:
                try:
                    # SQLite 的 CURRENT_TIMESTAMP 格式: "YYYY-MM-DD HH:MM:SS" (UTC时间)
                    last_active_str = last_active_val.replace('T', ' ').split('.')[0]
                    last_active = datetime.strptime(last_active_str, '%Y-%m-%d %H:%M:%S')
                    # SQLite CURRENT_TIMESTAMP 是 UTC，需要转换为本地时间
                    # 或者使用 datetime.utcnow() 进行比较
                    is_online = (datetime.utcnow() - last_active) < timedelta(minutes=5)
                except Exception as e:
                    current_app.logger.warning(f'解析 last_active 失败: {last_active_val}, 错误: {e}')
            
            # sqlite3.Row 对象使用字典式访问，但不是真正的字典，需要用 in 检查或直接访问
            data.append({
                'id': r['id'],
                'username': r['username'],
                'is_admin': bool(r['is_admin']) if 'is_admin' in r.keys() else False,
                'is_subject_admin': bool(r['is_subject_admin']) if has_subject_admin_field and 'is_subject_admin' in r.keys() else False,
                'is_locked': bool(r['is_locked']) if 'is_locked' in r.keys() else False,
                'created_at': r['created_at'] if 'created_at' in r.keys() else '',
                'is_online': is_online,
                'last_active': last_active_val
            })
        
        return jsonify({'status':'success','data': data, 'total': total})
    except Exception as e:
        current_app.logger.error(f'用户列表API错误: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': f'加载用户列表失败: {str(e)}'}), 500


@admin_api_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
def toggle_admin_status(user_id):
    """切换管理员权限"""
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


@admin_api_bp.route('/users/<int:user_id>/toggle_subject_admin', methods=['POST'])
def toggle_subject_admin_status(user_id):
    """切换科目管理员权限"""
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


@admin_api_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户"""

    def _ref_counts(uid: int):
        """统计哪些表还在引用该用户，用于给管理员友好提示"""
        # 说明：这里列出的是数据库里对 users.id 有外键/逻辑关联的主要表
        checks = [
            ('favorites', 'SELECT COUNT(1) FROM favorites WHERE user_id=?'),
            ('mistakes', 'SELECT COUNT(1) FROM mistakes WHERE user_id=?'),
            ('user_answers', 'SELECT COUNT(1) FROM user_answers WHERE user_id=?'),
            ('user_progress', 'SELECT COUNT(1) FROM user_progress WHERE user_id=?'),
            ('exams', 'SELECT COUNT(1) FROM exams WHERE user_id=?'),
            ('chat_messages(发送者)', 'SELECT COUNT(1) FROM chat_messages WHERE sender_id=?'),
            ('chat_members(会话成员)', 'SELECT COUNT(1) FROM chat_members WHERE user_id=?'),
            ('user_remarks(备注-owner)', 'SELECT COUNT(1) FROM user_remarks WHERE owner_user_id=?'),
            ('user_remarks(备注-target)', 'SELECT COUNT(1) FROM user_remarks WHERE target_user_id=?'),
            ('notification_dismissals', 'SELECT COUNT(1) FROM notification_dismissals WHERE user_id=?'),
            ('notifications(创建者)', 'SELECT COUNT(1) FROM notifications WHERE created_by=?'),
            ('questions(出题人)', 'SELECT COUNT(1) FROM questions WHERE created_by=?'),
        ]
        details = []
        for name, sql in checks:
            try:
                c = conn.execute(sql, (uid,)).fetchone()[0]
                if c and int(c) > 0:
                    details.append({'table': name, 'count': int(c)})
            except Exception:
                # 兼容：有些表可能在老库不存在/字段不同，忽略即可
                pass
        return details

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
        # 外键约束失败：返回“哪些表还在引用”
        msg = str(e)
        if 'FOREIGN KEY constraint failed' in msg:
            details = _ref_counts(user_id)
            if details:
                # 生成更易读的提示
                detail_str = '、'.join([f"{x['table']}({x['count']})" for x in details])
                return jsonify({
                    'status': 'error',
                    'message': f"删除失败：该用户仍有关联数据，请先处理后再删除。关联项：{detail_str}",
                    'details': details
                }), 400
            return jsonify({
                'status': 'error',
                'message': '删除失败：该用户仍有关联数据（外键约束），请先删除/转移其相关记录后再删除。',
                'details': []
            }), 400
        return jsonify({'status': 'error', 'message': msg}), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/users/create', methods=['POST'])
def admin_create_user():
    """创建用户"""
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


@admin_api_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
def admin_reset_password(user_id):
    """重置用户密码"""
    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400
    
    payload = request.json or {}
    new = payload.get('new_password') or ''
    
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


@admin_api_bp.route('/users/<int:user_id>/toggle_lock', methods=['POST'])
def admin_toggle_lock(user_id):
    """切换锁定状态"""
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


@admin_api_bp.route('/users/<int:user_id>/force_logout', methods=['POST'])
def admin_force_logout(user_id):
    """强制用户下线"""
    if user_id == session.get('user_id'):
        return jsonify({'status':'error','message':'管理员不能对自己进行操作'}), 400

    conn = get_db()
    try:
        # 增加会话版本，清空 last_active 使其立即显示离线
        conn.execute('UPDATE users SET session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id=?', (user_id,))
        if conn.total_changes == 0:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        conn.commit()

        return jsonify({'status':'success','message':'已强制下线该用户'})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


# 页面路由
# 页面路由已迁移到pages.py


@admin_api_bp.route('/users/export')
def admin_export_users():
    """导出用户CSV"""
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
    
    return out, 200, {
        'Content-Type':'text/csv; charset=utf-8',
        'Content-Disposition':'attachment; filename=users.csv'
    }


@admin_api_bp.route('/questions/import', methods=['POST'])
def import_questions_api():
    """导入题目"""
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
                            from app.core.utils.options_parser import parse_options
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
                INSERT INTO questions (subject_id, q_type, content, options, answer, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (subject_id, q_type, content, opts_json, answer, explanation))
            count += 1
        
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功导入{count}道题'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@admin_api_bp.route('/questions/export', methods=['GET'])
def export_questions_api():
    """导出题目"""
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


# ============== 通知管理 ==============

@admin_api_bp.route('/notifications', methods=['GET'])
def admin_api_notifications_list():
    """获取所有通知列表"""
    conn = get_db()
    rows = conn.execute('''
        SELECT n.id, n.title, n.content, n.n_type, n.priority, n.is_active,
               n.start_at, n.end_at, n.created_at, n.updated_at,
               u.username as created_by_name
        FROM notifications n
        LEFT JOIN users u ON n.created_by = u.id
        ORDER BY n.priority DESC, n.created_at DESC
    ''').fetchall()

    return jsonify({
        'status': 'success',
        'notifications': [dict(row) for row in rows]
    })


@admin_api_bp.route('/notifications', methods=['POST'])
def admin_api_notifications_create():
    """创建通知"""
    data = request.json or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    n_type = data.get('n_type', 'info')
    priority = data.get('priority', 0)
    is_active = 1 if data.get('is_active', True) else 0
    start_at = data.get('start_at') or None
    end_at = data.get('end_at') or None
    uid = session.get('user_id')

    if not title or not content:
        return jsonify({'status': 'error', 'message': '标题和内容不能为空'}), 400

    if n_type not in ('info', 'announcement', 'reminder', 'warning'):
        n_type = 'info'

    conn = get_db()
    try:
        cursor = conn.execute('''
            INSERT INTO notifications (title, content, n_type, priority, is_active, start_at, end_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, n_type, priority, is_active, start_at, end_at, uid))
        new_id = cursor.lastrowid
        conn.commit()

        return jsonify({'status': 'success', 'message': '通知创建成功', 'id': new_id})
    except Exception as e:
        import traceback
        current_app.logger.error(f'创建通知失败: {str(e)}\n{traceback.format_exc()}')
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/notifications/<int:nid>', methods=['GET'])
def admin_api_notifications_get(nid):
    """获取单个通知"""
    conn = get_db()
    row = conn.execute('SELECT * FROM notifications WHERE id = ?', (nid,)).fetchone()

    if not row:
        return jsonify({'status': 'error', 'message': '通知不存在'}), 404

    return jsonify({'status': 'success', 'notification': dict(row)})


@admin_api_bp.route('/notifications/<int:nid>', methods=['PUT'])
def admin_api_notifications_update(nid):
    """更新通知"""
    data = request.json or {}
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    n_type = data.get('n_type', 'info')
    priority = data.get('priority', 0)
    is_active = 1 if data.get('is_active', True) else 0
    start_at = data.get('start_at') or None
    end_at = data.get('end_at') or None

    if not title or not content:
        return jsonify({'status': 'error', 'message': '标题和内容不能为空'}), 400

    if n_type not in ('info', 'announcement', 'reminder', 'warning'):
        n_type = 'info'

    conn = get_db()
    try:
        conn.execute('''
            UPDATE notifications SET
                title = ?, content = ?, n_type = ?, priority = ?,
                is_active = ?, start_at = ?, end_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, content, n_type, priority, is_active, start_at, end_at, nid))

        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        conn.commit()
        return jsonify({'status': 'success', 'message': '通知更新成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/notifications/<int:nid>', methods=['DELETE'])
def admin_api_notifications_delete(nid):
    """删除通知"""
    conn = get_db()
    try:
        # 先删除关联的关闭记录
        conn.execute('DELETE FROM notification_dismissals WHERE notification_id = ?', (nid,))
        conn.execute('DELETE FROM notifications WHERE id = ?', (nid,))

        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        conn.commit()
        return jsonify({'status': 'success', 'message': '通知删除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/notifications/<int:nid>/toggle', methods=['POST'])
def admin_api_notifications_toggle(nid):
    """切换通知启用状态"""
    conn = get_db()
    try:
        conn.execute('''
            UPDATE notifications SET
                is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (nid,))

        if conn.total_changes == 0:
            return jsonify({'status': 'error', 'message': '通知不存在'}), 404

        conn.commit()

        row = conn.execute('SELECT is_active FROM notifications WHERE id = ?', (nid,)).fetchone()
        new_status = '启用' if row['is_active'] else '禁用'

        return jsonify({'status': 'success', 'message': f'通知已{new_status}', 'is_active': bool(row['is_active'])})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_api_bp.route('/questions/import/excel', methods=['POST'])
def import_questions_from_excel():
    """从Excel文件导入题库 (V2 - 分列格式)"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有文件部分'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'}), 400

    if not file or not file.filename.endswith('.xlsx'):
        return jsonify({'status': 'error', 'message': '只允许上传 .xlsx 文件'}), 400

    conn = get_db()
    
    try:
        df = pd.read_excel(file, sheet_name='题目示例').fillna('')
        
        required_columns = ['subject', 'q_type', 'content']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'status': 'error', 'message': f'Excel文件中缺少必需的列: {", ".join(missing_columns)}'}), 400

        subjects = conn.execute('SELECT id, name FROM subjects').fetchall()
        subject_map = {s['name']: s['id'] for s in subjects}

        imported_count = 0
        errors = []

        option_cols = sorted([col for col in df.columns if col.startswith('option_')])
        blank_cols = sorted([col for col in df.columns if col.startswith('blank_')])

        for index, row in df.iterrows():
            try:
                subject_name = str(row.get('subject', '')).strip()
                q_type = str(row.get('q_type', '')).strip()
                content = str(row.get('content', '')).strip()
                answer = str(row.get('answer', '')).strip()
                explanation = str(row.get('explanation', '')).strip()

                if not all([subject_name, q_type, content]):
                    errors.append(f'第 {index + 2} 行: 必填字段（subject, q_type, content）不能为空。')
                    continue

                if subject_name not in subject_map:
                    cursor = conn.execute('INSERT INTO subjects (name) VALUES (?)', (subject_name,))
                    subject_id = cursor.lastrowid
                    subject_map[subject_name] = subject_id
                    conn.commit()
                else:
                    subject_id = subject_map[subject_name]

                valid_q_types = ['选择题', '多选题', '判断题', '填空题', '问答题']
                if q_type not in valid_q_types:
                    errors.append(f'第 {index + 2} 行: 无效的题型 "{q_type}"。')
                    continue
                
                options_json = '[]'
                final_answer = answer

                if q_type in ['选择题', '多选题']:
                    options_list = []
                    for i, col_name in enumerate(option_cols):
                        option_text = str(row.get(col_name, '')).strip()
                        if option_text:
                            prefix = chr(ord('A') + i)
                            options_list.append(f"{prefix}. {option_text}")
                    if not options_list:
                        errors.append(f'第 {index + 2} 行: 选择题或多选题至少需要一个选项。')
                        continue
                    options_json = json.dumps(options_list, ensure_ascii=False)
                    if not final_answer:
                        errors.append(f'第 {index + 2} 行: 选择题或多选题的 `answer` 列不能为空。')
                        continue

                elif q_type == '填空题':
                    blank_answers = []
                    for col_name in blank_cols:
                        blank_text = str(row.get(col_name, '')).strip()
                        if blank_text:
                            blank_answers.append(blank_text)
                    if not blank_answers:
                        errors.append(f'第 {index + 2} 行: 填空题至少需要一个 `blank_` 答案。')
                        continue
                    final_answer = ';;'.join(blank_answers)
                
                elif not final_answer:
                     errors.append(f'第 {index + 2} 行: `answer` 列不能为空。')
                     continue

                conn.execute('''
                    INSERT INTO questions (subject_id, q_type, content, options, answer, explanation, created_by, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (subject_id, q_type, content, options_json, final_answer, explanation, session.get('user_id')))
                
                imported_count += 1

            except Exception as e:
                errors.append(f'第 {index + 2} 行: 导入失败 - {str(e)}')

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

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'处理文件失败: {str(e)}'}), 500


@admin_api_bp.route('/download_template')
def download_template():
    """提供题库导入模板文件的下载"""
    directory = os.path.join(current_app.root_path, '..', 'instance')
    return send_from_directory(directory, 'question_import_template.xlsx', as_attachment=True)


@admin_api_bp.route('/questions/upload_image', methods=['POST'])
def upload_question_image():
    """上传题目图片"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': '没有文件部分'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'}), 400

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return jsonify({'status': 'error', 'message': '无效的文件类型'}), 400

    try:
        filename = secure_filename(file.filename)
        # 为了避免重名，可以加上时间戳和随机数
        import time, random
        unique_filename = f"{int(time.time())}_{random.randint(1000, 9999)}_{filename}"
        
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'question_images')
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        
        # 返回可访问的URL
        file_url = url_for('main.main_pages.serve_upload', filename=f'question_images/{unique_filename}')
        
        return jsonify({'status': 'success', 'url': file_url, 'path': f'question_images/{unique_filename}'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'上传失败: {str(e)}'}), 500


@admin_api_bp.route('/questions/export_package', methods=['GET'])
def export_questions_package():
    """导出包含完整数据和图片的题目包"""
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


@admin_api_bp.route('/questions/import_package', methods=['POST'])
def import_questions_package():
    """导入题目包 (.zip)"""
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
                        q.get('created_by'),
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


# ========== 聊天管理 ==========
@admin_api_bp.route('/chat/stats', methods=['GET'])
def api_chat_stats():
    """获取聊天统计数据"""
    try:
        conn = get_db()
        
        # 会话总数
        conv_count = conn.execute('SELECT COUNT(*) FROM chat_conversations').fetchone()[0]
        
        # 消息总数
        msg_count = conn.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0]
        
        # 今日消息数
        today_msg_count = conn.execute('''
            SELECT COUNT(*) FROM chat_messages 
            WHERE DATE(created_at) = DATE('now')
        ''').fetchone()[0]
        
        # 活跃会话数（最近7天有消息的会话）
        active_conv_count = conn.execute('''
            SELECT COUNT(DISTINCT conversation_id) FROM chat_messages 
            WHERE created_at >= datetime('now', '-7 days')
        ''').fetchone()[0]
        
        # 私聊会话数
        direct_conv_count = conn.execute(
            'SELECT COUNT(*) FROM chat_conversations WHERE c_type = ?',
            ('direct',)
        ).fetchone()[0]
        
        return jsonify({
            'status': 'success',
            'data': {
                'conv_count': conv_count,
                'msg_count': msg_count,
                'today_msg_count': today_msg_count,
                'active_conv_count': active_conv_count,
                'direct_conv_count': direct_conv_count
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取聊天统计失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取统计数据失败'
        }), 500


@admin_api_bp.route('/chat/conversations', methods=['GET'])
def api_chat_conversations():
    """获取会话列表（支持分页和搜索）"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        keyword = request.args.get('keyword', '').strip()
        offset = (page - 1) * per_page
        
        conn = get_db()
        
        # 构建基础查询
        base_sql = '''
            SELECT 
                c.id,
                c.c_type,
                c.title,
                c.direct_pair_key,
                c.created_at,
                c.updated_at,
                (SELECT COUNT(DISTINCT user_id) FROM chat_members WHERE conversation_id = c.id) as member_count,
                (SELECT COUNT(*) FROM chat_messages WHERE conversation_id = c.id) as message_count,
                (SELECT MAX(id) FROM chat_messages WHERE conversation_id = c.id) as last_message_id,
                (SELECT MAX(created_at) FROM chat_messages WHERE conversation_id = c.id) as last_message_time
            FROM chat_conversations c
        '''
        
        where_clause = ''
        params = []
        
        if keyword:
            # 搜索：通过标题（暂时简化，只搜索有标题的会话）
            where_clause = ' WHERE c.title LIKE ?'
            params.append(f'%{keyword}%')
        
        # 获取总数
        count_sql = f'SELECT COUNT(*) FROM chat_conversations c{where_clause}'
        total = conn.execute(count_sql, params).fetchone()[0]
        
        # 获取分页数据
        data_sql = f'{base_sql}{where_clause} ORDER BY c.updated_at DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        rows = conn.execute(data_sql, params).fetchall()
        
        conversations = []
        for row in rows:
            conv = dict(row)
            
            # 对于direct会话，获取参与用户信息
            if conv['c_type'] == 'direct' and conv['direct_pair_key']:
                try:
                    parts = conv['direct_pair_key'].split(':')
                    if len(parts) == 2:
                        uid1, uid2 = int(parts[0]), int(parts[1])
                        # 获取用户信息
                        users = conn.execute('''
                            SELECT id, username, avatar 
                            FROM users 
                            WHERE id IN (?, ?)
                        ''', (uid1, uid2)).fetchall()
                        conv['members'] = [dict(u) for u in users]
                except (ValueError, IndexError):
                    pass
            
            conversations.append(conv)
        
        return jsonify({
            'status': 'success',
            'data': {
                'conversations': conversations,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取会话列表失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取会话列表失败'
        }), 500


@admin_api_bp.route('/chat/conversations/<int:conversation_id>/messages', methods=['GET'])
def api_chat_conversation_messages(conversation_id: int):
    """获取会话消息列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        offset = (page - 1) * per_page
        
        conn = get_db()
        
        # 验证会话是否存在
        conv = conn.execute(
            'SELECT id FROM chat_conversations WHERE id = ?',
            (conversation_id,)
        ).fetchone()
        if not conv:
            return jsonify({
                'status': 'error',
                'message': '会话不存在'
            }), 404
        
        # 获取消息列表
        messages = conn.execute('''
            SELECT 
                m.id,
                m.conversation_id,
                m.sender_id,
                u.username as sender_username,
                u.avatar as sender_avatar,
                m.content,
                m.content_type,
                m.created_at
            FROM chat_messages m
            LEFT JOIN users u ON m.sender_id = u.id
            WHERE m.conversation_id = ?
            ORDER BY m.id DESC
            LIMIT ? OFFSET ?
        ''', (conversation_id, per_page, offset)).fetchall()
        
        # 获取总数
        total = conn.execute(
            'SELECT COUNT(*) FROM chat_messages WHERE conversation_id = ?',
            (conversation_id,)
        ).fetchone()[0]
        
        return jsonify({
            'status': 'success',
            'data': {
                'messages': [dict(msg) for msg in messages],
                'total': total,
                'page': page,
                'per_page': per_page
            }
        })
    except Exception as e:
        current_app.logger.error(f"获取会话消息失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取消息列表失败'
        }), 500


@admin_api_bp.route('/chat/conversations/<int:conversation_id>', methods=['DELETE'])
def api_delete_conversation(conversation_id: int):
    """删除会话（级联删除相关消息和成员）"""
    try:
        conn = get_db()
        
        # 验证会话是否存在
        conv = conn.execute(
            'SELECT id FROM chat_conversations WHERE id = ?',
            (conversation_id,)
        ).fetchone()
        if not conv:
            return jsonify({
                'status': 'error',
                'message': '会话不存在'
            }), 404
        
        # 删除会话（由于外键约束，会自动删除相关消息和成员）
        conn.execute('DELETE FROM chat_conversations WHERE id = ?', (conversation_id,))
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': '会话已删除'
        })
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"删除会话失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除会话失败'
        }), 500


@admin_api_bp.route('/chat/messages/<int:message_id>', methods=['DELETE'])
def api_delete_message(message_id: int):
    """删除消息"""
    try:
        conn = get_db()
        
        # 验证消息是否存在
        msg = conn.execute(
            'SELECT id FROM chat_messages WHERE id = ?',
            (message_id,)
        ).fetchone()
        if not msg:
            return jsonify({
                'status': 'error',
                'message': '消息不存在'
            }), 404
        
        # 删除消息
        conn.execute('DELETE FROM chat_messages WHERE id = ?', (message_id,))
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': '消息已删除'
        })
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"删除消息失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除消息失败'
        }), 500


# ========== 编程题管理 ==========

@admin_api_bp.route('/coding/questions', methods=['GET'])
def api_get_coding_questions():
    """获取编程题列表"""
    try:
        conn = get_db()
        
        # 查询所有编程题
        rows = conn.execute('''
            SELECT q.id, q.subject_id, q.content, q.programming_language, 
                   q.time_limit, q.memory_limit, q.code_template, q.difficulty, 
                   q.tags, q.explanation, q.updated_at,
                   s.name as subject_name
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE q.q_type = '编程题'
            ORDER BY q.id DESC
        ''').fetchall()
        
        questions = []
        for row in rows:
            q = dict(row)
            # 截断内容预览
            if q.get('content') and len(q['content']) > 100:
                q['content'] = q['content'][:100] + '...'
            questions.append(q)
        
        return jsonify({
            'status': 'success',
            'data': questions
        })
    except Exception as e:
        current_app.logger.error(f"获取编程题列表失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取编程题列表失败'
        }), 500


@admin_api_bp.route('/coding/questions', methods=['POST'])
def api_create_coding_question():
    """创建编程题"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        # 验证必填字段
        if not data.get('subject_id') or not data.get('content'):
            return jsonify({
                'status': 'error',
                'message': '科目和题目内容不能为空'
            }), 400
        
        uid = session.get('user_id')
        if not uid:
            return jsonify({
                'status': 'unauthorized',
                'message': '请先登录'
            }), 401
        
        conn = get_db()
        
        # 插入编程题
        conn.execute('''
            INSERT INTO questions (
                subject_id, q_type, content, programming_language, 
                code_template, time_limit, memory_limit, difficulty, 
                tags, explanation, created_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            data.get('subject_id'),
            '编程题',
            data.get('content'),
            data.get('programming_language', 'python'),
            data.get('code_template', ''),
            data.get('time_limit', 5),
            data.get('memory_limit', 128),
            data.get('difficulty', '中等'),
            data.get('tags', ''),
            data.get('explanation', ''),
            uid
        ))
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': '编程题创建成功',
            'data': {'id': conn.lastrowid}
        }), 201
        
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({
            'status': 'error',
            'message': '数据已存在或违反约束'
        }), 400
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"创建编程题失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '创建编程题失败'
        }), 500


@admin_api_bp.route('/coding/questions/<int:question_id>', methods=['PUT'])
def api_update_coding_question(question_id):
    """更新编程题"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        uid = session.get('user_id')
        if not uid:
            return jsonify({
                'status': 'unauthorized',
                'message': '请先登录'
            }), 401
        
        conn = get_db()
        
        # 检查题目是否存在且是编程题
        question = conn.execute(
            'SELECT id, q_type FROM questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        
        if not question:
            return jsonify({
                'status': 'error',
                'message': '题目不存在'
            }), 404
        
        if question['q_type'] != '编程题':
            return jsonify({
                'status': 'error',
                'message': '该题目不是编程题'
            }), 400
        
        # 更新编程题
        conn.execute('''
            UPDATE questions SET
                subject_id = ?,
                content = ?,
                programming_language = ?,
                code_template = ?,
                time_limit = ?,
                memory_limit = ?,
                difficulty = ?,
                tags = ?,
                explanation = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get('subject_id'),
            data.get('content'),
            data.get('programming_language', 'python'),
            data.get('code_template', ''),
            data.get('time_limit', 5),
            data.get('memory_limit', 128),
            data.get('difficulty', '中等'),
            data.get('tags', ''),
            data.get('explanation', ''),
            uid,
            question_id
        ))
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': '编程题更新成功'
        })
        
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"更新编程题失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '更新编程题失败'
        }), 500


@admin_api_bp.route('/coding/questions/<int:question_id>', methods=['DELETE'])
def api_delete_coding_question(question_id):
    """删除编程题"""
    try:
        uid = session.get('user_id')
        if not uid:
            return jsonify({
                'status': 'unauthorized',
                'message': '请先登录'
            }), 401
        
        conn = get_db()
        
        # 检查题目是否存在且是编程题
        question = conn.execute(
            'SELECT id, q_type FROM questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        
        if not question:
            return jsonify({
                'status': 'error',
                'message': '题目不存在'
            }), 404
        
        if question['q_type'] != '编程题':
            return jsonify({
                'status': 'error',
                'message': '该题目不是编程题'
            }), 400
        
        # 删除编程题
        conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': '编程题删除成功'
        })
        
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f"删除编程题失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除编程题失败'
        }), 500

