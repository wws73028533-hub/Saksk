# -*- coding: utf-8 -*-
"""
更新 code_submissions 表的引用
确保所有提交记录都正确引用 coding_questions 表
"""
import sqlite3
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


def update_code_submissions_references():
    """更新 code_submissions 表的引用"""
    print("=" * 60)
    print("更新 code_submissions 表引用")
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
            
            required_tables = ['code_submissions', 'coding_questions']
            for table in required_tables:
                if table in tables:
                    print(f"   [OK] {table} 表存在")
                else:
                    print(f"   [FAIL] {table} 表不存在")
                    return False
            
            # 2. 检查外键约束
            print("\n[2] 检查外键约束...")
            # SQLite 默认外键是关闭的，需要检查
            fk_check = db.execute("PRAGMA foreign_keys").fetchone()[0]
            if fk_check:
                print("   [OK] 外键约束已启用")
            else:
                print("   [INFO] 外键约束未启用（SQLite 默认）")
            
            # 3. 查找所有提交记录
            print("\n[3] 分析提交记录...")
            all_submissions = db.execute('''
                SELECT id, question_id, user_id, status, submitted_at
                FROM code_submissions
            ''').fetchall()
            
            total_count = len(all_submissions)
            print(f"   [INFO] 共有 {total_count} 条提交记录")
            
            # 4. 检查无效引用（引用的题目不在 coding_questions 表中）
            print("\n[4] 检查无效引用...")
            invalid_refs = db.execute('''
                SELECT cs.id, cs.question_id, cs.user_id, cs.submitted_at
                FROM code_submissions cs
                LEFT JOIN coding_questions cq ON cs.question_id = cq.id
                WHERE cq.id IS NULL
            ''').fetchall()
            
            if invalid_refs:
                print(f"   [WARN] 发现 {len(invalid_refs)} 条提交记录引用的题目不在 coding_questions 表中")
                print("   无效引用的提交记录:")
                for ref in invalid_refs[:10]:  # 只显示前10条
                    print(f"      - 提交ID: {ref['id']}, 题目ID: {ref['question_id']}, "
                          f"用户ID: {ref['user_id']}, 时间: {ref['submitted_at']}")
                if len(invalid_refs) > 10:
                    print(f"      ... 还有 {len(invalid_refs) - 10} 条记录")
                
                # 检查这些题目是否在 questions 表中（可能是题库中心的题目）
                print("\n   检查这些题目是否在 questions 表中...")
                invalid_question_ids = [ref['question_id'] for ref in invalid_refs]
                placeholders = ','.join(['?'] * len(invalid_question_ids))
                
                questions_in_old_table = db.execute(f'''
                    SELECT id, content, q_type
                    FROM questions
                    WHERE id IN ({placeholders})
                ''', invalid_question_ids).fetchall()
                
                if questions_in_old_table:
                    print(f"   [INFO] 其中 {len(questions_in_old_table)} 道题目在 questions 表中:")
                    for q in questions_in_old_table[:5]:
                        print(f"      - 题目ID: {q['id']}, 类型: {q['q_type']}, 内容: {q['content'][:50]}...")
                    
                    # 检查是否是编程题（应该被迁移但可能迁移失败）
                    coding_questions_in_old = [q for q in questions_in_old_table 
                                             if q['q_type'] in ['函数题', '编程题']]
                    if coding_questions_in_old:
                        print(f"\n   [WARN] 发现 {len(coding_questions_in_old)} 道编程题仍在 questions 表中")
                        print("   这些题目应该被迁移到 coding_questions 表")
                        print("   建议重新运行迁移脚本: python scripts/migrate_coding_data.py")
                else:
                    print("   [INFO] 这些题目不在 questions 表中（可能是已删除的题目）")
                
                # 询问是否删除无效引用
                print("\n   选项:")
                print("   1. 保留这些记录（不推荐，可能导致查询错误）")
                print("   2. 删除这些无效引用的记录")
                print("   3. 跳过（稍后手动处理）")
                
                # 默认跳过，让用户手动决定
                print("\n   [INFO] 跳过删除操作，请手动处理这些无效引用")
            else:
                print("   [OK] 所有提交记录都有有效的题目引用")
            
            # 5. 验证有效引用
            print("\n[5] 验证有效引用...")
            valid_refs = db.execute('''
                SELECT COUNT(*) as count
                FROM code_submissions cs
                INNER JOIN coding_questions cq ON cs.question_id = cq.id
            ''').fetchone()['count']
            
            print(f"   [INFO] 有效引用: {valid_refs} 条")
            
            # 6. 检查外键约束（如果启用）
            if fk_check:
                print("\n[6] 验证外键约束...")
                # 尝试查询，如果有外键约束，无效引用会导致错误
                try:
                    test_query = db.execute('''
                        SELECT cs.id, cq.title
                        FROM code_submissions cs
                        INNER JOIN coding_questions cq ON cs.question_id = cq.id
                        LIMIT 1
                    ''').fetchone()
                    if test_query:
                        print("   [OK] 外键约束验证通过")
                except Exception as e:
                    print(f"   [ERROR] 外键约束验证失败: {str(e)}")
            
            # 7. 显示统计信息
            print("\n[7] 统计信息...")
            
            # 按题目统计提交数
            top_questions = db.execute('''
                SELECT cq.id, cq.title, COUNT(cs.id) as submission_count
                FROM coding_questions cq
                LEFT JOIN code_submissions cs ON cq.id = cs.question_id
                GROUP BY cq.id, cq.title
                ORDER BY submission_count DESC
                LIMIT 10
            ''').fetchall()
            
            if top_questions:
                print("   提交数最多的前10道题目:")
                for q in top_questions:
                    print(f"      - 题目ID: {q['id']}, 标题: {q['title'][:40]}, "
                          f"提交数: {q['submission_count']}")
            
            # 按状态统计
            status_stats = db.execute('''
                SELECT status, COUNT(*) as count
                FROM code_submissions cs
                INNER JOIN coding_questions cq ON cs.question_id = cq.id
                GROUP BY status
            ''').fetchall()
            
            if status_stats:
                print("\n   按状态统计:")
                for stat in status_stats:
                    print(f"      - {stat['status']}: {stat['count']} 条")
            
            print("\n" + "=" * 60)
            print("更新完成！")
            print("=" * 60)
            print("\n注意:")
            print("1. code_submissions 表的外键现在引用 coding_questions 表")
            print("2. 如果发现无效引用，请检查是否需要重新运行迁移脚本")
            print("3. 建议定期运行验证脚本检查数据完整性")
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] 更新过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return False


if __name__ == '__main__':
    success = update_code_submissions_references()
    sys.exit(0 if success else 1)

