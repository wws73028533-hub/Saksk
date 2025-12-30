# -*- coding: utf-8 -*-
"""
题目模型
"""
import json
from ..utils.database import get_db


class Question:
    """题目模型"""
    
    @staticmethod
    def get_by_id(question_id):
        """通过ID获取题目"""
        conn = get_db()
        row = conn.execute(
            'SELECT * FROM questions WHERE id = ?', (question_id,)
        ).fetchone()
        if row:
            q = dict(row)
            if q.get('options'):
                try:
                    q['options'] = json.loads(q['options'])
                except:
                    q['options'] = []
            return q
        return None
    
    @staticmethod
    def get_list(subject='all', q_type='all', mode='quiz', user_id=None):
        """获取题目列表（添加权限过滤）"""
        from app.core.utils.subject_permissions import can_user_access_subject
        
        conn = get_db()
        uid = user_id or -1
        
        sql = """
            SELECT q.*, s.name as subject,
                   CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
                   CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
            LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
            WHERE 1=1
        """
        params = [uid, uid]
        
        # 科目筛选
        if subject != 'all':
            sql += " AND s.name = ?"
            params.append(subject)
        
        # 题型筛选
        if q_type != 'all':
            sql += " AND q.q_type = ?"
            params.append(q_type)
        
        # 模式筛选
        if mode == 'favorites':
            sql += " AND f.id IS NOT NULL"
        elif mode == 'mistakes':
            sql += " AND m.id IS NOT NULL"
        
        sql += " ORDER BY q.id"
        
        rows = conn.execute(sql, params).fetchall()
        
        questions = []
        for row in rows:
            q = dict(row)
            
            # 权限检查：如果用户被限制访问该科目，跳过
            if user_id and q.get('subject_id'):
                if not can_user_access_subject(user_id, q['subject_id']):
                    continue
            
            if q.get('options'):
                try:
                    q['options'] = json.loads(q['options'])
                except:
                    q['options'] = []
            questions.append(q)
        
        return questions
    
    @staticmethod
    def get_count(subject='all', q_type='all', mode='quiz', user_id=None):
        """获取题目数量（添加权限过滤）"""
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        
        conn = get_db()
        uid = user_id or -1
        
        # 获取用户可访问的科目ID
        if user_id:
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids:
                return 0
        else:
            accessible_subject_ids = None
        
        if mode == 'favorites':
            base_sql = """FROM questions q 
                      LEFT JOIN subjects s ON q.subject_id = s.id 
                      JOIN favorites f ON f.question_id = q.id AND f.user_id = ? 
                      WHERE 1=1"""
            params = [uid]
        elif mode == 'mistakes':
            base_sql = """FROM questions q 
                      LEFT JOIN subjects s ON q.subject_id = s.id 
                      JOIN mistakes m ON m.question_id = q.id AND m.user_id = ? 
                      WHERE 1=1"""
            params = [uid]
        else:
            base_sql = "FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE 1=1"
            params = []
        
        if subject != 'all':
            base_sql += " AND s.name = ?"
            params.append(subject)
        
        if q_type != 'all':
            base_sql += " AND q.q_type = ?"
            params.append(q_type)
        
        # 权限过滤：只统计可访问科目的题目
        if accessible_subject_ids is not None:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            base_sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        
        sql = "SELECT COUNT(1) " + base_sql
        return conn.execute(sql, params).fetchone()[0]
    
    @staticmethod
    def get_subjects(user_id=None):
        """获取所有科目（添加权限过滤）"""
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        
        conn = get_db()
        
        if user_id:
            # 返回用户可访问的科目
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if not accessible_subject_ids:
                return []
            
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            rows = conn.execute(
                f'SELECT name FROM subjects WHERE id IN ({placeholders})',
                accessible_subject_ids
            ).fetchall()
        else:
            # 未登录用户：返回空列表
            rows = []
        
        return [row[0] for row in rows]
    
    @staticmethod
    def get_types():
        """获取所有题型"""
        conn = get_db()
        rows = conn.execute('SELECT DISTINCT q_type FROM questions').fetchall()
        return [row[0] for row in rows]

