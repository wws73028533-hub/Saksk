# -*- coding: utf-8 -*-
"""
添加 code_submissions 表的 score 列（如果不存在）
"""
import sqlite3
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


def add_score_column():
    """添加 score 列到 code_submissions 表"""
    print("=" * 60)
    print("添加 code_submissions.score 列")
    print("=" * 60)
    
    app = create_app('development')
    
    with app.app_context():
        from app.core.utils.database import get_db
        
        db = get_db()
        
        try:
            # 检查表是否存在
            tables = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            
            if 'code_submissions' not in tables:
                print("[ERROR] code_submissions 表不存在")
                return False
            
            # 检查 score 列是否存在
            cursor = db.execute("PRAGMA table_info(code_submissions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'score' in columns:
                print("[INFO] score 列已存在，无需添加")
                return True
            
            # 添加 score 列（SQLite 3.11.0+ 支持 DEFAULT，旧版本需要分步操作）
            print("[1] 添加 score 列...")
            try:
                db.execute('ALTER TABLE code_submissions ADD COLUMN score REAL DEFAULT 0.0')
                db.commit()
            except sqlite3.OperationalError as e:
                # 如果 DEFAULT 不支持，先添加列，然后更新值
                if 'non-constant default' in str(e).lower():
                    print("[WARN] SQLite 版本较旧，使用兼容方式添加列...")
                    db.execute('ALTER TABLE code_submissions ADD COLUMN score REAL')
                    db.commit()
                    # 设置默认值
                    db.execute('UPDATE code_submissions SET score = 0.0 WHERE score IS NULL')
                    db.commit()
                else:
                    raise
            
            print("[OK] score 列已成功添加")
            
            # 更新现有记录的 score（基于 passed_cases 和 total_cases）
            print("[2] 更新现有记录的 score...")
            db.execute('''
                UPDATE code_submissions
                SET score = CASE
                    WHEN total_cases > 0 THEN (passed_cases * 100.0 / total_cases)
                    ELSE 0.0
                END
                WHERE score IS NULL OR score = 0.0
            ''')
            db.commit()
            
            updated_count = db.execute('SELECT changes()').fetchone()[0]
            print(f"[OK] 已更新 {updated_count} 条记录的 score")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 迁移失败: {str(e)}")
            db.rollback()
            return False


if __name__ == '__main__':
    success = add_score_column()
    sys.exit(0 if success else 1)
