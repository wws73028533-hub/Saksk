# -*- coding: utf-8 -*-
"""测试数据库访问"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    print("[OK] Successfully imported create_app")
    
    app = create_app()
    print("[OK] Successfully created app")
    
    # 检查数据库路径
    db_path = app.config['DATABASE_PATH']
    print(f"\n[INFO] Database path: {db_path}")
    print(f"[INFO] Database exists: {os.path.exists(db_path)}")
    
    # 测试数据库连接
    from app.core.utils.database import get_db
    with app.app_context():
        conn = get_db()
        # 检查表是否存在
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(f"\n[INFO] Found {len(tables)} tables in database:")
        for table in sorted(tables)[:10]:
            print(f"  - {table}")
        
        # 检查users表数据
        try:
            user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            print(f"\n[INFO] Users in database: {user_count}")
        except Exception as e:
            print(f"[WARN] Cannot query users table: {e}")
        
        # 检查subjects表数据
        try:
            subject_count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
            print(f"[INFO] Subjects in database: {subject_count}")
        except Exception as e:
            print(f"[WARN] Cannot query subjects table: {e}")
        
        # 检查questions表数据
        try:
            question_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
            print(f"[INFO] Questions in database: {question_count}")
        except Exception as e:
            print(f"[WARN] Cannot query questions table: {e}")
    
    print("\n[OK] Database access test passed!")
    
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

