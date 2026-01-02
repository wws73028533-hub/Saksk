# -*- coding: utf-8 -*-
"""管理后台页面路由"""
from flask import Blueprint, render_template, session, request
from app.core.utils.database import get_db

admin_pages_bp = Blueprint('admin_pages', __name__)


@admin_pages_bp.route('/')
@admin_pages_bp.route('/dashboard')
def admin_dashboard():
    """管理后台首页"""
    conn = get_db()
    
    q_count = conn.execute('SELECT COUNT(1) FROM questions').fetchone()[0]
    s_count = conn.execute('SELECT COUNT(1) FROM subjects').fetchone()[0]
    u_count = conn.execute('SELECT COUNT(1) FROM users').fetchone()[0]
    admin_count = conn.execute('SELECT COUNT(1) FROM users WHERE is_admin = 1').fetchone()[0]
    
    recent_q = conn.execute(
        'SELECT id, content, q_type FROM questions ORDER BY id DESC LIMIT 5'
    ).fetchall()
    
    subject_dist = conn.execute('''
        SELECT s.name, COUNT(q.id) as count
        FROM subjects s
        LEFT JOIN questions q ON s.id = q.subject_id
        GROUP BY s.id
        ORDER BY count DESC
    ''').fetchall()
    
    return render_template('admin/admin_dashboard.html',
        stats={'q_count': q_count, 's_count': s_count, 'u_count': u_count, 'admin_count': admin_count},
        recent_questions=[dict(row) for row in recent_q],
        subject_distribution=[dict(row) for row in subject_dist]
    )


@admin_pages_bp.route('/users')
def admin_users_page():
    """用户管理页面"""
    conn = get_db()
    users = conn.execute('SELECT id, username, created_at, is_admin FROM users ORDER BY id').fetchall()
    return render_template('admin/admin_users.html', users=[dict(row) for row in users])


@admin_pages_bp.route('/subjects')
def admin_subjects_page():
    """科目管理页面"""
    return render_template('admin/admin_subjects.html')


@admin_pages_bp.route('/subjects/<int:subject_id>/questions')
def admin_questions_page(subject_id):
    """题集管理页面"""
    conn = get_db()
    
    # 获取科目信息（使用subjects表，题库中心模式）
    subject = conn.execute('SELECT id, name FROM subjects WHERE id=?', (subject_id,)).fetchone()
    
    if not subject:
        return "科目不存在", 404
    
    return render_template('admin/admin_questions.html', subject_id=subject_id, subject=dict(subject))


@admin_pages_bp.route('/subjects/<int:subject_id>/questions/duplicate-check')
def admin_duplicate_check_page(subject_id):
    """题集查重结果页面"""
    conn = get_db()
    
    # 获取科目信息
    subject = conn.execute('SELECT id, name FROM subjects WHERE id=?', (subject_id,)).fetchone()
    
    if not subject:
        return "科目不存在", 404
    
    return render_template('admin/admin_duplicate_check.html', subject_id=subject_id, subject=dict(subject))


@admin_pages_bp.route('/users/<int:user_id>')
def admin_user_detail_page(user_id):
    """用户详情页面"""
    conn = get_db()
    
    u = conn.execute(
        'SELECT id, username, is_admin, is_locked, created_at, avatar, contact, college, email, email_verified, email_verified_at FROM users WHERE id=?',
        (user_id,)
    ).fetchone()
    
    if not u:
        return "用户不存在", 404
    
    # 收藏/错题
    fav = conn.execute('SELECT COUNT(1) FROM favorites WHERE user_id=?', (user_id,)).fetchone()[0]
    mis = conn.execute('SELECT COUNT(1) FROM mistakes WHERE user_id=?', (user_id,)).fetchone()[0]
    
    # 答题统计
    r = conn.execute(
        'SELECT COUNT(1) AS total, SUM(is_correct) AS correct FROM user_answers WHERE user_id=?',
        (user_id,)
    ).fetchone()
    total = r['total'] or 0
    correct = r['correct'] or 0
    acc = round(correct * 100.0 / total, 1) if total else 0.0
    
    # 考试统计
    ex_ongoing = conn.execute('SELECT COUNT(1) FROM exams WHERE user_id=? AND status="ongoing"', (user_id,)).fetchone()[0]
    ex_submitted = conn.execute('SELECT COUNT(1) FROM exams WHERE user_id=? AND status="submitted"', (user_id,)).fetchone()[0]
    
    recent = conn.execute(
        'SELECT id, subject, total_score, started_at, submitted_at FROM exams WHERE user_id=? AND status="submitted" ORDER BY submitted_at DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    
    return render_template('admin/admin_user_detail.html',
        user=dict(u),
        stats={
            'favorites': fav,
            'mistakes': mis,
            'total_answers': total,
            'accuracy': acc,
            'exams_ongoing': ex_ongoing,
            'exams_submitted': ex_submitted
        },
        recent_exams=[dict(x) for x in recent]
    )


@admin_pages_bp.route('/popups')
def admin_popups_page():
    """弹窗管理页面"""
    return render_template('admin/admin_popups.html')


@admin_pages_bp.route('/notifications')
def admin_notifications_page():
    """通知管理页面"""
    return render_template('admin/admin_notifications.html')


@admin_pages_bp.route('/chat')
def admin_chat_page():
    """聊天管理页面"""
    return render_template('admin/admin_chat.html')


@admin_pages_bp.route('/subject_permissions')
def admin_subject_permissions_page():
    """题库管理页面（批量操作）"""
    return render_template('admin/admin_subject_permissions.html')


@admin_pages_bp.route('/settings')
def admin_settings_page():
    """系统设置页面"""
    return render_template('admin/admin_settings.html')


@admin_pages_bp.route('/settings/mail')
def admin_mail_settings_page():
    """邮件配置页面"""
    conn = get_db()
    # 获取当前邮件配置
    config_rows = conn.execute(
        'SELECT config_key, config_value, description FROM system_config WHERE config_key LIKE "mail_%" ORDER BY config_key'
    ).fetchall()
    
    mail_config = {}
    for row in config_rows:
        key = row['config_key']
        value = row['config_value']
        # 对于密码字段，不返回实际值
        if 'password' in key.lower():
            mail_config[key] = '***' if value else ''
        else:
            mail_config[key] = value
    
    return render_template('admin/admin_mail_settings.html', mail_config=mail_config)


@admin_pages_bp.route('/settings/limits')
def admin_limit_settings_page():
    """限制设置页面"""
    return render_template('admin/admin_limit_settings.html')


@admin_pages_bp.route('/permissions')
def admin_permissions_page():
    """权限管理页面"""
    return render_template('admin/admin_permissions.html')

