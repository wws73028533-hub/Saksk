# -*- coding: utf-8 -*-
"""
认证路由蓝图
"""
import sqlite3
from flask import Blueprint, render_template, request, jsonify, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import limiter
from ..utils.database import get_db
from ..utils.validators import validate_password

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login')
def login_page():
    """登录页面"""
    from_param = request.args.get('from', '')
    redirect_url = request.args.get('redirect', '')
    
    # 根据 from 参数设置提示信息
    tips = {
        'quiz': '刷题',
        'memo': '背题',
        '背题': '背题',
        'favorites': '收藏本',
        '收藏本': '收藏本',
        'mistakes': '错题本',
        '错题本': '错题本',
        'exam': '考试',
        '考试': '考试',
        'exams': '考试',
        'profile': '个人中心',
        'search': '搜索'
    }
    
    tip_message = tips.get(from_param, '')
    if tip_message:
        tip_message = f'使用{tip_message}功能需要先登录'
    
    return render_template('login.html', 
                         mode='login',
                         from_param=from_param,
                         redirect_url=redirect_url,
                         tip_message=tip_message)


@auth_bp.route('/register')
def register_page():
    """注册页面"""
    return render_template('login.html', mode='register')


@auth_bp.route('/api/register', methods=['POST'])
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
        row = conn.execute(
            'SELECT id, is_admin, session_version FROM users WHERE username=?',
            (username,)
        ).fetchone()
        
        session['user_id'] = row['id']
        session['username'] = username
        session['is_admin'] = bool(row['is_admin'])
        session['session_version'] = row['session_version'] or 0
        
        current_app.logger.info(f'新用户注册 - 用户: {username}, 管理员: {is_admin}, IP: {request.remote_addr}')
        
        # 获取重定向地址
        redirect_url = data.get('redirect', '/') if isinstance(data, dict) else '/'
        return jsonify({'status': 'success', 'redirect': redirect_url})
    except sqlite3.IntegrityError:
        current_app.logger.warning(f'注册失败: 用户名已存在 - 用户: {username}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名已存在'}), 409


@auth_bp.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login():
    """登录API"""
    data = request.json or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    
    if not username or not password:
        current_app.logger.warning(f'登录失败: 缺少用户名或密码 - IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400
    
    conn = get_db()
    row = conn.execute(
        'SELECT id, password_hash, is_admin, is_locked, session_version FROM users WHERE username=?',
        (username,)
    ).fetchone()
    
    if not row or not check_password_hash(row['password_hash'], password):
        current_app.logger.warning(f'登录失败: 用户名或密码错误 - 用户: {username}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 400
    
    if row['is_locked']:
        current_app.logger.warning(f'登录失败: 账户已锁定 - 用户: {username}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403
    
    session['user_id'] = row['id']
    session['username'] = username
    session['is_admin'] = bool(row['is_admin'])
    session['session_version'] = row['session_version'] or 0
    
    current_app.logger.info(f'用户登录成功 - 用户: {username}, IP: {request.remote_addr}')
    
    # 获取重定向地址
    redirect_url = request.json.get('redirect', '/') if request.json else '/'
    return jsonify({'status': 'success', 'redirect': redirect_url})


@auth_bp.route('/api/logout', methods=['POST'])
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

