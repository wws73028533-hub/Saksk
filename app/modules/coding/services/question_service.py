# -*- coding: utf-8 -*-
"""
题目服务
负责题目的CRUD、查询、筛选和统计
"""
from typing import Dict, Any, List, Optional
import json
from app.core.utils.database import get_db
from app.modules.coding.models.coding_question import CodingQuestion
from app.modules.coding.schemas.question_schemas import (
    QuestionCreateSchema,
    QuestionUpdateSchema
)


class QuestionService:
    """题目服务"""
    
    @staticmethod
    def get_questions(
        subject_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取题目列表（带筛选和分页）
        
        Args:
            subject_id: 科目ID（可选）
            difficulty: 难度（easy/medium/hard，可选）
            status: 状态（all/unsolved/solving/solved，可选）
            keyword: 搜索关键词（可选）
            page: 页码
            per_page: 每页数量
            user_id: 用户ID（用于计算用户状态和收藏状态）
        
        Returns:
            {
                'questions': List[Dict],
                'total': int,
                'page': int,
                'per_page': int
            }
        """
        db = get_db()
        
        # 构建查询条件（使用coding_questions表）
        conditions = []
        params = []
        
        if subject_id:
            conditions.append('cq.coding_subject_id = ?')
            params.append(subject_id)
        
        if difficulty:
            conditions.append('cq.difficulty = ?')
            params.append(difficulty)
        
        if keyword:
            conditions.append('(cq.title LIKE ? OR cq.description LIKE ?)')
            keyword_pattern = f'%{keyword}%'
            params.extend([keyword_pattern, keyword_pattern])
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        # 获取总数（使用coding_questions表）
        count_query = f'SELECT COUNT(*) as total FROM coding_questions cq WHERE {where_clause}'
        count_row = db.execute(count_query, params).fetchone()
        # 安全地转换为字典
        if count_row:
            try:
                if isinstance(count_row, dict):
                    total = count_row.get('total', 0)
                elif hasattr(count_row, 'keys'):
                    total = dict(count_row).get('total', 0)
                else:
                    # 如果是元组或列表，尝试按索引访问
                    total = count_row[0] if isinstance(count_row, (tuple, list)) else 0
            except (TypeError, IndexError, AttributeError):
                total = 0
        else:
            total = 0
        
        # 获取分页数据（使用coding_questions和coding_subjects表）
        offset = (page - 1) * per_page
        query = f'''
            SELECT cq.*, cs.name as subject_name
            FROM coding_questions cq
            LEFT JOIN coding_subjects cs ON cq.coding_subject_id = cs.id
            WHERE {where_clause}
            ORDER BY cq.id DESC
            LIMIT ? OFFSET ?
        '''
        params.extend([per_page, offset])
        
        rows = db.execute(query, params).fetchall()
        questions = []
        
        for row in rows:
            # 将sqlite3.Row转换为字典（安全处理）
            try:
                if isinstance(row, dict):
                    question = row.copy()
                elif hasattr(row, 'keys'):
                    question = dict(row)
                else:
                    # 如果row不是预期的类型，跳过
                    continue
            except (TypeError, AttributeError) as e:
                import traceback
                from flask import current_app
                if current_app:
                    current_app.logger.warning(f"转换题目行数据失败: {e}\n{traceback.format_exc()}")
                continue
            
            # 确保question是字典类型
            if not isinstance(question, dict):
                continue
            
            # 确保有id字段
            if 'id' not in question:
                continue
            
            # coding_questions表使用title字段，不需要转换
            if not question.get('title'):
                question['title'] = question.get('content', '')
            
            # 计算统计信息（添加错误处理）
            try:
                stats = QuestionService.calculate_statistics(question['id'])
                if isinstance(stats, dict):
                    question['acceptance_rate'] = stats.get('acceptance_rate', 0)
                    question['total_submissions'] = stats.get('total_submissions', 0)
                else:
                    question['acceptance_rate'] = 0
                    question['total_submissions'] = 0
            except Exception as e:
                # 如果统计计算失败，设置默认值并记录错误
                import traceback
                from flask import current_app
                if current_app:
                    current_app.logger.warning(f"计算题目 {question.get('id', 'unknown')} 统计信息失败: {e}\n{traceback.format_exc()}")
                question['acceptance_rate'] = 0
                question['total_submissions'] = 0
            
            # 检查用户状态（是否完成、是否收藏）
            if user_id:
                # 检查是否收藏（favorites表可能还在使用questions.id，需要检查）
                favorite = db.execute(
                    'SELECT id FROM favorites WHERE user_id = ? AND question_id = ?',
                    (user_id, question['id'])
                ).fetchone()
                question['is_favorite'] = favorite is not None
                
                # 检查完成状态
                accepted = db.execute(
                    '''
                    SELECT id FROM code_submissions
                    WHERE user_id = ? AND question_id = ? AND status = 'accepted'
                    LIMIT 1
                    ''',
                    (user_id, question['id'])
                ).fetchone()
                
                if accepted:
                    question['status'] = 'solved'
                else:
                    # 检查是否有提交记录
                    submitted = db.execute(
                        '''
                        SELECT id FROM code_submissions
                        WHERE user_id = ? AND question_id = ?
                        LIMIT 1
                        ''',
                        (user_id, question['id'])
                    ).fetchone()
                    question['status'] = 'solving' if submitted else 'unsolved'
            else:
                question['is_favorite'] = False
                question['status'] = 'unsolved'
            
            # 解析JSON字段
            if question.get('test_cases_json'):
                try:
                    test_cases = json.loads(question['test_cases_json'])
                    # 检查test_cases是字典还是列表
                    if isinstance(test_cases, dict):
                        question['examples'] = test_cases.get('test_cases', [])
                    elif isinstance(test_cases, list):
                        # 如果直接是列表，使用它
                        question['examples'] = test_cases
                    else:
                        question['examples'] = []
                except (json.JSONDecodeError, TypeError, AttributeError):
                    question['examples'] = []
            else:
                question['examples'] = []
            
            questions.append(question)
        
        # 根据status筛选（在获取数据后筛选）
        if status and status != 'all' and user_id:
            if status == 'solved':
                questions = [q for q in questions if q.get('status') == 'solved']
            elif status == 'unsolved':
                questions = [q for q in questions if q.get('status') == 'unsolved']
            elif status == 'solving':
                questions = [q for q in questions if q.get('status') == 'solving']
        
        return {
            'questions': questions,
            'total': total,
            'page': page,
            'per_page': per_page
        }
    
    @staticmethod
    def get_question(
        question_id: int,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取题目详情
        
        Args:
            question_id: 题目ID
            user_id: 用户ID（可选）
        
        Returns:
            题目字典，如果不存在返回None
        """
        question = CodingQuestion.get_by_id(question_id)
        if not question:
            return None
        
        # coding_questions表已经有title和description字段
        if not question.get('title'):
            question['title'] = question.get('content', '')
        if not question.get('description'):
            question['description'] = question.get('explanation', '')
        
        # 解析JSON字段
        if question.get('test_cases_json'):
            try:
                test_cases = json.loads(question['test_cases_json'])
                # 检查test_cases是字典还是列表
                if isinstance(test_cases, dict):
                    question['examples'] = test_cases.get('test_cases', [])
                    # 尝试从test_cases中提取constraints（如果test_cases中有的话）
                    question['constraints'] = test_cases.get('constraints', [])
                elif isinstance(test_cases, list):
                    # 如果直接是列表，使用它
                    question['examples'] = test_cases
                    question['constraints'] = []
                else:
                    question['examples'] = []
                    question['constraints'] = []
            except (json.JSONDecodeError, TypeError, AttributeError):
                question['examples'] = []
                question['constraints'] = []
        else:
            question['examples'] = []
            question['constraints'] = []
        
        # 检查用户状态
        if user_id:
            db = get_db()
            # 检查是否收藏
            favorite = db.execute(
                'SELECT id FROM favorites WHERE user_id = ? AND question_id = ?',
                (user_id, question_id)
            ).fetchone()
            question['is_favorite'] = favorite is not None
        else:
            question['is_favorite'] = False
        
        return question
    
    @staticmethod
    def create_question(data: QuestionCreateSchema) -> Dict[str, Any]:
        """
        创建题目
        
        Args:
            data: 题目创建Schema
        
        Returns:
            创建的题目字典
        """
        db = get_db()
        
        # 将examples转换为JSON格式（如果需要）
        test_cases_data = {
            'test_cases': data.examples or [],
            'hidden_cases': []
        }
        
        # 如果test_cases_json已提供，使用它；否则使用examples
        if data.test_cases_json:
            try:
                test_cases_data = json.loads(data.test_cases_json)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 插入题目到coding_questions表
        cursor = db.execute(
            '''
            INSERT INTO coding_questions 
            (coding_subject_id, title, q_type, difficulty, code_template, 
             programming_language, time_limit, memory_limit, test_cases_json, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                data.subject_id,  # coding_subject_id
                data.title,
                data.q_type,  # 使用q_type字段（函数题或编程题）
                data.difficulty,
                data.code_template or '',
                data.programming_language,
                data.time_limit,
                data.memory_limit,
                json.dumps(test_cases_data, ensure_ascii=False),
                data.description
            )
        )
        db.commit()
        
        question_id = cursor.lastrowid
        return QuestionService.get_question(question_id)
    
    @staticmethod
    def update_question(
        question_id: int,
        data: QuestionUpdateSchema
    ) -> Dict[str, Any]:
        """
        更新题目
        
        Args:
            question_id: 题目ID
            data: 题目更新Schema
        
        Returns:
            更新后的题目字典
        """
        db = get_db()
        
        # 获取现有题目
        existing = QuestionService.get_question(question_id)
        if not existing:
            raise ValueError(f'题目 {question_id} 不存在')
        
        # 构建更新字段
        updates = []
        params = []
        
        if data.subject_id is not None:
            updates.append('coding_subject_id = ?')
            params.append(data.subject_id)
        
        if data.title is not None:
            updates.append('title = ?')
            params.append(data.title)
        
        if data.description is not None:
            updates.append('description = ?')
            params.append(data.description)
        
        if data.q_type is not None:
            updates.append('q_type = ?')
            params.append(data.q_type)
        
        if data.difficulty is not None:
            updates.append('difficulty = ?')
            params.append(data.difficulty)
        
        if data.code_template is not None:
            updates.append('code_template = ?')
            params.append(data.code_template)
        
        if data.programming_language is not None:
            updates.append('programming_language = ?')
            params.append(data.programming_language)
        
        if data.time_limit is not None:
            updates.append('time_limit = ?')
            params.append(data.time_limit)
        
        if data.memory_limit is not None:
            updates.append('memory_limit = ?')
            params.append(data.memory_limit)
        
        if data.test_cases_json is not None:
            updates.append('test_cases_json = ?')
            params.append(data.test_cases_json)
        
        if not updates:
            return existing
        
        params.append(question_id)
        update_query = f'''
            UPDATE coding_questions
            SET {', '.join(updates)}
            WHERE id = ?
        '''
        
        db.execute(update_query, params)
        db.commit()
        
        return QuestionService.get_question(question_id)
    
    @staticmethod
    def delete_question(question_id: int) -> bool:
        """
        删除题目（支持函数题和编程题）
        
        Args:
            question_id: 题目ID
        
        Returns:
            是否删除成功
        """
        db = get_db()
        cursor = db.execute(
            "DELETE FROM coding_questions WHERE id = ?",
            (question_id,)
        )
        db.commit()
        
        return cursor.rowcount > 0
    
    @staticmethod
    def calculate_statistics(question_id: int) -> Dict[str, Any]:
        """
        计算题目统计信息（通过率、提交次数）
        
        Args:
            question_id: 题目ID
        
        Returns:
            统计信息字典
        """
        db = get_db()
        
        # 总提交次数
        total_row = db.execute(
            'SELECT COUNT(*) as total FROM code_submissions WHERE question_id = ?',
            (question_id,)
        ).fetchone()
        # 安全地转换为字典
        if total_row:
            try:
                if isinstance(total_row, dict):
                    total_submissions = total_row.get('total', 0)
                elif hasattr(total_row, 'keys'):
                    total_submissions = dict(total_row).get('total', 0)
                else:
                    # 如果是元组或列表，尝试按索引访问
                    total_submissions = total_row[0] if isinstance(total_row, (tuple, list)) else 0
            except (TypeError, IndexError, AttributeError):
                total_submissions = 0
        else:
            total_submissions = 0
        
        # 通过次数
        accepted_row = db.execute(
            '''
            SELECT COUNT(*) as total 
            FROM code_submissions 
            WHERE question_id = ? AND status = 'accepted'
            ''',
            (question_id,)
        ).fetchone()
        # 安全地转换为字典
        if accepted_row:
            try:
                if isinstance(accepted_row, dict):
                    accepted_submissions = accepted_row.get('total', 0)
                elif hasattr(accepted_row, 'keys'):
                    accepted_submissions = dict(accepted_row).get('total', 0)
                else:
                    # 如果是元组或列表，尝试按索引访问
                    accepted_submissions = accepted_row[0] if isinstance(accepted_row, (tuple, list)) else 0
            except (TypeError, IndexError, AttributeError):
                accepted_submissions = 0
        else:
            accepted_submissions = 0
        
        # 计算通过率
        acceptance_rate = (
            accepted_submissions / total_submissions
            if total_submissions > 0 else 0.0
        )
        
        return {
            'total_submissions': total_submissions,
            'accepted_submissions': accepted_submissions,
            'acceptance_rate': round(acceptance_rate, 2)
        }

