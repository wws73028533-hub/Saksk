# -*- coding: utf-8 -*-
"""
邮箱认证业务逻辑服务
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from flask import current_app
from app.core.models.user import User
from app.core.utils.email_service import EmailService
from app.core.utils.database import get_db


class EmailAuthService:
    """邮箱认证服务类"""
    
    # 验证码有效期（分钟）
    CODE_EXPIRE_MINUTES = 10
    # 验证码错误次数限制
    MAX_VERIFY_ATTEMPTS = 5
    
    @staticmethod
    def send_bind_code(user_id: int, email: str) -> Tuple[bool, Optional[str]]:
        """
        发送绑定邮箱验证码
        
        Args:
            user_id: 用户ID
            email: 邮箱地址
            
        Returns:
            (是否成功, 错误消息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确'
        
        # 检查邮箱是否已被其他用户使用
        if not User.is_email_available(email, exclude_user_id=user_id):
            return False, '邮箱已被其他用户使用'
        
        # 检查发送频率（1分钟内只能发送1次）
        conn = get_db()
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        recent_count = conn.execute(
            '''SELECT COUNT(*) FROM email_verification_codes
               WHERE email = ? AND code_type = 'bind' AND created_at > ?''',
            (email, one_minute_ago)
        ).fetchone()[0]
        
        if recent_count > 0:
            return False, '发送验证码过于频繁，请稍后再试'
        
        # 检查用户发送频率（1小时内最多5次）
        one_hour_ago = datetime.now() - timedelta(hours=1)
        user_recent_count = conn.execute(
            '''SELECT COUNT(*) FROM email_verification_codes
               WHERE user_id = ? AND code_type = 'bind' AND created_at > ?''',
            (user_id, one_hour_ago)
        ).fetchone()[0]
        
        if user_recent_count >= 5:
            return False, '发送验证码次数过多，请稍后再试'
        
        # 生成并发送验证码
        code = EmailService.generate_verification_code()
        success, sent_code = EmailService.send_verification_code(
            to_email=email,
            code_type='bind',
            code=code
        )
        
        if not success:
            return False, '邮件发送失败，请稍后再试'
        
        # 保存验证码到数据库
        try:
            expires_at = datetime.now() + timedelta(minutes=EmailAuthService.CODE_EXPIRE_MINUTES)
            conn.execute(
                '''INSERT INTO email_verification_codes
                   (email, code, code_type, user_id, expires_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (email, code, 'bind', user_id, expires_at)
            )
            conn.commit()
            
            current_app.logger.info(f'绑定邮箱验证码已发送: user_id={user_id}, email={email}')
            return True, None
            
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'保存验证码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试'
    
    @staticmethod
    def bind_email(user_id: int, email: str, code: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        绑定邮箱
        
        Args:
            user_id: 用户ID
            email: 邮箱地址
            code: 验证码
            
        Returns:
            (是否成功, 错误消息, 用户信息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确', None
        
        # 检查邮箱是否已被其他用户使用
        if not User.is_email_available(email, exclude_user_id=user_id):
            return False, '邮箱已被其他用户使用', None
        
        # 验证验证码
        conn = get_db()
        now = datetime.now()
        
        # 查找有效的验证码
        code_record = conn.execute(
            '''SELECT * FROM email_verification_codes
               WHERE email = ? AND code = ? AND code_type = 'bind'
                 AND user_id = ? AND is_used = 0 AND expires_at > ?
               ORDER BY created_at DESC
               LIMIT 1''',
            (email, code, user_id, now)
        ).fetchone()
        
        if not code_record:
            # 检查是否验证码错误次数过多
            recent_attempts = conn.execute(
                '''SELECT COUNT(*) FROM email_verification_codes
                   WHERE email = ? AND code_type = 'bind' AND user_id = ?
                     AND created_at > ? AND is_used = 0''',
                (email, user_id, datetime.now() - timedelta(minutes=10))
            ).fetchone()[0]
            
            if recent_attempts >= EmailAuthService.MAX_VERIFY_ATTEMPTS:
                return False, '验证码错误次数过多，请重新发送验证码', None
            
            return False, '验证码错误或已过期', None
        
        # 标记验证码为已使用
        try:
            conn.execute(
                '''UPDATE email_verification_codes
                   SET is_used = 1, used_at = ?
                   WHERE id = ?''',
                (now, code_record['id'])
            )
            
            # 绑定邮箱
            user = User.bind_email(user_id, email)
            if not user:
                conn.rollback()
                return False, '绑定邮箱失败', None
            
            conn.commit()
            
            current_app.logger.info(f'邮箱绑定成功: user_id={user_id}, email={email}')
            
            return True, None, {
                'email': user['email'],
                'email_verified': bool(user.get('email_verified', 0))
            }
            
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'绑定邮箱失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试', None
    
    @staticmethod
    def send_login_code(email: str) -> Tuple[bool, Optional[str]]:
        """
        发送登录验证码（支持自动注册）
        
        Args:
            email: 邮箱地址
            
        Returns:
            (是否成功, 错误消息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确'
        
        # 检查邮箱是否已绑定（未绑定也可以发送验证码，用于自动注册）
        user = User.get_by_email(email)
        user_id = user['id'] if user else None
        
        # 检查发送频率（1分钟内只能发送1次）
        conn = get_db()
        one_minute_ago = datetime.now() - timedelta(minutes=1)
        recent_count = conn.execute(
            '''SELECT COUNT(*) FROM email_verification_codes
               WHERE email = ? AND code_type = 'login' AND created_at > ?''',
            (email, one_minute_ago)
        ).fetchone()[0]
        
        if recent_count > 0:
            return False, '发送验证码过于频繁，请稍后再试'
        
        # 生成并发送验证码
        code = EmailService.generate_verification_code()
        success, sent_code = EmailService.send_verification_code(
            to_email=email,
            code_type='login',
            code=code
        )
        
        if not success:
            return False, '邮件发送失败，请稍后再试'
        
        # 保存验证码到数据库（user_id可以为None，表示用于自动注册）
        try:
            expires_at = datetime.now() + timedelta(minutes=EmailAuthService.CODE_EXPIRE_MINUTES)
            conn.execute(
                '''INSERT INTO email_verification_codes
                   (email, code, code_type, user_id, expires_at)
                   VALUES (?, ?, ?, ?, ?)''',
                (email, code, 'login', user_id, expires_at)
            )
            conn.commit()
            
            if user:
                current_app.logger.info(f'登录验证码已发送: email={email}, user_id={user_id}')
            else:
                current_app.logger.info(f'注册验证码已发送: email={email} (新用户)')
            return True, None
            
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'保存验证码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试'
    
    @staticmethod
    def verify_login_code(email: str, code: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        验证登录验证码（支持自动注册）
        
        Args:
            email: 邮箱地址
            code: 验证码
            
        Returns:
            (是否成功, 错误消息, 用户信息) 元组
        """
        # 验证邮箱格式
        if not EmailService.validate_email_format(email):
            return False, '邮箱格式不正确', None
        
        # 验证验证码
        conn = get_db()
        now = datetime.now()
        
        # 查找有效的验证码（user_id可以为None，用于自动注册）
        code_record = conn.execute(
            '''SELECT * FROM email_verification_codes
               WHERE email = ? AND code = ? AND code_type = 'login'
                 AND is_used = 0 AND expires_at > ?
               ORDER BY created_at DESC
               LIMIT 1''',
            (email, code, now)
        ).fetchone()
        
        if not code_record:
            # 检查是否验证码错误次数过多
            recent_attempts = conn.execute(
                '''SELECT COUNT(*) FROM email_verification_codes
                   WHERE email = ? AND code_type = 'login'
                     AND created_at > ? AND is_used = 0''',
                (email, datetime.now() - timedelta(minutes=10))
            ).fetchone()[0]
            
            if recent_attempts >= EmailAuthService.MAX_VERIFY_ATTEMPTS:
                return False, '验证码错误次数过多，请重新发送验证码', None
            
            return False, '验证码错误或已过期', None
        
        # 标记验证码为已使用
        try:
            conn.execute(
                '''UPDATE email_verification_codes
                   SET is_used = 1, used_at = ?
                   WHERE id = ?''',
                (now, code_record['id'])
            )
            
            # 检查用户是否存在
            user = User.get_by_email(email)
            
            if not user:
                # 自动注册：创建新用户
                # 从邮箱生成用户名（使用邮箱前缀，如果冲突则添加数字）
                email_prefix = email.split('@')[0]
                username = email_prefix
                counter = 1
                
                # 确保用户名唯一
                while User.get_by_username(username):
                    username = f"{email_prefix}{counter}"
                    counter += 1
                
                # 创建用户（不需要密码，因为使用验证码登录）
                # 生成一个随机密码（用户不会用到，但数据库字段需要）
                import secrets
                import string
                random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
                
                # 检查是否是第一个用户（自动成为管理员）
                count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
                is_admin = 1 if count == 0 else 0
                
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(random_password)
                
                # 插入用户，同时绑定邮箱
                conn.execute(
                    '''INSERT INTO users (username, password_hash, email, email_verified, email_verified_at, is_admin)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (username, password_hash, email, 1, now, is_admin)
                )
                conn.commit()
                
                # 获取新创建的用户
                user = User.get_by_email(email)
                current_app.logger.info(f'自动注册成功: email={email}, username={username}, user_id={user["id"]}')
            else:
                # 检查账户是否锁定
                if user.get('is_locked'):
                    conn.rollback()
                    return False, '账户已被锁定，请联系管理员', None
                
                current_app.logger.info(f'验证码登录成功: email={email}, user_id={user["id"]}')
            
            conn.commit()
            return True, None, user
            
        except Exception as e:
            conn.rollback()
            current_app.logger.error(f'验证登录验证码失败: {str(e)}', exc_info=True)
            return False, '系统错误，请稍后再试', None

