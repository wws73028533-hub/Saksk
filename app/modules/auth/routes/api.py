# -*- coding: utf-8 -*-
"""认证API路由"""
import sqlite3
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.extensions import limiter
from app.core.utils.database import get_db
from app.core.utils.validators import validate_password
from app.core.models.user import User
from app.modules.auth.schemas import (
    SendBindCodeSchema,
    BindEmailSchema,
    SendLoginCodeSchema,
    EmailLoginSchema,
    LoginSchema,
    SendForgotPasswordCodeSchema,
    ResetPasswordSchema
)
from app.modules.auth.services.email_service import EmailAuthService

auth_api_bp = Blueprint('auth_api', __name__)


@auth_api_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login():
    """登录API（支持用户名或邮箱登录）"""
    data = request.json or {}
    
    # 使用Pydantic验证
    try:
        login_data = LoginSchema.model_validate(data)
    except Exception as e:
        current_app.logger.warning(f'登录失败: 数据验证失败 - {str(e)}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': f'数据验证失败: {str(e)}'}), 400
    
    identifier = login_data.username.strip()
    password = login_data.password
    remember = login_data.remember
    
    if not identifier or not password:
        current_app.logger.warning(f'登录失败: 缺少用户名或密码 - IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名和密码不能为空'}), 400
    
    conn = get_db()
    
    # 检查 is_subject_admin 和 is_notification_admin 字段是否存在
    try:
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        has_subject_admin_field = 'is_subject_admin' in user_cols
        has_notification_admin_field = 'is_notification_admin' in user_cols
        # 如果字段不存在，尝试添加
        if not has_subject_admin_field:
            try:
                conn.execute('ALTER TABLE users ADD COLUMN is_subject_admin INTEGER DEFAULT 0')
                conn.commit()
                has_subject_admin_field = True
            except Exception:
                pass
        if not has_notification_admin_field:
            try:
                conn.execute('ALTER TABLE users ADD COLUMN is_notification_admin INTEGER DEFAULT 0')
                conn.commit()
                has_notification_admin_field = True
            except Exception:
                pass
    except Exception:
        has_subject_admin_field = False
        has_notification_admin_field = False
    
    # 使用User模型的verify_password方法（支持邮箱和用户名）
    user = User.verify_password(identifier, password)
    
    if not user:
        current_app.logger.warning(f'登录失败: 用户名或密码错误 - 用户: {identifier}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '用户名或密码错误'}), 400
    
    if user.get('is_locked'):
        current_app.logger.warning(f'登录失败: 账户已锁定 - 用户: {identifier}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403
    
    # 关键：使用 Flask 的永久会话机制
    session.permanent = remember
    
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['is_admin'] = bool(user.get('is_admin', 0))
    session['is_subject_admin'] = bool(user.get('is_subject_admin', 0)) if has_subject_admin_field else False
    session['is_notification_admin'] = bool(user.get('is_notification_admin', 0)) if has_notification_admin_field else False
    session['session_version'] = user.get('session_version') or 0
    
    current_app.logger.info(
        f'用户登录成功 - 用户: {identifier}, remember={remember}, IP: {request.remote_addr}'
    )
    
    # 检查用户是否需要设置密码
    needs_password_set = not User.has_password_set(user['id'])
    
    redirect_url = login_data.redirect or '/'
    return jsonify({
        'status': 'success', 
        'redirect': redirect_url, 
        'remember': remember,
        'needs_password_set': needs_password_set
    })


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


@auth_api_bp.route('/email/send-bind-code', methods=['POST'])
@limiter.limit("1 per minute;5 per hour")  # 同一邮箱1分钟1次，同一用户1小时5次
def api_send_bind_code():
    """发送绑定邮箱验证码API"""
    # 检查用户是否登录
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    # 检查请求内容类型
    if not request.is_json:
        current_app.logger.warning(f'绑定邮箱验证码请求不是JSON格式, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': '请求必须是JSON格式'}), 400
    
    data = request.json or {}
    
    # 记录请求数据（用于调试）
    current_app.logger.debug(f'绑定邮箱验证码请求: user_id={user_id}, data={data}, IP: {request.remote_addr}')
    
    # 使用Pydantic验证
    try:
        schema = SendBindCodeSchema.model_validate(data)
    except Exception as e:
        error_msg = str(e)
        current_app.logger.warning(f'绑定邮箱验证码请求数据验证失败: {error_msg}, 数据: {data}, IP: {request.remote_addr}')
        # 提取更友好的错误信息
        if 'email' in error_msg.lower() or 'value_error' in error_msg.lower():
            return jsonify({'status': 'error', 'message': '邮箱格式不正确，请检查邮箱地址'}), 400
        return jsonify({'status': 'error', 'message': f'数据验证失败: {error_msg}'}), 400
    
    # 调用业务逻辑服务
    success, error_msg = EmailAuthService.send_bind_code(user_id, schema.email)
    
    if not success:
        current_app.logger.warning(f'发送绑定邮箱验证码失败: user_id={user_id}, email={schema.email}, error={error_msg}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': error_msg}), 400
    
    return jsonify({
        'status': 'success',
        'message': '验证码已发送到邮箱'
    }), 200


@auth_api_bp.route('/email/bind', methods=['POST'])
@limiter.limit("10 per minute")
def api_bind_email():
    """绑定邮箱API"""
    # 检查用户是否登录
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': '请先登录'}), 401
    
    data = request.json or {}
    
    # 使用Pydantic验证
    try:
        schema = BindEmailSchema.model_validate(data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'数据验证失败: {str(e)}'}), 400
    
    # 调用业务逻辑服务
    success, error_msg, user_data = EmailAuthService.bind_email(
        user_id, schema.email, schema.code
    )
    
    if not success:
        return jsonify({'status': 'error', 'message': error_msg}), 400
    
    return jsonify({
        'status': 'success',
        'message': '邮箱绑定成功',
        'data': user_data
    }), 200


