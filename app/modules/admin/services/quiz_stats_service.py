# -*- coding: utf-8 -*-
"""
刷题统计管理服务
"""
from typing import Dict, Any, List, Optional
from app.core.utils.database import get_db
from app.core.utils.subject_permissions import (
    get_user_quiz_count,
    get_quiz_limit_count,
    is_quiz_limit_enabled
)


class QuizStatsService:
    """刷题统计管理服务类"""
    
    @staticmethod
    def get_user_quiz_stats(user_id: int) -> Dict[str, Any]:
        """
        获取用户刷题统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户刷题统计字典
        """
        conn = get_db()
        
        # 获取用户信息
        user = conn.execute(
            'SELECT id, username, is_admin FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        
        # 获取刷题统计
        stats = conn.execute(
            'SELECT total_answered, last_reset_at, updated_at FROM user_quiz_stats WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        
        current_count = stats['total_answered'] if stats else 0
        limit_count = get_quiz_limit_count()
        is_enabled = is_quiz_limit_enabled()
        
        return {
            'user': {
                'id': user['id'],
                'username': user['username'],
                'is_admin': bool(user['is_admin'])
            },
            'stats': {
                'total_answered': current_count,
                'limit_count': limit_count,
                'remaining': max(0, limit_count - current_count) if is_enabled else None,
                'is_limit_enabled': is_enabled,
                'last_reset_at': stats['last_reset_at'] if stats else None,
                'updated_at': stats['updated_at'] if stats else None
            }
        }
    
    @staticmethod
    def reset_user_quiz_count(user_id: int) -> None:
        """
        重置用户刷题数
        
        Args:
            user_id: 用户ID
        """
        from app.core.utils.subject_permissions import reset_user_quiz_count
        reset_user_quiz_count(user_id)
    
    @staticmethod
    def batch_reset_quiz_count(user_ids: List[int]) -> Dict[str, Any]:
        """
        批量重置用户刷题数
        
        Args:
            user_ids: 用户ID列表
            
        Returns:
            操作结果字典
        """
        success_count = 0
        
        for user_id in user_ids:
            try:
                QuizStatsService.reset_user_quiz_count(user_id)
                success_count += 1
            except Exception:
                continue
        
        return {
            'success_count': success_count,
            'total_count': len(user_ids),
            'message': f'成功重置 {success_count} 个用户的刷题数'
        }





