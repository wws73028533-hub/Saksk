# -*- coding: utf-8 -*-
"""
代码提交数据模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.utils.database import get_db


class CodeSubmission:
    """代码提交模型"""
    
    @staticmethod
    def create(
        user_id: int,
        question_id: int,
        code: str,
        language: str,
        status: str,
        passed_cases: int,
        total_cases: int,
        execution_time: Optional[float] = None,
        error_message: Optional[str] = None,
        score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        创建提交记录
        
        Args:
            user_id: 用户ID
            question_id: 题目ID
            code: 代码
            language: 编程语言
            status: 提交状态
            passed_cases: 通过的测试用例数
            total_cases: 总测试用例数
            execution_time: 执行时间（秒）
            error_message: 错误信息
            score: 得分（可选，如果不提供则自动计算）
        
        Returns:
            提交记录字典
        """
        db = get_db()
        
        # 如果没有提供得分，自动计算
        if score is None:
            score = (passed_cases / total_cases * 100.0) if total_cases > 0 else 0.0
        
        cursor = db.execute(
            '''
            INSERT INTO code_submissions 
            (user_id, question_id, code, language, status, passed_cases, total_cases, 
             execution_time, error_message, score, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''',
            (user_id, question_id, code, language, status, passed_cases, total_cases,
             execution_time, error_message, score)
        )
        db.commit()
        
        submission_id = cursor.lastrowid
        return CodeSubmission.get_by_id(submission_id)
    
    @staticmethod
    def get_by_id(submission_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取提交记录
        
        Args:
            submission_id: 提交ID
        
        Returns:
            提交记录字典，如果不存在返回None
        """
        db = get_db()
        row = db.execute(
            '''
            SELECT cs.*, cq.title as question_title
            FROM code_submissions cs
            LEFT JOIN coding_questions cq ON cs.question_id = cq.id
            WHERE cs.id = ?
            ''',
            (submission_id,)
        ).fetchone()
        
        if not row:
            return None
        
        result = dict(row)
        # 格式化时间
        if result.get('submitted_at'):
            result['submitted_at'] = result['submitted_at']
        return result
    
    @staticmethod
    def get_by_user_and_question(
        user_id: int,
        question_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取用户对某题目的提交记录
        
        Args:
            user_id: 用户ID
            question_id: 题目ID
            limit: 返回数量限制
        
        Returns:
            提交记录列表
        """
        db = get_db()
        rows = db.execute(
            '''
            SELECT * FROM code_submissions
            WHERE user_id = ? AND question_id = ?
            ORDER BY submitted_at DESC
            LIMIT ?
            ''',
            (user_id, question_id, limit)
        ).fetchall()
        
        return [dict(row) for row in rows]

