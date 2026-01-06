# -*- coding: utf-8 -*-
"""认证API路由"""
import sqlite3
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.extensions import limiter
from app.core.utils.database import get_db
from app.core.utils.validators import validate_password
from app.core.utils.decorators import jwt_required
from app.core.models.user import User
from app.modules.auth.schemas import (
    SendBindCodeSchema,
    BindEmailSchema,
    SendLoginCodeSchema,
    EmailLoginSchema,
    LoginSchema,
    SendForgotPasswordCodeSchema,
    ResetPasswordSchema,
    WechatLoginSchema
)
from app.modules.auth.services.email_service import EmailAuthService
from app.modules.auth.services.wechat_auth_service import WechatAuthService
from app.modules.auth.services.web_login_service import (
    WebLoginService,
    WebWechatBindService,
    WechatTempTokenService,
    set_web_session,
)
from app.core.utils.jwt_utils import generate_jwt_token

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


@auth_api_bp.route('/wechat/login', methods=['POST'])
@limiter.limit("100 per minute")  # 开发环境使用更宽松的限流，生产环境可通过配置调整
def api_wechat_login():
    """微信登录API"""
    try:
        data = request.json or {}
        
        # 使用Pydantic验证
        try:
            schema = WechatLoginSchema.model_validate(data)
        except Exception as e:
            current_app.logger.warning(f'微信登录失败: 数据验证失败 - {str(e)}, IP: {request.remote_addr}')
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        # 验证code
        wechat_data = WechatAuthService.verify_code(schema.code)
        if wechat_data.get('error'):
            current_app.logger.warning(f'微信登录失败: {wechat_data.get("error")}, IP: {request.remote_addr}')
            return jsonify({
                'status': 'error',
                'message': wechat_data.get('error', '微信登录失败：code无效')
            }), 400
        
        openid = wechat_data.get('openid')
        if not openid:
            current_app.logger.warning(f'微信登录失败: 未获取到openid, IP: {request.remote_addr}')
            return jsonify({
                'status': 'error',
                'message': '微信登录失败：code无效'
            }), 400
        
        # 先查找是否已绑定（users.openid）
        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE openid = ?', (openid,)).fetchone()
        if row:
            user = dict(row)
            user['is_new_user'] = False
        else:
            # 未绑定：根据 allow_create 决定返回“需绑定/创建”还是直接自动创建
            if not getattr(schema, 'allow_create', True):
                temp = WechatTempTokenService.issue(openid, schema.user_info)
                return jsonify({
                    'status': 'success',
                    'data': {
                        'need_bind': True,
                        'wechat_temp_token': temp['token'],
                        'expires_at': temp['expires_at']
                    }
                }), 200

            # 自动创建（兼容旧逻辑）
            try:
                user = WechatAuthService.get_or_create_user(openid, schema.user_info)
            except Exception as e:
                current_app.logger.error(f'微信登录失败: 创建用户失败 - {str(e)}, IP: {request.remote_addr}', exc_info=True)
                return jsonify({
                    'status': 'error',
                    'message': '创建用户失败，请稍后重试'
                }), 500
            
            if not user:
                current_app.logger.warning(f'微信登录失败: 用户信息获取失败, IP: {request.remote_addr}')
                return jsonify({
                    'status': 'error',
                    'message': '用户信息获取失败'
                }), 500
        
        # 检查账户是否锁定
        if user.get('is_locked'):
            current_app.logger.warning(f'微信登录失败: 账户已锁定 - openid: {openid}, IP: {request.remote_addr}')
            return jsonify({
                'status': 'error',
                'message': '账户已被锁定，请联系管理员'
            }), 403
        
        # 生成JWT token
        try:
            token = generate_jwt_token(user['id'], openid, session_version=int(user.get('session_version') or 0))
        except Exception as e:
            current_app.logger.error(f'微信登录失败: 生成token失败 - {str(e)}, IP: {request.remote_addr}', exc_info=True)
            return jsonify({
                'status': 'error',
                'message': '生成token失败，请稍后重试'
            }), 500
        
        current_app.logger.info(
            f'微信登录成功 - user_id: {user["id"]}, username: {user.get("username")}, is_new_user: {user.get("is_new_user", False)}, IP: {request.remote_addr}'
        )
        
        # 返回响应
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': user['id'],
                'token': token,
                'user_info': {
                    'id': user['id'],
                    'username': user.get('username'),
                    'avatar': user.get('avatar'),
                    'is_new_user': user.get('is_new_user', False)
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'微信登录异常: {str(e)}, IP: {request.remote_addr}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '登录失败，请稍后重试'
        }), 500


