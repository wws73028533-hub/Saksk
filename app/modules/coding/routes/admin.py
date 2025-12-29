# -*- coding: utf-8 -*-
"""编程题管理端路由"""
from flask import Blueprint, request, jsonify, session, current_app, render_template
from typing import Dict, Any
from app.core.utils.decorators import admin_required
from app.modules.coding.services.question_service import QuestionService
from app.modules.coding.schemas.question_schemas import (
    QuestionCreateSchema,
    QuestionUpdateSchema
)

coding_admin_bp = Blueprint('coding_admin', __name__)


# ==================== 管理端页面路由 ====================

@coding_admin_bp.route('/')
@admin_required
def admin_coding_dashboard():
    """编程管理主页面（集成所有管理功能）"""
    return render_template('admin/coding/dashboard.html')


@coding_admin_bp.route('/subjects')
@admin_required
def admin_subjects_page():
    """题目集（科目）管理页面（独立页面，保留兼容性）"""
    return render_template('admin/coding/subjects.html')


@coding_admin_bp.route('/questions')
@admin_required
def admin_questions_page():
    """题目管理页面（独立页面，保留兼容性）"""
    subject_id = request.args.get('subject', type=int)
    return render_template('admin/coding/questions.html', subject_id=subject_id or 0)


# ==================== 题目集管理API ====================

@coding_admin_bp.route('/api/subjects', methods=['GET'])
@admin_required
def api_get_subjects():
    """获取题目集列表（管理端）"""
    try:
        from app.core.utils.database import get_db
        import sqlite3
        
        db = get_db()
        
        # 使用 coding_subjects 和 coding_questions 表
        rows = db.execute('''
            SELECT 
                s.id,
                s.name,
                s.description,
                s.is_locked,
                s.created_at,
                COUNT(DISTINCT CASE WHEN q.q_type = '函数题' THEN q.id END) as function_count,
                COUNT(DISTINCT CASE WHEN q.q_type = '编程题' THEN q.id END) as coding_count,
                COUNT(DISTINCT q.id) as total_count
            FROM coding_subjects s
            LEFT JOIN coding_questions q ON s.id = q.coding_subject_id
            GROUP BY s.id, s.name, s.description, s.is_locked, s.created_at
            ORDER BY s.id
        ''').fetchall()
        
        subjects = []
        for row in rows:
            try:
                is_locked = row['is_locked']
                if is_locked is None:
                    is_locked = False
                else:
                    is_locked = bool(is_locked)
                
                subjects.append({
                    'id': int(row['id']),
                    'name': str(row['name']) if row['name'] else '',
                    'description': str(row['description']) if row['description'] else '',
                    'is_locked': is_locked,
                    'created_at': str(row['created_at']) if row['created_at'] else '',
                    'function_count': int(row['function_count']) if row['function_count'] else 0,
                    'coding_count': int(row['coding_count']) if row['coding_count'] else 0,
                    'total_count': int(row['total_count']) if row['total_count'] else 0
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
        current_app.logger.error(f"获取题目集列表失败: {e}\n{error_detail}")
        return jsonify({
            'status': 'error',
            'message': f'获取题目集列表失败: {str(e)}'
        }), 500


@coding_admin_bp.route('/api/subjects', methods=['POST'])
@admin_required
def api_create_subject():
    """创建题目集"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        is_locked = data.get('is_locked', False)
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': '题目集名称不能为空'
            }), 400
        
        from app.core.utils.database import get_db
        db = get_db()
        
        try:
            # 检查 description 字段是否存在
            try:
                db.execute("SELECT description FROM subjects LIMIT 1").fetchone()
                has_description = True
            except:
                has_description = False
            
            # 使用 coding_subjects 表
            db.execute('''
                INSERT INTO coding_subjects (name, description, is_locked)
                VALUES (?, ?, ?)
            ''', (name, description, 1 if is_locked else 0))
            db.commit()
            
            # 获取新创建的题目集
            new_subject = db.execute('''
                SELECT * FROM coding_subjects WHERE id = last_insert_rowid()
            ''').fetchone()
            
            return jsonify({
                'status': 'success',
                'message': '题目集创建成功',
                'data': dict(new_subject)
            }), 201
        except Exception as e:
            db.rollback()
            if 'UNIQUE constraint' in str(e):
                return jsonify({
                    'status': 'error',
                    'message': '题目集名称已存在'
                }), 400
            raise
    
    except Exception as e:
        current_app.logger.error(f"创建题目集失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '创建题目集失败'
        }), 500


@coding_admin_bp.route('/api/subjects/<int:subject_id>', methods=['PUT'])
@admin_required
def api_update_subject(subject_id: int):
    """更新题目集"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        is_locked = data.get('is_locked', False)
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': '题目集名称不能为空'
            }), 400
        
        from app.core.utils.database import get_db
        db = get_db()
        
        try:
            # 检查 description 字段是否存在
            try:
                db.execute("SELECT description FROM subjects LIMIT 1").fetchone()
                has_description = True
            except:
                has_description = False
            
            if has_description:
                db.execute('''
                    UPDATE subjects
                    SET name = ?, description = ?, is_locked = ?
                    WHERE id = ?
                ''', (name, description, 1 if is_locked else 0, subject_id))
            else:
                db.execute('''
                    UPDATE subjects
                    SET name = ?, is_locked = ?
                    WHERE id = ?
                ''', (name, 1 if is_locked else 0, subject_id))
            db.commit()
            
            # 获取更新后的题目集
            updated_subject = db.execute('''
                SELECT * FROM subjects WHERE id = ?
            ''', (subject_id,)).fetchone()
            
            if not updated_subject:
                return jsonify({
                    'status': 'error',
                    'message': '题目集不存在'
                }), 404
            
            return jsonify({
                'status': 'success',
                'message': '题目集更新成功',
                'data': dict(updated_subject)
            }), 200
        except Exception as e:
            db.rollback()
            if 'UNIQUE constraint' in str(e):
                return jsonify({
                    'status': 'error',
                    'message': '题目集名称已存在'
                }), 400
            raise
    
    except Exception as e:
        current_app.logger.error(f"更新题目集失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '更新题目集失败'
        }), 500


