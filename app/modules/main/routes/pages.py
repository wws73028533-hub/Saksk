# -*- coding: utf-8 -*-
"""主页面路由"""
from flask import Blueprint, render_template, request, session, redirect, send_from_directory, current_app
import json
import os
from datetime import datetime, timedelta
from app.core.utils.database import get_db
from app.core.utils.decorators import login_required

main_pages_bp = Blueprint('main_pages', __name__)

def _get_accessible_subject_rows(conn, uid):
    """获取用户可访问的科目（id/name），并过滤锁定科目。"""
    if uid:
        from app.core.utils.subject_permissions import get_user_accessible_subjects
        accessible_subject_ids = get_user_accessible_subjects(uid)
        if not accessible_subject_ids:
            return []
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        rows = conn.execute(
            f"SELECT id, name FROM subjects WHERE id IN ({placeholders}) AND (is_locked=0 OR is_locked IS NULL) ORDER BY id",
            accessible_subject_ids,
        ).fetchall()
        return [dict(r) for r in rows]

    rows = conn.execute(
        "SELECT id, name FROM subjects WHERE (is_locked=0 OR is_locked IS NULL) ORDER BY id"
    ).fetchall()
    return [dict(r) for r in rows]


@main_pages_bp.route('/hub')
def hub():
    """介绍页"""
    uid = session.get('user_id')
    conn = get_db()

    subject_total = 0
    question_total = 0
    my_bank_total = 0

    try:
        if uid:
            subjects_meta = _get_accessible_subject_rows(conn, uid)
            subject_total = len(subjects_meta or [])

            subject_ids = [
                int(s['id'])
                for s in (subjects_meta or [])
                if s and s.get('id') is not None
            ]
            if subject_ids:
                placeholders = ','.join(['?'] * len(subject_ids))
                question_total = conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM questions q
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    """,
                    subject_ids,
                ).fetchone()[0]
        else:
            subject_total = conn.execute(
                "SELECT COUNT(*) FROM subjects WHERE (is_locked=0 OR is_locked IS NULL)"
            ).fetchone()[0]
            question_total = conn.execute(
                """
                SELECT COUNT(*)
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                """
            ).fetchone()[0]
    except Exception as e:
        current_app.logger.error(f"Error fetching hub stats: {e}")
        subject_total = 0
        question_total = 0

    if uid:
        try:
            my_bank_total = conn.execute(
                "SELECT COUNT(*) FROM user_question_banks WHERE user_id = ? AND status = 1",
                (uid,),
            ).fetchone()[0]
        except Exception:
            my_bank_total = 0

    return render_template(
        'main/hub.html',
        subject_total=subject_total,
        question_total=question_total,
        my_bank_total=my_bank_total,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/')
def index():
    """首页（公共题库）"""
    uid = session.get('user_id')
    conn = get_db()

    subjects_meta = []
    try:
        subjects_meta = _get_accessible_subject_rows(conn, uid)
    except Exception:
        subjects_meta = []

    subject_counts = {}
    quiz_count = 0

    if uid:
        try:
            subject_ids = [
                int(s['id'])
                for s in (subjects_meta or [])
                if s and s.get('id') is not None
            ]
            if subject_ids:
                placeholders = ','.join(['?'] * len(subject_ids))
                rows = conn.execute(
                    f"""
                    SELECT q.subject_id as subject_id, COUNT(*) as cnt
                    FROM questions q
                    LEFT JOIN subjects s ON q.subject_id = s.id
                    WHERE q.subject_id IN ({placeholders})
                      AND (s.is_locked=0 OR s.is_locked IS NULL)
                    GROUP BY q.subject_id
                    """,
                    subject_ids,
                ).fetchall()
                subject_counts = {
                    int(r['subject_id']): int(r['cnt'])
                    for r in rows
                    if r and r['subject_id'] is not None
                }
            quiz_count = int(sum(subject_counts.values())) if subject_counts else 0
        except Exception:
            subject_counts = {}
            quiz_count = 0
    else:
        try:
            quiz_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                """
            ).fetchone()[0]
        except Exception:
            quiz_count = 0

        try:
            rows = conn.execute(
                """
                SELECT q.subject_id as subject_id, COUNT(*) as cnt
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                GROUP BY q.subject_id
                """
            ).fetchall()
            subject_counts = {
                int(r['subject_id']): int(r['cnt'])
                for r in rows
                if r and r['subject_id'] is not None
            }
        except Exception:
            subject_counts = {}

    return render_template(
        'main/public_bank.html',
        quiz_count=quiz_count,
        subjects_meta=subjects_meta,
        subject_counts=subject_counts,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )

