# -*- coding: utf-8 -*-
"""用户API路由"""
from flask import Blueprint, request, jsonify, session, current_app, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from app.core.utils.database import get_db
from datetime import datetime, timedelta
import os
import uuid

user_api_bp = Blueprint('user_api', __name__)


# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_streak_days(conn, user_id):
    """计算连续学习天数"""
    try:
        # 获取最近的答题日期
        rows = conn.execute(
            '''SELECT DISTINCT DATE(created_at) as date
               FROM user_answers
               WHERE user_id = ?
               ORDER BY date DESC
               LIMIT 100''',
            (user_id,)
        ).fetchall()
        
        if not rows:
            return 0
        
        dates = [datetime.strptime(r['date'], '%Y-%m-%d').date() for r in rows]
        today = datetime.now().date()
        
        # 如果最近一次答题不是今天或昨天，连续天数为0
        if dates[0] < today - timedelta(days=1):
            return 0
        
        streak = 1
        for i in range(1, len(dates)):
            if dates[i-1] - dates[i] == timedelta(days=1):
                streak += 1
            else:
                break
        
        return streak
    except:
        return 0


@user_api_bp.route('/user/stats')
def user_stats():
    """获取用户统计数据"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    conn = get_db()
    
    try:
        # 获取用户基本信息
        user = conn.execute(
            'SELECT id, username, email, created_at FROM users WHERE id = ?',
            (uid,)
        ).fetchone()
        
        # 统计数据
        total_questions = conn.execute('SELECT COUNT(*) FROM questions').fetchone()[0]
        
        favorites_count = conn.execute(
            'SELECT COUNT(*) FROM favorites WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        mistakes_count = conn.execute(
            'SELECT COUNT(*) FROM mistakes WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        # 答题统计
        answered_count = conn.execute(
            'SELECT COUNT(DISTINCT question_id) FROM user_answers WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        correct_count = conn.execute(
            'SELECT COUNT(DISTINCT question_id) FROM user_answers WHERE user_id = ? AND is_correct = 1',
            (uid,)
        ).fetchone()[0]
        
        # 考试统计
        exam_count = conn.execute(
            'SELECT COUNT(*) FROM exams WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        finished_exam_count = conn.execute(
            'SELECT COUNT(*) FROM exams WHERE user_id = ? AND status = "finished"',
            (uid,)
        ).fetchone()[0]
        
        return jsonify({
            'status': 'success',
            'data': {
                'user': dict(user) if user else None,
                'total_questions': total_questions,
                'favorites_count': favorites_count,
                'mistakes_count': mistakes_count,
                'answered_count': answered_count,
                'correct_count': correct_count,
                'accuracy': round(correct_count / answered_count * 100, 1) if answered_count > 0 else 0,
                'exam_count': exam_count,
                'finished_exam_count': finished_exam_count
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/user/update', methods=['POST'])
def update_user():
    """更新用户信息"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    data = request.json
    
    # 这里可以添加更新用户信息的逻辑
    # 例如：更新邮箱、密码等
    
    return jsonify({'status': 'success', 'message': '更新成功'})


