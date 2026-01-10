# -*- coding: utf-8 -*-
"""
装饰器工具函数
"""
from functools import wraps
from flask import session, redirect, url_for, jsonify, request, g
from app.core.utils.database import get_db


def _validate_jwt_user(payload):
    """校验 JWT 对应用户状态（用于强制下线/锁定/删除/解绑微信后的立即失效）"""
    try:
        user_id = payload.get('user_id')
        if not user_id:
            return False, 'token格式错误'

        token_sv = int(payload.get('session_version') or 0)
        token_openid = str(payload.get('openid') or '').strip()

        conn = get_db()
        try:
            user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        except Exception:
            user_cols = []

        has_openid = 'openid' in user_cols
        has_locked = 'is_locked' in user_cols
        has_sv = 'session_version' in user_cols

        fields = ['id']
        if has_locked:
            fields.append('is_locked')
        if has_sv:
            fields.append('session_version')
        if has_openid:
            fields.append('openid')

        row = conn.execute(
            f"SELECT {', '.join(fields)} FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
        if not row:
            return False, '用户不存在或已被删除'
        row = dict(row)

        # 锁定
        if has_locked and int(row.get('is_locked') or 0) == 1:
            return False, '账户已被锁定'

        # 会话版本不匹配（管理员强制下线、重置密码、解绑微信等会 bump）
        if has_sv:
            db_sv = int(row.get('session_version') or 0)
            if token_sv != db_sv:
                return False, '会话已失效，请重新登录'

        # token 带 openid 时，要求与 DB 一致（解绑微信会导致不一致）
        if token_openid and has_openid:
            db_openid = str(row.get('openid') or '').strip()
            if token_openid != db_openid:
                return False, '微信已解绑或账号已变更，请重新登录'

        return True, None
    except Exception:
        return False, 'token验证失败'


def login_required(f):
    """
    登录验证装饰器
    
    用法:
        @login_required
        def my_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            # API请求返回JSON
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            # 页面请求重定向到登录页
            return redirect(url_for('auth.auth_pages.login_page'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    管理员验证装饰器
    
    用法:
        @admin_required
        def admin_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            return redirect(url_for('auth.auth_pages.login_page'))
        
        if not session.get('is_admin'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员权限'}), 403
            return redirect(url_for('main.main_pages.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def current_user_id():
    """获取当前用户ID（兼容session和JWT）"""
    # 优先从JWT获取（小程序）
    if hasattr(g, 'current_user_id'):
        return g.current_user_id
    # 从session获取（Web）
    return session.get('user_id')


def current_username():
    """获取当前用户名"""
    return session.get('username')


def is_admin():
    """判断当前用户是否是管理员"""
    return bool(session.get('is_admin'))


def subject_admin_required(f):
    """
    科目管理员验证装饰器（允许管理员和科目管理员）
    
    用法:
        @subject_admin_required
        def subject_admin_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            return redirect(url_for('auth.auth_pages.login_page'))
        
        # 管理员和科目管理员都可以访问
        is_admin_user = session.get('is_admin')
        is_subject_admin_user = session.get('is_subject_admin')
        
        if not (is_admin_user or is_subject_admin_user):
            if request.path.startswith('/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403
            return redirect(url_for('main.main_pages.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def is_subject_admin():
    """判断当前用户是否是科目管理员"""
    return bool(session.get('is_subject_admin'))


def notification_admin_required(f):
    """
    通知管理员验证装饰器（允许管理员和通知管理员）
    
    用法:
        @notification_admin_required
        def notification_admin_view():
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.path.startswith('/api'):
                return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
            return redirect(url_for('auth.auth_pages.login_page'))
        
        # 管理员和通知管理员都可以访问
        is_admin_user = session.get('is_admin')
        is_notification_admin_user = session.get('is_notification_admin')
        
        if not (is_admin_user or is_notification_admin_user):
            if request.path.startswith('/api'):
                return jsonify({'status': 'forbidden', 'message': '需要管理员或通知管理员权限'}), 403
            return redirect(url_for('main.main_pages.index'))
        
        return f(*args, **kwargs)
    return decorated_function


def is_notification_admin():
    """判断当前用户是否是通知管理员"""
    return bool(session.get('is_notification_admin'))


def jwt_required(f):
    """
    JWT验证装饰器（用于小程序API）
    
    用法:
        @jwt_required
        def my_api():
            user_id = g.current_user_id
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify, g
        from app.core.utils.jwt_utils import decode_jwt_token
        
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({
                'status': 'error',
                'message': '缺少认证token'
            }), 401
        
        try:
            # 移除 'Bearer ' 前缀
            if token.startswith('Bearer '):
                token = token[7:]
            
            # 验证token
            payload = decode_jwt_token(token)
            if not payload:
                return jsonify({
                    'status': 'error',
                    'message': 'token无效或已过期'
                }), 401
            
            ok, err = _validate_jwt_user(payload)
            if not ok:
                return jsonify({'status': 'error', 'message': err or 'token无效或已过期'}), 401

            user_id = payload.get('user_id')
            if not user_id:
                return jsonify({
                    'status': 'error',
                    'message': 'token格式错误'
                }), 401
            
            # 将user_id添加到g对象
            g.current_user_id = user_id
            g.current_user_openid = payload.get('openid')
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'JWT验证失败: {str(e)}', exc_info=True)
            return jsonify({
                'status': 'error',
                'message': 'token验证失败'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


def auth_required(f):
    """
    通用认证装饰器（同时支持session和JWT）
    
    用法:
        @auth_required
        def my_api():
            user_id = get_current_user_id()
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify, g, current_app
        from app.core.utils.jwt_utils import decode_jwt_token
        
        # 先尝试JWT token（小程序）
        # Flask的headers不区分大小写，但为了兼容性，尝试多种方式
        token = request.headers.get('Authorization') or request.headers.get('authorization')
        debug_enabled = bool(current_app.config.get('DEBUG'))
        
        if token:
            raw_token = token.strip()
            if raw_token.startswith('Bearer '):
                raw_token = raw_token[7:].strip()

            payload = None
            try:
                payload = decode_jwt_token(raw_token)
            except Exception as e:
                if debug_enabled and request.path == '/api/quiz/subjects':
                    current_app.logger.debug("JWT token验证异常: %s", str(e), exc_info=True)

            if payload:
                ok, err = _validate_jwt_user(payload)
                if not ok:
                    return jsonify({'status': 'unauthorized', 'message': err or 'token无效或已过期'}), 401
                user_id = payload.get('user_id')
                if user_id:
                    g.current_user_id = user_id
                    g.current_user_openid = payload.get('openid')
                    if debug_enabled and request.path == '/api/quiz/subjects':
                        current_app.logger.debug("JWT token验证成功: user_id=%s", user_id)
                    return f(*args, **kwargs)
            else:
                if debug_enabled and request.path == '/api/quiz/subjects':
                    current_app.logger.debug("JWT token验证失败: payload为空")
        
        # 再尝试session（Web）
        user_id = session.get('user_id')
        if user_id:
            g.current_user_id = user_id
            return f(*args, **kwargs)
        
        # 未认证
        if request.path.startswith('/api'):
            return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
        return redirect(url_for('auth.auth_pages.login_page'))
    
    return decorated_function
