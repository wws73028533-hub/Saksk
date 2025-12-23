# -*- coding: utf-8 -*-
"""
管理后台路由蓝图
"""
import json
import sqlite3
import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from ..utils.database import get_db
from ..utils.validators import parse_int, validate_password
from ..extensions import limiter
import pandas as pd

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'json'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@admin_bp.route('/')
@admin_bp.route('/dashboard')
def admin_dashboard():
    """管理后台首页"""
    conn = get_db()
    
    q_count = conn.execute('SELECT COUNT(1) FROM questions').fetchone()[0]
    s_count = conn.execute('SELECT COUNT(1) FROM subjects').fetchone()[0]
    u_count = conn.execute('SELECT COUNT(1) FROM users').fetchone()[0]
    admin_count = conn.execute('SELECT COUNT(1) FROM users WHERE is_admin = 1').fetchone()[0]
    
    recent_q = conn.execute(
        'SELECT id, content, q_type FROM questions ORDER BY id DESC LIMIT 5'
    ).fetchall()
    
    subject_dist = conn.execute('''
        SELECT s.name, COUNT(q.id) as count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id
        ORDER BY count DESC
    ''').fetchall()
    
    return render_template('admin_dashboard.html',
        stats={'q_count': q_count, 's_count': s_count, 'u_count': u_count, 'admin_count': admin_count},
        recent_questions=[dict(row) for row in recent_q],
        subject_distribution=[dict(row) for row in subject_dist]
    )


@admin_bp.route('/api/subjects', methods=['GET'])
def api_get_subjects():
    """获取科目列表"""
    conn = get_db()
    rows = conn.execute('''
        SELECT s.id, s.name, COUNT(q.id) as question_count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id, s.name
        ORDER BY s.id
    ''').fetchall()
    
    subjects = [dict(row) for row in rows]
    return jsonify(subjects)


@admin_bp.route('/types', methods=['GET'])
def get_question_types():
    """获取题型列表"""
    conn = get_db()
    types = [row[0] for row in conn.execute('SELECT DISTINCT q_type FROM questions').fetchall()]
    return jsonify(types)


@admin_bp.route('/questions', methods=['GET'])
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
    questions = [dict(row) for row in rows]
    
    return jsonify(questions)


@admin_bp.route('/questions/<int:question_id>', methods=['GET'])
def get_single_question(question_id):
    """获取单个题目"""
    conn = get_db()
    row = conn.execute('SELECT * FROM questions WHERE id=?', (question_id,)).fetchone()
    
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'not found'}), 404