@auth_api_bp.route('/wechat/create', methods=['POST'])
@limiter.limit("60 per minute")
def api_wechat_create_from_temp():
    """微信未绑定时：创建新账号（基于 wechat_temp_token）"""
    data = request.json or {}
    temp_token = (data.get('wechat_temp_token') or '').strip()
    if not temp_token:
        return jsonify({'status': 'error', 'message': '缺少 wechat_temp_token'}), 400

    try:
        temp = WechatTempTokenService.peek(temp_token)
        if not temp:
            return jsonify({'status': 'error', 'message': '临时票据无效或已过期'}), 401
        openid = temp.get('openid')
        user_info = temp.get('user_info')
        if not openid:
            return jsonify({'status': 'error', 'message': '临时票据无效'}), 401

        user = WechatAuthService.get_or_create_user(openid, user_info)
        if not user:
            return jsonify({'status': 'error', 'message': '创建用户失败'}), 500
        if user.get('is_locked'):
            return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403

        token = generate_jwt_token(user['id'], openid, session_version=int(user.get('session_version') or 0))
        WechatTempTokenService.delete(temp_token)
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': user['id'],
                'token': token,
                'user_info': {
                    'id': user['id'],
                    'username': user.get('username'),
                    'avatar': user.get('avatar'),
                    'is_new_user': user.get('is_new_user', False)
                }
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f'微信创建账号失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '创建失败，请稍后重试'}), 500


@auth_api_bp.route('/wechat/bind/send_code', methods=['POST'])
@limiter.limit("1 per minute;10 per hour")
def api_wechat_bind_send_code():
    """绑定已有账号：发送邮箱验证码（不登录也可用，需 wechat_temp_token）"""
    data = request.json or {}
    temp_token = (data.get('wechat_temp_token') or '').strip()
    email = (data.get('email') or '').strip()
    if not temp_token or not email:
        return jsonify({'status': 'error', 'message': '缺少参数'}), 400

    temp = WechatTempTokenService.peek(temp_token)
    if not temp:
        return jsonify({'status': 'error', 'message': '临时票据无效或已过期'}), 401

    # 仅允许“绑定已有账号”，不自动注册
    user = User.get_by_email(email) if hasattr(User, 'get_by_email') else None
    if not user:
        # 兼容 User 模型未实现 get_by_email：直接查库
        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        user = dict(row) if row else None
    if not user:
        return jsonify({'status': 'error', 'message': '该邮箱未注册，无法绑定'}), 400

    ok, err = EmailAuthService.send_login_code(email)
    if not ok:
        return jsonify({'status': 'error', 'message': err or '发送失败'}), 400
    return jsonify({'status': 'success', 'message': '验证码已发送到邮箱'}), 200