@main_pages_bp.route('/subjects/<int:subject_id>')
def subject_detail_page(subject_id: int):
    """科目详情页：承接题型/标签/收藏等选择与开始刷题。"""
    uid = session.get('user_id')
    conn = get_db()

    subject = conn.execute(
        "SELECT id, name, is_locked FROM subjects WHERE id = ?",
        (subject_id,),
    ).fetchone()

    if not subject or int(subject['is_locked'] or 0) == 1:
        return "科目不存在或已锁定", 404

    # 已登录用户：校验科目权限
    if uid:
        from app.core.utils.subject_permissions import can_user_access_subject
        if not can_user_access_subject(uid, int(subject_id)):
            return "无权限访问该科目", 403

    # 题型列表
    types = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT q_type FROM questions WHERE subject_id = ? ORDER BY q_type",
            (subject_id,),
        ).fetchall()
        if r and r[0]
    ]

    # 科目题量
    total_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE q.subject_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """,
        (subject_id,),
    ).fetchone()[0]

    fav_count = 0
    mistake_count = 0
    user_tags = []
    if uid:
        try:
            fav_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                WHERE f.user_id = ? AND q.subject_id = ?
                """,
                (uid, subject_id),
            ).fetchone()[0]
        except Exception:
            fav_count = 0

        try:
            mistake_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                WHERE m.user_id = ? AND q.subject_id = ?
                """,
                (uid, subject_id),
            ).fetchone()[0]
        except Exception:
            mistake_count = 0

        try:
            from app.modules.quiz.services.question_tags_service import list_user_tags
            user_tags = list_user_tags(conn, uid)
        except Exception:
            user_tags = []

    return render_template(
        'main/subject_detail.html',
        subject_id=int(subject['id']),
        subject_name=subject['name'],
        types=types,
        total_count=total_count,
        fav_count=fav_count,
        mistake_count=mistake_count,
        user_tags=user_tags,
        logged_in=bool(uid),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/favorites')
@login_required
def favorites_detail_page():
    """收藏详情页（新页面）：选择科目/题型/标签后进入刷题/背题。"""
    uid = session.get('user_id')
    conn = get_db()

    tab = (request.args.get('tab') or '').strip().lower()
    if tab not in ('practice', 'stats'):
        tab = 'practice'

    subjects_meta = _get_accessible_subject_rows(conn, uid)
    subjects = [s['name'] for s in subjects_meta]
    accessible_subject_ids = [s['id'] for s in subjects_meta]

    # 预选科目（可选：subject_id=...）
    subject_id = request.args.get('subject_id', type=int)
    subject_name = 'all'
    if subject_id:
        matched = next((s for s in subjects_meta if int(s['id']) == int(subject_id)), None)
        if matched:
            subject_name = matched['name']

    # 题型映射：subject -> [types]
    subject_q_types = {}
    if accessible_subject_ids:
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        rows = conn.execute(
            f"""
            SELECT s.name, GROUP_CONCAT(DISTINCT q.q_type)
            FROM subjects s
            LEFT JOIN questions q ON s.id = q.subject_id
            WHERE s.id IN ({placeholders}) AND (s.is_locked=0 OR s.is_locked IS NULL)
            GROUP BY s.name
            ORDER BY s.id
            """,
            accessible_subject_ids,
        ).fetchall()
        for row in rows:
            if row[0] and row[1]:
                subject_q_types[row[0]] = sorted(list(set(row[1].split(','))))
            elif row[0]:
                subject_q_types[row[0]] = []

    # 总收藏数（按权限过滤）
    fav_total = 0
    try:
        sql = """
            SELECT COUNT(*)
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid]
        if accessible_subject_ids:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        fav_total = conn.execute(sql, params).fetchone()[0]
    except Exception:
        fav_total = 0

    # 各科目收藏数（用于徽标）
    fav_by_subject = {}
    try:
        if accessible_subject_ids:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id as subject_id, COUNT(*) as cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + accessible_subject_ids,
            ).fetchall()
            fav_by_subject = {int(r['subject_id']): int(r['cnt']) for r in rows if r and r['subject_id'] is not None}
    except Exception:
        fav_by_subject = {}

    # 收藏分布：题型
    fav_by_type = []
    try:
        sql = """
            SELECT COALESCE(q.q_type, '未知') AS q_type, COUNT(*) AS cnt
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid]
        if accessible_subject_ids:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        sql += " GROUP BY q.q_type ORDER BY cnt DESC"
        rows = conn.execute(sql, params).fetchall()
        fav_by_type = [{'q_type': (r['q_type'] or '未知'), 'count': int(r['cnt'] or 0)} for r in (rows or []) if r]
    except Exception:
        fav_by_type = []

    fav_subject_rows = []
    try:
        for s in subjects_meta or []:
            sid = int(s['id'])
            cnt = int(fav_by_subject.get(sid, 0) or 0)
            if cnt > 0:
                fav_subject_rows.append({'subject_id': sid, 'subject': s['name'], 'count': cnt})
        fav_subject_rows.sort(key=lambda x: x['count'], reverse=True)
    except Exception:
        fav_subject_rows = []

    fav_subject_max = max([x.get('count', 0) for x in fav_subject_rows], default=0)
    fav_type_max = max([x.get('count', 0) for x in fav_by_type], default=0)

    user_tags = []
    try:
        from app.modules.quiz.services.question_tags_service import list_user_tags
        user_tags = list_user_tags(conn, uid)
    except Exception:
        user_tags = []

    return render_template(
        'main/favorites_detail.html',
        favorites_total=fav_total,
        subjects_meta=subjects_meta,
        subject_q_types_json=json.dumps(subject_q_types, ensure_ascii=False),
        fav_by_subject=fav_by_subject,
        fav_subject_rows=fav_subject_rows,
        fav_subject_max=fav_subject_max or 1,
        fav_by_type=fav_by_type,
        fav_type_max=fav_type_max or 1,
        selected_subject=subject_name,
        user_tags=user_tags,
        active_tab=tab,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/mistakes')
@login_required
def mistakes_detail_page():
    """错题详情页（新页面）：选择科目/题型/标签后进入刷题/背题。"""
    uid = session.get('user_id')
    conn = get_db()

    tab = (request.args.get('tab') or '').strip().lower()
    if tab not in ('practice', 'stats'):
        tab = 'practice'

    mistakes_has_wrong_count = False
    try:
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(mistakes)").fetchall()]
        mistakes_has_wrong_count = 'wrong_count' in cols
    except Exception:
        mistakes_has_wrong_count = False

    subjects_meta = _get_accessible_subject_rows(conn, uid)
    subjects = [s['name'] for s in subjects_meta]
    accessible_subject_ids = [s['id'] for s in subjects_meta]

    subject_id = request.args.get('subject_id', type=int)
    subject_name = 'all'
    if subject_id:
        matched = next((s for s in subjects_meta if int(s['id']) == int(subject_id)), None)
        if matched:
            subject_name = matched['name']

    subject_q_types = {}
    if accessible_subject_ids:
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        rows = conn.execute(
            f"""
            SELECT s.name, GROUP_CONCAT(DISTINCT q.q_type)
            FROM subjects s
            LEFT JOIN questions q ON s.id = q.subject_id
            WHERE s.id IN ({placeholders}) AND (s.is_locked=0 OR s.is_locked IS NULL)
            GROUP BY s.name
            ORDER BY s.id
            """,
            accessible_subject_ids,
        ).fetchall()
        for row in rows:
            if row[0] and row[1]:
                subject_q_types[row[0]] = sorted(list(set(row[1].split(','))))
            elif row[0]:
                subject_q_types[row[0]] = []

    mis_total = 0
    mis_times = 0
    try:
        if mistakes_has_wrong_count:
            sql = """
                SELECT
                  COUNT(*) AS cnt,
                  SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            """
        else:
            sql = """
                SELECT COUNT(*) AS cnt
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            """
        params = [uid]
        if accessible_subject_ids:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        row = conn.execute(sql, params).fetchone()
        mis_total = int(row['cnt'] or 0) if row else 0
        if mistakes_has_wrong_count:
            mis_times = int(row['times'] or 0) if row else 0
        else:
            mis_times = mis_total
    except Exception:
        mis_total = 0
        mis_times = 0

    mis_by_subject = {}
    try:
        if accessible_subject_ids:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id as subject_id, COUNT(*) as cnt
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + accessible_subject_ids,
            ).fetchall()
            mis_by_subject = {int(r['subject_id']): int(r['cnt']) for r in rows if r and r['subject_id'] is not None}
    except Exception:
        mis_by_subject = {}

    # 错题分布：题型
    mis_by_type = []
    try:
        sql = """
            SELECT COALESCE(q.q_type, '未知') AS q_type, COUNT(*) AS cnt
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = [uid]
        if accessible_subject_ids:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        sql += " GROUP BY q.q_type ORDER BY cnt DESC"
        rows = conn.execute(sql, params).fetchall()
        mis_by_type = [{'q_type': (r['q_type'] or '未知'), 'count': int(r['cnt'] or 0)} for r in (rows or []) if r]
    except Exception:
        mis_by_type = []

    mis_subject_rows = []
    try:
        for s in subjects_meta or []:
            sid = int(s['id'])
            cnt = int(mis_by_subject.get(sid, 0) or 0)
            if cnt > 0:
                mis_subject_rows.append({'subject_id': sid, 'subject': s['name'], 'count': cnt})
        mis_subject_rows.sort(key=lambda x: x['count'], reverse=True)
    except Exception:
        mis_subject_rows = []

    mis_subject_max = max([x.get('count', 0) for x in mis_subject_rows], default=0)
    mis_type_max = max([x.get('count', 0) for x in mis_by_type], default=0)

    user_tags = []
    try:
        from app.modules.quiz.services.question_tags_service import list_user_tags
        user_tags = list_user_tags(conn, uid)
    except Exception:
        user_tags = []

    return render_template(
        'main/mistakes_detail.html',
        mistakes_total=mis_total,
        mistakes_times=mis_times,
        subjects_meta=subjects_meta,
        subject_q_types_json=json.dumps(subject_q_types, ensure_ascii=False),
        mis_by_subject=mis_by_subject,
        mis_subject_rows=mis_subject_rows,
        mis_subject_max=mis_subject_max or 1,
        mis_by_type=mis_by_type,
        mis_type_max=mis_type_max or 1,
        selected_subject=subject_name,
        user_tags=user_tags,
        active_tab=tab,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid or 0,
    )


