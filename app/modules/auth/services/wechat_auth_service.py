# -*- coding: utf-8 -*-
"""
微信认证服务
负责微信登录相关的业务逻辑
"""
import requests
import json
from typing import Dict, Any, Optional
from flask import current_app
from app.core.utils.database import get_db
from app.core.models.user import User


class WechatAuthService:
    """微信认证服务"""
    
    @staticmethod
    def verify_code(code: str) -> Dict[str, Any]:
        """
        验证微信code，返回openid和session_key
        
        Args:
            code: 微信登录code
        
        Returns:
            包含openid和session_key的字典，如果失败返回错误信息
        """
        # 从配置或环境变量获取微信小程序配置
        appid = current_app.config.get('WECHAT_APPID') or current_app.config.get('WX_APPID')
        secret = current_app.config.get('WECHAT_SECRET') or current_app.config.get('WX_SECRET')
        
        if not appid or not secret:
            current_app.logger.error('微信小程序配置缺失：WECHAT_APPID 或 WECHAT_SECRET')
            return {'error': '微信小程序配置缺失'}
        
        # 调用微信API
        url = 'https://api.weixin.qq.com/sns/jscode2session'
        params = {
            'appid': appid,
            'secret': secret,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            # 检查是否有错误
            if 'errcode' in data:
                current_app.logger.warning(f'微信登录失败: {data.get("errmsg", "未知错误")}, errcode: {data.get("errcode")}')
                return {'error': data.get('errmsg', '微信登录失败')}
            
            # 返回openid和session_key
            return {
                'openid': data.get('openid'),
                'session_key': data.get('session_key'),
                'unionid': data.get('unionid')  # 可选，需要开放平台
            }
        except requests.RequestException as e:
            current_app.logger.error(f'微信API请求失败: {str(e)}')
            return {'error': '网络请求失败，请稍后重试'}
        except Exception as e:
            current_app.logger.error(f'微信登录异常: {str(e)}')
            return {'error': '微信登录失败'}
    
    @staticmethod
    def get_or_create_user(openid: str, user_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        根据openid获取或创建用户
        
        Args:
            openid: 微信openid
            user_info: 微信用户信息（可选，包含nickName、avatarUrl等）
        
        Returns:
            用户信息字典，包含is_new_user字段表示是否为新用户
        """
        if not openid:
            raise ValueError('openid不能为空')
        
        conn = get_db()
        
        # 先查找是否已存在该openid的用户
        row = conn.execute(
            'SELECT * FROM users WHERE openid = ?', (openid,)
        ).fetchone()
        
        if row:
            # 用户已存在，更新用户信息（如果需要）
            user = dict(row)
            is_new_user = False
            
            # 如果提供了用户信息，可以更新头像和昵称（可选）
            if user_info:
                updates = []
                params = []
                
                # 更新头像（如果提供）
                if user_info.get('avatarUrl') and not user.get('avatar'):
                    updates.append('avatar = ?')
                    params.append(user_info.get('avatarUrl'))
                
                # 更新用户名（如果为空或默认用户名）
                if user_info.get('nickName') and (not user.get('username') or user.get('username', '').startswith('微信用户_')):
                    # 检查用户名是否已被占用
                    existing = conn.execute(
                        'SELECT id FROM users WHERE username = ? AND id != ?',
                        (user_info.get('nickName'), user['id'])
                    ).fetchone()
                    if not existing:
                        updates.append('username = ?')
                        params.append(user_info.get('nickName'))
                
                if updates:
                    params.append(user['id'])
                    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                    conn.execute(sql, params)
                    conn.commit()
                    # 重新获取用户信息
                    row = conn.execute('SELECT * FROM users WHERE id = ?', (user['id'],)).fetchone()
                    user = dict(row)
            
            user['is_new_user'] = False
            return user
        else:
            # 新用户，创建账户
            username = user_info.get('nickName') if user_info and user_info.get('nickName') else f'微信用户_{openid[-6:]}'
            
            # 检查用户名是否已被占用
            existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            if existing:
                # 如果用户名被占用，添加后缀
                counter = 1
                while True:
                    new_username = f'{username}_{counter}'
                    existing = conn.execute('SELECT id FROM users WHERE username = ?', (new_username,)).fetchone()
                    if not existing:
                        username = new_username
                        break
                    counter += 1
            
            # 创建新用户
            avatar = user_info.get('avatarUrl') if user_info else None
            
            # 新用户不需要password_hash（微信登录不需要密码）
            conn.execute(
                '''INSERT INTO users (username, openid, avatar, password_hash, has_password_set)
                   VALUES (?, ?, ?, ?, ?)''',
                (username, openid, avatar, '', 0)
            )
            conn.commit()
            
            # 获取新创建的用户
            row = conn.execute('SELECT * FROM users WHERE openid = ?', (openid,)).fetchone()
            user = dict(row)
            user['is_new_user'] = True
            
            current_app.logger.info(f'新用户注册: {username} (openid: {openid})')
            return user