@user_api_bp.route('/profile/update', methods=['POST'])
def update_profile():
    """更新用户个人资料"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    data = request.json or {}
    
    avatar = data.get('avatar')
    contact = data.get('contact')
    college = data.get('college')
    
    conn = get_db()
    
    try:
        # 构建更新SQL
        updates = []
        params = []
        
        if avatar is not None:
            updates.append('avatar = ?')
            params.append(avatar)
        if contact is not None:
            updates.append('contact = ?')
            params.append(contact)
        if college is not None:
            updates.append('college = ?')
            params.append(college)
        
        if not updates:
            return jsonify({'status': 'error', 'message': '没有需要更新的内容'}), 400
        
        params.append(uid)
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)
        conn.commit()
        
        return jsonify({'status': 'success', 'message': '更新成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'更新失败: {str(e)}'}), 500


@user_api_bp.route('/profile')
def api_profile():
    """获取用户个人资料"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    conn = get_db()
    
    try:
        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        has_openid = 'openid' in user_cols
        # 获取用户基本信息
        if has_openid:
            user_row = conn.execute(
                'SELECT id, username, created_at, is_admin, avatar, contact, college, email, email_verified, openid FROM users WHERE id = ?',
                (uid,)
            ).fetchone()
        else:
            user_row = conn.execute(
                'SELECT id, username, created_at, is_admin, avatar, contact, college, email, email_verified FROM users WHERE id = ?',
                (uid,)
            ).fetchone()
        
        if not user_row:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 将Row对象转换为字典
        user = dict(user_row)
        
        # 检查用户是否设置了密码
        from app.core.models.user import User
        has_password_set = User.has_password_set(uid)
        
        # 统计数据
        favorites_count = conn.execute(
            'SELECT COUNT(*) FROM favorites WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        mistakes_count = conn.execute(
            'SELECT COUNT(*) FROM mistakes WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        # 答题统计
        total_answered = conn.execute(
            'SELECT COUNT(*) FROM user_answers WHERE user_id = ?',
            (uid,)
        ).fetchone()[0]
        
        correct_answered = conn.execute(
            'SELECT COUNT(*) FROM user_answers WHERE user_id = ? AND is_correct = 1',
            (uid,)
        ).fetchone()[0]
        
        accuracy = round(correct_answered / total_answered * 100, 1) if total_answered > 0 else 0
        
        # 计算连续学习天数
        streak_days = calculate_streak_days(conn, uid)
        
        return jsonify({
            'status': 'success',
            'data': {
                'username': user['username'],
                'avatar': user['avatar'],
                'contact': user['contact'],
                'college': user['college'],
                'email': user.get('email'),
                'email_verified': bool(user.get('email_verified', 0)),
                'wechat_bound': bool(user.get('openid')) if has_openid else False,
                'created_at': user['created_at'][:10] if user['created_at'] else '-',
                'is_admin': bool(user['is_admin']),
                'has_password_set': has_password_set,
                'streak_days': streak_days,
                'total_answered': total_answered,
                'correct_answered': correct_answered,
                'accuracy': accuracy,
                'favorites_count': favorites_count,
                'mistakes_count': mistakes_count
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'加载失败: {str(e)}'}), 500


@user_api_bp.route('/profile/password', methods=['POST'])
def change_password():
    """修改密码或设置密码"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    data = request.json or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    is_set_password = data.get('is_set_password', False)  # 是否为设置密码
    
    if not new_password:
        return jsonify({'status': 'error', 'message': '请填写新密码'}), 400
    
    if len(new_password) < 8:
        return jsonify({'status': 'error', 'message': '新密码至少8位'}), 400
    
    conn = get_db()
    
    try:
        # 检查用户是否存在
        user = conn.execute(
            'SELECT password_hash FROM users WHERE id = ?',
            (uid,)
        ).fetchone()
        
        if not user:
            return jsonify({'status': 'error', 'message': '用户不存在'}), 404
        
        # 检查用户是否设置了密码
        from app.core.models.user import User
        has_password = User.has_password_set(uid)
        
        # 如果是设置密码（用户还没有设置密码），不需要验证当前密码
        if is_set_password or not has_password:
            # 设置密码
            User.update_password(uid, new_password, set_password=True)
            return jsonify({'status': 'success', 'message': '密码设置成功'})
        else:
            # 修改密码，需要验证当前密码
            if not current_password:
                return jsonify({'status': 'error', 'message': '请填写当前密码'}), 400
            
            # 验证当前密码
            if not check_password_hash(user['password_hash'], current_password):
                return jsonify({'status': 'error', 'message': '当前密码错误'}), 400
            
            # 更新密码
            User.update_password(uid, new_password, set_password=False)
            return jsonify({'status': 'success', 'message': '密码修改成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'操作失败: {str(e)}'}), 500


@user_api_bp.route('/stats/daily')
def stats_daily():
    """获取每日答题统计"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    days = request.args.get('days', 30, type=int)
    conn = get_db()
    
    try:
        # 获取最近N天的答题记录
        rows = conn.execute(
            '''SELECT DATE(created_at) as date, 
                      COUNT(*) as total,
                      SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_answers 
               WHERE user_id = ? AND created_at >= DATE('now', ?)
               GROUP BY DATE(created_at)
               ORDER BY date''',
            (uid, f'-{days} days')
        ).fetchall()
        
        data = [{'date': r['date'], 'total': r['total'], 'correct': r['correct']} for r in rows]
        
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/stats/by_subject')
def stats_by_subject():
    """按科目统计答题情况"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    conn = get_db()
    
    try:
        rows = conn.execute(
            '''SELECT s.name as subject,
                      COUNT(*) as total,
                      SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_answers ua
               JOIN questions q ON ua.question_id = q.id
               LEFT JOIN subjects s ON q.subject_id = s.id
               WHERE ua.user_id = ?
               GROUP BY s.name
               ORDER BY total DESC''',
            (uid,)
        ).fetchall()
        
        data = [{'subject': r['subject'] or '未分类', 'total': r['total'], 'correct': r['correct']} for r in rows]
        
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/stats/by_type')
def stats_by_type():
    """按题型统计答题情况"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    conn = get_db()
    
    try:
        rows = conn.execute(
            '''SELECT q.q_type,
                      COUNT(*) as total,
                      SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) as correct
               FROM user_answers ua
               JOIN questions q ON ua.question_id = q.id
               WHERE ua.user_id = ?
               GROUP BY q.q_type
               ORDER BY total DESC''',
            (uid,)
        ).fetchall()
        
        data = [{'q_type': r['q_type'] or '未知', 'total': r['total'], 'correct': r['correct']} for r in rows]
        
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_api_bp.route('/profile/avatar', methods=['POST'])
def upload_avatar():
    """上传用户头像"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    uid = session.get('user_id')
    
    # 检查是否有文件
    if 'avatar' not in request.files:
        return jsonify({'status': 'error', 'message': '没有上传文件'}), 400
    
    file = request.files['avatar']
    
    # 检查文件名
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '没有选择文件'}), 400
    
    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': '不支持的文件类型，请上传图片文件（png, jpg, jpeg, gif, webp）'}), 400
    
    try:
        # 生成唯一文件名
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"avatar_{uid}_{uuid.uuid4().hex[:8]}.{ext}"
        
        # 确保上传目录存在
        upload_folder = current_app.config['UPLOAD_FOLDER']
        avatars_folder = os.path.join(upload_folder, 'avatars')
        os.makedirs(avatars_folder, exist_ok=True)
        
        # 保存文件
        filepath = os.path.join(avatars_folder, filename)
        file.save(filepath)
        
        # 更新数据库
        avatar_url = f'/uploads/avatars/{filename}'
        conn = get_db()
        
        # 删除旧头像文件（如果存在）
        old_avatar = conn.execute(
            'SELECT avatar FROM users WHERE id = ?',
            (uid,)
        ).fetchone()
        
        if old_avatar and old_avatar['avatar']:
            old_path = old_avatar['avatar'].replace('/uploads/', '')
            old_file = os.path.join(upload_folder, old_path)
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                except:
                    pass
        
        # 保存新头像路径
        conn.execute(
            'UPDATE users SET avatar = ? WHERE id = ?',
            (avatar_url, uid)
        )
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': '头像上传成功',
            'avatar_url': avatar_url
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'上传失败: {str(e)}'}), 500


@user_api_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """访问上传的文件"""
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, filename)

