# -*- coding: utf-8 -*-
"""编程题API路由"""
from flask import Blueprint, request, jsonify, session, current_app
from typing import Dict, Any
from app.core.utils.decorators import login_required
from app.modules.coding.services.code_executor import PythonExecutor
from app.modules.coding.services.judge_service import JudgeService
from app.modules.coding.services.question_service import QuestionService
from app.modules.coding.services.submission_service import SubmissionService
from app.modules.coding.schemas.submission_schemas import (
    ExecuteCodeSchema,
    SubmitCodeSchema
)
from app.core.extensions import limiter

coding_api_bp = Blueprint('coding_api', __name__)


# ==================== 题目相关API ====================

@coding_api_bp.route('/subjects', methods=['GET'])
@login_required
def api_get_subjects():
    """获取科目列表（用于筛选）"""
    try:
        from app.core.utils.database import get_db
        
        db = get_db()
        # 获取所有编程题科目（使用coding_subjects表）
        # 使用LEFT JOIN确保即使没有题目的科目也会显示
        rows = db.execute('''
            SELECT DISTINCT cs.id, cs.name
            FROM coding_subjects cs
            LEFT JOIN coding_questions cq ON cs.id = cq.coding_subject_id
            ORDER BY cs.id
        ''').fetchall()
        
        subjects = []
        for row in rows:
            try:
                subjects.append({
                    'id': int(row['id']),
                    'name': str(row['name']) if row['name'] else ''
                })
            except Exception as row_error:
                current_app.logger.error(f"处理行数据失败: {row_error}, row: {dict(row)}")
                continue
        
        return jsonify({
            'status': 'success',
            'data': {
                'subjects': subjects
            }
        }), 200
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        current_app.logger.error(f"获取科目列表失败: {e}\n{error_detail}")
        return jsonify({
            'status': 'error',
            'message': f'获取科目列表失败: {str(e)}'
        }), 500


@coding_api_bp.route('/subjects/stats', methods=['GET'])
@login_required
def api_get_subjects_stats():
    """获取科目统计信息（用于首页展示）"""
    try:
        from app.core.utils.database import get_db
        
        db = get_db()
        user_id = session.get('user_id')
        
        # 获取每个科目的统计信息（使用coding_subjects和coding_questions表）
        # 使用LEFT JOIN确保即使没有题目的科目也会显示
        rows = db.execute('''
            SELECT 
                cs.id,
                cs.name,
                COUNT(DISTINCT cq.id) as total_questions,
                COUNT(DISTINCT CASE WHEN sub.status = 'accepted' THEN cq.id END) as solved_questions,
                COUNT(DISTINCT sub.id) as total_submissions
            FROM coding_subjects cs
            LEFT JOIN coding_questions cq ON cs.id = cq.coding_subject_id
            LEFT JOIN code_submissions sub ON cq.id = sub.question_id AND sub.user_id = ?
            GROUP BY cs.id, cs.name
            ORDER BY cs.id
        ''', (user_id,)).fetchall()
        
        subjects = []
        for row in rows:
            total = row['total_questions'] or 0
            solved = row['solved_questions'] or 0
            subjects.append({
                'id': row['id'],
                'name': row['name'],
                'total_questions': total,
                'solved_questions': solved,
                'total_submissions': row['total_submissions'] or 0,
                'progress_rate': (solved / total * 100) if total > 0 else 0
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'subjects': subjects
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取科目统计失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取科目统计失败'
        }), 500


