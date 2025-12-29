# -*- coding: utf-8 -*-
"""
提交服务
负责提交记录的CRUD和统计
"""
from typing import Dict, Any, List, Optional
from app.core.utils.database import get_db
from app.modules.coding.models.code_submission import CodeSubmission


class SubmissionService:
    """提交服务"""
    
    @staticmethod
    def create_submission(
        user_id: int,
        question_id: int,
        code: str,
        language: str,
        judge_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建提交记录并更新统计信息
        
        Args:
            user_id: 用户ID
            question_id: 题目ID
            code: 代码
            language: 编程语言
            judge_result: 判题结果（来自JudgeService）
        
        Returns:
            提交记录字典
        """
        db = get_db()
        
        # 计算得分（通过的测试用例数 / 总测试用例数）
        passed_cases = judge_result.get('passed_cases', 0)
        total_cases = judge_result.get('total_cases', 1)
        score = (passed_cases / total_cases * 100.0) if total_cases > 0 else 0.0
        
        # 创建提交记录
        submission = CodeSubmission.create(
            user_id=user_id,
            question_id=question_id,
            code=code,
            language=language,
            status=judge_result['status'],
            passed_cases=passed_cases,
            total_cases=total_cases,
            execution_time=judge_result.get('execution_time'),
            error_message=judge_result.get('error_message'),
            score=score
        )
        
        # 更新题目级别的统计信息
        SubmissionService._update_question_statistics(
            db, user_id, question_id, judge_result, score
        )
        
        # 更新用户总统计信息
        SubmissionService._update_user_statistics(db, user_id)
        
        return submission
    
    @staticmethod
    def _update_question_statistics(
        db,
        user_id: int,
        question_id: int,
        judge_result: Dict[str, Any],
        score: float
    ):
        """更新用户对特定题目的统计信息"""
        from datetime import datetime
        status = judge_result['status']
        is_accepted = (status == 'accepted')
        execution_time = judge_result.get('execution_time')
        submitted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查是否已存在统计记录
        existing = db.execute('''
            SELECT * FROM coding_statistics
            WHERE user_id = ? AND question_id = ?
        ''', (user_id, question_id)).fetchone()
        
        if existing:
            # 更新现有记录
            new_total = existing['total_submissions'] + 1
            new_accepted = existing['accepted_submissions']
            new_best_time = existing['best_time']
            new_best_score = existing['best_score']
            new_first_accepted = existing['first_accepted_at']
            
            if is_accepted:
                new_accepted += 1
                if not new_first_accepted:
                    new_first_accepted = submitted_at
                if execution_time and (not new_best_time or execution_time < new_best_time):
                    new_best_time = execution_time
                if score > new_best_score:
                    new_best_score = score
            
            db.execute('''
                UPDATE coding_statistics
                SET total_submissions = ?,
                    accepted_submissions = ?,
                    best_time = ?,
                    best_score = ?,
                    first_accepted_at = ?,
                    last_submitted_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND question_id = ?
            ''', (
                new_total, new_accepted, new_best_time, new_best_score,
                new_first_accepted, submitted_at, user_id, question_id
            ))
        else:
            # 创建新记录
            db.execute('''
                INSERT INTO coding_statistics (
                    user_id, question_id, total_submissions, accepted_submissions,
                    best_time, best_score, first_accepted_at, last_submitted_at
                )
                VALUES (?, ?, 1, ?, ?, ?, ?, ?)
            ''', (
                user_id, question_id,
                1 if is_accepted else 0,
                execution_time if is_accepted else None,
                score if is_accepted else 0.0,
                submitted_at if is_accepted else None,
                submitted_at
            ))
        
        db.commit()
    
    @staticmethod
    def _update_user_statistics(db, user_id: int):
        """更新用户总统计信息"""
        # 计算总提交次数
        total_submissions = db.execute('''
            SELECT COUNT(*) as count FROM code_submissions WHERE user_id = ?
        ''', (user_id,)).fetchone()['count']
        
        # 计算通过次数
        accepted_submissions = db.execute('''
            SELECT COUNT(*) as count FROM code_submissions
            WHERE user_id = ? AND status = 'accepted'
        ''', (user_id,)).fetchone()['count']
        
        # 计算通过的题目数（去重）
        solved_questions = db.execute('''
            SELECT COUNT(DISTINCT question_id) as count FROM code_submissions
            WHERE user_id = ? AND status = 'accepted'
        ''', (user_id,)).fetchone()['count']
        
        # 计算总得分（所有提交的得分之和）
        total_score_result = db.execute('''
            SELECT SUM(score) as total FROM code_submissions WHERE user_id = ?
        ''', (user_id,)).fetchone()
        total_score = total_score_result['total'] if total_score_result['total'] else 0.0
        
        # 计算平均得分
        average_score = (total_score / total_submissions) if total_submissions > 0 else 0.0
        
        # 计算通过率
        acceptance_rate = (accepted_submissions / total_submissions) if total_submissions > 0 else 0.0
        
        # 检查是否已存在统计记录
        existing = db.execute('''
            SELECT id FROM user_coding_stats WHERE user_id = ?
        ''', (user_id,)).fetchone()
        
        if existing:
            # 更新现有记录
            db.execute('''
                UPDATE user_coding_stats
                SET total_submissions = ?,
                    accepted_submissions = ?,
                    solved_questions = ?,
                    total_score = ?,
                    average_score = ?,
                    acceptance_rate = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                total_submissions, accepted_submissions, solved_questions,
                total_score, average_score, acceptance_rate, user_id
            ))
        else:
            # 创建新记录
            db.execute('''
                INSERT INTO user_coding_stats (
                    user_id, total_submissions, accepted_submissions,
                    solved_questions, total_score, average_score, acceptance_rate
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, total_submissions, accepted_submissions,
                solved_questions, total_score, average_score, acceptance_rate
            ))
        
        db.commit()
    
    @staticmethod
    def get_submissions(
        user_id: Optional[int] = None,
        question_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        获取提交历史（分页、筛选）
        
        Args:
            user_id: 用户ID（可选）
            question_id: 题目ID（可选）
            status: 状态筛选（可选）
            page: 页码
            per_page: 每页数量
        
        Returns:
            {
                'submissions': List[Dict],
                'total': int,
                'page': int,
                'per_page': int
            }
        """
        db = get_db()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if user_id:
            conditions.append('cs.user_id = ?')
            params.append(user_id)
        
        if question_id:
            conditions.append('cs.question_id = ?')
            params.append(question_id)
        
        if status:
            conditions.append('cs.status = ?')
            params.append(status)
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        # 获取总数
        count_query = f'''
            SELECT COUNT(*) as total
            FROM code_submissions cs
            WHERE {where_clause}
        '''
        total = db.execute(count_query, params).fetchone()['total']
        
        # 获取分页数据
        offset = (page - 1) * per_page
        query = f'''
            SELECT cs.*, cq.title as question_title
            FROM code_submissions cs
            LEFT JOIN coding_questions cq ON cs.question_id = cq.id
            WHERE {where_clause}
            ORDER BY cs.submitted_at DESC
            LIMIT ? OFFSET ?
        '''
        params.extend([per_page, offset])
        
        rows = db.execute(query, params).fetchall()
        submissions = [dict(row) for row in rows]
        
        return {
            'submissions': submissions,
            'total': total,
            'page': page,
            'per_page': per_page
        }
    
    @staticmethod
    def get_submission(
        submission_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取提交详情
        
        Args:
            submission_id: 提交ID
            user_id: 用户ID（可选，用于权限检查）
        
        Returns:
            提交记录字典，如果不存在返回None
        """
        submission = CodeSubmission.get_by_id(submission_id)
        
        if not submission:
            return None
        
        # 如果指定了user_id，检查权限
        if user_id and submission['user_id'] != user_id:
            return None
        
        return submission
    
    @staticmethod
    def get_best_submission(
        user_id: int,
        question_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取最佳提交记录（首次通过）
        
        Args:
            user_id: 用户ID
            question_id: 题目ID
        
        Returns:
            提交记录字典，如果没有通过记录返回None
        """
        db = get_db()
        row = db.execute(
            '''
            SELECT * FROM code_submissions
            WHERE user_id = ? AND question_id = ? AND status = 'accepted'
            ORDER BY submitted_at ASC
            LIMIT 1
            ''',
            (user_id, question_id)
        ).fetchone()
        
        if not row:
            return None
        
        return dict(row)
    
    @staticmethod
    def get_user_statistics(user_id: int) -> Dict[str, Any]:
        """
        获取用户统计信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            统计信息字典
        """
        db = get_db()
        
        # 总提交次数
        total_submissions = db.execute(
            'SELECT COUNT(*) as total FROM code_submissions WHERE user_id = ?',
            (user_id,)
        ).fetchone()['total']
        
        # 通过次数
        accepted_submissions = db.execute(
            'SELECT COUNT(*) as total FROM code_submissions WHERE user_id = ? AND status = ?',
            (user_id, 'accepted')
        ).fetchone()['total']
        
        # 通过的题目数（去重）
        solved_questions = db.execute(
            '''
            SELECT COUNT(DISTINCT question_id) as total
            FROM code_submissions
            WHERE user_id = ? AND status = 'accepted'
            ''',
            (user_id,)
        ).fetchone()['total']
        
        # 总题目数（编程题）
        total_questions = db.execute(
            "SELECT COUNT(*) as total FROM questions WHERE q_type = '编程题'"
        ).fetchone()['total']
        
        # 计算通过率
        acceptance_rate = (
            accepted_submissions / total_submissions
            if total_submissions > 0 else 0.0
        )
        
        return {
            'total_submissions': total_submissions,
            'accepted_submissions': accepted_submissions,
            'total_questions': total_questions,
            'solved_questions': solved_questions,
            'acceptance_rate': round(acceptance_rate, 2)
        }