@auth_api_bp.route('/wechat/bind', methods=['POST'])
@limiter.limit("60 per minute")
def api_wechat_bind_existing_user():
    """微信未绑定时：绑定已有账号（账号密码 / 邮箱验证码）"""
    data = request.json or {}
    temp_token = (data.get('wechat_temp_token') or '').strip()
    bind_mode = (data.get('bind_mode') or '').strip()
    if not temp_token or bind_mode not in ('password', 'email_code'):
        return jsonify({'status': 'error', 'message': '参数错误'}), 400

    try:
        temp = WechatTempTokenService.peek(temp_token)
        if not temp:
            return jsonify({'status': 'error', 'message': '临时票据无效或已过期'}), 401
        openid = temp.get('openid')
        if not openid:
            return jsonify({'status': 'error', 'message': '临时票据无效'}), 401

        # 防止 openid 被重复绑定
        conn = get_db()
        existing = conn.execute('SELECT id FROM users WHERE openid = ?', (openid,)).fetchone()
        if existing:
            return jsonify({'status': 'error', 'message': '该微信已绑定其他账号'}), 409

        target_user = None
        if bind_mode == 'password':
            account = (data.get('account') or '').strip()
            password = data.get('password') or ''
            if not account or not password:
                return jsonify({'status': 'error', 'message': '缺少账号或密码'}), 400
            target_user = User.verify_password(account, password)
            if not target_user:
                return jsonify({'status': 'error', 'message': '账号或密码错误'}), 403
        else:
            email = (data.get('email') or '').strip()
            code = (data.get('code') or '').strip()
            if not email or not code:
                return jsonify({'status': 'error', 'message': '缺少邮箱或验证码'}), 400

            # 仅允许绑定已有账号，不自动注册
            row = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            if not row:
                return jsonify({'status': 'error', 'message': '该邮箱未注册，无法绑定'}), 400

            ok, err, user_data = EmailAuthService.verify_login_code(email, code)
            if not ok or not user_data:
                return jsonify({'status': 'error', 'message': err or '验证码错误或已过期'}), 403
            target_user = user_data

        if target_user.get('is_locked'):
            return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403

        # 绑定 openid 到该用户
        try:
            conn.execute('UPDATE users SET openid = ? WHERE id = ?', (openid, int(target_user['id'])))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return jsonify({'status': 'error', 'message': '该微信已绑定其他账号'}), 409
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'绑定微信失败: {e}', exc_info=True)
            return jsonify({'status': 'error', 'message': '绑定失败，请稍后重试'}), 500

        token = generate_jwt_token(int(target_user['id']), openid, session_version=int(target_user.get('session_version') or 0))
        WechatTempTokenService.delete(temp_token)
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': int(target_user['id']),
                'token': token,
                'user_info': {
                    'id': int(target_user['id']),
                    'username': target_user.get('username'),
                    'avatar': target_user.get('avatar'),
                    'is_new_user': False
                }
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f'微信绑定异常: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '绑定失败，请稍后重试'}), 500


@auth_api_bp.route('/web_login/qrcode', methods=['POST'])
@limiter.limit("60 per minute")
def api_web_login_qrcode():
    """Web：创建扫码登录会话并返回小程序码图片 URL"""
    try:
        meta = {
            "ip": request.remote_addr,
            "ua": request.headers.get("User-Agent", ""),
        }
        sess = WebLoginService.create_session(meta=meta)
        sess = WebLoginService.generate_qrcode_image(sess)
        env_version = (current_app.config.get("WECHAT_MINICODE_ENV_VERSION") or "").strip() or (
            "develop" if bool(current_app.config.get("DEBUG") or current_app.debug) else "release"
        )
        return jsonify({
            "status": "success",
            "data": {
                "sid": sess["sid"],
                "expires_at": sess["expires_at"],
                "qrcode_url": sess.get("qrcode_url"),
                "page_used": sess.get("page_used"),
                "page_fallback": bool(sess.get("page_fallback")),
                "env_version": env_version,
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f'生成扫码二维码失败: {e}', exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@auth_api_bp.route('/web_login/sessions/<sid>', methods=['GET'])
@limiter.exempt
def api_web_login_session_status(sid: str):
    """Web：轮询扫码登录会话状态"""
    try:
        sess = WebLoginService.get_session(sid)
        if not sess:
            return jsonify({"status": "error", "message": "sid不存在"}), 404

        if sess.get("state") == "confirmed":
            sess = WebLoginService.ensure_exchange_token(sid)

        return jsonify({
            "status": "success",
            "data": {
                "sid": sess.get("sid"),
                "state": sess.get("state"),
                "expires_at": sess.get("expires_at"),
                "token": sess.get("token") if sess.get("state") == "confirmed" else None,
                "token_expires_at": sess.get("token_expires_at") if sess.get("state") == "confirmed" else None,
            }
        }), 200
    except TimeoutError:
        return jsonify({"status": "success", "data": {"sid": sid, "state": "expired"}}), 200
    except Exception as e:
        current_app.logger.error(f'查询扫码会话失败: {e}', exc_info=True)
        return jsonify({"status": "error", "message": "查询失败"}), 500


@auth_api_bp.route('/web_login/confirm', methods=['POST'])
@jwt_required
@limiter.limit("60 per minute")
def api_web_login_confirm():
    """小程序：用户点击确认登录（必须JWT）"""
    data = request.json or {}
    sid = (data.get("sid") or "").strip()
    nonce = (data.get("nonce") or "").strip()
    if not sid or not nonce:
        return jsonify({"status": "error", "message": "缺少参数"}), 400

    from flask import g
    user_id = getattr(g, "current_user_id", None)
    if not user_id:
        return jsonify({"status": "error", "message": "未登录"}), 401

    try:
        WebLoginService.confirm_session(sid=sid, nonce=nonce, user_id=int(user_id))
        return jsonify({"status": "success", "message": "已确认"}), 200
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "sid不存在"}), 404
    except TimeoutError:
        return jsonify({"status": "error", "message": "会话已过期"}), 410
    except PermissionError:
        return jsonify({"status": "error", "message": "nonce无效"}), 403
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 409
    except Exception as e:
        current_app.logger.error(f'确认扫码登录失败: {e}', exc_info=True)
        return jsonify({"status": "error", "message": "确认失败"}), 500


@auth_api_bp.route('/web_login/exchange', methods=['POST'])
@limiter.limit("120 per minute")
def api_web_login_exchange():
    """Web：用一次性 token 换取 session 登录态"""
    data = request.json or {}
    token = (data.get("token") or "").strip()
    if not token:
        return jsonify({"status": "error", "message": "缺少token"}), 400

    try:
        token_data = WebLoginService.consume_exchange_token(token)
        user_id = int(token_data["user_id"])
        sid = str(token_data.get("sid") or "")
        user = set_web_session(user_id)
        if sid:
            WebLoginService.mark_exchanged(sid)
        return jsonify({
            "status": "success",
            "data": {
                "user_id": user.get("id"),
                "username": user.get("username"),
            }
        }), 200
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "token无效"}), 404
    except TimeoutError:
        return jsonify({"status": "error", "message": "token已过期"}), 410
    except Exception as e:
        current_app.logger.error(f'扫码登录兑换失败: {e}', exc_info=True)
        return jsonify({"status": "error", "message": "兑换失败"}), 500


