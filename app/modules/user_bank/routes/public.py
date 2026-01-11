# -*- coding: utf-8 -*-
"""公开题库广场路由"""
from flask import Blueprint, render_template, request, jsonify
from app.core.utils.database import get_db
from app.core.utils.decorators import auth_required, current_user_id

public_bank_bp = Blueprint('public_bank', __name__)


@public_bank_bp.route('/public/banks')
def bank_plaza():
    """题库广场页面"""
    return render_template('user_bank/plaza.html')


@public_bank_bp.route('/api/public/banks', methods=['GET'])
def get_public_banks():
    """获取公开题库列表（包含用户公开题库和管理员公共题库）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort = request.args.get('sort', 'newest')  # newest, popular, questions
    keyword = request.args.get('keyword', '').strip()
    bank_type = request.args.get('type', '')  # all, user, system

    conn = get_db()
    all_banks = []

    # 1. 获取用户公开题库
    if bank_type != 'system':
        user_query = '''
            SELECT b.id, b.name, b.public_description as description, b.question_count,
                   b.public_use_count as use_count, b.allow_copy, b.public_at,
                   u.id as owner_id, u.username as owner_nickname, u.avatar as owner_avatar,
                   'user' as bank_type
            FROM user_question_banks b
            JOIN users u ON b.user_id = u.id
            WHERE b.is_public = 1 AND b.status = 1
        '''
        user_params = []

        if keyword:
            user_query += ' AND (b.name LIKE ? OR b.public_description LIKE ?)'
            user_params.extend([f'%{keyword}%', f'%{keyword}%'])

        user_banks = conn.execute(user_query, user_params).fetchall()
        all_banks.extend([dict(b) for b in user_banks])

    # 2. 获取管理员公共题库（subjects表）
    if bank_type != 'user':
        system_query = '''
            SELECT s.id, s.name, s.description, s.created_at as public_at,
                   (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                   1 as allow_copy, 0 as use_count,
                   NULL as owner_id, '系统管理员' as owner_nickname, NULL as owner_avatar,
                   'system' as bank_type
            FROM subjects s
            WHERE 1=1
        '''
        system_params = []

        if keyword:
            system_query += ' AND (s.name LIKE ? OR s.description LIKE ?)'
            system_params.extend([f'%{keyword}%', f'%{keyword}%'])

        system_banks = conn.execute(system_query, system_params).fetchall()
        all_banks.extend([dict(b) for b in system_banks])

    # 排序
    if sort == 'popular':
        all_banks.sort(key=lambda x: (x.get('use_count') or 0, x.get('public_at') or ''), reverse=True)
    elif sort == 'questions':
        all_banks.sort(key=lambda x: (x.get('question_count') or 0, x.get('public_at') or ''), reverse=True)
    else:  # newest
        all_banks.sort(key=lambda x: x.get('public_at') or '', reverse=True)

    # 分页
    total = len(all_banks)
    start = (page - 1) * per_page
    end = start + per_page
    paged_banks = all_banks[start:end]

    return jsonify({
        'code': 0,
        'data': {
            'banks': paged_banks,
            'total': total,
            'page': page
        }
    })


@public_bank_bp.route('/api/public/banks/<int:bank_id>', methods=['GET'])
def get_public_bank_detail(bank_id):
    """获取公开题库详情"""
    bank_type = request.args.get('type', 'user')  # user or system
    conn = get_db()

    if bank_type == 'system':
        # 查询系统公共题库（subjects表）
        bank = conn.execute('''
            SELECT s.id, s.name, s.description,
                   (SELECT COUNT(*) FROM questions q WHERE q.subject_id = s.id) as question_count,
                   1 as allow_copy, 0 as use_count,
                   '系统管理员' as owner_nickname, NULL as owner_avatar,
                   'system' as bank_type
            FROM subjects s
            WHERE s.id = ?
        ''', (bank_id,)).fetchone()

        if not bank:
            return jsonify({'code': 1, 'message': '题库不存在'}), 404
    else:
        # 查询用户公开题库
        bank = conn.execute('''
            SELECT b.id, b.name, b.public_description as description, b.question_count,
                   b.public_use_count as use_count, b.allow_copy,
                   u.username as owner_nickname, u.avatar as owner_avatar,
                   'user' as bank_type
            FROM user_question_banks b
            JOIN users u ON b.user_id = u.id
            WHERE b.id = ? AND b.is_public = 1 AND b.status = 1
        ''', (bank_id,)).fetchone()

        if not bank:
            return jsonify({'code': 1, 'message': '题库不存在或未公开'}), 404

    return jsonify({
        'code': 0,
        'data': dict(bank)
    })


@public_bank_bp.route('/api/public/banks/<int:bank_id>/join', methods=['POST'])
@auth_required
def join_public_bank(bank_id):
    """加入公开题库刷题"""
    user_id = current_user_id()
    conn = get_db()

    bank = conn.execute(
        'SELECT id FROM user_question_banks WHERE id = ? AND is_public = 1 AND status = 1',
        (bank_id,)
    ).fetchone()

    if not bank:
        return jsonify({'code': 1, 'message': '题库不存在或未公开'}), 404

    # 记录使用
    existing = conn.execute(
        'SELECT id FROM public_bank_users WHERE bank_id = ? AND user_id = ?',
        (bank_id, user_id)
    ).fetchone()

    if not existing:
        conn.execute('''
            INSERT INTO public_bank_users (bank_id, user_id, last_access_at, access_count)
            VALUES (?, ?, CURRENT_TIMESTAMP, 1)
        ''', (bank_id, user_id))
        conn.execute(
            'UPDATE user_question_banks SET public_use_count = public_use_count + 1 WHERE id = ?',
            (bank_id,)
        )
        conn.commit()

    return jsonify({'code': 0, 'message': '已加入'})


@public_bank_bp.route('/bank/join')
def join_bank_page():
    """分享链接跳转页面"""
    token = request.args.get('token', '')
    return render_template('user_bank/join.html', token=token)