@auth_api_bp.route('/email/send-login-code', methods=['POST'])
@limiter.limit("1 per minute;10 per hour")  # 同一邮箱1分钟1次，同一IP1小时10次
def api_send_login_code():
    """发送登录验证码API"""
    data = request.json or {}
    
    # 使用Pydantic验证
    try:
        schema = SendLoginCodeSchema.model_validate(data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'数据验证失败: {str(e)}'}), 400
    
    # 调用业务逻辑服务
    success, error_msg = EmailAuthService.send_login_code(schema.email)
    
    if not success:
        # 防止邮箱枚举攻击：即使邮箱未绑定也返回相同消息
        return jsonify({
            'status': 'success',
            'message': '验证码已发送，请查收邮件'
        }), 200
    
    return jsonify({
        'status': 'success',
        'message': '验证码已发送，请查收邮件'
    }), 200


@auth_api_bp.route('/email/login', methods=['POST'])
@limiter.limit("10 per minute")
def api_email_login():
    """邮箱验证码登录API"""
    data = request.json or {}
    
    # 使用Pydantic验证
    try:
        schema = EmailLoginSchema.model_validate(data)
    except Exception as e:
        current_app.logger.warning(f'验证码登录失败: 数据验证失败 - {str(e)}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': f'数据验证失败: {str(e)}'}), 400
    
    # 调用业务逻辑服务
    success, error_msg, user = EmailAuthService.verify_login_code(
        schema.email, schema.code
    )
    
    if not success:
        current_app.logger.warning(
            f'验证码登录失败: {error_msg} - 邮箱: {schema.email}, IP: {request.remote_addr}'
        )
        return jsonify({'status': 'error', 'message': error_msg}), 400
    
    # 创建会话
    conn = get_db()
    
    # 检查 is_subject_admin 和 is_notification_admin 字段是否存在
    try:
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        has_subject_admin_field = 'is_subject_admin' in user_cols
        has_notification_admin_field = 'is_notification_admin' in user_cols
    except Exception:
        has_subject_admin_field = False
        has_notification_admin_field = False
    
    session.permanent = False  # 验证码登录默认不保持登录
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['is_admin'] = bool(user.get('is_admin', 0))
    session['is_subject_admin'] = bool(user.get('is_subject_admin', 0)) if has_subject_admin_field else False
    session['is_notification_admin'] = bool(user.get('is_notification_admin', 0)) if has_notification_admin_field else False
    session['session_version'] = user.get('session_version') or 0
    
    current_app.logger.info(
        f'验证码登录成功 - 邮箱: {schema.email}, 用户: {user["username"]}, IP: {request.remote_addr}'
    )
    
    # 检查用户是否需要设置密码
    needs_password_set = not User.has_password_set(user['id'])
    
    redirect_url = data.get('redirect', '/') if isinstance(data, dict) else '/'
    return jsonify({
        'status': 'success',
        'redirect': redirect_url,
        'needs_password_set': needs_password_set
    }), 200


@auth_api_bp.route('/forgot-password/send-code', methods=['POST'])
@limiter.limit("1 per minute;5 per hour")  # 同一邮箱1分钟1次，同一IP1小时5次
def api_send_forgot_password_code():
    """发送忘记密码验证码API"""
    data = request.json or {}
    
    # 使用Pydantic验证
    try:
        schema = SendForgotPasswordCodeSchema.model_validate(data)
    except Exception as e:
        current_app.logger.warning(f'发送忘记密码验证码失败: 数据验证失败 - {str(e)}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': f'数据验证失败: {str(e)}'}), 400
    
    # 调用业务逻辑服务
    success, error_msg = EmailAuthService.send_reset_password_code(schema.email)
    
    if not success:
        # 如果是频率限制等错误，返回真实错误消息
        # 如果是邮箱未绑定，服务层已返回True，不会到这里
        return jsonify({
            'status': 'error',
            'message': error_msg or '发送验证码失败，请稍后再试'
        }), 400
    
    # 防止邮箱枚举攻击：统一返回成功消息
    return jsonify({
        'status': 'success',
        'message': '验证码已发送，请查收邮件'
    }), 200


@auth_api_bp.route('/forgot-password/reset', methods=['POST'])
@limiter.limit("10 per minute")
def api_reset_password():
    """重置密码API"""
    data = request.json or {}
    
    # 使用Pydantic验证
    try:
        schema = ResetPasswordSchema.model_validate(data)
    except Exception as e:
        current_app.logger.warning(f'重置密码失败: 数据验证失败 - {str(e)}, IP: {request.remote_addr}')
        return jsonify({'status': 'error', 'message': f'数据验证失败: {str(e)}'}), 400
    
    # 调用业务逻辑服务
    success, error_msg = EmailAuthService.reset_password(
        schema.email, schema.code, schema.new_password
    )
    
    if not success:
        # 防止邮箱枚举攻击：统一返回相同的错误消息
        current_app.logger.warning(
            f'重置密码失败: {error_msg} - 邮箱: {schema.email}, IP: {request.remote_addr}'
        )
        # 统一返回相同的错误消息，防止通过错误消息判断邮箱是否存在
        return jsonify({'status': 'error', 'message': '验证码错误或已过期'}), 400
    
    current_app.logger.info(
        f'密码重置成功 - 邮箱: {schema.email}, IP: {request.remote_addr}'
    )
    
    return jsonify({
        'status': 'success',
        'message': '密码重置成功'
    }), 200

