# -*- coding: utf-8 -*-
"""
编程题数据模型
"""
from typing import Optional, Dict, Any
from app.core.utils.database import get_db


class CodingQuestion:
    """编程题模型"""
    
    @staticmethod
    def get_by_id(question_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取题目
        
        Args:
            question_id: 题目ID
        
        Returns:
            题目字典，如果不存在返回None
        """
        db = get_db()
        row = db.execute(
            '''
            SELECT q.*, s.name as subject_name
            FROM coding_questions q
            LEFT JOIN coding_subjects s ON q.coding_subject_id = s.id
            WHERE q.id = ?
            ''',
            (question_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return dict(row)
    
    @staticmethod
    def get_test_cases(question_id: int) -> Dict[str, Any]:
        """
        获取题目的测试用例
        
        Args:
            question_id: 题目ID
        
        Returns:
            测试用例字典（包含test_cases和hidden_cases）
        """
        db = get_db()
        row = db.execute(
            'SELECT test_cases_json FROM coding_questions WHERE id = ?',
            (question_id,)
        ).fetchone()
        
        if not row or not row['test_cases_json']:
            return {'test_cases': [], 'hidden_cases': []}
        
        import json
        try:
            return json.loads(row['test_cases_json'])
        except (json.JSONDecodeError, TypeError):
            return {'test_cases': [], 'hidden_cases': []}

