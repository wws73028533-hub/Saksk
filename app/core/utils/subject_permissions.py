# -*- coding: utf-8 -*-
"""
科目权限检查工具函数（黑名单模式）
"""
from typing import List, Tuple, Optional
from app.core.utils.database import get_db


def is_admin(user_id: int) -> bool:
    """检查用户是否是管理员"""
    conn = get_db()
    user = conn.execute(
        'SELECT is_admin FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    return bool(user and user['is_admin']) if user else False


def get_user_restricted_subjects(user_id: int) -> List[int]:
    """
    获取用户被限制的科目ID列表（黑名单）
    
    Args:
        user_id: 用户ID
        
    Returns:
        被限制的科目ID列表
    """
    # 管理员无限制
    if is_admin(user_id):
        return []
    
    conn = get_db()
    rows = conn.execute(
        'SELECT subject_id FROM user_subjects WHERE user_id = ?',
        (user_id,)
    ).fetchall()
    
    return [row['subject_id'] for row in rows]


def can_user_access_subject(user_id: int, subject_id: int) -> bool:
    """
    检查用户是否可以访问指定科目（黑名单模式）
    
    Args:
        user_id: 用户ID
        subject_id: 科目ID
        
    Returns:
        True 如果用户可以访问，False 如果被限制
    """
    # 管理员可以访问所有科目
    if is_admin(user_id):
        return True
    
    # 检查是否在黑名单中
    conn = get_db()
    restricted = conn.execute(
        'SELECT id FROM user_subjects WHERE user_id = ? AND subject_id = ?',
        (user_id, subject_id)
    ).fetchone()
    
    # 如果在黑名单中，返回 False；否则返回 True（默认有权限）
    return restricted is None


def get_user_accessible_subjects(user_id: int) -> List[int]:
    """
    获取用户可访问的科目ID列表（黑名单模式）
    
    Args:
        user_id: 用户ID
        
    Returns:
        可访问的科目ID列表
    """
    # 管理员可以访问所有科目
    if is_admin(user_id):
        conn = get_db()
        rows = conn.execute('SELECT id FROM subjects').fetchall()
        return [row['id'] for row in rows]
    
    # 普通用户：所有科目 - 被限制的科目
    conn = get_db()
    all_subjects = conn.execute('SELECT id FROM subjects').fetchall()
    all_subject_ids = [row['id'] for row in all_subjects]
    
    restricted_ids = get_user_restricted_subjects(user_id)
    accessible_ids = [sid for sid in all_subject_ids if sid not in restricted_ids]
    
    return accessible_ids


def filter_subjects_by_permission(user_id: Optional[int], subject_ids: List[int]) -> List[int]:
    """
    根据用户权限过滤科目ID列表
    
    Args:
        user_id: 用户ID（None 表示未登录用户）
        subject_ids: 科目ID列表
        
    Returns:
        过滤后的科目ID列表
    """
    if user_id is None:
        # 未登录用户：返回空列表（需要登录才能访问）
        return []
    
    # 管理员可以访问所有科目
    if is_admin(user_id):
        return subject_ids
    
    # 普通用户：过滤掉被限制的科目
    restricted_ids = get_user_restricted_subjects(user_id)
    return [sid for sid in subject_ids if sid not in restricted_ids]


def is_quiz_limit_enabled() -> bool:
    """
    检查刷题数限制功能是否开启
    
    Returns:
        True 如果功能开启，False 如果关闭
    """
    conn = get_db()
    config = conn.execute(
        'SELECT config_value FROM system_config WHERE config_key = ?',
        ('quiz_limit_enabled',)
    ).fetchone()
    
    if not config:
        return False
    
    return config['config_value'] == '1'


def get_quiz_limit_count() -> int:
    """
    获取刷题数限制数量
    
    Returns:
        限制数量（默认100）
    """
    conn = get_db()
    config = conn.execute(
        'SELECT config_value FROM system_config WHERE config_key = ?',
        ('quiz_limit_count',)
    ).fetchone()
    
    if not config:
        return 100
    
    try:
        return int(config['config_value'])
    except (ValueError, TypeError):
        return 100


def get_user_quiz_count(user_id: int) -> int:
    """
    获取用户当前刷题数
    
    Args:
        user_id: 用户ID
        
    Returns:
        当前刷题数
    """
    conn = get_db()
    stats = conn.execute(
        'SELECT total_answered FROM user_quiz_stats WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    return stats['total_answered'] if stats else 0


def check_quiz_limit(user_id: int) -> Tuple[bool, str]:
    """
    检查用户是否达到刷题限制
    
    Args:
        user_id: 用户ID
        
    Returns:
        (是否达到限制, 提示信息)
        如果功能关闭或用户是管理员/VIP，返回 (False, "")
        如果达到限制，返回 (True, "提示信息")
    """
    # 功能未开启，不限制
    if not is_quiz_limit_enabled():
        return False, ""
    
    # 管理员不受限制（后续可扩展VIP）
    if is_admin(user_id):
        return False, ""
    
    # 检查刷题数
    current_count = get_user_quiz_count(user_id)
    limit_count = get_quiz_limit_count()
    
    if current_count >= limit_count:
        message = f"已达到刷题限制（{limit_count}题），请付费或联系管理员"
        return True, message
    
    return False, ""


def increment_user_quiz_count(user_id: int) -> None:
    """
    增加用户刷题数（仅在功能开启时增加）
    
    Args:
        user_id: 用户ID
    """
    # 如果功能未开启，不增加计数
    if not is_quiz_limit_enabled():
        return
    
    # 管理员不增加计数（因为管理员不受限制）
    if is_admin(user_id):
        return
    
    conn = get_db()
    
    # 检查是否已存在统计记录
    existing = conn.execute(
        'SELECT id FROM user_quiz_stats WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    if existing:
        # 更新现有记录
        conn.execute(
            '''UPDATE user_quiz_stats 
               SET total_answered = total_answered + 1,
                   updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?''',
            (user_id,)
        )
    else:
        # 创建新记录
        conn.execute(
            '''INSERT INTO user_quiz_stats (user_id, total_answered)
               VALUES (?, 1)''',
            (user_id,)
        )
    
    conn.commit()


def reset_user_quiz_count(user_id: int) -> None:
    """
    重置用户刷题数
    
    Args:
        user_id: 用户ID
    """
    conn = get_db()
    
    existing = conn.execute(
        'SELECT id FROM user_quiz_stats WHERE user_id = ?',
        (user_id,)
    ).fetchone()
    
    if existing:
        conn.execute(
            '''UPDATE user_quiz_stats 
               SET total_answered = 0,
                   last_reset_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?''',
            (user_id,)
        )
    else:
        conn.execute(
            '''INSERT INTO user_quiz_stats (user_id, total_answered, last_reset_at)
               VALUES (?, 0, CURRENT_TIMESTAMP)''',
            (user_id,)
        )
    
    conn.commit()





