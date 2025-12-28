# -*- coding: utf-8 -*-
"""主页面路由"""
from flask import Blueprint, render_template, request, session, redirect, send_from_directory, current_app
import json
import os
from app.core.utils.database import get_db

main_pages_bp = Blueprint('main_pages', __name__)


@main_pages_bp.route('/')
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
        
        # 获取所有科目（过滤掉锁定的科目）
        subjects = [row[0] for row in conn.execute("SELECT name FROM subjects WHERE is_locked=0 OR is_locked IS NULL ORDER BY id").fetchall()]
        
        # 获取所有题型（作为备用）
        q_types = [row[0] for row in conn.execute("SELECT DISTINCT q_type FROM questions").fetchall()]

        # 获取每个科目下的题型
        subject_q_types = {}
        rows = conn.execute("""
            SELECT s.name, GROUP_CONCAT(DISTINCT q.q_type)
            FROM subjects s
            LEFT JOIN questions q ON s.id = q.subject_id
            GROUP BY s.name
            ORDER BY s.id
        """).fetchall()
        for row in rows:
            if row[0] and row[1]:
                subject_q_types[row[0]] = sorted(list(set(row[1].split(','))))
            elif row[0]:
                subject_q_types[row[0]] = []
    except Exception as e:
        current_app.logger.error(f"Error fetching index page data: {e}")
        quiz_count = 0
        fav_count = 0
        mistake_count = 0
        subjects = []
        q_types = []
        subject_q_types = {}
    
    return render_template('main/index.html',
                         quiz_count=quiz_count,
                         fav_count=fav_count,
                         mistake_count=mistake_count,
                         subjects=subjects,
                         q_types=q_types,
                         subject_q_types_json=json.dumps(subject_q_types, ensure_ascii=False),
                         logged_in=bool(uid),
                         username=session.get('username'),
                         is_admin=session.get('is_admin', False),
                         is_subject_admin=session.get('is_subject_admin', False),
                         user_id=uid or 0)


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

    # 获取所有科目和题型用于筛选下拉框（过滤掉锁定的科目）
    try:
        subjects = [row[0] for row in conn.execute("SELECT name FROM subjects WHERE is_locked=0 OR is_locked IS NULL").fetchall()]
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
    return render_template('main/history.html', records=records)


@main_pages_bp.route('/profile')
def profile_page():
    """个人资料页面（只读）"""
    username = session.get('username', '用户')
    is_admin = session.get('is_admin', False)
    return render_template('main/user_profile.html', username=username, is_admin=is_admin)


@main_pages_bp.route('/account')
def account_page():
    """账号管理页面（密码修改等）"""
    return render_template('main/profile.html')


@main_pages_bp.route('/quiz_settings')
def quiz_settings_page():
    """题库设置页面"""
    if not session.get('user_id'):
        return redirect('/login')
    return render_template(
        'main/quiz_settings.html',
        logged_in=True,
        username=session.get('username'),
        user_id=session.get('user_id')
    )


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
    return render_template(
        'main/about.html',
        logged_in=bool(session.get('user_id')),
        username=session.get('username'),
        is_admin=session.get('is_admin', False),
    )

