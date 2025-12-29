# -*- coding: utf-8 -*-
"""
验证编程题数据迁移结果
"""
import sqlite3
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


def verify_migration():
    """验证迁移结果"""
    print("=" * 60)
    print("验证编程题数据迁移结果")
    print("=" * 60)
    
    app = create_app('development')
    
    with app.app_context():
        from app.core.utils.database import get_db
        
        db = get_db()
        
        try:
            # 1. 检查表是否存在
            print("\n[1] 检查表结构...")
            tables = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            
            required_tables = ['coding_subjects', 'coding_questions', 'code_submissions']
            for table in required_tables:
                if table in tables:
                    print(f"   [OK] {table} 表存在")
                else:
                    print(f"   [FAIL] {table} 表不存在")
            
            # 2. 统计数据
            print("\n[2] 统计数据...")
            
            # 原始数据
            old_coding_count = db.execute('''
                SELECT COUNT(*) as count FROM questions
                WHERE q_type IN ('函数题', '编程题')
            ''').fetchone()['count']
            print(f"   questions 表中的编程题数量: {old_coding_count}")
            
            # 新表数据
            new_question_count = db.execute('''
                SELECT COUNT(*) as count FROM coding_questions
            ''').fetchone()['count']
            print(f"   coding_questions 表中的题目数量: {new_question_count}")
            
            new_subject_count = db.execute('''
                SELECT COUNT(*) as count FROM coding_subjects
            ''').fetchone()['count']
            print(f"   coding_subjects 表中的题目集数量: {new_subject_count}")
            
            submission_count = db.execute('''
                SELECT COUNT(*) as count FROM code_submissions
            ''').fetchone()['count']
            print(f"   code_submissions 表中的提交记录数量: {submission_count}")
            
            # 3. 检查数据完整性
            print("\n[3] 检查数据完整性...")
            
            # 检查是否有孤立的提交记录（引用的题目不在新表中）
            orphaned_submissions = db.execute('''
                SELECT COUNT(*) as count
                FROM code_submissions cs
                LEFT JOIN coding_questions cq ON cs.question_id = cq.id
                WHERE cq.id IS NULL
            ''').fetchone()['count']
            
            if orphaned_submissions > 0:
                print(f"   [WARN] 发现 {orphaned_submissions} 条提交记录引用的题目不在 coding_questions 表中")
            else:
                print("   [OK] 所有提交记录都有对应的题目")
            
            # 检查是否有题目没有关联的题目集
            orphaned_questions = db.execute('''
                SELECT COUNT(*) as count
                FROM coding_questions cq
                LEFT JOIN coding_subjects cs ON cq.coding_subject_id = cs.id
                WHERE cs.id IS NULL
            ''').fetchone()['count']
            
            if orphaned_questions > 0:
                print(f"   [WARN] 发现 {orphaned_questions} 道题目没有关联的题目集")
            else:
                print("   [OK] 所有题目都有关联的题目集")
            
            # 4. 检查字段完整性
            print("\n[4] 检查字段完整性...")
            
            # 检查必填字段
            missing_title = db.execute('''
                SELECT COUNT(*) as count FROM coding_questions
                WHERE title IS NULL OR title = ''
            ''').fetchone()['count']
            
            if missing_title > 0:
                print(f"   [WARN] 发现 {missing_title} 道题目缺少标题")
            else:
                print("   [OK] 所有题目都有标题")
            
            missing_test_cases = db.execute('''
                SELECT COUNT(*) as count FROM coding_questions
                WHERE test_cases_json IS NULL OR test_cases_json = ''
            ''').fetchone()['count']
            
            if missing_test_cases > 0:
                print(f"   [WARN] 发现 {missing_test_cases} 道题目缺少测试用例")
            else:
                print("   [OK] 所有题目都有测试用例")
            
            # 5. 显示一些示例数据
            print("\n[5] 示例数据...")
            
            sample_questions = db.execute('''
                SELECT cq.id, cq.title, cq.q_type, cq.difficulty, cs.name as subject_name
                FROM coding_questions cq
                LEFT JOIN coding_subjects cs ON cq.coding_subject_id = cs.id
                LIMIT 5
            ''').fetchall()
            
            if sample_questions:
                print("   前5道题目:")
                for q in sample_questions:
                    print(f"      - ID: {q['id']}, 标题: {q['title']}, 类型: {q['q_type']}, "
                          f"难度: {q['difficulty']}, 题目集: {q['subject_name']}")
            
            sample_subjects = db.execute('''
                SELECT cs.id, cs.name, COUNT(cq.id) as question_count
                FROM coding_subjects cs
                LEFT JOIN coding_questions cq ON cs.id = cq.coding_subject_id
                GROUP BY cs.id, cs.name
                LIMIT 5
            ''').fetchall()
            
            if sample_subjects:
                print("\n   前5个题目集:")
                for s in sample_subjects:
                    print(f"      - ID: {s['id']}, 名称: {s['name']}, 题目数: {s['question_count']}")
            
            print("\n" + "=" * 60)
            print("验证完成！")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] 验证过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = verify_migration()
    sys.exit(0 if success else 1)