@coding_api_bp.route('/subjects/<int:subject_id>/overview', methods=['GET'])
@login_required
def api_get_subject_overview(subject_id: int):
    """获取题目集（科目）概述信息"""
    try:
        from app.core.utils.database import get_db
        
        db = get_db()
        user_id = session.get('user_id')
        
        # 获取科目基本信息（使用coding_subjects表）
        subject = db.execute(
            'SELECT * FROM coding_subjects WHERE id = ?', (subject_id,)
        ).fetchone()
        
        if not subject:
            return jsonify({
                'status': 'error',
                'message': '科目不存在'
            }), 404
        
        # 获取题目统计（使用coding_questions表）
        question_stats = db.execute('''
            SELECT 
                COUNT(DISTINCT cq.id) as total_questions,
                COUNT(DISTINCT CASE WHEN cs.status = 'accepted' THEN cq.id END) as solved_questions,
                COUNT(DISTINCT cs.id) as total_submissions
            FROM coding_questions cq
            LEFT JOIN code_submissions cs ON cq.id = cs.question_id AND cs.user_id = ?
            WHERE cq.coding_subject_id = ?
        ''', (user_id, subject_id)).fetchone()
        
        # 获取各题型统计（包含已解决数量）
        type_stats = db.execute('''
            SELECT 
                cq.difficulty,
                COUNT(DISTINCT cq.id) as total_count,
                COUNT(DISTINCT CASE WHEN cs.status = 'accepted' AND cs.user_id = ? THEN cs.question_id END) as solved_count
            FROM coding_questions cq
            LEFT JOIN code_submissions cs ON cq.id = cs.question_id
            WHERE cq.coding_subject_id = ?
            GROUP BY cq.difficulty
        ''', (user_id, subject_id)).fetchall()
        
        # 计算用户分数和排名（使用coding_questions表）
        user_score = db.execute('''
            SELECT 
                COUNT(DISTINCT cs.question_id) as solved_count,
                SUM(CASE WHEN cs.status = 'accepted' THEN 1 ELSE 0 END) as accepted_count
            FROM code_submissions cs
            INNER JOIN coding_questions cq ON cs.question_id = cq.id
            WHERE cs.user_id = ? AND cq.coding_subject_id = ?
        ''', (user_id, subject_id)).fetchone()
        
        # 计算排名（基于已解决题目数）
        rank_result = db.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM (
                SELECT user_id, COUNT(DISTINCT question_id) as solved
                FROM code_submissions cs
                INNER JOIN coding_questions cq ON cs.question_id = cq.id
                WHERE cs.status = 'accepted' AND cq.coding_subject_id = ?
                GROUP BY user_id
                HAVING solved > (
                    SELECT COUNT(DISTINCT question_id)
                    FROM code_submissions cs2
                    INNER JOIN coding_questions cq2 ON cs2.question_id = cq2.id
                    WHERE cs2.user_id = ? AND cs2.status = 'accepted' 
                    AND cq2.coding_subject_id = ?
                )
            )
        ''', (subject_id, user_id, subject_id)).fetchone()
        
        # 获取用户首次提交时间
        first_submission = db.execute('''
            SELECT MIN(cs.submitted_at) as first_submitted_at
            FROM code_submissions cs
            INNER JOIN coding_questions cq ON cs.question_id = cq.id
            WHERE cs.user_id = ? AND cq.coding_subject_id = ?
        ''', (user_id, subject_id)).fetchone()
        
        # 获取总参与人数
        total_participants = db.execute('''
            SELECT COUNT(DISTINCT cs.user_id) as count
            FROM code_submissions cs
            INNER JOIN coding_questions cq ON cs.question_id = cq.id
            WHERE cq.coding_subject_id = ?
        ''', (subject_id,)).fetchone()
        
        # 构建题型统计
        difficulty_stats = {}
        for stat in type_stats:
            stat_dict = dict(stat) if stat else {}
            difficulty = stat_dict.get('difficulty') or 'easy'
            difficulty_stats[difficulty] = {
                'total': stat_dict.get('total_count', 0) or 0,
                'solved': stat_dict.get('solved_count', 0) or 0
            }
        
        # 安全地获取字段值（sqlite3.Row对象不支持.get()方法）
        subject_dict = dict(subject) if subject else {}
        question_stats_dict = dict(question_stats) if question_stats else {}
        user_score_dict = dict(user_score) if user_score else {}
        rank_result_dict = dict(rank_result) if rank_result else {}
        total_participants_dict = dict(total_participants) if total_participants else {}
        first_submission_dict = dict(first_submission) if first_submission else {}
        
        overview = {
            'subject': {
                'id': subject_dict.get('id', 0),
                'name': subject_dict.get('name', ''),
                'description': subject_dict.get('description', '')
            },
            'question_stats': {
                'total': question_stats_dict.get('total_questions', 0) or 0,
                'solved': question_stats_dict.get('solved_questions', 0) or 0,
                'total_submissions': question_stats_dict.get('total_submissions', 0) or 0,
                'difficulty_stats': difficulty_stats
            },
            'user_stats': {
                'score': user_score_dict.get('solved_count', 0) or 0,
                'solved_count': user_score_dict.get('accepted_count', 0) or 0,
                'rank': rank_result_dict.get('rank', 0) or 0,
                'total_participants': total_participants_dict.get('count', 0) or 0,
                'first_submitted_at': first_submission_dict.get('first_submitted_at') if first_submission_dict.get('first_submitted_at') else None,
                'progress_rate': (question_stats_dict.get('solved_questions', 0) / question_stats_dict.get('total_questions', 1) * 100) if question_stats_dict.get('total_questions', 0) > 0 else 0
            },
            'status': {
                'is_open': True,  # 默认开放，可以根据实际业务逻辑判断
                'type': 'fixed',  # 固定时间类型
                'set_type': 'normal'  # 普通题目集
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': overview
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取题目集概述失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目集概述失败'
        }), 500


@coding_api_bp.route('/questions', methods=['GET'])
@login_required
def api_get_questions():
    """获取题目列表"""
    try:
        subject_id = request.args.get('subject', type=int)
        difficulty = request.args.get('difficulty')
        status = request.args.get('status', 'all')
        keyword = request.args.get('keyword', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        user_id = session.get('user_id')
        result = QuestionService.get_questions(
            subject_id=subject_id,
            difficulty=difficulty,
            status=status,
            keyword=keyword,
            page=page,
            per_page=per_page,
            user_id=user_id
        )
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        current_app.logger.error(f"获取题目列表失败: {e}\n{error_detail}", exc_info=True)
        # 在开发环境下返回详细错误信息
        error_message = '获取题目列表失败'
        if current_app.config.get('DEBUG', False):
            error_message = f'获取题目列表失败: {str(e)}\n{error_detail}'
        return jsonify({
            'status': 'error',
            'message': error_message
        }), 500


@coding_api_bp.route('/questions/<int:question_id>', methods=['GET'])
@login_required
def api_get_question(question_id: int):
    """获取题目详情"""
    try:
        user_id = session.get('user_id')
        question = QuestionService.get_question(question_id, user_id=user_id)
        
        if not question:
            return jsonify({
                'status': 'error',
                'message': '题目不存在'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': question
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取题目详情失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目详情失败'
        }), 500


# ==================== 代码执行API ====================

@coding_api_bp.route('/execute', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def api_execute():
    """运行代码（不判题）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        # 使用Pydantic验证
        try:
            schema = ExecuteCodeSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        # 执行代码
        executor = PythonExecutor(
            time_limit=schema.time_limit or 5,
            output_limit=10000
        )
        result = executor.execute(
            code=schema.code,
            language=schema.language,
            input_data=schema.input
        )
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"代码执行失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '代码执行失败'
        }), 500


@coding_api_bp.route('/submit', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def api_submit():
    """提交代码（自动判题）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        # 使用Pydantic验证
        try:
            schema = SubmitCodeSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401
        
        # 判题
        judge_service = JudgeService()
        judge_result = judge_service.judge(
            question_id=schema.question_id,
            code=schema.code,
            language=schema.language
        )
        
        # 创建提交记录
        submission = SubmissionService.create_submission(
            user_id=user_id,
            question_id=schema.question_id,
            code=schema.code,
            language=schema.language,
            judge_result=judge_result
        )
        
        # 获取题目信息以返回完整数据
        from app.modules.coding.models.coding_question import CodingQuestion
        question = CodingQuestion.get_by_id(schema.question_id)
        
        # 计算得分
        passed_cases = judge_result.get('passed_cases', 0)
        total_cases = judge_result.get('total_cases', 1)
        score = (passed_cases / total_cases * 100.0) if total_cases > 0 else 0.0
        
        return jsonify({
            'status': 'success',
            'data': {
                'submission_id': submission['id'],
                'status': judge_result['status'],
                'passed_cases': passed_cases,
                'total_cases': total_cases,
                'execution_time': judge_result.get('execution_time', 0),
                'error_message': judge_result.get('error_message', ''),
                'score': score,
                'total_score': 100.0,  # 总分固定为100
                'time_limit': question.get('time_limit', 5) * 1000 if question else 5000,  # 转换为毫秒
                'memory_limit': question.get('memory_limit', 128) * 1024 if question else 131072,  # 转换为KB
                'memory_used': 0,  # 当前不支持内存统计
                'test_results': judge_result.get('test_results', [])  # 测试用例详细结果
            }
        }), 200
    
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"提交代码失败: {e}", exc_info=True)
        # 返回更详细的错误信息（开发环境）
        error_message = '提交代码失败'
        if current_app.config.get('DEBUG', False):
            error_message = f'提交代码失败: {str(e)}'
        return jsonify({
            'status': 'error',
            'message': error_message
        }), 500


# ==================== 代码草稿API ====================

@coding_api_bp.route('/drafts/<int:question_id>', methods=['GET'])
@login_required
def api_get_draft(question_id: int):
    """获取代码草稿"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401
        
        from app.core.utils.database import get_db
        db = get_db()
        
        row = db.execute(
            'SELECT code, language FROM code_drafts WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        ).fetchone()
        
        if row:
            return jsonify({
                'status': 'success',
                'data': {
                    'code': row['code'],
                    'language': row['language'] or 'python'
                }
            }), 200
        else:
            return jsonify({
                'status': 'success',
                'data': {
                    'code': '',
                    'language': 'python'
                }
            }), 200
    except Exception as e:
        current_app.logger.error(f"获取代码草稿失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取代码草稿失败'
        }), 500


@coding_api_bp.route('/drafts/<int:question_id>', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def api_save_draft(question_id: int):
    """保存代码草稿"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        from app.core.utils.database import get_db
        db = get_db()
        
        # 使用 INSERT OR REPLACE 来更新或插入草稿
        db.execute('''
            INSERT OR REPLACE INTO code_drafts (user_id, question_id, code, language, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, question_id, code, language))
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': '代码已保存'
        }), 200
    except Exception as e:
        current_app.logger.error(f"保存代码草稿失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '保存代码草稿失败'
        }), 500


