# -*- coding: utf-8 -*-
"""
主页路由蓝图
"""
from flask import Blueprint, render_template, request, session, redirect, send_from_directory, current_app
import os
import os
from ..utils.database import get_db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """首页"""
    uid = session.get('user_id')
    conn = get_db()
    
    try:
        # 统计基础数据
        quiz_count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        
        # 统计当前用户的收藏/错题
        if uid:
            fav_count = conn.execute(
                "SELECT COUNT(*) FROM favorites f INNER JOIN questions q ON f.question_id = q.id WHERE f.user_id = ?",
                (uid,)
            ).fetchone()[0]
            mistake_count = conn.execute(
                "SELECT COUNT(*) FROM mistakes m INNER JOIN questions q ON m.question_id = q.id WHERE m.user_id = ?",
                (uid,)
            ).fetchone()[0]
        else:
            fav_count = 0
            mistake_count = 0
        
        # 获取所有科目和题型
        subjects = [row[0] for row in conn.execute("SELECT name FROM subjects").fetchall()]
        q_types = [row[0] for row in conn.execute("SELECT DISTINCT q_type FROM questions").fetchall()]
    except Exception as e:
        quiz_count = 0
        fav_count = 0
        mistake_count = 0
        subjects = []
        q_types = []
    
    return render_template('index.html',
                         quiz_count=quiz_count,
                         fav_count=fav_count,
                         mistake_count=mistake_count,
                         subjects=subjects,
                         q_types=q_types,
                         logged_in=bool(uid),
                         username=session.get('username'),
                         is_admin=session.get('is_admin', False),
                         user_id=uid or 0)


@main_bp.route('/search')
def search_page():
    """搜索页面 - 支持高级搜索选项"""
    keyword = request.args.get('keyword', '').strip()
    subject_filter = request.args.get('subject', '').strip()
    type_filter = request.args.get('type', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 每页显示数量

    uid = session.get('user_id') or -1
    conn = get_db()

    # 获取所有科目和题型用于筛选下拉框
    try:
        subjects = [row[0] for row in conn.execute("SELECT name FROM subjects").fetchall()]
        q_types = [row[0] for row in conn.execute("SELECT DISTINCT q_type FROM questions").fetchall()]
    except:
        subjects = []
        q_types = []

    # 如果没有关键词，显示空的搜索页面
    if not keyword:
        return render_template('search.html',
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
    """

    search_term = f'%{keyword}%'
    params = [uid, uid, search_term, search_term, search_term, search_term]

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

    import json
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

    return render_template('search.html',
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


@main_bp.route('/history')
def history_page():
    """刷题统计页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect('/login')
    # 尝试加载最近提交记录（若表不存在则返回空列表）
    records = []
    try:
        conn = get_db()
        records = conn.execute(
            'SELECT id, status, created_at, code_snippet FROM submissions WHERE user_id = ? ORDER BY created_at DESC LIMIT 100',
            (uid,)
        ).fetchall()
    except Exception:
        # 表不存在或查询失败
        records = []
    return render_template('history.html', records=records)


@main_bp.route('/profile')
def profile_page():
    """个人资料页面（只读）"""
    username = session.get('username', '用户')
    is_admin = session.get('is_admin', False)
    return render_template('user_profile.html', username=username, is_admin=is_admin)


@main_bp.route('/account')
def account_page():
    """账号管理页面（密码修改等）"""
    return render_template('profile.html')


@main_bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """安全地提供上传的文件"""
    directory = os.path.join(current_app.root_path, '..', 'uploads')
    return send_from_directory(directory, filename)