@auth_api_bp.route('/wechat/bind_qrcode', methods=['POST'])
@limiter.limit("30 per minute")
def api_wechat_bind_qrcode():
    """Web：账号管理页生成绑定微信二维码（需session登录）"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    try:
        meta = {"ip": request.remote_addr, "ua": request.headers.get("User-Agent", "")}
        sess = WebWechatBindService.create_session(web_user_id=int(uid), meta=meta)
        sess = WebWechatBindService.generate_qrcode_image(sess)
        return jsonify({
            'status': 'success',
            'data': {
                'sid': sess['sid'],
                'expires_at': sess['expires_at'],
                'qrcode_url': sess.get('qrcode_url'),
                'page_used': sess.get('page_used'),
                'page_fallback': bool(sess.get('page_fallback')),
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f'生成绑定微信二维码失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@auth_api_bp.route('/wechat/bind_sessions/<sid>', methods=['GET'])
@limiter.exempt
def api_wechat_bind_session_status(sid: str):
    """Web：轮询绑定微信会话状态（需session登录且只能查询自己的sid）"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    sess_data = WebWechatBindService.get_session(sid)
    if not sess_data:
        return jsonify({'status': 'error', 'message': 'sid不存在'}), 404
    if int(sess_data.get('web_user_id') or 0) != int(uid):
        return jsonify({'status': 'error', 'message': '无权限'}), 403

    return jsonify({
        'status': 'success',
        'data': {
            'sid': sess_data.get('sid'),
            'state': sess_data.get('state'),
            'expires_at': sess_data.get('expires_at'),
            'bound_at': sess_data.get('bound_at'),
        }
    }), 200


