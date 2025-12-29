# -*- coding: utf-8 -*-
"""
编程题数据迁移脚本
将 questions 表中的编程题数据迁移到 coding_questions 表
将相关的 subjects 数据迁移到 coding_subjects 表
"""
import sqlite3
import sys
import os
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


def migrate_coding_data():
    """迁移编程题数据"""
    print("=" * 60)
    print("编程题数据迁移脚本")
    print("=" * 60)
    
    # 创建应用上下文
    app = create_app('development')
    
    with app.app_context():
        from app.core.utils.database import get_db
        
        db = get_db()
        
        try:
            # 1. 检查新表是否存在
            print("\n[1] 检查新表是否存在...")
            tables = [row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            
            if 'coding_subjects' not in tables:
                print("   [ERROR] coding_subjects 表不存在，请先运行 init_db() 创建表")
                return False
            
            if 'coding_questions' not in tables:
                print("   [ERROR] coding_questions 表不存在，请先运行 init_db() 创建表")
                return False
            
            print("   [OK] 新表已存在")
            
            # 2. 检查是否有编程题数据需要迁移
            print("\n[2] 检查需要迁移的数据...")
            coding_questions = db.execute('''
                SELECT id, subject_id, content, q_type, explanation, difficulty,
                       code_template, programming_language, time_limit, memory_limit,
                       test_cases_json, created_at
                FROM questions
                WHERE q_type IN ('函数题', '编程题')
            ''').fetchall()
            
            if not coding_questions:
                print("   [INFO] 没有找到需要迁移的编程题数据")
                return True
            
            print(f"   [INFO] 找到 {len(coding_questions)} 道编程题需要迁移")
            
            # 3. 获取所有相关的 subjects
            print("\n[3] 收集相关的题目集...")
            subject_ids = set()
            for q in coding_questions:
                if q['subject_id']:
                    subject_ids.add(q['subject_id'])
            
            if not subject_ids:
                print("   [WARN] 没有找到相关的题目集")
            else:
                print(f"   [INFO] 找到 {len(subject_ids)} 个题目集需要迁移")
            
            # 4. 迁移 subjects 到 coding_subjects
            print("\n[4] 迁移题目集数据...")
            subject_id_mapping = {}  # 旧ID -> 新ID的映射
            
            for old_subject_id in subject_ids:
                # 检查是否已经迁移过
                existing = db.execute('''
                    SELECT id FROM coding_subjects WHERE id = ?
                ''', (old_subject_id,)).fetchone()
                
                if existing:
                    print(f"   [SKIP] 题目集 ID {old_subject_id} 已存在，跳过")
                    subject_id_mapping[old_subject_id] = old_subject_id
                    continue
                
                # 获取原题目集数据（兼容可能缺少的字段）
                try:
                    # 先检查字段是否存在
                    cols = [r['name'] for r in db.execute("PRAGMA table_info(subjects)").fetchall()]
                    has_description = 'description' in cols
                    has_is_locked = 'is_locked' in cols
                    has_created_at = 'created_at' in cols
                    
                    select_fields = ['name']
                    if has_description:
                        select_fields.append('description')
                    if has_is_locked:
                        select_fields.append('is_locked')
                    if has_created_at:
                        select_fields.append('created_at')
                    
                    query = f'SELECT {", ".join(select_fields)} FROM subjects WHERE id = ?'
                    old_subject = db.execute(query, (old_subject_id,)).fetchone()
                except Exception as e:
                    print(f"   [ERROR] 查询题目集 ID {old_subject_id} 失败: {str(e)}")
                    continue
                
                if not old_subject:
                    print(f"   [WARN] 题目集 ID {old_subject_id} 不存在，跳过")
                    continue
                
                # 检查名称是否已存在
                name_check = db.execute('''
                    SELECT id FROM coding_subjects WHERE name = ?
                ''', (old_subject['name'],)).fetchone()
                
                if name_check:
                    print(f"   [WARN] 题目集名称 '{old_subject['name']}' 已存在，使用现有ID")
                    subject_id_mapping[old_subject_id] = name_check['id']
                    continue
                
                # 准备插入数据（sqlite3.Row 使用字典式访问，但不支持 .get()）
                name = old_subject['name']
                if has_description:
                    description = old_subject['description'] if old_subject['description'] else ''
                else:
                    description = ''
                
                if has_is_locked:
                    is_locked = old_subject['is_locked'] if old_subject['is_locked'] is not None else 0
                else:
                    is_locked = 0
                
                if has_created_at:
                    created_at = old_subject['created_at'] if old_subject['created_at'] else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                else:
                    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 插入到 coding_subjects
                db.execute('''
                    INSERT INTO coding_subjects (id, name, description, is_locked, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (old_subject_id, name, description, is_locked, created_at))
                subject_id_mapping[old_subject_id] = old_subject_id
                print(f"   [OK] 迁移题目集: {old_subject['name']} (ID: {old_subject_id})")
            
            db.commit()
            
            # 5. 迁移编程题数据
            print("\n[5] 迁移编程题数据...")
            migrated_count = 0
            skipped_count = 0
            error_count = 0
            
            for q in coding_questions:
                try:
                    # 检查是否已经迁移过
                    existing = db.execute('''
                        SELECT id FROM coding_questions WHERE id = ?
                    ''', (q['id'],)).fetchone()
                    
                    if existing:
                        print(f"   [SKIP] 题目 ID {q['id']} 已存在，跳过")
                        skipped_count += 1
                        continue
                    
                    # 获取新的 subject_id
                    old_subject_id = q['subject_id']
                    if old_subject_id and old_subject_id in subject_id_mapping:
                        new_subject_id = subject_id_mapping[old_subject_id]
                    elif old_subject_id:
                        # 如果 subject_id 不在映射中，尝试直接使用
                        new_subject_id = old_subject_id
                    else:
                        print(f"   [WARN] 题目 ID {q['id']} 没有关联的题目集，跳过")
                        error_count += 1
                        continue
                    
                    # 准备数据
                    title = q['content'] if q['content'] else '无标题'
                    description = q['explanation'] if q['explanation'] else ''
                    q_type = q['q_type'] if q['q_type'] else '编程题'
                    difficulty = q['difficulty']
                    
                    # 转换 difficulty（如果是数字）
                    if isinstance(difficulty, int):
                        if difficulty == 1:
                            difficulty = 'easy'
                        elif difficulty == 2:
                            difficulty = 'medium'
                        elif difficulty == 3:
                            difficulty = 'hard'
                        else:
                            difficulty = 'easy'
                    elif not difficulty or difficulty not in ['easy', 'medium', 'hard']:
                        difficulty = 'easy'
                    
                    code_template = q['code_template'] if q['code_template'] else ''
                    programming_language = q['programming_language'] if q['programming_language'] else 'python'
                    time_limit = q['time_limit']
                    if time_limit is None:
                        time_limit = 5
                    memory_limit = q['memory_limit']
                    if memory_limit is None:
                        memory_limit = 128
                    test_cases_json = q['test_cases_json'] if q['test_cases_json'] else '{"test_cases":[],"hidden_cases":[]}'
                    
                    # 验证 test_cases_json 格式
                    try:
                        json.loads(test_cases_json)
                    except:
                        test_cases_json = '{"test_cases":[],"hidden_cases":[]}'
                    
                    created_at = q['created_at']
                    if not created_at:
                        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 插入到 coding_questions
                    db.execute('''
                        INSERT INTO coding_questions (
                            id, coding_subject_id, title, q_type, description, difficulty,
                            code_template, programming_language, time_limit, memory_limit,
                            test_cases_json, is_enabled, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        q['id'],
                        new_subject_id,
                        title,
                        q_type,
                        description,
                        difficulty,
                        code_template,
                        programming_language,
                        time_limit,
                        memory_limit,
                        test_cases_json,
                        1,  # is_enabled
                        created_at
                    ))
                    
                    migrated_count += 1
                    if migrated_count % 10 == 0:
                        print(f"   [进度] 已迁移 {migrated_count} 道题目...")
                    
                except Exception as e:
                    print(f"   [ERROR] 迁移题目 ID {q['id']} 失败: {str(e)}")
                    error_count += 1
                    continue
            
            db.commit()
            
            print(f"\n[6] 迁移完成统计:")
            print(f"   - 成功迁移: {migrated_count} 道题目")
            print(f"   - 跳过（已存在）: {skipped_count} 道题目")
            print(f"   - 失败: {error_count} 道题目")
            print(f"   - 迁移题目集: {len(subject_id_mapping)} 个")
            
            # 7. 验证迁移结果
            print("\n[7] 验证迁移结果...")
            new_count = db.execute('SELECT COUNT(*) as count FROM coding_questions').fetchone()['count']
            print(f"   [INFO] coding_questions 表中共有 {new_count} 道题目")
            
            new_subject_count = db.execute('SELECT COUNT(*) as count FROM coding_subjects').fetchone()['count']
            print(f"   [INFO] coding_subjects 表中共有 {new_subject_count} 个题目集")
            
            print("\n" + "=" * 60)
            print("数据迁移完成！")
            print("=" * 60)
            print("\n注意：")
            print("1. questions 表中的原始数据仍然保留")
            print("2. code_submissions 表中的 question_id 仍然引用 questions 表")
            print("3. 如果需要，可以手动更新 code_submissions 表的引用")
            print("4. 迁移完成后，建议备份数据库")
            
            return True
            
        except Exception as e:
            print(f"\n[ERROR] 迁移过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            db.rollback()
            return False


if __name__ == '__main__':
    success = migrate_coding_data()
    sys.exit(0 if success else 1)

