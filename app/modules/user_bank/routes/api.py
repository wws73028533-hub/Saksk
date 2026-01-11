# -*- coding: utf-8 -*-
"""用户题库API路由"""
import json
import random
import string
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app, g
from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id, jwt_required

user_bank_api_bp = Blueprint('user_bank_api', __name__)

# 兼容小程序端的返回结构：小程序侧 request() 以 status=success/error 判断成功与否。
# 该模块历史返回为 {code: 0/1, ...}，这里在不破坏原有字段的前提下补齐 status 字段。
@user_bank_api_bp.after_request
def _compat_add_status_field(response):
    try:
        if not response.is_json:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict):
            return response
        if 'status' in payload or 'code' not in payload:
            return response

        payload['status'] = 'success' if payload.get('code') == 0 else 'error'
        response.set_data(json.dumps(payload, ensure_ascii=False))
    except Exception:
        return response
    return response

# ============================================
# 工具函数
# ============================================

def generate_share_code(length=6):
    """生成6位大写字母+数字分享码"""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        # 确保至少包含1个字母和1个数字
        if any(c.isalpha() for c in code) and any(c.isdigit() for c in code):
            return code


def check_bank_access(user_id, bank_id):
    """
    检查用户是否有权访问题库
    返回: (has_access: bool, permission: str, access_type: str)
    """
    conn = get_db()
    bank = conn.execute(
        'SELECT * FROM user_question_banks WHERE id = ?',
        (bank_id,)
    ).fetchone()

    if not bank or bank['status'] == 0:
        return (False, None, None)

    # 1. 创建者：完全权限
    if bank['user_id'] == user_id:
        return (True, 'owner', 'owner')

    # 2. 公开题库：所有登录用户可访问
    if bank['is_public']:
        permission = 'copy' if bank['allow_copy'] else 'read'
        return (True, permission, 'public')

    # 3. 分享授权：检查分享记录
    share_record = conn.execute('''
        SELECT bsr.*, bs.permission, bs.is_active, bs.expires_at
        FROM bank_share_records bsr
        JOIN bank_shares bs ON bsr.share_id = bs.id
        WHERE bsr.user_id = ? AND bsr.bank_id = ? AND bsr.status = 1
    ''', (user_id, bank_id)).fetchone()

    if share_record:
        share_active = share_record['is_active']
        expires_at = share_record['expires_at']
        if share_active and (not expires_at or datetime.fromisoformat(expires_at) > datetime.now()):
            return (True, share_record['permission'], 'shared')

    # 4. 未授权
    return (False, None, None)


def get_bank_category_name(category_id, user_id):
    """获取分类名称"""
    if not category_id:
        return None
    conn = get_db()
    cat = conn.execute(
        'SELECT name FROM user_bank_categories WHERE id = ? AND user_id = ?',
        (category_id, user_id)
    ).fetchone()
    return cat['name'] if cat else None


# ============================================
# 题库分类管理 API
# ============================================

@user_bank_api_bp.route('/categories', methods=['GET'])
@auth_required
def get_categories():
    """获取分类列表"""
    user_id = current_user_id()
    conn = get_db()

    categories = conn.execute('''
        SELECT c.*,
               (SELECT COUNT(*) FROM user_question_banks WHERE category_id = c.id AND status = 1) as bank_count
        FROM user_bank_categories c
        WHERE c.user_id = ?
        ORDER BY c.sort_order ASC, c.id ASC
    ''', (user_id,)).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'categories': [dict(c) for c in categories]
        }
    })


@user_bank_api_bp.route('/categories', methods=['POST'])
@auth_required
def create_category():
    """创建分类"""
    user_id = current_user_id()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'code': 1, 'message': '分类名称不能为空'}), 400
    if len(name) > 50:
        return jsonify({'code': 1, 'message': '分类名称不能超过50个字符'}), 400

    conn = get_db()

    # 检查分类数量限制
    count = conn.execute(
        'SELECT COUNT(*) as cnt FROM user_bank_categories WHERE user_id = ?',
        (user_id,)
    ).fetchone()['cnt']

    if count >= 10:
        return jsonify({'code': 1, 'message': '最多只能创建10个分类'}), 400

    # 检查重复
    existing = conn.execute(
        'SELECT id FROM user_bank_categories WHERE user_id = ? AND name = ?',
        (user_id, name)
    ).fetchone()

    if existing:
        return jsonify({'code': 1, 'message': '分类名称已存在'}), 400

    cursor = conn.execute(
        '''INSERT INTO user_bank_categories (user_id, name, description, sort_order)
           VALUES (?, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_categories WHERE user_id = ?))''',
        (user_id, name, description, user_id)
    )
    conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'id': cursor.lastrowid,
            'name': name
        }
    })


@user_bank_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@auth_required
def update_category(category_id):
    """编辑分类"""
    user_id = current_user_id()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'code': 1, 'message': '分类名称不能为空'}), 400

    conn = get_db()

    # 检查分类是否存在且属于当前用户
    cat = conn.execute(
        'SELECT id FROM user_bank_categories WHERE id = ? AND user_id = ?',
        (category_id, user_id)
    ).fetchone()

    if not cat:
        return jsonify({'code': 1, 'message': '分类不存在'}), 404

    # 检查重复
    existing = conn.execute(
        'SELECT id FROM user_bank_categories WHERE user_id = ? AND name = ? AND id != ?',
        (user_id, name, category_id)
    ).fetchone()

    if existing:
        return jsonify({'code': 1, 'message': '分类名称已存在'}), 400

    conn.execute(
        '''UPDATE user_bank_categories SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND user_id = ?''',
        (name, description, category_id, user_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '更新成功'})


@user_bank_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@auth_required
def delete_category(category_id):
    """删除分类"""
    user_id = current_user_id()
    conn = get_db()

    # 检查分类是否存在
    cat = conn.execute(
        'SELECT id FROM user_bank_categories WHERE id = ? AND user_id = ?',
        (category_id, user_id)
    ).fetchone()

    if not cat:
        return jsonify({'code': 1, 'message': '分类不存在'}), 404

    # 检查是否有题库使用此分类
    bank_count = conn.execute(
        'SELECT COUNT(*) as cnt FROM user_question_banks WHERE category_id = ? AND status = 1',
        (category_id,)
    ).fetchone()['cnt']

    if bank_count > 0:
        return jsonify({'code': 1, 'message': f'该分类下还有{bank_count}个题库，请先移除'}), 400

    conn.execute('DELETE FROM user_bank_categories WHERE id = ?', (category_id,))
    conn.commit()

    return jsonify({'code': 0, 'message': '删除成功'})


# ============================================
# 用户题库管理 API
# ============================================

