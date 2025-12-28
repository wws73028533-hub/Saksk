# -*- coding: utf-8 -*-
"""
测试编程题数据库迁移脚本
用于验证 questions 表字段和 code_submissions 表是否正确创建
"""
import sqlite3
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

def test_database_migration():
    """测试数据库迁移"""
    print("=" * 60)
    print("测试编程题数据库迁移")
    print("=" * 60)
    
    # 创建应用上下文
    app = create_app('development')
    
    with app.app_context():
        from app.utils.database import get_db, init_db
        
        # 初始化数据库（触发迁移）
        print("\n[1] 初始化数据库...")
        init_db()
        
        # 获取数据库连接
        conn = get_db()
        cur = conn.cursor()
        
        # 检查 questions 表的字段
        print("\n[2] 检查 questions 表字段...")
        question_cols = [r['name'] for r in cur.execute("PRAGMA table_info(questions)").fetchall()]
        
        required_fields = [
            'code_template',
            'programming_language',
            'time_limit',
            'memory_limit',
            'test_cases_json'
        ]
        
        print(f"   questions 表现有字段: {', '.join(question_cols)}")
        print(f"\n   检查编程题字段:")
        
        all_passed = True
        for field in required_fields:
            if field in question_cols:
                print(f"   [OK] {field} - 已存在")
            else:
                print(f"   [FAIL] {field} - 缺失")
                all_passed = False
        
        # 检查 code_submissions 表
        print("\n[3] 检查 code_submissions 表...")
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        if 'code_submissions' in tables:
            print("   [OK] code_submissions 表已创建")
            
            # 检查表结构
            submission_cols = [r['name'] for r in cur.execute("PRAGMA table_info(code_submissions)").fetchall()]
            print(f"   表字段: {', '.join(submission_cols)}")
            
            required_submission_fields = [
                'id', 'user_id', 'question_id', 'code', 'language',
                'status', 'passed_cases', 'total_cases', 'execution_time',
                'error_message', 'submitted_at'
            ]
            
            print(f"\n   检查表结构:")
            for field in required_submission_fields:
                if field in submission_cols:
                    print(f"   [OK] {field}")
                else:
                    print(f"   [FAIL] {field} - 缺失")
                    all_passed = False
        else:
            print("   [FAIL] code_submissions 表未创建")
            all_passed = False
        
        # 检查索引
        print("\n[4] 检查索引...")
        indexes = [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_code_submissions%'"
        ).fetchall()]
        
        if 'idx_code_submissions_user_question' in indexes:
            print("   [OK] idx_code_submissions_user_question 索引已创建")
        else:
            print("   [FAIL] idx_code_submissions_user_question 索引未创建")
            all_passed = False
        
        # 测试结果
        print("\n" + "=" * 60)
        if all_passed:
            print("[SUCCESS] 所有测试通过！数据库迁移成功。")
        else:
            print("[FAIL] 部分测试失败，请检查数据库迁移逻辑。")
        print("=" * 60)
        
        return all_passed

if __name__ == '__main__':
    try:
        success = test_database_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

