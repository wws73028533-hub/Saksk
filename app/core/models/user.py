# -*- coding: utf-8 -*-
"""
用户模型
"""
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from ..utils.database import get_db


class User:
    """用户模型"""
    
    @staticmethod
    def create(username, password, is_admin=False):
        """创建用户"""
        conn = get_db()
        password_hash = generate_password_hash(password)
        
        # 检查是否是第一个用户（自动成为管理员）
        count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        if count == 0:
            is_admin = True
        
        conn.execute(
            'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
            (username, password_hash, 1 if is_admin else 0)
        )
        conn.commit()
        return User.get_by_username(username)
    
    @staticmethod
    def get_by_id(user_id):
        """通过ID获取用户"""
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_username(username):
        """通过用户名获取用户"""
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        return dict(row) if row else None
    
    @staticmethod
    def verify_password(identifier: str, password: str) -> Optional[dict]:
        """
        验证密码（支持用户名或邮箱）
        
        Args:
            identifier: 用户名或邮箱
            password: 密码
            
        Returns:
            用户信息字典，如果验证失败返回None
        """
        if not identifier or not password:
            return None
        
        conn = get_db()
        
        # 判断是邮箱还是用户名（简单判断：包含@符号）
        if '@' in identifier:
            # 使用邮箱查询
            row = conn.execute(
                'SELECT * FROM users WHERE email = ?', (identifier,)
            ).fetchone()
        else:
            # 使用用户名查询
            row = conn.execute(
                'SELECT * FROM users WHERE username = ?', (identifier,)
            ).fetchone()
        
        if not row:
            return None
        
        user = dict(row)
        if not check_password_hash(user['password_hash'], password):
            return None
        
        return user
    
    @staticmethod
    def update_password(user_id, new_password):
        """更新密码"""
        conn = get_db()
        password_hash = generate_password_hash(new_password)
        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (password_hash, user_id)
        )
        conn.commit()
    
    @staticmethod
    def update_profile(user_id, avatar=None, contact=None, college=None):
        """更新用户资料"""
        conn = get_db()
        updates = []
        params = []
        
        if avatar is not None:
            updates.append('avatar = ?')
            params.append(avatar)
        if contact is not None:
            updates.append('contact = ?')
            params.append(contact)
        if college is not None:
            updates.append('college = ?')
            params.append(college)
        
        if updates:
            params.append(user_id)
            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            conn.execute(sql, params)
            conn.commit()
        
        return User.get_by_id(user_id)
    
    @staticmethod
    def get_all(search='', page=1, size=10, sort='created_at', order='desc'):
        """获取所有用户（分页）"""
        conn = get_db()
        offset = (page - 1) * size
        
        where = 'WHERE 1=1'
        params = []
        if search:
            where += ' AND username LIKE ?'
            params.append(f'%{search}%')
        
        # 验证排序字段
        allowed_sorts = {'created_at', 'username', 'id'}
        if sort not in allowed_sorts:
            sort = 'created_at'
        if order not in ('asc', 'desc'):
            order = 'desc'
        
        # 获取总数
        total = conn.execute(
            f'SELECT COUNT(*) FROM users {where}', params
        ).fetchone()[0]
        
        # 获取数据
        rows = conn.execute(
            f'SELECT id, username, is_admin, is_locked, created_at FROM users {where} ORDER BY {sort} {order} LIMIT ? OFFSET ?',
            params + [size, offset]
        ).fetchall()
        
        return {
            'data': [dict(row) for row in rows],
            'total': total
        }
    
    @staticmethod
    def get_by_email(email: str) -> Optional[dict]:
        """通过邮箱获取用户"""
        if not email:
            return None
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        return dict(row) if row else None
    
    @staticmethod
    def bind_email(user_id: int, email: str) -> Optional[dict]:
        """绑定邮箱到用户账户"""
        conn = get_db()
        try:
            # 检查邮箱是否已被其他用户使用
            existing = conn.execute(
                'SELECT id FROM users WHERE email = ? AND id != ?',
                (email, user_id)
            ).fetchone()
            if existing:
                return None  # 邮箱已被使用
            
            from datetime import datetime
            # 更新用户邮箱信息
            conn.execute(
                '''UPDATE users 
                   SET email = ?, email_verified = 1, email_verified_at = ?
                   WHERE id = ?''',
                (email, datetime.now(), user_id)
            )
            conn.commit()
            return User.get_by_id(user_id)
        except Exception:
            conn.rollback()
            return None
    
    @staticmethod
    def update_email_verified(user_id: int, verified: bool = True) -> Optional[dict]:
        """更新邮箱验证状态"""
        conn = get_db()
        try:
            from datetime import datetime
            if verified:
                conn.execute(
                    '''UPDATE users 
                       SET email_verified = 1, email_verified_at = ?
                       WHERE id = ?''',
                    (datetime.now(), user_id)
                )
            else:
                conn.execute(
                    'UPDATE users SET email_verified = 0, email_verified_at = NULL WHERE id = ?',
                    (user_id,)
                )
            conn.commit()
            return User.get_by_id(user_id)
        except Exception:
            conn.rollback()
            return None
    
    @staticmethod
    def is_email_available(email: str, exclude_user_id: Optional[int] = None) -> bool:
        """检查邮箱是否可用（未被其他用户使用）"""
        if not email:
            return False
        conn = get_db()
        if exclude_user_id:
            row = conn.execute(
                'SELECT id FROM users WHERE email = ? AND id != ?',
                (email, exclude_user_id)
            ).fetchone()
        else:
            row = conn.execute(
                'SELECT id FROM users WHERE email = ?',
                (email,)
            ).fetchone()
        return row is None