@coding_admin_bp.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
@admin_required
def api_delete_subject(subject_id: int):
    """删除题目集"""
    try:
        from app.core.utils.database import get_db
        db = get_db()
        
        # 检查是否有题目关联
        question_count = db.execute('''
            SELECT COUNT(*) as count FROM coding_questions WHERE coding_subject_id = ?
        ''', (subject_id,)).fetchone()
        
        if question_count['count'] > 0:
            return jsonify({
                'status': 'error',
                'message': f'该题目集下还有 {question_count["count"]} 道题目，无法删除'
            }), 400
        
        db.execute('DELETE FROM coding_subjects WHERE id = ?', (subject_id,))
        db.commit()
        
        return jsonify({
            'status': 'success',
            'message': '题目集删除成功'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"删除题目集失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除题目集失败'
        }), 500


# ==================== 题目管理API ====================

@coding_admin_bp.route('/api/questions', methods=['GET'])
@admin_required
def api_get_questions():
    """获取题目列表（管理端）"""
    try:
        subject_id = request.args.get('subject_id', type=int)
        q_type = request.args.get('q_type')  # 题目类型：函数题/编程题
        difficulty = request.args.get('difficulty')
        is_enabled = request.args.get('is_enabled')
        keyword = request.args.get('keyword', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        from app.core.utils.database import get_db
        db = get_db()
        
        # 构建查询条件
        where_clauses = []
        params = []
        
        if subject_id:
            where_clauses.append('q.coding_subject_id = ?')
            params.append(subject_id)
        
        if q_type:
            where_clauses.append('q.q_type = ?')
            params.append(q_type)
        # 注意：coding_questions表的所有题目都是函数题或编程题，不需要额外过滤
        
        if difficulty:
            where_clauses.append('q.difficulty = ?')
            params.append(difficulty)
        
        if is_enabled is not None:
            where_clauses.append('q.is_enabled = ?')
            params.append(1 if is_enabled else 0)
        
        if keyword:
            where_clauses.append('(q.title LIKE ? OR q.description LIKE ?)')
            params.extend([f'%{keyword}%', f'%{keyword}%'])
        
        where_clause = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        # 获取总数 - 使用 coding_questions 表
        total_row = db.execute(f'''
            SELECT COUNT(*) as count
            FROM coding_questions q
            WHERE {where_clause}
        ''', params).fetchone()
        total = dict(total_row).get('count', 0) if total_row else 0
        
        # 获取题目列表 - 使用 coding_questions 和 coding_subjects 表
        offset = (page - 1) * per_page
        rows = db.execute(f'''
            SELECT 
                q.*,
                s.name as subject_name,
                COUNT(DISTINCT cs.id) as total_submissions,
                COUNT(DISTINCT CASE WHEN cs.status = 'accepted' THEN cs.id END) as accepted_submissions
            FROM coding_questions q
            LEFT JOIN coding_subjects s ON q.coding_subject_id = s.id
            LEFT JOIN code_submissions cs ON q.id = cs.question_id
            WHERE {where_clause}
            GROUP BY q.id
            ORDER BY q.id DESC
            LIMIT ? OFFSET ?
        ''', params + [per_page, offset]).fetchall()
        
        questions = []
        for row in rows:
            # 将sqlite3.Row转换为字典
            row_dict = dict(row)
            
            total_sub = row_dict.get('total_submissions', 0) or 0
            accepted_sub = row_dict.get('accepted_submissions', 0) or 0
            acceptance_rate = (accepted_sub / total_sub) if total_sub > 0 else None
            
            questions.append({
                'id': row_dict.get('id', 0),
                'subject_id': row_dict.get('coding_subject_id', 0),
                'subject_name': row_dict.get('subject_name', ''),
                'title': row_dict.get('title', ''),
                'content': row_dict.get('title', ''),  # 兼容旧字段名
                'q_type': row_dict.get('q_type', '编程题'),
                'description': row_dict.get('description', ''),
                'difficulty': row_dict.get('difficulty', 'easy'),
                'code_template': row_dict.get('code_template', ''),
                'test_cases_json': row_dict.get('test_cases_json', ''),
                'is_enabled': bool(row_dict.get('is_enabled', 1)),
                'total_submissions': total_sub,
                'acceptance_rate': acceptance_rate
            })
        
        return jsonify({
            'status': 'success',
            'data': {
                'questions': questions,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"获取题目列表失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取题目列表失败'
        }), 500


@coding_admin_bp.route('/api/questions', methods=['POST'])
@admin_required
def api_create_question():
    """创建题目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        # 使用Pydantic验证
        try:
            schema = QuestionCreateSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        question = QuestionService.create_question(schema)
        
        return jsonify({
            'status': 'success',
            'message': '题目创建成功',
            'data': question
        }), 201
    
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"创建题目失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '创建题目失败'
        }), 500


@coding_admin_bp.route('/api/questions/<int:question_id>', methods=['PUT'])
@admin_required
def api_update_question(question_id: int):
    """更新题目"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        # 使用Pydantic验证
        try:
            schema = QuestionUpdateSchema.model_validate(data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据验证失败: {str(e)}'
            }), 400
        
        question = QuestionService.update_question(question_id, schema)
        
        return jsonify({
            'status': 'success',
            'message': '题目更新成功',
            'data': question
        }), 200
    
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"更新题目失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '更新题目失败'
        }), 500


@coding_admin_bp.route('/api/questions/<int:question_id>', methods=['DELETE'])
@admin_required
def api_delete_question(question_id: int):
    """删除题目"""
    try:
        success = QuestionService.delete_question(question_id)
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': '题目不存在或删除失败'
            }), 404
        
        return jsonify({
            'status': 'success',
            'message': '题目删除成功'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"删除题目失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '删除题目失败'
        }), 500


@coding_admin_bp.route('/api/questions/batch_delete', methods=['POST'])
@admin_required
def api_batch_delete_questions():
    """批量删除题目"""
    try:
        data = request.get_json()
        if not data or 'ids' not in data:
            return jsonify({
                'status': 'error',
                'message': '请求数据不能为空'
            }), 400
        
        ids = data.get('ids', [])
        if not isinstance(ids, list) or len(ids) == 0:
            return jsonify({
                'status': 'error',
                'message': '请提供要删除的题目ID列表'
            }), 400
        
        deleted_count = 0
        for question_id in ids:
            if QuestionService.delete_question(question_id):
                deleted_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'成功删除 {deleted_count} 道题目',
            'data': {
                'deleted_count': deleted_count,
                'total_count': len(ids)
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"批量删除题目失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '批量删除题目失败'
        }), 500