@coding_api_bp.route('/drafts/<int:question_id>', methods=['DELETE'])
@login_required
def api_delete_draft(question_id: int):
    """删除代码草稿"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401
        
        from app.core.utils.database import get_db
        db = get_db()
        
        db.execute(
            'DELETE FROM code_drafts WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        )
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': '草稿已删除'
        }), 200
    except Exception as e:
        current_app.logger.error(f"删除代码草稿失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除代码草稿失败'
        }), 500


# ==================== 提交历史API ====================

@coding_api_bp.route('/submissions', methods=['GET'])
@login_required
def api_get_submissions():
    """获取提交历史"""
    try:
        user_id = session.get('user_id')
        question_id = request.args.get('question_id', type=int)
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        result = SubmissionService.get_submissions(
            user_id=user_id,
            question_id=question_id,
            status=status,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取提交历史失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取提交历史失败'
        }), 500


@coding_api_bp.route('/submissions/<int:submission_id>', methods=['GET'])
@login_required
def api_get_submission(submission_id: int):
    """获取提交详情"""
    try:
        user_id = session.get('user_id')
        submission = SubmissionService.get_submission(submission_id, user_id=user_id)
        
        if not submission:
            return jsonify({
                'status': 'error',
                'message': '提交记录不存在'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': submission
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取提交详情失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取提交详情失败'
        }), 500


# ==================== 统计API ====================

@coding_api_bp.route('/statistics', methods=['GET'])
@login_required
def api_get_statistics():
    """获取用户统计"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '请先登录'
            }), 401
        
        stats = SubmissionService.get_user_statistics(user_id)
        
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取统计信息失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取统计信息失败'
        }), 500


