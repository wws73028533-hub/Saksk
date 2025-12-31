# -*- coding: utf-8 -*-
"""弹窗业务逻辑服务"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.utils.database import get_db
from app.modules.popups.schemas import PopupResponseSchema, PopupStatsSchema


class PopupService:
    """弹窗服务类"""
    
    @staticmethod
    def _now_expr() -> str:
        """SQLite 当前时间表达式"""
        return "CURRENT_TIMESTAMP"
    
    @staticmethod
    def get_active_popups_for_user(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用户应显示的活跃弹窗列表（支持轮播/队列）
        
        Args:
            user_id: 用户ID
            limit: 返回的最大数量（用于轮播）
        
        Returns:
            弹窗列表，按优先级降序排列
        """
        conn = get_db()
        
        # 查询活跃的弹窗，排除用户已关闭的
        rows = conn.execute(
            f"""
            SELECT
                p.id, p.title, p.content, p.popup_type, p.priority,
                p.start_at, p.end_at, p.created_at
            FROM popups p
            LEFT JOIN popup_dismissals d
                ON d.popup_id = p.id AND d.user_id = ?
            WHERE p.is_active = 1
                AND d.id IS NULL
                AND (p.start_at IS NULL OR datetime(p.start_at) <= datetime({PopupService._now_expr()}))
                AND (p.end_at IS NULL OR datetime(p.end_at) >= datetime({PopupService._now_expr()}))
            ORDER BY p.priority DESC, p.created_at DESC, p.id DESC
            LIMIT ?
            """,
            (user_id, limit)
        ).fetchall()
        
        return [dict(row) for row in rows]
    
    @staticmethod
    def record_popup_view(popup_id: int, user_id: Optional[int] = None) -> None:
        """
        记录弹窗显示次数（用于统计）
        
        Args:
            popup_id: 弹窗ID
            user_id: 用户ID（可选，匿名用户为None）
        """
        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO popup_views (popup_id, user_id) VALUES (?, ?)',
                (popup_id, user_id)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            # 记录错误但不影响主流程
            import traceback
            from flask import current_app
            current_app.logger.error(f'记录弹窗显示失败: {str(e)}\n{traceback.format_exc()}')
    
    @staticmethod
    def dismiss_popup(popup_id: int, user_id: int) -> bool:
        """
        关闭弹窗（记录到popup_dismissals，用户将不再看到该弹窗）
        
        Args:
            popup_id: 弹窗ID
            user_id: 用户ID
        
        Returns:
            是否成功
        """
        conn = get_db()
        try:
            # 使用 INSERT OR IGNORE 避免重复插入
            conn.execute(
                'INSERT OR IGNORE INTO popup_dismissals (user_id, popup_id) VALUES (?, ?)',
                (user_id, popup_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            import traceback
            from flask import current_app
            current_app.logger.error(f'关闭弹窗失败: {str(e)}\n{traceback.format_exc()}')
            return False
    
    @staticmethod
    def get_popup_stats(popup_id: int) -> Optional[Dict[str, Any]]:
        """
        获取弹窗统计信息
        
        Args:
            popup_id: 弹窗ID
        
        Returns:
            统计信息字典，包含总显示次数、总关闭次数、关闭率
        """
        conn = get_db()
        
        # 检查弹窗是否存在
        popup = conn.execute('SELECT id FROM popups WHERE id = ?', (popup_id,)).fetchone()
        if not popup:
            return None
        
        # 统计显示次数
        view_count = conn.execute(
            'SELECT COUNT(*) FROM popup_views WHERE popup_id = ?',
            (popup_id,)
        ).fetchone()[0]
        
        # 统计关闭次数
        dismissal_count = conn.execute(
            'SELECT COUNT(*) FROM popup_dismissals WHERE popup_id = ?',
            (popup_id,)
        ).fetchone()[0]
        
        # 计算关闭率
        dismissal_rate = dismissal_count / view_count if view_count > 0 else 0.0
        
        return {
            'popup_id': popup_id,
            'total_views': view_count,
            'total_dismissals': dismissal_count,
            'dismissal_rate': round(dismissal_rate, 4)
        }
    
    @staticmethod
    def get_all_popups_stats() -> List[Dict[str, Any]]:
        """
        获取所有弹窗的统计信息
        
        Returns:
            统计信息列表
        """
        conn = get_db()
        
        # 获取所有弹窗
        popups = conn.execute('SELECT id FROM popups ORDER BY id DESC').fetchall()
        
        stats_list = []
        for popup in popups:
            stats = PopupService.get_popup_stats(popup['id'])
            if stats:
                stats_list.append(stats)
        
        return stats_list