@auth_api_bp.route('/wechat/bind_confirm', methods=['POST'])
@limiter.limit("60 per minute")
def api_wechat_bind_confirm():
    """小程序：扫码后确认绑定（不要求JWT，使用 wx.login code 获取 openid）"""
    data = request.json or {}
    sid = (data.get('sid') or '').strip()
    nonce = (data.get('nonce') or '').strip()
    code = (data.get('code') or '').strip()
    if not sid or not nonce or not code:
        return jsonify({'status': 'error', 'message': '缺少参数'}), 400

    wechat_data = WechatAuthService.verify_code(code)
    if wechat_data.get('error'):
        return jsonify({'status': 'error', 'message': wechat_data.get('error') or '微信登录失败'}), 400
    openid = wechat_data.get('openid')
    if not openid:
        return jsonify({'status': 'error', 'message': '微信登录失败：未获取到openid'}), 400

    try:
        WebWechatBindService.confirm_bind(sid=sid, nonce=nonce, openid=str(openid))
        return jsonify({'status': 'success', 'message': '绑定成功'}), 200
    except FileNotFoundError:
        return jsonify({'status': 'error', 'message': 'sid不存在'}), 404
    except TimeoutError:
        return jsonify({'status': 'error', 'message': '会话已过期'}), 410
    except PermissionError:
        return jsonify({'status': 'error', 'message': 'nonce无效'}), 403
    except RuntimeError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 409
    except Exception as e:
        current_app.logger.error(f'确认绑定微信失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '绑定失败'}), 500


@auth_api_bp.route('/wechat/unbind', methods=['POST'])
@limiter.limit("30 per minute")
def api_wechat_unbind():
    """Web：解绑微信（需session登录）"""
    uid = session.get('user_id')
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT openid, session_version FROM users WHERE id = ?',
            (int(uid),)
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404

        old_openid = (row['openid'] or '').strip() if 'openid' in row.keys() else ''
        old_sv = int(row['session_version'] or 0) if 'session_version' in row.keys() else 0

        # 解绑当前用户，并提升会话版本（强制小程序 JWT 失效），但保持 Web 端当前 session 可用
        conn.execute(
            'UPDATE users SET openid = NULL, session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE id = ?',
            (int(uid),)
        )
        # 兼容历史数据可能存在 openid 重复：一并清理，确保该微信可再次绑定/登录
        if old_openid:
            conn.execute(
                'UPDATE users SET openid = NULL, session_version = COALESCE(session_version,0) + 1, last_active = NULL WHERE openid = ?',
                (old_openid,)
            )
        conn.commit()
        session['session_version'] = old_sv + 1
        return jsonify({'status': 'success', 'message': '解绑成功'}), 200
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f'解绑微信失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '解绑失败'}), 500


@auth_api_bp.route('/mini/login', methods=['POST'])
@limiter.limit("60 per minute")
def api_mini_password_login():
    """小程序：账号/邮箱 + 密码 登录（返回JWT，不写session）"""
    data = request.json or {}
    identifier = (data.get('username') or data.get('account') or '').strip()
    password = data.get('password') or ''
    if not identifier or not password:
        return jsonify({'status': 'error', 'message': '账号和密码不能为空'}), 400

    try:
        user = User.verify_password(identifier, password)
        if not user:
            return jsonify({'status': 'error', 'message': '账号或密码错误'}), 403
        if user.get('is_locked'):
            return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403

        openid = str(user.get('openid') or '').strip()
        token = generate_jwt_token(int(user['id']), openid, session_version=int(user.get('session_version') or 0))
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': int(user['id']),
                'token': token,
                'user_info': {
                    'id': int(user['id']),
                    'username': user.get('username'),
                    'avatar': user.get('avatar'),
                    'is_new_user': False,
                    'wechat_bound': bool(openid)
                }
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f'小程序密码登录异常: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '登录失败，请稍后重试'}), 500


@auth_api_bp.route('/mini/email/send-login-code', methods=['POST'])
@limiter.limit("1 per minute;10 per hour")
def api_mini_send_login_code():
    """小程序：发送邮箱登录验证码（支持自动注册）"""
    data = request.json or {}
    email = (data.get('email') or '').strip()
    if not email:
        return jsonify({'status': 'error', 'message': '邮箱不能为空'}), 400
    try:
        success, error_msg = EmailAuthService.send_login_code(email)
        if not success:
            return jsonify({'status': 'error', 'message': error_msg or '发送失败'}), 400
        return jsonify({'status': 'success', 'message': '验证码已发送到邮箱'}), 200
    except Exception as e:
        current_app.logger.error(f'小程序发送登录验证码异常: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '发送失败，请稍后重试'}), 500


@auth_api_bp.route('/mini/email/login', methods=['POST'])
@limiter.limit("60 per minute")
def api_mini_email_login():
    """小程序：邮箱验证码登录（返回JWT，不写session）"""
    data = request.json or {}
    email = (data.get('email') or '').strip()
    code = (data.get('code') or '').strip()
    if not email or not code:
        return jsonify({'status': 'error', 'message': '邮箱和验证码不能为空'}), 400

    try:
        success, error_msg, user_data = EmailAuthService.verify_login_code(email, code)
        if not success or not user_data:
            return jsonify({'status': 'error', 'message': error_msg or '验证码错误或已过期'}), 403
        if user_data.get('is_locked'):
            return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403

        openid = str(user_data.get('openid') or '').strip()
        token = generate_jwt_token(int(user_data['id']), openid, session_version=int(user_data.get('session_version') or 0))
        return jsonify({
            'status': 'success',
            'data': {
                'user_id': int(user_data['id']),
                'token': token,
                'user_info': {
                    'id': int(user_data['id']),
                    'username': user_data.get('username'),
                    'avatar': user_data.get('avatar'),
                    'is_new_user': bool(user_data.get('is_new_user', False)),
                    'wechat_bound': bool(openid)
                }
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f'小程序邮箱验证码登录异常: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '登录失败，请稍后重试'}), 500


@auth_api_bp.route('/mini/wechat/bind', methods=['POST'])
@jwt_required
@limiter.limit("60 per minute")
def api_mini_wechat_bind():
    """小程序：已登录用户绑定微信（密码/邮箱登录后弹窗绑定）"""
    from flask import g

    data = request.json or {}
    code = (data.get('code') or '').strip()
    if not code:
        return jsonify({'status': 'error', 'message': '缺少code'}), 400

    wechat_data = WechatAuthService.verify_code(code)
    if wechat_data.get('error'):
        return jsonify({'status': 'error', 'message': wechat_data.get('error') or '微信登录失败'}), 400

    openid = str(wechat_data.get('openid') or '').strip()
    if not openid:
        return jsonify({'status': 'error', 'message': '微信登录失败：未获取到openid'}), 400

    uid = int(getattr(g, 'current_user_id', 0) or 0)
    if not uid:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    conn = get_db()
    try:
        row = conn.execute(
            'SELECT id, username, avatar, is_locked, session_version, openid FROM users WHERE id = ?',
            (uid,)
        ).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        user = dict(row)

        if int(user.get('is_locked') or 0) == 1:
            return jsonify({'status': 'error', 'message': '账户已被锁定，请联系管理员'}), 403

        existing_openid = str(user.get('openid') or '').strip()
        if existing_openid:
            # 已绑定：如果绑定的是同一个微信，直接返回成功；否则提示先解绑
            if existing_openid != openid:
                return jsonify({'status': 'error', 'message': '该账号已绑定其他微信，如需更换请先解绑'}), 409

            token = generate_jwt_token(uid, existing_openid, session_version=int(user.get('session_version') or 0))
            return jsonify({
                'status': 'success',
                'data': {
                    'token': token,
                    'user_info': {
                        'id': uid,
                        'username': user.get('username'),
                        'avatar': user.get('avatar'),
                        'wechat_bound': True,
                    }
                }
            }), 200

        # 防止 openid 被重复绑定
        existing = conn.execute('SELECT id FROM users WHERE openid = ? LIMIT 1', (openid,)).fetchone()
        if existing and int(existing['id']) != uid:
            return jsonify({'status': 'error', 'message': '该微信已绑定其他账号'}), 409

        try:
            conn.execute('UPDATE users SET openid = ? WHERE id = ?', (openid, uid))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return jsonify({'status': 'error', 'message': '该微信已绑定其他账号'}), 409

        # 绑定完成后返回包含 openid 的新 JWT（便于后续强制下线校验）
        refreshed = User.get_by_id(uid) or user
        token = generate_jwt_token(uid, openid, session_version=int(refreshed.get('session_version') or 0))
        return jsonify({
            'status': 'success',
            'data': {
                'token': token,
                'user_info': {
                    'id': uid,
                    'username': refreshed.get('username'),
                    'avatar': refreshed.get('avatar'),
                    'wechat_bound': True,
                }
            }
        }), 200
    except Exception as e:
        conn.rollback()
        current_app.logger.error(f'小程序绑定微信失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': '绑定失败，请稍后重试'}), 500
