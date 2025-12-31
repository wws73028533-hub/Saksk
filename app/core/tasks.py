# -*- coding: utf-8 -*-
"""
后台任务模块
提供定时任务功能，如清理过期验证码
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
from flask import Flask, current_app
from app.core.utils.database import get_db


class BackgroundTaskManager:
    """后台任务管理器"""
    
    def __init__(self, app: Optional[Flask] = None):
        """
        初始化任务管理器
        
        Args:
            app: Flask应用实例
        """
        self.app = app
        self.thread: Optional[threading.Thread] = None
        self.running = False
    
    def init_app(self, app: Flask) -> None:
        """
        初始化应用
        
        Args:
            app: Flask应用实例
        """
        self.app = app
    
    def start(self) -> None:
        """启动后台任务"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_tasks, daemon=True)
        self.thread.start()
        if self.app:
            self.app.logger.info('后台任务已启动')
    
    def stop(self) -> None:
        """停止后台任务"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        if self.app:
            self.app.logger.info('后台任务已停止')
    
    def _run_tasks(self) -> None:
        """运行后台任务"""
        if not self.app:
            return
        
        with self.app.app_context():
            while self.running:
                try:
                    # 清理过期验证码（每小时执行一次）
                    self._cleanup_expired_codes()
                    
                    # 等待1小时
                    for _ in range(3600):  # 3600秒 = 1小时
                        if not self.running:
                            break
                        time.sleep(1)
                except Exception as e:
                    if self.app:
                        self.app.logger.error(f'后台任务执行错误: {str(e)}', exc_info=True)
                    # 发生错误时等待5分钟再重试
                    for _ in range(300):  # 5分钟
                        if not self.running:
                            break
                        time.sleep(1)
    
    def _cleanup_expired_codes(self) -> None:
        """清理过期的验证码"""
        try:
            # 在后台线程中需要创建新的数据库连接
            import sqlite3
            from flask import current_app
            
            db_path = current_app.config['DATABASE_PATH']
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            now = datetime.now()
            
            # 删除所有过期的验证码
            result = conn.execute(
                '''DELETE FROM email_verification_codes
                   WHERE expires_at < ?''',
                (now,)
            )
            deleted_count = result.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                current_app.logger.info(f'清理过期验证码: 删除了 {deleted_count} 条记录')
        except Exception as e:
            current_app.logger.error(f'清理过期验证码失败: {str(e)}', exc_info=True)


# 全局任务管理器实例
task_manager = BackgroundTaskManager()


def start_background_tasks(app: Flask) -> None:
    """
    启动后台任务
    
    Args:
        app: Flask应用实例
    """
    task_manager.init_app(app)
    task_manager.start()