@admin_bp.route('/questions', methods=['POST'])
def add_question():
    """添加题目"""
    data = request.json
    uid = session.get('user_id')
    
    try:
        conn = get_db()
        conn.execute('''
            INSERT INTO questions (subject_id, q_type, content, options, answer, explanation, difficulty, tags, image_path, created_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            data.get('subject_id'),
            data.get('q_type'),
            data.get('content'),
            data.get('options','[]'),
            data.get('answer',''),
            data.get('explanation',''),
            data.get('difficulty', 1),
            data.get('tags'),
            data.get('image_path'),
            uid
        ))
        new_id = conn.lastrowid
        conn.commit()
        
        return jsonify({'status':'success','message':'题目新增成功', 'id': new_id})
    except Exception as e:
        return jsonify({'status':'error','message':str(e)}), 500


@admin_bp.route('/questions/<int:question_id>', methods=['PUT'])
def edit_question(question_id):
    """编辑题目"""
    data = request.json
    
    try:
        conn = get_db()
        conn.execute('''
            UPDATE questions SET
                subject_id=?, q_type=?, content=?, options=?, answer=?, explanation=?,
                difficulty=?, tags=?, image_path=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (
            data.get('subject_id'),
            data.get('q_type'),
            data.get('content'),
            data.get('options','[]'),
            data.get('answer',''),
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


@admin_bp.route('/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    """删除题目"""
    conn = get_db()
    conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    conn.commit()
    
    return jsonify({'status': 'success', 'message': '题目删除成功'})


@admin_bp.route('/questions/batch_delete', methods=['POST'])
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


@admin_bp.route('/questions/batch_move_subject', methods=['POST'])
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


@admin_bp.route('/questions/batch_set_difficulty', methods=['POST'])
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


@admin_bp.route('/questions/batch_tags', methods=['POST'])
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


@admin_bp.route('/api/subjects', methods=['POST'])
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
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/api/subjects/<int:subject_id>', methods=['PUT'])
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


@admin_bp.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
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


@admin_bp.route('/users')
def admin_users_page():
    """用户管理页面"""
    conn = get_db()
    users = conn.execute('SELECT id, username, created_at, is_admin FROM users ORDER BY id').fetchall()
    return render_template('admin_users.html', users=[dict(row) for row in users])


@admin_bp.route('/api/users')
@limiter.exempt
def admin_api_users():
    """用户列表API"""
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
    
    rows = conn.execute(
        f'SELECT id, username, is_admin, is_locked, created_at, last_active FROM users {where} ORDER BY {sort_map[sort]} {order} LIMIT ? OFFSET ?',
        params + [size, offset]
    ).fetchall()
    
    from datetime import datetime, timedelta
    
    data = []
    for r in rows:
        # 判断在线状态：5分钟内有活动视为在线
        is_online = False
        if r['last_active']:
            try:
                # SQLite 的 CURRENT_TIMESTAMP 格式: "YYYY-MM-DD HH:MM:SS" (UTC时间)
                last_active_str = r['last_active'].replace('T', ' ').split('.')[0]
                last_active = datetime.strptime(last_active_str, '%Y-%m-%d %H:%M:%S')
                # SQLite CURRENT_TIMESTAMP 是 UTC，需要转换为本地时间
                # 或者使用 datetime.utcnow() 进行比较
                is_online = (datetime.utcnow() - last_active) < timedelta(minutes=5)
            except Exception as e:
                current_app.logger.warning(f'解析 last_active 失败: {r["last_active"]}, 错误: {e}')
        
        data.append({
            'id': r['id'],
            'username': r['username'],
            'is_admin': bool(r['is_admin']),
            'is_locked': bool(r['is_locked']) if 'is_locked' in r.keys() else False,
            'created_at': r['created_at'] if 'created_at' in r.keys() else '',
            'is_online': is_online,
            'last_active': r['last_active'] if 'last_active' in r.keys() else None
        })
    
    return jsonify({'status':'success','data': data, 'total': total})


@admin_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
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


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """删除用户"""
    if user_id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': '不能删除自己'}), 400
    
    conn = get_db()
    try:
        u = conn.execute('SELECT id, is_admin FROM users WHERE id=?', (user_id,)).fetchone()
        
        if not u:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        if u['is_admin']:
            admin_count = conn.execute('SELECT COUNT(1) FROM users WHERE is_admin = 1').fetchone()[0]
            if admin_count <= 1:
                return jsonify({'status': 'error', 'message': '不能删除最后一个管理员'}), 400
        
        # 级联清理
        conn.execute('DELETE FROM favorites WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM mistakes WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_answers WHERE user_id=?', (user_id,))
        conn.execute('DELETE FROM user_progress WHERE user_id=?', (user_id,))
        conn.execute('UPDATE questions SET created_by=NULL WHERE created_by=?', (user_id,))
        conn.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
        
        return jsonify({'status': 'success', 'message': '用户已删除'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@admin_bp.route('/users/create', methods=['POST'])
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


@admin_bp.route('/users/<int:user_id>/reset_password', methods=['POST'])
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


@admin_bp.route('/users/<int:user_id>/toggle_lock', methods=['POST'])
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


@admin_bp.route('/users/<int:user_id>/force_logout', methods=['POST'])
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
@admin_bp.route('/subjects')
def admin_subjects_page():
    """科目管理页面"""
    return render_template('admin_subjects.html')


@admin_bp.route('/subjects/<int:subject_id>/questions')
def admin_questions_page(subject_id):
    """题集管理页面"""
    conn = get_db()
    
    # 获取科目信息
    subject = conn.execute('SELECT id, name FROM subjects WHERE id=?', (subject_id,)).fetchone()
    
    if not subject:
        return "科目不存在", 404
    
    return render_template('admin_questions.html', subject_id=subject_id, subject=dict(subject))


@admin_bp.route('/users/<int:user_id>')
def admin_user_detail_page(user_id):
    """用户详情页面"""
    conn = get_db()
    
    u = conn.execute(
        'SELECT id, username, is_admin, is_locked, created_at, avatar, contact, college FROM users WHERE id=?',
        (user_id,)
    ).fetchone()
    
    if not u:
        return "用户不存在", 404
    
    # 收藏/错题
    fav = conn.execute('SELECT COUNT(1) FROM favorites WHERE user_id=?', (user_id,)).fetchone()[0]
    mis = conn.execute('SELECT COUNT(1) FROM mistakes WHERE user_id=?', (user_id,)).fetchone()[0]
    
    # 答题统计
    r = conn.execute(
        'SELECT COUNT(1) AS total, SUM(is_correct) AS correct FROM user_answers WHERE user_id=?',
        (user_id,)
    ).fetchone()
    total = r['total'] or 0
    correct = r['correct'] or 0
    acc = round(correct * 100.0 / total, 1) if total else 0.0
    
    # 考试统计
    ex_ongoing = conn.execute('SELECT COUNT(1) FROM exams WHERE user_id=? AND status="ongoing"', (user_id,)).fetchone()[0]
    ex_submitted = conn.execute('SELECT COUNT(1) FROM exams WHERE user_id=? AND status="submitted"', (user_id,)).fetchone()[0]
    
    recent = conn.execute(
        'SELECT id, subject, total_score, started_at, submitted_at FROM exams WHERE user_id=? AND status="submitted" ORDER BY submitted_at DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    
    return render_template('admin_user_detail.html',
        user=dict(u),
        stats={
            'favorites': fav,
            'mistakes': mis,
            'total_answers': total,
            'accuracy': acc,
            'exams_ongoing': ex_ongoing,
            'exams_submitted': ex_submitted
        },
        recent_exams=[dict(x) for x in recent]
    )


@admin_bp.route('/users/export')
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


@admin_bp.route('/questions/import', methods=['POST'])
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
            
            if q_type == '选择题':
                opts_json = json.dumps(item.get('选项', []), ensure_ascii=False)
            elif q_type == '填空题':
                import re
                matches = re.findall(r'\{(.*?)\}', content)
                if matches:
                    answer = ' '.join(matches)
                    content = re.sub(r'\{.*?\}', '______', content)
            
            conn.execute('''
                INSERT INTO questions (subject_id, q_type, content, options, answer, explanation)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (subject_id, q_type, content, opts_json, answer, explanation))
            count += 1
        
        conn.commit()
        return jsonify({'status': 'success', 'message': f'成功导入{count}道题'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@admin_bp.route('/questions/export', methods=['GET'])
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

@admin_bp.route('/notifications')
def admin_notifications_page():
    """通知管理页面"""
    return render_template('admin_notifications.html')


@admin_bp.route('/api/notifications', methods=['GET'])
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


@admin_bp.route('/api/notifications', methods=['POST'])
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


@admin_bp.route('/api/notifications/<int:nid>', methods=['GET'])
def admin_api_notifications_get(nid):
    """获取单个通知"""
    conn = get_db()
    row = conn.execute('SELECT * FROM notifications WHERE id = ?', (nid,)).fetchone()

    if not row:
        return jsonify({'status': 'error', 'message': '通知不存在'}), 404

    return jsonify({'status': 'success', 'notification': dict(row)})


@admin_bp.route('/api/notifications/<int:nid>', methods=['PUT'])
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


@admin_bp.route('/api/notifications/<int:nid>', methods=['DELETE'])
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


@admin_bp.route('/api/notifications/<int:nid>/toggle', methods=['POST'])
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


@admin_bp.route('/api/questions/import/excel', methods=['POST'])
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


@admin_bp.route('/download_template')
def download_template():
    """提供题库导入模板文件的下载"""
    directory = os.path.join(current_app.root_path, '..', 'instance')
    return send_from_directory(directory, 'question_import_template.xlsx', as_attachment=True)


@admin_bp.route('/api/questions/upload_image', methods=['POST'])
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
        file_url = url_for('main.serve_upload', filename=f'question_images/{unique_filename}')
        
        return jsonify({'status': 'success', 'url': file_url, 'path': f'question_images/{unique_filename}'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'上传失败: {str(e)}'}), 500

