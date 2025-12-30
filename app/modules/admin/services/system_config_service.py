# -*- coding: utf-8 -*-
"""
系统配置管理服务
"""
from typing import Dict, Any, List, Optional
from app.core.utils.database import get_db


class SystemConfigService:
    """系统配置管理服务类"""
    
    @staticmethod
    def get_all_configs() -> List[Dict[str, Any]]:
        """
        获取所有系统配置
        
        Returns:
            配置列表
        """
        conn = get_db()
        rows = conn.execute(
            'SELECT * FROM system_config ORDER BY config_key'
        ).fetchall()
        
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_config(config_key: str) -> Optional[Dict[str, Any]]:
        """
        获取指定配置
        
        Args:
            config_key: 配置键
            
        Returns:
            配置字典，如果不存在返回None
        """
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM system_config WHERE config_key = ?',
            (config_key,)
        ).fetchone()
        
        return dict(row) if row else None
    
    @staticmethod
    def update_config(
        config_key: str,
        config_value: str,
        description: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        更新系统配置
        
        Args:
            config_key: 配置键
            config_value: 配置值
            description: 配置说明（可选）
            admin_id: 操作的管理员ID（可选）
            
        Returns:
            更新后的配置字典
        """
        conn = get_db()
        
        # 检查配置是否存在
        existing = conn.execute(
            'SELECT id FROM system_config WHERE config_key = ?',
            (config_key,)
        ).fetchone()
        
        if existing:
            # 更新现有配置
            if description:
                conn.execute(
                    '''UPDATE system_config 
                       SET config_value = ?, description = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                       WHERE config_key = ?''',
                    (config_value, description, admin_id, config_key)
                )
            else:
                conn.execute(
                    '''UPDATE system_config 
                       SET config_value = ?, updated_at = CURRENT_TIMESTAMP, updated_by = ?
                       WHERE config_key = ?''',
                    (config_value, admin_id, config_key)
                )
        else:
            # 创建新配置
            conn.execute(
                '''INSERT INTO system_config 
                   (config_key, config_value, description, updated_by)
                   VALUES (?, ?, ?, ?)''',
                (config_key, config_value, description or '', admin_id)
            )
        
        conn.commit()
        
        return SystemConfigService.get_config(config_key)
    
    @staticmethod
    def get_quiz_limit_config() -> Dict[str, Any]:
        """
        获取刷题限制相关配置
        
        Returns:
            包含功能开关和限制数量的字典
        """
        enabled_config = SystemConfigService.get_config('quiz_limit_enabled')
        count_config = SystemConfigService.get_config('quiz_limit_count')
        
        return {
            'quiz_limit_enabled': enabled_config['config_value'] == '1' if enabled_config else False,
            'quiz_limit_count': int(count_config['config_value']) if count_config else 100
        }





