# -*- coding: utf-8 -*-
"""用户题库页面路由"""
from flask import Blueprint, render_template, redirect, url_for, request, session
from app.core.utils.database import get_db
from app.core.utils.decorators import login_required

user_bank_pages_bp = Blueprint('user_bank_pages', __name__)


@user_bank_pages_bp.route('/')
@login_required
def banks_list():
    """我的题库首页（复用题库广场模板）"""
    return render_template(
        'user_bank/my_banks.html',
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=session.get('user_id') or 0,
    )


@user_bank_pages_bp.route('/manage')
@login_required
def banks_manage():
    """创建者后台：题库管理（复用科目/题集管理模板）"""
    return render_template('user_bank/banks.html')


@user_bank_pages_bp.route('/manage/shares')
@login_required
def manage_shares():
    """创建者后台：分享管理"""
    return render_template('user_bank/shares_manage_all.html')


@user_bank_pages_bp.route('/<int:bank_id>')
@login_required
def bank_detail(bank_id):
    """题库详情/题目管理页面"""
    return render_template('user_bank/bank_questions.html', bank_id=bank_id)


@user_bank_pages_bp.route('/<int:bank_id>/practice')
@login_required
def bank_practice(bank_id: int):
    """题库练习详情页：与科目详情页一致的练习设置入口。"""
    uid = session.get('user_id')
    conn = get_db()

    from app.modules.user_bank.routes.api import check_bank_access, _load_bank_tag_store

    has_access, permission, access_type = check_bank_access(uid, int(bank_id))
    if not has_access:
        return "题库不存在或无权限访问", 404

    bank = conn.execute(
        """
        SELECT id, name, description, question_count, status
        FROM user_question_banks
        WHERE id = ? AND status = 1
        """,
        (int(bank_id),),
    ).fetchone()

    if not bank:
        return "题库不存在或无权限访问", 404

    types = [
        r['q_type']
        for r in conn.execute(
            """
            SELECT DISTINCT q_type
            FROM user_bank_questions
            WHERE bank_id = ? AND q_type IS NOT NULL AND q_type != ''
            ORDER BY q_type
            """,
            (int(bank_id),),
        ).fetchall()
        if r and r['q_type']
    ]

    # 题库题量：优先用缓存字段；异常时回退实时统计
    total_count = int(bank['question_count'] or 0)
    if total_count <= 0:
        try:
            total_count = conn.execute(
                "SELECT COUNT(*) FROM user_bank_questions WHERE bank_id = ?",
                (int(bank_id),),
            ).fetchone()[0]
        except Exception:
            total_count = 0

    fav_count = 0
    mistake_count = 0
    try:
        fav_count = conn.execute(
            "SELECT COUNT(*) FROM user_bank_favorites WHERE user_id = ? AND bank_id = ?",
            (uid, int(bank_id)),
        ).fetchone()[0]
    except Exception:
        fav_count = 0

    try:
        mistake_count = conn.execute(
            "SELECT COUNT(*) FROM user_bank_mistakes WHERE user_id = ? AND bank_id = ?",
            (uid, int(bank_id)),
        ).fetchone()[0]
    except Exception:
        mistake_count = 0

    # 题库标签（来自 user_progress bank_<id>_tags）
    tags_list = []
    try:
        store = _load_bank_tag_store(conn, int(bank_id), int(uid))
        tag_counts = {t: 0 for t in (store.get('tags') or []) if isinstance(t, str) and t.strip()}
        question_tags = store.get('question_tags', {}) or {}
        for _q_id, tags in question_tags.items():
            if not isinstance(tags, list):
                continue
            for t in tags:
                if t in tag_counts:
                    tag_counts[t] += 1
        tags_list = [{'name': t, 'count': int(tag_counts.get(t, 0))} for t in (store.get('tags') or []) if t in tag_counts]
    except Exception:
        tags_list = []

    return render_template(
        'user_bank/bank_practice.html',
        bank_id=int(bank['id']),
        bank_name=bank['name'],
        bank_description=bank['description'] or '',
        total_count=total_count,
        fav_count=fav_count,
        mistake_count=mistake_count,
        types=types,
        user_tags=tags_list,
        permission=permission,
        access_type=access_type,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@user_bank_pages_bp.route('/<int:bank_id>/search')
@login_required
def bank_search(bank_id: int):
    """题库内搜索页：搜索范围限定在当前题库。"""
    uid = session.get('user_id')
    keyword = (request.args.get('keyword') or '').strip()
    type_filter = (request.args.get('type') or 'all').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20

    from app.modules.user_bank.routes.api import check_bank_access

    has_access, _permission, _access_type = check_bank_access(uid, int(bank_id))
    if not has_access:
        return "题库不存在或无权限访问", 404

    conn = get_db()
    bank = conn.execute(
        "SELECT id, name, status FROM user_question_banks WHERE id = ? AND status = 1",
        (int(bank_id),),
    ).fetchone()
    if not bank:
        return "题库不存在或无权限访问", 404

    available_types = [
        r['q_type']
        for r in conn.execute(
            """
            SELECT DISTINCT q_type
            FROM user_bank_questions
            WHERE bank_id = ? AND q_type IS NOT NULL AND q_type != ''
            ORDER BY q_type
            """,
            (int(bank_id),),
        ).fetchall()
        if r and r['q_type']
    ]

    # 无关键词：展示空搜索页
    if not keyword:
        return render_template(
            'user_bank/bank_search.html',
            bank_id=int(bank['id']),
            bank_name=bank['name'],
            keyword='',
            type_filter=type_filter or 'all',
            available_types=available_types,
            questions=[],
            page=1,
            total_pages=0,
            logged_in=True,
            username=session.get('username'),
            is_admin=session.get('is_admin', False),
            is_subject_admin=session.get('is_subject_admin', False),
            is_notification_admin=session.get('is_notification_admin', False),
            user_id=uid or 0,
        )

    search_term = f'%{keyword}%'
    sql = """
        SELECT id, content, q_type, answer, explanation, updated_at
        FROM user_bank_questions
        WHERE bank_id = ?
          AND (
            content LIKE ? OR explanation LIKE ? OR options LIKE ? OR answer LIKE ?
          )
    """
    params = [int(bank_id), search_term, search_term, search_term, search_term]

    if type_filter and type_filter != 'all':
        sql += " AND q_type = ?"
        params.append(type_filter)

    sql += " ORDER BY updated_at DESC, id DESC"

    # 分页
    total = conn.execute(
        f"SELECT COUNT(1) FROM ({sql}) as t",
        params,
    ).fetchone()[0]
    total_pages = (total + per_page - 1) // per_page if total else 0
    page = max(1, min(page, max(total_pages, 1)))
    offset = (page - 1) * per_page

    rows = conn.execute(
        sql + " LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()

    questions = [dict(r) for r in rows]

    return render_template(
        'user_bank/bank_search.html',
        bank_id=int(bank['id']),
        bank_name=bank['name'],
        keyword=keyword,
        type_filter=type_filter or 'all',
        available_types=available_types,
        questions=questions,
        page=page,
        total_pages=total_pages,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@user_bank_pages_bp.route('/add')
@login_required
def bank_add():
    """创建题库页面"""
    return render_template('user_bank/bank_edit.html', bank_id=None, mode='add')


@user_bank_pages_bp.route('/<int:bank_id>/edit')
@login_required
def bank_edit(bank_id):
    """编辑题库页面"""
    return render_template('user_bank/bank_edit.html', bank_id=bank_id, mode='edit')


@user_bank_pages_bp.route('/<int:bank_id>/questions/add')
@login_required
def question_add(bank_id):
    """添加题目页面"""
    return render_template('user_bank/question_edit.html', bank_id=bank_id, question_id=None, mode='add')


@user_bank_pages_bp.route('/<int:bank_id>/questions/<int:question_id>/edit')
@login_required
def question_edit(bank_id, question_id):
    """编辑题目页面"""
    return render_template('user_bank/question_edit.html', bank_id=bank_id, question_id=question_id, mode='edit')


@user_bank_pages_bp.route('/<int:bank_id>/shares')
@login_required
def shares_manage(bank_id):
    """分享管理页面"""
    return render_template('user_bank/shares.html', bank_id=bank_id)


@user_bank_pages_bp.route('/shared')
@login_required
def shared_banks():
    """收到的分享列表页面"""
    return render_template('user_bank/shared_banks.html')


@user_bank_pages_bp.route('/<int:bank_id>/quiz')
@login_required
def bank_quiz(bank_id):
    """题库刷题页面（复用共有题库刷题模板）"""
    bank_mode = (request.args.get('mode') or 'all').strip().lower()

    # 兼容旧的个人题库刷题参数：all/random/wrong
    params = [f'bank_id={bank_id}']
    if bank_mode == 'wrong':
        params.append('source=mistakes')
    elif bank_mode == 'favorites':
        params.append('source=favorites')
    elif bank_mode == 'random':
        params.append('shuffle_questions=1')

    return redirect('/quiz?' + '&'.join(params))