@user_bank_api_bp.route('/list', methods=['GET'])
@auth_required
def get_banks():
    """获取我的题库列表"""
    user_id = current_user_id()
    category_id = request.args.get('category_id', type=int)
    is_public = request.args.get('is_public', type=int)

    conn = get_db()

    query = '''
        SELECT b.*, c.name as category_name
        FROM user_question_banks b
        LEFT JOIN user_bank_categories c ON b.category_id = c.id
        WHERE b.user_id = ? AND b.status = 1
    '''
    params = [user_id]

    if category_id is not None:
        query += ' AND b.category_id = ?'
        params.append(category_id)

    if is_public is not None:
        query += ' AND b.is_public = ?'
        params.append(is_public)

    query += ' ORDER BY b.updated_at DESC'

    banks = conn.execute(query, params).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'banks': [dict(b) for b in banks],
            'total': len(banks)
        }
    })


@user_bank_api_bp.route('/<int:bank_id>', methods=['GET'])
@auth_required
def get_bank_detail(bank_id):
    """获取题库详情"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()
    bank = conn.execute('''
        SELECT b.*, c.name as category_name, u.username as owner_username
        FROM user_question_banks b
        LEFT JOIN user_bank_categories c ON b.category_id = c.id
        LEFT JOIN users u ON b.user_id = u.id
        WHERE b.id = ?
    ''', (bank_id,)).fetchone()

    result = dict(bank)
    result['permission'] = permission
    result['access_type'] = access_type

    # 获取题库中的题型列表
    types_result = conn.execute('''
        SELECT DISTINCT q_type FROM user_bank_questions
        WHERE bank_id = ? AND q_type IS NOT NULL AND q_type != ''
        ORDER BY q_type
    ''', (bank_id,)).fetchall()
    result['available_types'] = [t['q_type'] for t in types_result]

    return jsonify({
        'code': 0,
        'data': result
    })


@user_bank_api_bp.route('', methods=['POST'])
@auth_required
def create_bank():
    """创建题库"""
    user_id = current_user_id()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    category_id = data.get('category_id')

    if not name:
        return jsonify({'code': 1, 'message': '题库名称不能为空'}), 400
    if len(name) < 2 or len(name) > 50:
        return jsonify({'code': 1, 'message': '题库名称需要2-50个字符'}), 400
    if description and len(description) > 200:
        return jsonify({'code': 1, 'message': '描述不能超过200个字符'}), 400

    conn = get_db()

    # 检查题库数量限制
    count = conn.execute(
        'SELECT COUNT(*) as cnt FROM user_question_banks WHERE user_id = ? AND status = 1',
        (user_id,)
    ).fetchone()['cnt']

    if count >= 20:
        return jsonify({'code': 1, 'message': '最多只能创建20个题库'}), 400

    # 检查分类是否存在
    if category_id:
        cat = conn.execute(
            'SELECT id FROM user_bank_categories WHERE id = ? AND user_id = ?',
            (category_id, user_id)
        ).fetchone()
        if not cat:
            return jsonify({'code': 1, 'message': '分类不存在'}), 400

    cursor = conn.execute(
        '''INSERT INTO user_question_banks (user_id, category_id, name, description)
           VALUES (?, ?, ?, ?)''',
        (user_id, category_id, name, description)
    )
    conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'id': cursor.lastrowid,
            'name': name
        }
    })


@user_bank_api_bp.route('/<int:bank_id>', methods=['PUT'])
@auth_required
def update_bank(bank_id):
    """编辑题库"""
    user_id = current_user_id()
    data = request.get_json() or {}

    conn = get_db()

    # 检查权限
    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    updates = []
    params = []

    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name or len(name) < 2 or len(name) > 50:
            return jsonify({'code': 1, 'message': '题库名称需要2-50个字符'}), 400
        updates.append('name = ?')
        params.append(name)

    if 'description' in data:
        description = (data['description'] or '').strip()
        if description and len(description) > 200:
            return jsonify({'code': 1, 'message': '描述不能超过200个字符'}), 400
        updates.append('description = ?')
        params.append(description)

    if 'category_id' in data:
        category_id = data['category_id']
        if category_id:
            cat = conn.execute(
                'SELECT id FROM user_bank_categories WHERE id = ? AND user_id = ?',
                (category_id, user_id)
            ).fetchone()
            if not cat:
                return jsonify({'code': 1, 'message': '分类不存在'}), 400
        updates.append('category_id = ?')
        params.append(category_id)

    if not updates:
        return jsonify({'code': 1, 'message': '没有要更新的内容'}), 400

    updates.append('updated_at = CURRENT_TIMESTAMP')
    params.append(bank_id)

    conn.execute(
        f'UPDATE user_question_banks SET {", ".join(updates)} WHERE id = ?',
        params
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '更新成功'})


@user_bank_api_bp.route('/<int:bank_id>', methods=['DELETE'])
@auth_required
def delete_bank(bank_id):
    """删除题库"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 软删除
    conn.execute(
        'UPDATE user_question_banks SET status = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '删除成功'})


@user_bank_api_bp.route('/<int:bank_id>/public', methods=['POST'])
@auth_required
def set_bank_public(bank_id):
    """设置题库公开状态"""
    user_id = current_user_id()
    data = request.get_json() or {}
    is_public = data.get('is_public', False)
    public_description = (data.get('public_description') or '').strip()
    allow_copy = data.get('allow_copy', True)

    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if is_public:
        conn.execute('''
            UPDATE user_question_banks
            SET is_public = 1, public_description = ?, allow_copy = ?,
                public_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (public_description, 1 if allow_copy else 0, bank_id))
        message = '题库已公开'
    else:
        conn.execute('''
            UPDATE user_question_banks
            SET is_public = 0, public_at = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (bank_id,))
        message = '题库已设为私密'

    conn.commit()

    return jsonify({'code': 0, 'message': message})


# ============================================
# 题目管理 API
# ============================================

@user_bank_api_bp.route('/<int:bank_id>/questions', methods=['GET'])
@auth_required
def get_bank_questions(bank_id):
    """获取题库题目列表"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    q_type = request.args.get('q_type', '')
    keyword = request.args.get('keyword', '').strip()

    conn = get_db()

    query = 'SELECT * FROM user_bank_questions WHERE bank_id = ?'
    count_query = 'SELECT COUNT(*) as cnt FROM user_bank_questions WHERE bank_id = ?'
    params = [bank_id]

    if q_type:
        query += ' AND q_type = ?'
        count_query += ' AND q_type = ?'
        params.append(q_type)

    if keyword:
        query += ' AND content LIKE ?'
        count_query += ' AND content LIKE ?'
        params.append(f'%{keyword}%')

    total = conn.execute(count_query, params).fetchone()['cnt']

    query += ' ORDER BY sort_order ASC, id ASC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])

    questions = conn.execute(query, params).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'questions': [dict(q) for q in questions],
            'total': total,
            'page': page,
            'per_page': per_page,
            'permission': permission,
            'access_type': access_type
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/questions', methods=['POST'])
@auth_required
def add_question(bank_id):
    """添加题目（自建）"""
    user_id = current_user_id()
    conn = get_db()

    # 检查权限
    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    q_type = (data.get('q_type') or '').strip()
    options = data.get('options')
    answer = data.get('answer')
    explanation = (data.get('explanation') or '').strip()
    difficulty = data.get('difficulty', 1)

    if not content:
        return jsonify({'code': 1, 'message': '题干不能为空'}), 400
    if not q_type:
        return jsonify({'code': 1, 'message': '题型不能为空'}), 400

    # 处理选项
    import json
    options_str = json.dumps(options, ensure_ascii=False) if options else None

    cursor = conn.execute('''
        INSERT INTO user_bank_questions
        (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, source_type, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
    ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, bank_id))

    # 更新题目数量
    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'id': cursor.lastrowid
        },
        'message': '添加成功'
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>', methods=['PUT'])
@auth_required
def update_question(bank_id, question_id):
    """编辑题目"""
    user_id = current_user_id()
    conn = get_db()

    # 检查题库权限
    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 检查题目
    question = conn.execute(
        'SELECT id, source_type FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 非自建题目禁止编辑
    if question['source_type'] != 'custom':
        return jsonify({'code': 1, 'message': '非自建题目不能编辑，请删除后重新添加'}), 400

    data = request.get_json() or {}
    updates = []
    params = []

    if 'content' in data:
        content = (data['content'] or '').strip()
        if not content:
            return jsonify({'code': 1, 'message': '题干不能为空'}), 400
        updates.append('content = ?')
        params.append(content)

    if 'q_type' in data:
        updates.append('q_type = ?')
        params.append(data['q_type'])

    if 'options' in data:
        import json
        updates.append('options = ?')
        params.append(json.dumps(data['options'], ensure_ascii=False) if data['options'] else None)

    if 'answer' in data:
        updates.append('answer = ?')
        params.append(data['answer'])

    if 'explanation' in data:
        updates.append('explanation = ?')
        params.append((data['explanation'] or '').strip())

    if 'difficulty' in data:
        updates.append('difficulty = ?')
        params.append(data['difficulty'])

    if not updates:
        return jsonify({'code': 1, 'message': '没有要更新的内容'}), 400

    updates.append('updated_at = CURRENT_TIMESTAMP')
    params.append(question_id)

    conn.execute(
        f'UPDATE user_bank_questions SET {", ".join(updates)} WHERE id = ?',
        params
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '更新成功'})


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>', methods=['DELETE'])
@auth_required
def delete_question(bank_id, question_id):
    """删除题目"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    conn.execute('DELETE FROM user_bank_questions WHERE id = ?', (question_id,))
    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count - 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '删除成功'})