@main_pages_bp.route('/search')
def search_page():
    """搜索页面 - 支持高级搜索选项"""
    keyword = request.args.get('keyword', '').strip()
    subject_filter = request.args.get('subject', '').strip()
    type_filter = request.args.get('type', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 每页显示数量

    uid = session.get('user_id') or -1
    conn = get_db()

    # 获取所有科目和题型用于筛选下拉框（添加权限过滤）
    from app.core.utils.subject_permissions import get_user_accessible_subjects
    try:
        user_id = session.get('user_id')
        if user_id:
            accessible_subject_ids = get_user_accessible_subjects(user_id)
            if accessible_subject_ids:
                placeholders = ','.join(['?'] * len(accessible_subject_ids))
                subjects = [row[0] for row in conn.execute(
                    f"SELECT name FROM subjects WHERE id IN ({placeholders}) AND (is_locked=0 OR is_locked IS NULL)",
                    accessible_subject_ids
                ).fetchall()]
            else:
                subjects = []
        else:
            subjects = []  # 未登录用户返回空列表
        q_types = [row[0] for row in conn.execute("SELECT DISTINCT q_type FROM questions").fetchall()]
    except:
        subjects = []
        q_types = []

    # 如果没有关键词，显示空的搜索页面
    if not keyword:
        return render_template('main/search.html',
                             keyword='',
                             questions=[],
                             subjects=subjects,
                             q_types=q_types,
                             subject=subject_filter,
                             q_type=type_filter,
                             page=1,
                             total_pages=0,
                             search_history=[],
                             logged_in=bool(session.get('user_id')),
                             username=session.get('username'))

    # 构建搜索SQL
    sql_base = """
        SELECT q.*, s.name as subject,
               CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav,
               CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mistake
        FROM questions q
        LEFT JOIN subjects s ON q.subject_id = s.id
        LEFT JOIN favorites f ON q.id = f.question_id AND f.user_id = ?
        LEFT JOIN mistakes m ON q.id = m.question_id AND m.user_id = ?
        WHERE (q.content LIKE ? OR q.explanation LIKE ? OR q.options LIKE ? OR q.answer LIKE ?)
        AND (s.is_locked=0 OR s.is_locked IS NULL)
    """

    search_term = f'%{keyword}%'
    params = [uid, uid, search_term, search_term, search_term, search_term]
    
    # 添加权限过滤：只搜索用户可访问的科目
    if user_id:
        if accessible_subject_ids:
            placeholders = ','.join(['?'] * len(accessible_subject_ids))
            sql_base += f" AND q.subject_id IN ({placeholders})"
            params.extend(accessible_subject_ids)
        else:
            # 如果没有可访问的科目，返回空结果
            sql_base += " AND 1=0"
    else:
        # 未登录用户：返回空结果
        sql_base += " AND 1=0"

    # 添加科目筛选
    if subject_filter:
        sql_base += " AND s.name = ?"
        params.append(subject_filter)

    # 添加题型筛选
    if type_filter:
        sql_base += " AND q.q_type = ?"
        params.append(type_filter)

    # 先获取总数
    count_sql = f"SELECT COUNT(*) FROM ({sql_base})"
    total_count = conn.execute(count_sql, params).fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 0

    # 确保页码有效
    if page < 1:
        page = 1
    if total_pages > 0 and page > total_pages:
        page = total_pages

    # 添加排序和分页
    sql = sql_base + " ORDER BY q.id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])

    rows = conn.execute(sql, params).fetchall()
    
    questions = []
    for row in rows:
        q = dict(row)
        
        # 提前处理答案和选项
        correct_answer_key = str(q.get('answer', '')).strip()
        q['full_answer'] = correct_answer_key  # 默认答案为标识符

        if q.get('options') and isinstance(q.get('options'), str):
            try:
                options_list = json.loads(q['options'])
                if isinstance(options_list, list):
                    new_options = []
                    options_map = {}
                    for item_str in options_list:
                        delimiter = '、' if '、' in item_str else '.'
                        parts = item_str.split(delimiter, 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            new_options.append({'key': key, 'value': value})
                            options_map[key] = value
                    q['options'] = new_options

                    # 尝试为所有选项构建完整答案
                    if correct_answer_key in options_map:
                        q['full_answer'] = f"{correct_answer_key}. {options_map[correct_answer_key]}"
                else:
                    q['options'] = []
            except (json.JSONDecodeError, TypeError):
                q['options'] = []
        else:
            q['options'] = []
        questions.append(q)

    return render_template('main/search.html',
                         keyword=keyword,
                         questions=questions,
                         subjects=subjects,
                         q_types=q_types,
                         subject=subject_filter,
                         q_type=type_filter,
                         page=page,
                         total_pages=total_pages,
                         search_history=[],
                         logged_in=bool(session.get('user_id')),
                         username=session.get('username'))


@main_pages_bp.route('/history')
def history_page():
    """学习统计页面：汇总 + 趋势 + 薄弱点"""
    uid = session.get('user_id')
    if not uid:
        return redirect('/login')

    conn = get_db()

    def _column_exists(table: str, column: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            return any(r and r['name'] == column for r in rows)
        except Exception:
            return False

    subjects_meta = _get_accessible_subject_rows(conn, uid)
    subject_ids = [
        int(s['id'])
        for s in (subjects_meta or [])
        if s and s.get('id') is not None
    ]

    # 公共题库总题数（按权限与锁定过滤）
    total_questions = 0
    try:
        base_sql = """
            SELECT COUNT(*)
            FROM questions q
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE (s.is_locked=0 OR s.is_locked IS NULL)
        """
        params = []
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            base_sql += f" AND q.subject_id IN ({placeholders})"
            params.extend(subject_ids)
        total_questions = conn.execute(base_sql, params).fetchone()[0]
    except Exception:
        total_questions = 0

    # 复用 join + 权限过滤（公共题库）
    ua_from = """
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        LEFT JOIN subjects s ON q.subject_id = s.id
        WHERE ua.user_id = ?
          AND (s.is_locked=0 OR s.is_locked IS NULL)
    """
    ua_params_base = [uid]
    if subject_ids:
        placeholders = ','.join(['?'] * len(subject_ids))
        ua_from += f" AND q.subject_id IN ({placeholders})"
        ua_params_base.extend(subject_ids)

    # 全局汇总（公共题库）
    answered_count = 0
    correct_count = 0
    last_activity = None
    try:
        row = conn.execute(
            f"""
            SELECT
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct,
              MAX(ua.created_at) AS last_activity
            {ua_from}
            """,
            ua_params_base,
        ).fetchone()
        answered_count = int(row['answered'] or 0) if row else 0
        correct_count = int(row['correct'] or 0) if row else 0
        last_activity = (row['last_activity'] if row else None) or None
    except Exception:
        answered_count = 0
        correct_count = 0
        last_activity = None

    accuracy = round(correct_count * 100 / answered_count, 1) if answered_count > 0 else 0.0
    completion = round(answered_count * 100 / total_questions, 1) if total_questions > 0 else 0.0

    # 收藏/错题（公共题库）
    favorites_count = 0
    mistakes_count = 0
    mistakes_times = 0  # 若存在 wrong_count 则为累计次数，否则退化为 mistakes_count
    try:
        fav_sql = """
            SELECT COUNT(*)
            FROM favorites f
            JOIN questions q ON f.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        fav_params = [uid]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            fav_sql += f" AND q.subject_id IN ({placeholders})"
            fav_params.extend(subject_ids)
        favorites_count = conn.execute(fav_sql, fav_params).fetchone()[0]
    except Exception:
        favorites_count = 0

    mistakes_has_wrong_count = _column_exists('mistakes', 'wrong_count')
    mistakes_has_updated_at = _column_exists('mistakes', 'updated_at')
    try:
        mis_sql = """
            SELECT
              COUNT(*) AS cnt,
              SUM(CASE WHEN m.wrong_count IS NULL THEN 1 ELSE m.wrong_count END) AS times
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
        """
        mis_params = [uid]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            mis_sql += f" AND q.subject_id IN ({placeholders})"
            mis_params.extend(subject_ids)
        if not mistakes_has_wrong_count:
            mis_sql = mis_sql.replace("m.wrong_count", "NULL")
        row = conn.execute(mis_sql, mis_params).fetchone()
        mistakes_count = int(row['cnt'] or 0) if row else 0
        mistakes_times = int(row['times'] or 0) if row else 0
        if not mistakes_has_wrong_count:
            mistakes_times = mistakes_count
    except Exception:
        mistakes_count = 0
        mistakes_times = 0

    # 连续学习天数（基于 user_answers 的 DATE(created_at)）
    streak_days = 0
    try:
        rows = conn.execute(
            f"SELECT DISTINCT DATE(ua.created_at) AS day {ua_from} ORDER BY day DESC LIMIT 120",
            ua_params_base,
        ).fetchall()
        dates = []
        for r in rows or []:
            if r and r['day']:
                try:
                    dates.append(datetime.strptime(r['day'], '%Y-%m-%d').date())
                except Exception:
                    continue
        today = datetime.now().date()
        if dates and dates[0] >= (today - timedelta(days=1)):
            streak_days = 1
            for i in range(1, len(dates)):
                if dates[i - 1] - dates[i] == timedelta(days=1):
                    streak_days += 1
                else:
                    break
    except Exception:
        streak_days = 0

    def _count_since(days: int) -> tuple[int, int]:
        if days <= 0:
            return answered_count, correct_count
        try:
            row = conn.execute(
                f"""
                SELECT
                  COUNT(*) AS answered,
                  SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                {ua_from}
                  AND ua.created_at >= datetime('now', ?)
                """,
                ua_params_base + [f'-{days} days'],
            ).fetchone()
            return int(row['answered'] or 0), int(row['correct'] or 0)
        except Exception:
            return 0, 0

    answered_7d, correct_7d = _count_since(7)
    answered_30d, correct_30d = _count_since(30)

    # 趋势窗口（只影响趋势图展示）
    window_days = request.args.get('days', 30, type=int)
    if window_days not in (7, 30, 90):
        window_days = 30

    daily = []
    daily_max = 0
    window_answered = 0
    window_correct = 0
    window_accuracy = 0.0
    try:
        rows = conn.execute(
            f"""
            SELECT
              DATE(ua.created_at) AS day,
              COUNT(*) AS total,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
              AND ua.created_at >= datetime('now', ?)
            GROUP BY DATE(ua.created_at)
            ORDER BY day
            """,
            ua_params_base + [f'-{window_days} days'],
        ).fetchall()
        data_map = {r['day']: {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in (rows or []) if r and r['day']}

        today = datetime.now().date()
        start = today - timedelta(days=window_days - 1)
        for i in range(window_days):
            d = start + timedelta(days=i)
            key = d.strftime('%Y-%m-%d')
            total = int((data_map.get(key) or {}).get('total', 0))
            correct = int((data_map.get(key) or {}).get('correct', 0))
            acc = round(correct * 100 / total, 1) if total > 0 else 0.0
            daily_max = max(daily_max, total)
            daily.append({'day': key, 'total': total, 'correct': correct, 'accuracy': acc})

        window_answered = sum(int(x.get('total', 0) or 0) for x in daily)
        window_correct = sum(int(x.get('correct', 0) or 0) for x in daily)
        window_accuracy = round(window_correct * 100 / window_answered, 1) if window_answered > 0 else 0.0
    except Exception as e:
        current_app.logger.warning(f"history daily stats failed: {e}")
        daily = []
        daily_max = 0
        window_answered = 0
        window_correct = 0
        window_accuracy = 0.0

    # 科目维度（公共题库）
    subject_rows = []
    try:
        # 总题数（每科目）
        total_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS total
                FROM questions q
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                subject_ids,
            ).fetchall()
            total_map = {int(r['subject_id']): int(r['total'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

        # 已做/正确（每科目）
        ans_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id,
                       COUNT(*) AS answered,
                       SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
                FROM user_answers ua
                JOIN questions q ON ua.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE ua.user_id = ?
                  AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            ans_map = {
                int(r['subject_id']): {'answered': int(r['answered'] or 0), 'correct': int(r['correct'] or 0)}
                for r in (rows or [])
                if r and r['subject_id'] is not None
            }

        # 错题/收藏（每科目）
        mis_map = {}
        fav_map = {}
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM mistakes m
                JOIN questions q ON m.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            mis_map = {int(r['subject_id']): int(r['cnt'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

            rows = conn.execute(
                f"""
                SELECT q.subject_id AS subject_id, COUNT(*) AS cnt
                FROM favorites f
                JOIN questions q ON f.question_id = q.id
                LEFT JOIN subjects s ON q.subject_id = s.id
                WHERE f.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
                  AND q.subject_id IN ({placeholders})
                GROUP BY q.subject_id
                """,
                [uid] + subject_ids,
            ).fetchall()
            fav_map = {int(r['subject_id']): int(r['cnt'] or 0) for r in (rows or []) if r and r['subject_id'] is not None}

        for s in subjects_meta or []:
            sid = int(s['id'])
            total = int(total_map.get(sid, 0))
            answered = int((ans_map.get(sid) or {}).get('answered', 0))
            correct = int((ans_map.get(sid) or {}).get('correct', 0))
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            comp = round(answered * 100 / total, 1) if total > 0 else 0.0
            subject_rows.append({
                'subject_id': sid,
                'subject': s['name'],
                'total': total,
                'answered': answered,
                'correct': correct,
                'accuracy': acc,
                'completion': comp,
                'mistakes': int(mis_map.get(sid, 0)),
                'favorites': int(fav_map.get(sid, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history subject stats failed: {e}")
        subject_rows = []

    # 题型维度（公共题库）
    type_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(q.q_type, '未知') AS q_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY q.q_type
            ORDER BY answered DESC
            """,
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            type_rows.append({
                'q_type': r['q_type'] or '未知',
                'answered': answered,
                'correct': correct,
                'accuracy': round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history type stats failed: {e}")
        type_rows = []

    # 难度维度（公共题库）
    difficulty_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(q.difficulty, 1) AS difficulty,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY q.difficulty
            ORDER BY difficulty ASC
            """,
            ua_params_base,
        ).fetchall()
        for r in rows or []:
            diff = int(r['difficulty'] or 1)
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            label = {1: '简单', 2: '中等', 3: '困难'}.get(diff, f'难度{diff}')
            difficulty_rows.append({
                'difficulty': diff,
                'label': label,
                'answered': answered,
                'correct': correct,
                'accuracy': round(correct * 100 / answered, 1) if answered > 0 else 0.0,
            })
    except Exception as e:
        current_app.logger.warning(f"history difficulty stats failed: {e}")
        difficulty_rows = []

    # 薄弱点：科目 × 题型（公共题库）
    weakness_rows = []
    try:
        rows = conn.execute(
            f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(q.q_type, '未知') AS q_type,
              COUNT(*) AS answered,
              SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct
            {ua_from}
            GROUP BY s.name, q.q_type
            HAVING answered >= 5
            ORDER BY (correct * 1.0 / answered) ASC, answered DESC
            LIMIT 8
            """,
            ua_params_base,
        ).fetchall()

        # 错题分布（用于提示强弱）
        mis_rows = conn.execute(
            f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(q.q_type, '未知') AS q_type,
              COUNT(*) AS mistakes
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            {('AND q.subject_id IN (' + ','.join(['?']*len(subject_ids)) + ')') if subject_ids else ''}
            GROUP BY s.name, q.q_type
            """,
            [uid] + (subject_ids if subject_ids else []),
        ).fetchall()
        mis_map = {(r['subject'] or '未分类', r['q_type'] or '未知'): int(r['mistakes'] or 0) for r in (mis_rows or []) if r}

        for r in rows or []:
            answered = int(r['answered'] or 0)
            correct = int(r['correct'] or 0)
            acc = round(correct * 100 / answered, 1) if answered > 0 else 0.0
            key = (r['subject'] or '未分类', r['q_type'] or '未知')
            weakness_rows.append({
                'subject': r['subject'] or '未分类',
                'q_type': r['q_type'] or '未知',
                'answered': answered,
                'correct': correct,
                'accuracy': acc,
                'mistakes': int(mis_map.get(key, 0)),
            })
    except Exception as e:
        current_app.logger.warning(f"history weakness stats failed: {e}")
        weakness_rows = []

    # 最近错题（公共题库）
    recent_mistakes = []
    try:
        order_by = "m.created_at DESC"
        if mistakes_has_wrong_count:
            # 优先看错得多的题，其次最近更新
            order_by = "m.wrong_count DESC, COALESCE(m.updated_at, m.created_at) DESC" if mistakes_has_updated_at else "m.wrong_count DESC, m.created_at DESC"
        sql = f"""
            SELECT
              COALESCE(s.name, '未分类') AS subject,
              COALESCE(q.q_type, '未知') AS q_type,
              q.id AS question_id,
              q.content AS content,
              q.difficulty AS difficulty,
              m.created_at AS created_at
              {', m.wrong_count AS wrong_count' if mistakes_has_wrong_count else ''}
            FROM mistakes m
            JOIN questions q ON m.question_id = q.id
            LEFT JOIN subjects s ON q.subject_id = s.id
            WHERE m.user_id = ? AND (s.is_locked=0 OR s.is_locked IS NULL)
            {('AND q.subject_id IN (' + ','.join(['?']*len(subject_ids)) + ')') if subject_ids else ''}
            ORDER BY {order_by}
            LIMIT 8
        """
        rows = conn.execute(sql, [uid] + (subject_ids if subject_ids else [])).fetchall()
        for r in rows or []:
            content = (r['content'] or '').strip().replace('\r', ' ').replace('\n', ' ')
            snippet = content[:80] + ('…' if len(content) > 80 else '')
            recent_mistakes.append({
                'subject': r['subject'] or '未分类',
                'q_type': r['q_type'] or '未知',
                'question_id': int(r['question_id']),
                'snippet': snippet,
                'difficulty': int(r['difficulty'] or 1),
                'wrong_count': int(r['wrong_count'] or 1) if mistakes_has_wrong_count else None,
            })
    except Exception as e:
        current_app.logger.warning(f"history recent mistakes failed: {e}")
        recent_mistakes = []

    # 用于 UI 的“下一步建议”
    next_actions = []
    try:
        for w in (weakness_rows or [])[:3]:
            next_actions.append({
                'title': f"{w['subject']} · {w['q_type']}",
                'meta': f"正确率 {w['accuracy']}%（已做 {w['answered']}）",
                'subject': w['subject'],
                'q_type': w['q_type'],
            })
    except Exception:
        next_actions = []

    return render_template(
        'main/history.html',
        total_questions=total_questions,
        answered_count=answered_count,
        correct_count=correct_count,
        accuracy=accuracy,
        completion=completion,
        favorites_count=favorites_count,
        mistakes_count=mistakes_count,
        mistakes_times=mistakes_times,
        streak_days=streak_days,
        last_activity=last_activity,
        answered_7d=answered_7d,
        correct_7d=correct_7d,
        answered_30d=answered_30d,
        correct_30d=correct_30d,
        window_days=window_days,
        daily=daily,
        daily_max=daily_max or 1,
        window_answered=window_answered,
        window_correct=window_correct,
        window_accuracy=window_accuracy,
        subject_rows=subject_rows,
        type_rows=type_rows,
        difficulty_rows=difficulty_rows,
        weakness_rows=weakness_rows,
        recent_mistakes=recent_mistakes,
        next_actions=next_actions,
        logged_in=True,
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
        user_id=uid,
    )


@main_pages_bp.route('/profile')
def profile_page():
    """个人资料页面（兼容旧入口）"""
    return redirect('/settings/account/profile')


@main_pages_bp.route('/account')
def account_page():
    """账号管理页面"""
    return redirect('/settings/account/profile')


@main_pages_bp.route('/account/profile')
def account_profile_page():
    """账号 - 个人资料"""
    return redirect('/settings/account/profile')


@main_pages_bp.route('/account/security')
def account_security_page():
    """账号 - 账号安全"""
    return redirect('/settings/account/security')


@main_pages_bp.route('/account/bindings')
def account_bindings_page():
    """账号 - 账号绑定"""
    return redirect('/settings/account/bindings')


@main_pages_bp.route('/settings')
def settings_page():
    """设置页入口"""
    return redirect('/settings/account/profile')


@main_pages_bp.route('/settings/account/profile')
def settings_account_profile_page():
    """设置 - 账号管理 - 个人资料"""
    return render_template('main/account/profile.html')


@main_pages_bp.route('/settings/account/security')
def settings_account_security_page():
    """设置 - 账号管理 - 账号安全"""
    return render_template('main/account/security.html')


@main_pages_bp.route('/settings/account/bindings')
def settings_account_bindings_page():
    """设置 - 账号管理 - 账号绑定"""
    return render_template('main/account/bindings.html')


@main_pages_bp.route('/settings/hotkeys')
def settings_hotkeys_page():
    """设置 - 快捷键"""
    return render_template('main/settings/hotkeys.html')


@main_pages_bp.route('/settings/practice')
def settings_practice_page():
    """设置 - 练习管理"""
    return render_template('main/settings/practice.html')


@main_pages_bp.route('/settings/about')
def settings_about_page():
    """设置 - 关于"""
    return render_template('main/settings/about.html')


@main_pages_bp.route('/quiz_settings')
def quiz_settings_page():
    """题库设置页面"""
    return redirect('/settings')


@main_pages_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """安全地提供上传的文件（支持音视频 Range 请求）"""
    directory = os.path.join(current_app.root_path, '..', 'uploads')
    resp = send_from_directory(directory, filename, conditional=True)
    # 让浏览器/音频组件更愿意做断点/Range 拉取（部分移动端对流式更敏感）
    resp.headers.setdefault('Accept-Ranges', 'bytes')
    return resp


@main_pages_bp.route('/contact_admin')
def contact_admin_page():
    """联系管理员入口页

    目标：
    - 普通用户：可一键跳转到与管理员的私聊（自动创建/复用会话）
    - 管理员：提示"不可用"（避免自己联系自己）

    说明：此页仅做入口/路由分流，实际聊天在 /chat 页面内完成。
    """
    if not session.get('user_id'):
        return redirect('/login')

    # 管理员不需要"联系管理员"（避免自己给自己发起会话）
    if session.get('is_admin'):
        return render_template(
            'main/contact_admin.html',
            logged_in=True,
            username=session.get('username'),
            is_admin=True,
            disabled=True,
            reason='您当前已是管理员，无需联系管理员。',
        )

    conn = get_db()

    # 选一个管理员作为接收方：优先按 last_active 最新，其次 id 最小
    admin = conn.execute(
        """
        SELECT id, username
        FROM users
        WHERE is_admin = 1
        ORDER BY (last_active IS NULL) ASC, last_active DESC, id ASC
        LIMIT 1
        """
    ).fetchone()

    if not admin:
        return render_template(
            'main/contact_admin.html',
            logged_in=True,
            username=session.get('username'),
            is_admin=False,
            disabled=True,
            reason='系统暂未配置管理员账号，请稍后再试。',
        )

    return render_template(
        'main/contact_admin.html',
        logged_in=True,
        username=session.get('username'),
        is_admin=False,
        disabled=False,
        admin_user_id=admin['id'],
        admin_username=admin['username'],
    )


@main_pages_bp.route('/about')
def about_page():
    """关于页面（占位）"""
    return redirect('/settings/about')
