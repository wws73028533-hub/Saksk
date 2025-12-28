# -*- coding: utf-8 -*-
"""认证API路由"""
import sqlite3
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.extensions import limiter
from app.core.utils.database import get_db
from app.core.utils.validators import validate_password

auth_api_bp = Blueprint('auth_api', __name__)


@auth_api_bp.route('/register', methods=['POST'])
@limiter.limit("3 per hour")
def api_register():
    """注册API"""
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400
    
    # 密码强度校验
    valid, msg = validate_password(password)
    if not valid:
        return jsonify({'status': 'error', 'message': msg}), 400
    
    conn = get_db()
    try:
        ph = generate_password_hash(password)
        cnt = conn.execute('SELECT COUNT(1) FROM users').fetchone()[0]
        is_admin = 1 if cnt == 0 else 0
        
        conn.execute(
            'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
            (username, ph, is_admin)
        )
        conn.commit()
        
        # 自动登录
        # 检查 is_subject_admin 字段是否存在
        try:
            user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            has_subject_admin_field = 'is_subject_admin' in user_cols
        except Exception:
            has_subject_admin_field = False
        
        if has_subject_admin_field:
            query = 'SELECT id, is_admin, is_subject_admin, session_version FROM users WHERE username=?'
        else:
            query = 'SELECT id, is_admin, session_version FROM users WHERE username=?'
        
        row = conn.execute(query, (username,)).fetchone()
        
        session['user_id'] = row['id']
        session['username'] = username
        session['is_admin'] = bool(row['is_admin'])
        session['is_subject_admin'] = bool(row['is_subject_admin']) if has_subject_admin_field and 'is_subject_admin' in row.keys() else False
        session['session_version'] = row['session_version'] or 0
        
        current_app.logger.info(f'新用户注册 - 用户: {username}, 管理员: {is_admin}, IP: {request.remote_addr}')
        
        # 获取重定向地址
        redirect_url = data.get('redirect', '/') if isinstance(data, dict) else '/'
        return jsonify({'status': 'success', 'redirect': redirect_url})
    except sqlite3.IntegrityError:
        current_app.logger.warning(f'注册失败: 用户名已存在 - 用户: {username}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名已存在'}), 409


@auth_api_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login():
    """登录API（支持"保持登录"）"""
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    remember = bool(data.get('remember'))

    if not username or not password:
        current_app.logger.warning(f'登录失败: 缺少用户名或密码 - IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400

    conn = get_db()
    
    # 检查 is_subject_admin 字段是否存在
    try:
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        has_subject_admin_field = 'is_subject_admin' in user_cols
        # 如果字段不存在，尝试添加
        if not has_subject_admin_field:
            try:
                conn.execute('ALTER TABLE users ADD COLUMN is_subject_admin INTEGER DEFAULT 0')
                conn.commit()
                has_subject_admin_field = True
            except Exception:
                pass
    except Exception:
        has_subject_admin_field = False
    
    # 根据字段是否存在构建查询
    if has_subject_admin_field:
        query = 'SELECT id, password_hash, is_admin, is_subject_admin, is_locked, session_version FROM users WHERE username=?'
    else:
        query = 'SELECT id, password_hash, is_admin, is_locked, session_version FROM users WHERE username=?'
    
    row = conn.execute(query, (username,)).fetchone()

    if not row or not check_password_hash(row['password_hash'], password):
        current_app.logger.warning(f'登录失败: 用户名或密码错误 - 用户: {username}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 400

    if row['is_locked']:
        current_app.logger.warning(f'登录失败: 账户已锁定 - 用户: {username}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403

    # 关键：使用 Flask 的永久会话机制
    # remember=True -> session.permanent=True，由 PERMANENT_SESSION_LIFETIME 控制过期时间
    session.permanent = remember

    session['user_id'] = row['id']
    session['username'] = username
    session['is_admin'] = bool(row['is_admin'])
    session['is_subject_admin'] = bool(row['is_subject_admin']) if has_subject_admin_field and 'is_subject_admin' in row.keys() else False
    session['session_version'] = row['session_version'] or 0

    current_app.logger.info(
        f'用户登录成功 - 用户: {username}, remember={remember}, IP: {request.remote_addr}'
    )

    redirect_url = data.get('redirect', '/') if isinstance(data, dict) else '/'
    return jsonify({'status': 'success', 'redirect': redirect_url, 'remember': remember})


@auth_api_bp.route('/logout', methods=['POST'])
def api_logout():
    """登出API"""
    user_id = session.get('user_id')
    username = session.get('username')

    # 清空 last_active，使用户立即显示为离线
    if user_id:
        try:
            conn = get_db()
            conn.execute('UPDATE users SET last_active = NULL WHERE id = ?', (user_id,))
            conn.commit()
        except Exception as e:
            current_app.logger.error(f'登出时清空 last_active 失败: {e}')

        current_app.logger.info(f'用户登出 - 用户: {username}, ID: {user_id}, IP: {request.remote_addr}')

    session.clear()
    return jsonify({'status': 'success'})