@coding_api_bp.route('/questions/<int:question_id>/rankings', methods=['GET'])
@login_required
def api_get_question_rankings(question_id: int):
    """获取题目排名（按得分排序）"""
    try:
        from app.core.utils.database import get_db
        
        db = get_db()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        offset = (page - 1) * per_page
        
        # 获取每个用户的最佳提交（按得分排序，使用score字段）
        # 按首次通过时间排序（最快通过的在前）
        rankings = db.execute('''
            SELECT 
                cs.user_id,
                u.username,
                MAX(cs.score) as best_score,
                MAX(CASE WHEN cs.status = 'accepted' THEN cs.score ELSE 0 END) as accepted_score,
                MIN(CASE WHEN cs.status = 'accepted' THEN cs.execution_time ELSE NULL END) as best_time,
                MIN(CASE WHEN cs.status = 'accepted' THEN cs.submitted_at ELSE NULL END) as first_accepted_at,
                COUNT(*) as total_submissions,
                MAX(cs.submitted_at) as last_submitted_at
            FROM code_submissions cs
            INNER JOIN users u ON cs.user_id = u.id
            WHERE cs.question_id = ?
            GROUP BY cs.user_id, u.username
            ORDER BY 
                accepted_score DESC,
                best_score DESC,
                best_time ASC,
                first_accepted_at ASC
            LIMIT ? OFFSET ?
        ''', (question_id, per_page, offset)).fetchall()
        
        # 获取总数
        total = db.execute('''
            SELECT COUNT(DISTINCT user_id) as count
            FROM code_submissions
            WHERE question_id = ?
        ''', (question_id,)).fetchone()
        
        # 获取当前用户的排名
        current_user_id = session.get('user_id')
        user_rank = None
        if current_user_id:
            user_best = db.execute('''
                SELECT 
                    MAX(cs.score) as best_score,
                    MAX(CASE WHEN cs.status = 'accepted' THEN cs.score ELSE 0 END) as accepted_score,
                    MIN(CASE WHEN cs.status = 'accepted' THEN cs.execution_time ELSE NULL END) as best_time
                FROM code_submissions cs
                WHERE cs.question_id = ? AND cs.user_id = ?
            ''', (question_id, current_user_id)).fetchone()
            
            if user_best and user_best['accepted_score']:
                rank_result = db.execute('''
                    SELECT COUNT(*) + 1 as rank
                    FROM (
                        SELECT 
                            cs.user_id,
                            MAX(CASE WHEN cs.status = 'accepted' THEN cs.score ELSE 0 END) as accepted_score,
                            MIN(CASE WHEN cs.status = 'accepted' THEN cs.execution_time ELSE NULL END) as best_time
                        FROM code_submissions cs
                        WHERE cs.question_id = ?
                        GROUP BY cs.user_id
                        HAVING accepted_score > ? OR (accepted_score = ? AND best_time < ?)
                    )
                ''', (question_id, user_best['accepted_score'], user_best['accepted_score'], user_best['best_time'] or 999999)).fetchone()
                user_rank = rank_result['rank'] if rank_result else None
        
        result = []
        for idx, row in enumerate(rankings, start=offset + 1):
            result.append({
                'rank': idx,
                'user_id': row['user_id'],
                'username': row['username'],
                'best_score': round(row['best_score'], 2) if row['best_score'] else 0,
                'accepted_score': round(row['accepted_score'], 2) if row['accepted_score'] else 0,
                'best_time': round(row['best_time'], 3) if row['best_time'] else None,
                'first_accepted_at': row['first_accepted_at'],
                'total_submissions': row['total_submissions'],
                'last_submitted_at': row['last_submitted_at']
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'rankings': result,
                'total': total['count'] if total else 0,
                'page': page,
                'per_page': per_page,
                'user_rank': user_rank
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取题目排名失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目排名失败'
        }), 500