@user_bank_api_bp.route('/<int:bank_id>/questions/batch_delete', methods=['POST'])
@auth_required
def batch_delete_questions(bank_id):
    """批量删除题目"""
    user_id = current_user_id()
    data = request.get_json() or {}
    question_ids = data.get('question_ids', [])

    if not question_ids:
        return jsonify({'code': 1, 'message': '请选择要删除的题目'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    placeholders = ','.join(['?'] * len(question_ids))
    conn.execute(
        f'DELETE FROM user_bank_questions WHERE id IN ({placeholders}) AND bank_id = ?',
        question_ids + [bank_id]
    )

    # 重新计算题目数量
    count = conn.execute(
        'SELECT COUNT(*) as cnt FROM user_bank_questions WHERE bank_id = ?',
        (bank_id,)
    ).fetchone()['cnt']

    conn.execute(
        'UPDATE user_question_banks SET question_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (count, bank_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': f'成功删除{len(question_ids)}道题目'})


@user_bank_api_bp.route('/<int:bank_id>/questions/copy', methods=['POST'])
@auth_required
def copy_questions(bank_id):
    """从公共题库复制题目"""
    user_id = current_user_id()
    data = request.get_json() or {}
    question_ids = data.get('question_ids', [])
    source_type = data.get('source_type', 'public')

    if not question_ids:
        return jsonify({'code': 1, 'message': '请选择要复制的题目'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 从公共题库复制
    placeholders = ','.join(['?'] * len(question_ids))
    questions = conn.execute(
        f'SELECT id, content, q_type, options, answer, explanation, difficulty, image_path FROM questions WHERE id IN ({placeholders})',
        question_ids
    ).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '未找到指定的题目'}), 404

    copied_count = 0
    for q in questions:
        conn.execute('''
            INSERT INTO user_bank_questions
            (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, image_path,
             source_type, source_question_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
        ''', (bank_id, user_id, q['content'], q['q_type'], q['options'], q['answer'],
              q['explanation'], q['difficulty'], q['image_path'], source_type, q['id'], bank_id))
        copied_count += 1

    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (copied_count, bank_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': f'成功复制{copied_count}道题目'})


@user_bank_api_bp.route('/<int:bank_id>/questions/import', methods=['POST'])
@auth_required
def import_questions(bank_id):
    """从错题本/收藏夹导入题目"""
    user_id = current_user_id()
    data = request.get_json() or {}
    source = data.get('source')  # 'mistakes' or 'favorites'
    subject_id = data.get('subject_id')
    question_ids = data.get('question_ids', [])

    if source not in ('mistakes', 'favorites'):
        return jsonify({'code': 1, 'message': '无效的来源'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 构建查询
    if source == 'mistakes':
        query = '''
            SELECT q.id, q.content, q.q_type, q.options, q.answer, q.explanation, q.difficulty, q.image_path
            FROM questions q
            JOIN mistakes m ON q.id = m.question_id
            WHERE m.user_id = ?
        '''
        source_type = 'mistake'
    else:
        query = '''
            SELECT q.id, q.content, q.q_type, q.options, q.answer, q.explanation, q.difficulty, q.image_path
            FROM questions q
            JOIN favorites f ON q.id = f.question_id
            WHERE f.user_id = ?
        '''
        source_type = 'favorite'

    params = [user_id]

    if subject_id:
        query += ' AND q.subject_id = ?'
        params.append(subject_id)

    if question_ids:
        placeholders = ','.join(['?'] * len(question_ids))
        query += f' AND q.id IN ({placeholders})'
        params.extend(question_ids)

    questions = conn.execute(query, params).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '未找到可导入的题目'}), 404

    imported_count = 0
    for q in questions:
        conn.execute('''
            INSERT INTO user_bank_questions
            (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, image_path,
             source_type, source_question_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
        ''', (bank_id, user_id, q['content'], q['q_type'], q['options'], q['answer'],
              q['explanation'], q['difficulty'], q['image_path'], source_type, q['id'], bank_id))
        imported_count += 1

    conn.execute(
        'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (imported_count, bank_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': f'成功导入{imported_count}道题目'})


@user_bank_api_bp.route('/<int:bank_id>/questions/import/json', methods=['POST'])
@auth_required
def import_questions_json(bank_id):
    """直接导入题目数据（JSON格式）"""
    user_id = current_user_id()
    data = request.get_json() or {}
    questions = data.get('questions', [])

    if not questions or not isinstance(questions, list):
        return jsonify({'code': 1, 'message': '请提供有效的题目数据'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    imported_count = 0
    errors = []

    for idx, q in enumerate(questions):
        q_type = (q.get('题型') or q.get('q_type') or '').strip()
        content = (q.get('题干') or q.get('content') or '').strip()
        answer = q.get('答案') or q.get('answer') or ''
        explanation = q.get('解析') or q.get('explanation') or ''
        difficulty = q.get('难度') or q.get('difficulty') or 1

        if not q_type or not content:
            errors.append(f'第{idx+1}题: 题型或题干为空')
            continue

        # 处理选项
        options = q.get('选项') or q.get('options') or []
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except:
                options = []

        options_str = json.dumps(options, ensure_ascii=False) if options else None

        try:
            conn.execute('''
                INSERT INTO user_bank_questions
                (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, source_type, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
            ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, bank_id))
            imported_count += 1
        except Exception as e:
            errors.append(f'第{idx+1}题: 导入失败 - {str(e)}')

    # 更新题目数量
    if imported_count > 0:
        conn.execute(
            'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (imported_count, bank_id)
        )
        conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'imported': imported_count,
            'errors': errors[:10]
        },
        'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
    })


# ============================================
# 分享管理 API
# ============================================

@user_bank_api_bp.route('/<int:bank_id>/shares', methods=['GET'])
@auth_required
def get_shares(bank_id):
    """获取分享列表"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    shares = conn.execute('''
        SELECT * FROM bank_shares WHERE bank_id = ? ORDER BY created_at DESC
    ''', (bank_id,)).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'shares': [dict(s) for s in shares]
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/shares', methods=['POST'])
@auth_required
def create_share(bank_id):
    """创建分享"""
    user_id = current_user_id()
    data = request.get_json() or {}
    share_type = data.get('type', 'code')  # 'code' or 'link'
    permission = data.get('permission', 'read')
    expires_in = data.get('expires_in')  # 有效天数
    max_uses = data.get('max_uses')

    if permission not in ('read', 'copy'):
        return jsonify({'code': 1, 'message': '无效的权限级别'}), 400

    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    # 检查分享数量限制
    share_count = conn.execute(
        'SELECT COUNT(*) as cnt FROM bank_shares WHERE bank_id = ? AND is_active = 1',
        (bank_id,)
    ).fetchone()['cnt']

    if share_count >= 10:
        return jsonify({'code': 1, 'message': '每个题库最多只能创建10个分享'}), 400

    # 计算过期时间
    expires_at = None
    if expires_in:
        expires_at = (datetime.now() + timedelta(days=int(expires_in))).isoformat()

    share_code = None
    share_token = None

    if share_type == 'code':
        # 生成唯一分享码
        while True:
            share_code = generate_share_code()
            existing = conn.execute(
                'SELECT id FROM bank_shares WHERE share_code = ?', (share_code,)
            ).fetchone()
            if not existing:
                break
    else:
        share_token = str(uuid.uuid4()).replace('-', '')

    cursor = conn.execute('''
        INSERT INTO bank_shares (bank_id, owner_id, share_code, share_token, permission, expires_at, max_uses)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (bank_id, user_id, share_code, share_token, permission, expires_at, max_uses))

    # 更新分享数量
    conn.execute(
        'UPDATE user_question_banks SET share_count = share_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (bank_id,)
    )
    conn.commit()

    result = {
        'share_id': cursor.lastrowid,
        'expires_at': expires_at
    }

    if share_code:
        result['share_code'] = share_code
    if share_token:
        # 构建分享链接
        base_url = current_app.config.get('SHARE_BASE_URL', request.host_url.rstrip('/'))
        result['share_link'] = f'{base_url}/bank/join?token={share_token}'

    return jsonify({
        'code': 0,
        'data': result
    })


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>', methods=['DELETE'])
@auth_required
def delete_share(bank_id, share_id):
    """撤销分享"""
    user_id = current_user_id()
    conn = get_db()

    share = conn.execute(
        'SELECT id FROM bank_shares WHERE id = ? AND bank_id = ? AND owner_id = ?',
        (share_id, bank_id, user_id)
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    conn.execute('UPDATE bank_shares SET is_active = 0 WHERE id = ?', (share_id,))
    conn.commit()

    return jsonify({'code': 0, 'message': '分享已撤销'})


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>/records', methods=['GET'])
@auth_required
def get_share_records(bank_id, share_id):
    """查看分享使用记录"""
    user_id = current_user_id()
    conn = get_db()

    share = conn.execute(
        'SELECT id FROM bank_shares WHERE id = ? AND bank_id = ? AND owner_id = ?',
        (share_id, bank_id, user_id)
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    records = conn.execute('''
        SELECT bsr.*, u.username as nickname, u.avatar
        FROM bank_share_records bsr
        JOIN users u ON bsr.user_id = u.id
        WHERE bsr.share_id = ?
        ORDER BY bsr.created_at DESC
    ''', (share_id,)).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'records': [dict(r) for r in records]
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/shares/<int:share_id>/records/<int:target_user_id>', methods=['DELETE'])
@auth_required
def remove_share_record(bank_id, share_id, target_user_id):
    """移除特定用户的访问权限"""
    user_id = current_user_id()
    conn = get_db()

    share = conn.execute(
        'SELECT id FROM bank_shares WHERE id = ? AND bank_id = ? AND owner_id = ?',
        (share_id, bank_id, user_id)
    ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享不存在或无权操作'}), 404

    conn.execute(
        'UPDATE bank_share_records SET status = 0 WHERE share_id = ? AND user_id = ?',
        (share_id, target_user_id)
    )
    conn.commit()

    return jsonify({'code': 0, 'message': '已移除该用户的访问权限'})


# ============================================
# 被分享者接口 API
# ============================================

@user_bank_api_bp.route('/join', methods=['POST'])
@auth_required
def join_bank():
    """通过分享码/链接加入题库"""
    user_id = current_user_id()
    data = request.get_json() or {}
    share_code = (data.get('share_code') or '').strip().upper()
    share_token = (data.get('token') or '').strip()

    if not share_code and not share_token:
        return jsonify({'code': 1, 'message': '请提供分享码或分享链接'}), 400

    conn = get_db()

    if share_code:
        share = conn.execute(
            'SELECT * FROM bank_shares WHERE share_code = ? AND is_active = 1',
            (share_code,)
        ).fetchone()
    else:
        share = conn.execute(
            'SELECT * FROM bank_shares WHERE share_token = ? AND is_active = 1',
            (share_token,)
        ).fetchone()

    if not share:
        return jsonify({'code': 1, 'message': '分享码/链接无效或已过期'}), 404

    # 检查过期
    if share['expires_at']:
        if datetime.fromisoformat(share['expires_at']) < datetime.now():
            return jsonify({'code': 1, 'message': '分享已过期'}), 400

    # 检查使用次数
    if share['max_uses'] and share['current_uses'] >= share['max_uses']:
        return jsonify({'code': 1, 'message': '分享已达到最大使用次数'}), 400

    # 不能加入自己的题库
    if share['owner_id'] == user_id:
        return jsonify({'code': 1, 'message': '不能加入自己的题库'}), 400

    bank_id = share['bank_id']

    # 检查题库状态
    bank = conn.execute(
        'SELECT b.*, u.username as owner_username FROM user_question_banks b JOIN users u ON b.user_id = u.id WHERE b.id = ? AND b.status = 1',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或已被删除'}), 404

    # 检查是否已加入
    existing = conn.execute(
        'SELECT id, status FROM bank_share_records WHERE share_id = ? AND user_id = ?',
        (share['id'], user_id)
    ).fetchone()

    if existing:
        if existing['status'] == 1:
            return jsonify({'code': 1, 'message': '您已加入此题库'}), 400
        else:
            # 重新激活
            conn.execute(
                'UPDATE bank_share_records SET status = 1, last_access_at = CURRENT_TIMESTAMP WHERE id = ?',
                (existing['id'],)
            )
    else:
        conn.execute('''
            INSERT INTO bank_share_records (share_id, bank_id, user_id, last_access_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (share['id'], bank_id, user_id))

        # 更新使用次数
        conn.execute(
            'UPDATE bank_shares SET current_uses = current_uses + 1 WHERE id = ?',
            (share['id'],)
        )

    conn.commit()

    return jsonify({
        'code': 0,
        'data': {
            'bank_id': bank_id,
            'bank_name': bank['name'],
            'owner_nickname': bank['owner_username'],
            'question_count': bank['question_count'],
            'permission': share['permission']
        }
    })


@user_bank_api_bp.route('/shared', methods=['GET'])
@auth_required
def get_shared_banks():
    """获取收到的分享列表"""
    user_id = current_user_id()
    conn = get_db()

    banks = conn.execute('''
        SELECT b.id as bank_id, b.name as bank_name, b.question_count,
               bs.permission, bsr.last_access_at, bsr.access_count,
               u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar
        FROM bank_share_records bsr
        JOIN bank_shares bs ON bsr.share_id = bs.id
        JOIN user_question_banks b ON bsr.bank_id = b.id
        JOIN users u ON b.user_id = u.id
        WHERE bsr.user_id = ? AND bsr.status = 1 AND b.status = 1 AND bs.is_active = 1
        ORDER BY bsr.last_access_at DESC
    ''', (user_id,)).fetchall()

    return jsonify({
        'code': 0,
        'data': {
            'banks': [dict(b) for b in banks]
        }
    })


@user_bank_api_bp.route('/shared/<int:bank_id>', methods=['DELETE'])
@auth_required
def remove_shared_bank(bank_id):
    """移除收到的分享"""
    user_id = current_user_id()
    conn = get_db()

    conn.execute('''
        UPDATE bank_share_records SET status = 0
        WHERE user_id = ? AND bank_id = ?
    ''', (user_id, bank_id))
    conn.commit()

    return jsonify({'code': 0, 'message': '已移除'})


# ============================================
# 刷题接口 API
# ============================================

@user_bank_api_bp.route('/<int:bank_id>/quiz', methods=['GET'])
@auth_required
def get_quiz_questions(bank_id):
    """获取刷题题目"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    mode = request.args.get('mode', 'all')
    limit = request.args.get('limit', 20, type=int)
    q_type = (request.args.get('q_type') or '').strip()
    tag = (request.args.get('tag') or '').strip()

    conn = get_db()

    tag_question_ids = None
    if tag and tag != 'all':
        try:
            store = _load_bank_tag_store(conn, bank_id, user_id)
            question_tags = store.get('question_tags', {}) or {}
            tag_question_ids = []
            for q_id, tags in question_tags.items():
                if not isinstance(tags, list):
                    continue
                if tag in tags:
                    try:
                        tag_question_ids.append(int(q_id))
                    except Exception:
                        continue
        except Exception:
            tag_question_ids = []

        if not tag_question_ids:
            return jsonify({'code': 0, 'data': {'questions': [], 'total': 0}})

    type_condition = ' AND q.q_type = ?' if q_type else ''
    type_params = [q_type] if q_type else []

    tag_condition = ''
    tag_params = []
    if tag_question_ids is not None:
        # 去重，避免无意义的 SQL 变量膨胀
        tag_question_ids = sorted(set(tag_question_ids))
        # SQLite 默认变量上限约 999；超过时改为安全的整数拼接（已强制 int 转换）
        if len(tag_question_ids) <= 900:
            tag_condition = ' AND q.id IN ({})'.format(','.join('?' * len(tag_question_ids)))
            tag_params = tag_question_ids
        else:
            tag_condition = ' AND q.id IN ({})'.format(','.join(str(i) for i in tag_question_ids))
            tag_params = []

    if mode == 'wrong':
        # 错题模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY m.wrong_count DESC, m.updated_at DESC
            LIMIT ?
        ''', [bank_id, user_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    elif mode == 'favorites':
        # 收藏模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY f.created_at DESC
            LIMIT ?
        ''', [bank_id, user_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    elif mode == 'random':
        # 随机模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY RANDOM() LIMIT ?
        ''', [bank_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition, [bank_id] + type_params + tag_params).fetchone()['cnt']
    else:
        # 顺序模式
        questions = conn.execute('''
            SELECT q.* FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition + '''
            ORDER BY q.sort_order ASC, q.id ASC LIMIT ?
        ''', [bank_id] + type_params + tag_params + [limit]).fetchall()

        total = conn.execute('''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            WHERE q.bank_id = ?
        ''' + type_condition + tag_condition, [bank_id] + type_params + tag_params).fetchone()['cnt']

    # 更新访问记录
    if access_type == 'shared':
        conn.execute('''
            UPDATE bank_share_records
            SET last_access_at = CURRENT_TIMESTAMP, access_count = access_count + 1
            WHERE user_id = ? AND bank_id = ?
        ''', (user_id, bank_id))
    elif access_type == 'public':
        # 更新公开题库使用记录
        existing = conn.execute(
            'SELECT id FROM public_bank_users WHERE bank_id = ? AND user_id = ?',
            (bank_id, user_id)
        ).fetchone()

        if existing:
            conn.execute('''
                UPDATE public_bank_users
                SET last_access_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE bank_id = ? AND user_id = ?
            ''', (bank_id, user_id))
        else:
            conn.execute('''
                INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
                VALUES (?, ?, CURRENT_TIMESTAMP, 1)
            ''', (bank_id, user_id))
            # 更新公开使用人数
            conn.execute(
                'UPDATE user_question_banks SET public_use_count = public_use_count + 1 WHERE id = ?',
                (bank_id,)
            )

    conn.commit()

    # 获取用户的收藏和错题状态
    question_ids = [q['id'] for q in questions]

    if question_ids:
        # 获取收藏状态
        fav_query = 'SELECT question_id FROM user_bank_favorites WHERE user_id = ? AND question_id IN ({})'.format(
            ','.join('?' * len(question_ids))
        )
        fav_rows = conn.execute(fav_query, [user_id] + question_ids).fetchall()
        fav_set = {r['question_id'] for r in fav_rows}

        # 获取错题状态
        mistake_query = 'SELECT question_id FROM user_bank_mistakes WHERE user_id = ? AND question_id IN ({})'.format(
            ','.join('?' * len(question_ids))
        )
        mistake_rows = conn.execute(mistake_query, [user_id] + question_ids).fetchall()
        mistake_set = {r['question_id'] for r in mistake_rows}
    else:
        fav_set = set()
        mistake_set = set()

    # 构建返回数据，添加收藏和错题状态
    result_questions = []
    for q in questions:
        q_dict = dict(q)
        q_dict['is_fav'] = 1 if q_dict['id'] in fav_set else 0
        q_dict['is_mistake'] = 1 if q_dict['id'] in mistake_set else 0
        result_questions.append(q_dict)

    return jsonify({
        'code': 0,
        'data': {
            'questions': result_questions,
            'total': total
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/quiz/record', methods=['POST'])
@auth_required
def record_quiz_result(bank_id):
    """记录答题结果"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    data = request.get_json() or {}
    question_id = data.get('question_id')
    user_answer = data.get('user_answer')
    is_correct = data.get('is_correct')

    if not question_id:
        return jsonify({'code': 1, 'message': '缺少题目ID'}), 400

    conn = get_db()

    # 验证题目属于该题库
    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 记录或更新答题记录
    conn.execute('''
        INSERT INTO user_bank_answers (user_id, bank_id, question_id, user_answer, is_correct)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            user_answer = excluded.user_answer,
            is_correct = excluded.is_correct,
            created_at = CURRENT_TIMESTAMP
    ''', (user_id, bank_id, question_id, user_answer, 1 if is_correct else 0))

    # 处理错题记录
    if not is_correct:
        conn.execute('''
            INSERT INTO user_bank_mistakes (user_id, bank_id, question_id, wrong_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, question_id) DO UPDATE SET
                wrong_count = wrong_count + 1,
                updated_at = CURRENT_TIMESTAMP
        ''', (user_id, bank_id, question_id))
    else:
        # 答对了，从错题中移除
        conn.execute(
            'DELETE FROM user_bank_mistakes WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        )

    conn.commit()

    return jsonify({'code': 0, 'message': '记录成功'})


@user_bank_api_bp.route('/<int:bank_id>/my-stats', methods=['GET'])
@auth_required
def get_my_stats(bank_id):
    """获取我的答题统计"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    stats = conn.execute('''
        SELECT
            COUNT(*) as total_answered,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_count,
            SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as wrong_count
        FROM user_bank_answers
        WHERE user_id = ? AND bank_id = ?
    ''', (user_id, bank_id)).fetchone()

    total = stats['total_answered'] or 0
    correct = stats['correct_count'] or 0
    wrong = stats['wrong_count'] or 0
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    return jsonify({
        'code': 0,
        'data': {
            'total_answered': total,
            'correct_count': correct,
            'wrong_count': wrong,
            'accuracy': accuracy
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/user-counts', methods=['GET'])
@auth_required
def get_user_counts(bank_id):
    """获取题库的用户统计（总数、收藏数、错题数，支持题型和来源筛选）"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    q_type = request.args.get('q_type', '').strip()
    source = request.args.get('source', 'all').strip()
    tag = (request.args.get('tag') or '').strip()

    conn = get_db()

    tag_question_ids = None
    if tag and tag != 'all':
        try:
            store = _load_bank_tag_store(conn, bank_id, user_id)
            question_tags = store.get('question_tags', {}) or {}
            tag_question_ids = []
            for q_id, tags in question_tags.items():
                if not isinstance(tags, list):
                    continue
                if tag in tags:
                    try:
                        tag_question_ids.append(int(q_id))
                    except Exception:
                        continue
        except Exception:
            tag_question_ids = []

        if not tag_question_ids:
            return jsonify({'code': 0, 'data': {'total': 0, 'favorites': 0, 'mistakes': 0}})

    # 构建基础查询条件
    type_condition = ' AND q.q_type = ?' if q_type else ''
    type_params = [q_type] if q_type else []

    tag_condition = ''
    tag_params = []
    if tag_question_ids is not None:
        tag_question_ids = sorted(set(tag_question_ids))
        if len(tag_question_ids) <= 900:
            tag_condition = ' AND q.id IN ({})'.format(','.join('?' * len(tag_question_ids)))
            tag_params = tag_question_ids
        else:
            tag_condition = ' AND q.id IN ({})'.format(','.join(str(i) for i in tag_question_ids))
            tag_params = []

    # 根据 source 筛选
    if source == 'favorites':
        # 获取收藏题目数
        total_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition
        total = conn.execute(total_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    elif source == 'mistakes':
        # 获取用户错题
        total_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition
        total = conn.execute(total_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    else:
        # 获取全部题目
        total_query = 'SELECT COUNT(*) as cnt FROM user_bank_questions q WHERE q.bank_id = ?' + type_condition + tag_condition
        total = conn.execute(total_query, [bank_id] + type_params + tag_params).fetchone()['cnt']

    # 获取收藏数（基于当前题型筛选）
    try:
        favorites_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_favorites f ON q.id = f.question_id
            WHERE q.bank_id = ? AND f.user_id = ?
        ''' + type_condition + tag_condition
        favorites = conn.execute(favorites_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    except Exception:
        favorites = 0

    # 获取错题数（基于当前题型筛选）
    try:
        mistakes_query = '''
            SELECT COUNT(*) as cnt FROM user_bank_questions q
            JOIN user_bank_mistakes m ON q.id = m.question_id
            WHERE q.bank_id = ? AND m.user_id = ?
        ''' + type_condition + tag_condition
        mistakes = conn.execute(mistakes_query, [bank_id, user_id] + type_params + tag_params).fetchone()['cnt']
    except Exception:
        mistakes = 0

    return jsonify({
        'code': 0,
        'data': {
            'total': total,
            'favorites': favorites,
            'mistakes': mistakes
        }
    })


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>/favorite', methods=['POST'])
@auth_required
def toggle_favorite(bank_id, question_id):
    """切换题目收藏状态"""
    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    # 检查题目是否存在
    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'code': 1, 'message': '题目不存在'}), 404

    # 检查是否已收藏
    existing = conn.execute(
        'SELECT id FROM user_bank_favorites WHERE user_id = ? AND question_id = ?',
        (user_id, question_id)
    ).fetchone()

    if existing:
        # 取消收藏
        conn.execute(
            'DELETE FROM user_bank_favorites WHERE user_id = ? AND question_id = ?',
            (user_id, question_id)
        )
        conn.commit()
        return jsonify({
            'code': 0,
            'message': '已取消收藏',
            'is_favorite': False
        })
    else:
        # 添加收藏
        conn.execute(
            '''INSERT INTO user_bank_favorites (user_id, bank_id, question_id)
               VALUES (?, ?, ?)''',
            (user_id, bank_id, question_id)
        )
        conn.commit()
        return jsonify({
            'code': 0,
            'message': '已收藏',
            'is_favorite': True
        })


# ============================================
# 导入导出 API
# ============================================

@user_bank_api_bp.route('/<int:bank_id>/questions/export/excel', methods=['GET'])
@auth_required
def export_questions_excel(bank_id):
    """导出题目为Excel文件"""
    import pandas as pd
    import io
    from flask import send_file

    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    # 获取题库信息
    bank = conn.execute(
        'SELECT name FROM user_question_banks WHERE id = ?',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    # 获取题目
    questions = conn.execute('''
        SELECT q_type, content, options, answer, explanation, difficulty
        FROM user_bank_questions
        WHERE bank_id = ?
        ORDER BY sort_order ASC, id ASC
    ''', (bank_id,)).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    # 准备数据
    import json
    data = []
    max_options = 0

    for q in questions:
        opts = []
        if q['options']:
            try:
                opts = json.loads(q['options'])
            except:
                opts = []
        max_options = max(max_options, len(opts))

    for q in questions:
        row = {
            'q_type': q['q_type'],
            'content': q['content'],
            'answer': q['answer'] or '',
            'explanation': q['explanation'] or '',
            'difficulty': q['difficulty'] or 1
        }

        opts = []
        if q['options']:
            try:
                opts = json.loads(q['options'])
            except:
                opts = []

        for i in range(max_options):
            row[f'option_{i+1}'] = opts[i] if i < len(opts) else ''

        data.append(row)

    # 创建Excel
    df = pd.DataFrame(data)

    # 重排列顺序
    cols = ['q_type', 'content']
    option_cols = [f'option_{i+1}' for i in range(max_options)]
    cols.extend(option_cols)
    cols.extend(['answer', 'explanation', 'difficulty'])
    df = df.reindex(columns=cols)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='题目', index=False)

    output.seek(0)

    filename = f"{bank['name']}_题目导出.xlsx"
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@user_bank_api_bp.route('/<int:bank_id>/questions/import/excel', methods=['POST'])
@auth_required
def import_questions_excel(bank_id):
    """从Excel文件导入题目"""
    import pandas as pd
    import json

    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.xlsx'):
        return jsonify({'code': 1, 'message': '请上传.xlsx格式的文件'}), 400

    try:
        df = pd.read_excel(file).fillna('')

        # 检查必需列
        required_cols = ['q_type', 'content']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            return jsonify({'code': 1, 'message': f'Excel文件缺少必需列: {", ".join(missing)}'}), 400

        # 获取选项列
        option_cols = sorted([col for col in df.columns if col.startswith('option_')])

        imported_count = 0
        errors = []

        for idx, row in df.iterrows():
            q_type = str(row.get('q_type', '')).strip()
            content = str(row.get('content', '')).strip()
            answer = str(row.get('answer', '')).strip()
            explanation = str(row.get('explanation', '')).strip()
            difficulty = int(row.get('difficulty', 1)) if row.get('difficulty') else 1

            if not q_type or not content:
                errors.append(f'第{idx+2}行: 题型或题干为空')
                continue

            # 处理选项
            options = []
            if q_type in ('选择题', '多选题'):
                for col in option_cols:
                    opt = str(row.get(col, '')).strip()
                    if opt:
                        options.append(opt)
                if len(options) < 2:
                    errors.append(f'第{idx+2}行: 选择题至少需要2个选项')
                    continue

            options_str = json.dumps(options, ensure_ascii=False) if options else None

            # 插入题目
            conn.execute('''
                INSERT INTO user_bank_questions
                (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, source_type, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                        (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
            ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, bank_id))
            imported_count += 1

        # 更新题目数量
        if imported_count > 0:
            conn.execute(
                'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (imported_count, bank_id)
            )
            conn.commit()

        return jsonify({
            'code': 0,
            'data': {
                'imported': imported_count,
                'errors': errors[:10]  # 最多返回10条错误
            },
            'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
        })

    except Exception as e:
        return jsonify({'code': 1, 'message': f'导入失败: {str(e)}'}), 500


@user_bank_api_bp.route('/<int:bank_id>/questions/export/package', methods=['GET'])
@auth_required
def export_questions_package(bank_id):
    """导出题目包（ZIP格式，含图片）"""
    import json
    import zipfile
    import io
    import os
    from flask import send_file

    user_id = current_user_id()
    has_access, permission, access_type = check_bank_access(user_id, bank_id)

    if not has_access:
        return jsonify({'code': 403, 'message': '无权访问此题库'}), 403

    conn = get_db()

    bank = conn.execute(
        'SELECT name FROM user_question_banks WHERE id = ?',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在'}), 404

    questions = conn.execute('''
        SELECT id, q_type, content, options, answer, explanation, difficulty, image_path
        FROM user_bank_questions
        WHERE bank_id = ?
        ORDER BY sort_order ASC, id ASC
    ''', (bank_id,)).fetchall()

    if not questions:
        return jsonify({'code': 1, 'message': '题库中没有题目'}), 400

    # 创建ZIP
    zip_buffer = io.BytesIO()
    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        questions_data = []
        image_count = 0

        for q in questions:
            q_data = {
                'q_type': q['q_type'],
                'content': q['content'],
                'options': json.loads(q['options']) if q['options'] else [],
                'answer': q['answer'],
                'explanation': q['explanation'],
                'difficulty': q['difficulty']
            }

            # 处理图片
            if q['image_path']:
                image_filename = os.path.basename(q['image_path'])
                full_path = os.path.join(upload_folder, q['image_path'].lstrip('/uploads/'))

                if os.path.exists(full_path):
                    new_image_name = f"images/{image_count}_{image_filename}"
                    zf.write(full_path, new_image_name)
                    q_data['image_path'] = new_image_name
                    image_count += 1

            questions_data.append(q_data)

        # 写入data.json
        zf.writestr('data.json', json.dumps(questions_data, ensure_ascii=False, indent=2))

    zip_buffer.seek(0)

    filename = f"{bank['name']}_题库包.zip"
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


@user_bank_api_bp.route('/<int:bank_id>/questions/import/package', methods=['POST'])
@auth_required
def import_questions_package(bank_id):
    """导入题目包（ZIP格式）"""
    import json
    import zipfile
    import os

    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id, question_count FROM user_question_banks WHERE id = ? AND user_id = ? AND status = 1',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或无权操作'}), 404

    if 'file' not in request.files:
        return jsonify({'code': 1, 'message': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({'code': 1, 'message': '请上传.zip格式的文件'}), 400

    upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, '..', 'uploads'))

    try:
        with zipfile.ZipFile(file, 'r') as zf:
            if 'data.json' not in zf.namelist():
                return jsonify({'code': 1, 'message': '压缩包中缺少data.json文件'}), 400

            with zf.open('data.json') as f:
                questions_data = json.load(f)

            imported_count = 0
            errors = []

            for idx, q in enumerate(questions_data):
                q_type = q.get('q_type', '').strip()
                content = q.get('content', '').strip()
                answer = q.get('answer', '')
                explanation = q.get('explanation', '')
                difficulty = q.get('difficulty', 1)
                options = q.get('options', [])

                if not q_type or not content:
                    errors.append(f'第{idx+1}题: 题型或题干为空')
                    continue

                options_str = json.dumps(options, ensure_ascii=False) if options else None

                # 处理图片
                image_path = None
                if q.get('image_path'):
                    src_image = q['image_path']
                    if src_image in zf.namelist():
                        # 保存图片
                        img_data = zf.read(src_image)
                        ext = os.path.splitext(src_image)[1]
                        new_filename = f"user_bank_{bank_id}_{uuid.uuid4().hex}{ext}"
                        new_path = os.path.join(upload_folder, 'questions', new_filename)
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)

                        with open(new_path, 'wb') as img_file:
                            img_file.write(img_data)

                        image_path = f"/uploads/questions/{new_filename}"

                # 插入题目
                conn.execute('''
                    INSERT INTO user_bank_questions
                    (bank_id, user_id, content, q_type, options, answer, explanation, difficulty, image_path, source_type, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'custom',
                            (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM user_bank_questions WHERE bank_id = ?))
                ''', (bank_id, user_id, content, q_type, options_str, answer, explanation, difficulty, image_path, bank_id))
                imported_count += 1

            # 更新题目数量
            if imported_count > 0:
                conn.execute(
                    'UPDATE user_question_banks SET question_count = question_count + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (imported_count, bank_id)
                )
                conn.commit()

            return jsonify({
                'code': 0,
                'data': {
                    'imported': imported_count,
                    'errors': errors[:10]
                },
                'message': f'成功导入{imported_count}道题目' + (f'，{len(errors)}条错误' if errors else '')
            })

    except Exception as e:
        return jsonify({'code': 1, 'message': f'导入失败: {str(e)}'}), 500


# ========================================
# 个人题库标签管理
# ========================================

def _get_bank_tag_store_key(bank_id: int) -> str:
    """获取题库标签存储的 key"""
    return f'bank_{bank_id}_tags'


def _load_bank_tag_store(conn, bank_id: int, user_id: int) -> dict:
    """
    加载题库的标签存储数据
    结构: { 'tags': ['tag1', 'tag2', ...], 'question_tags': { 'q_id': ['tag1', ...], ... } }
    """
    key = _get_bank_tag_store_key(bank_id)
    row = conn.execute(
        'SELECT data FROM user_progress WHERE user_id = ? AND p_key = ?',
        (user_id, key)
    ).fetchone()

    if row and row['data']:
        try:
            return json.loads(row['data'])
        except:
            pass

    return {'tags': [], 'question_tags': {}}


def _save_bank_tag_store(conn, bank_id: int, user_id: int, store: dict):
    """保存题库的标签存储数据"""
    key = _get_bank_tag_store_key(bank_id)
    data_str = json.dumps(store, ensure_ascii=False)

    existing = conn.execute(
        'SELECT id FROM user_progress WHERE user_id = ? AND p_key = ?',
        (user_id, key)
    ).fetchone()

    if existing:
        conn.execute(
            'UPDATE user_progress SET data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (data_str, existing['id'])
        )
    else:
        conn.execute(
            'INSERT INTO user_progress (user_id, p_key, data) VALUES (?, ?, ?)',
            (user_id, key, data_str)
        )

    conn.commit()


@user_bank_api_bp.route('/<int:bank_id>/tags', methods=['GET', 'POST'])
@jwt_required
def bank_tags_api(bank_id: int):
    """
    获取/创建题库标签
    GET: 获取题库的所有标签
    POST: 创建新标签
    """
    user_id = g.current_user_id
    conn = get_db()

    # 检查题库权限
    bank = conn.execute(
        '''SELECT id, user_id FROM user_question_banks WHERE id = ? AND (user_id = ? OR is_public = 1)''',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'status': 'error', 'message': '题库不存在或无权访问'}), 404

    store = _load_bank_tag_store(conn, bank_id, user_id)

    if request.method == 'GET':
        # 统计每个标签的使用次数
        tag_counts = {}
        for tag in store.get('tags', []):
            tag_counts[tag] = 0

        question_tags = store.get('question_tags', {})
        for q_id, tags in question_tags.items():
            for tag in tags:
                if tag in tag_counts:
                    tag_counts[tag] += 1

        tags_list = [{'name': tag, 'count': tag_counts.get(tag, 0)} for tag in store.get('tags', [])]

        return jsonify({
            'status': 'success',
            'data': {'tags': tags_list}
        })

    elif request.method == 'POST':
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()

        if not name:
            return jsonify({'status': 'error', 'message': '标签名不能为空'}), 400

        if len(name) > 20:
            return jsonify({'status': 'error', 'message': '标签名不能超过20个字符'}), 400

        tags = store.get('tags', [])
        if name in tags:
            return jsonify({'status': 'error', 'message': '标签已存在'}), 400

        tags.append(name)
        store['tags'] = tags
        _save_bank_tag_store(conn, bank_id, user_id, store)

        return jsonify({
            'status': 'success',
            'data': {'name': name}
        })


@user_bank_api_bp.route('/<int:bank_id>/questions/<int:question_id>/tags', methods=['GET', 'POST'])
@jwt_required
def bank_question_tags_api(bank_id: int, question_id: int):
    """
    获取/设置题目标签
    GET: 获取题目的标签
    POST: 设置题目的标签
    """
    user_id = g.current_user_id
    conn = get_db()

    # 检查题库权限
    bank = conn.execute(
        '''SELECT id, user_id FROM user_question_banks WHERE id = ? AND (user_id = ? OR is_public = 1)''',
        (bank_id, user_id)
    ).fetchone()

    if not bank:
        return jsonify({'status': 'error', 'message': '题库不存在或无权访问'}), 404

    # 检查题目是否存在
    question = conn.execute(
        'SELECT id FROM user_bank_questions WHERE id = ? AND bank_id = ?',
        (question_id, bank_id)
    ).fetchone()

    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'}), 404

    store = _load_bank_tag_store(conn, bank_id, user_id)

    if request.method == 'GET':
        question_tags = store.get('question_tags', {})
        tags = question_tags.get(str(question_id), [])

        return jsonify({
            'status': 'success',
            'data': {'tags': tags}
        })

    elif request.method == 'POST':
        data = request.get_json() or {}
        new_tags = data.get('tags', [])

        if not isinstance(new_tags, list):
            return jsonify({'status': 'error', 'message': '标签必须是数组'}), 400

        # 过滤无效标签
        valid_tags = [t for t in new_tags if isinstance(t, str) and t.strip()]
        valid_tags = [t.strip()[:20] for t in valid_tags]  # 限制长度

        # 确保所有使用的标签都在 tags 列表中
        all_tags = set(store.get('tags', []))
        for tag in valid_tags:
            if tag not in all_tags:
                all_tags.add(tag)

        store['tags'] = list(all_tags)

        question_tags = store.get('question_tags', {})
        question_tags[str(question_id)] = valid_tags
        store['question_tags'] = question_tags

        _save_bank_tag_store(conn, bank_id, user_id, store)

        return jsonify({
            'status': 'success',
            'data': {'tags': valid_tags}
        })
