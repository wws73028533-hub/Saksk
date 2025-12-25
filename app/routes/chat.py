# -*- coding: utf-8 -*-
"""用户聊天路由蓝图

实现：
- /chat ：聊天主页面（左侧会话列表、右侧消息区）
- /api/chat/* ：创建会话、拉取会话列表、拉取消息、发送消息、轮询未读

说明：
- 采用 SQLite 持久化（chat_conversations/chat_members/chat_messages）
- 采用轮询方式实时刷新（不引入 WebSocket，保持现有项目依赖简单）
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from ..utils.database import get_db
from ..extensions import limiter
import os
import uuid
import json
import subprocess
import shutil

chat_bp = Blueprint('chat', __name__)


CHAT_IMAGE_EXTS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
CHAT_AUDIO_EXTS = {'webm', 'wav', 'mp3', 'm4a', 'ogg'}

# iOS Safari 对 audio/webm 支持不稳定（很多机型直接无法播放），
# 因此上传时建议优先使用 m4a/mp3（前端录音也会尽量选择 ogg/webm，但播放端可能失败）。
# 后端这里允许多种格式，但不会做转码；如需“全端可播”，建议后续引入转码到 m4a/mp3。


def _allowed_image(filename: str) -> bool:
    return bool(filename) and ('.' in filename) and (filename.rsplit('.', 1)[1].lower() in CHAT_IMAGE_EXTS)


def _allowed_audio(filename: str) -> bool:
    return bool(filename) and ('.' in filename) and (filename.rsplit('.', 1)[1].lower() in CHAT_AUDIO_EXTS)


def _ffmpeg_exists() -> bool:
    """检测系统是否可用 ffmpeg"""
    try:
        return shutil.which('ffmpeg') is not None
    except Exception:
        return False


def _transcode_to_m4a(src_abs: str, dst_abs: str) -> tuple[bool, str]:
    """使用 ffmpeg 将音频转码为 m4a(aac)

    返回：(success, error_message)
    """
    if not _ffmpeg_exists():
        return False, 'ffmpeg_not_found'

    # -y 覆盖；-vn 去视频；aac 兼容性最好；-movflags +faststart 便于流式播放
    cmd = [
        'ffmpeg', '-y',
        '-i', src_abs,
        '-vn',
        '-c:a', 'aac',
        '-b:a', '64k',
        '-ar', '44100',
        '-ac', '1',
        '-movflags', '+faststart',
        dst_abs,
    ]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if p.returncode != 0:
            return False, (p.stderr.decode('utf-8', errors='ignore')[:4000] or 'ffmpeg_failed')
        return True, ''
    except Exception as e:
        return False, str(e)


def _transcode_to_mp3(src_abs: str, dst_abs: str) -> tuple[bool, str]:
    """使用 ffmpeg 将音频转码为 mp3（作为 m4a 失败时的兜底）

    返回：(success, error_message)
    """
    if not _ffmpeg_exists():
        return False, 'ffmpeg_not_found'

    cmd = [
        'ffmpeg', '-y',
        '-i', src_abs,
        '-vn',
        '-c:a', 'libmp3lame',
        '-b:a', '96k',
        '-ar', '44100',
        '-ac', '1',
        dst_abs,
    ]
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if p.returncode != 0:
            return False, (p.stderr.decode('utf-8', errors='ignore')[:4000] or 'ffmpeg_failed')
        return True, ''
    except Exception as e:
        return False, str(e)


@chat_bp.route('/chat')
def chat_page():
    if not session.get('user_id'):
        return ("请先登录", 401)
    return render_template(
        'chat.html',
        logged_in=True,
        username=session.get('username'),
        user_id=session.get('user_id'),
        is_admin=bool(session.get('is_admin')),
    )


@chat_bp.route('/api/chat/users')
@limiter.exempt
def chat_users():
    """用于创建聊天时的用户列表（简单按活跃/用户名排序）"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    q = (request.args.get('q') or '').strip()

    conn = get_db()
    params = [uid]
    sql = """
        SELECT id, username, avatar, last_active
        FROM users
        WHERE id != ?
    """
    if q:
        sql += " AND username LIKE ?"
        params.append(f"%{q}%")

    # 排序优化：精确命中优先，其次前缀命中；再按活跃度与用户名
    # 说明：即使前端不做精确匹配，这里也尽量把最可能目标排在前面
    if q:
        sql += " ORDER BY (LOWER(username) = LOWER(?)) DESC, (LOWER(username) LIKE LOWER(?) ) DESC, (last_active IS NULL) ASC, last_active DESC, username ASC LIMIT 50"
        params.append(q)
        params.append(f"{q}%")
    else:
        sql += " ORDER BY (last_active IS NULL) ASC, last_active DESC, username ASC LIMIT 50"

    rows = conn.execute(sql, params).fetchall()
    return jsonify({'status': 'success', 'data': [dict(r) for r in rows]})


@chat_bp.route('/api/chat/conversations')
@limiter.exempt
def chat_conversations():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    conn = get_db()

    # 会话列表：
    # - direct：拼出对方用户信息（昵称/头像/备注）
    # - last_message：若最后一条是图片消息，给前端一个占位文案
    rows = conn.execute(
        """
        SELECT c.id as conversation_id,
               c.c_type,
               c.title,
               c.updated_at,

               -- 对方（direct 私聊）
               pu.id as peer_user_id,
               pu.username as peer_username,
               pu.avatar as peer_avatar,
               ur.remark as peer_remark,

               -- 最后一条消息
               lm.content_type as last_message_type,
               lm.content as last_message,

               -- 未读数
               (
                 SELECT COUNT(1)
                 FROM chat_messages m
                 WHERE m.conversation_id = c.id
                   AND m.id > COALESCE(cm.last_read_message_id, 0)
                   AND m.sender_id != ?
               ) AS unread_count
        FROM chat_conversations c
        JOIN chat_members mb ON mb.conversation_id = c.id AND mb.user_id = ?
        LEFT JOIN chat_members cm ON cm.conversation_id = c.id AND cm.user_id = ?

        -- 取对方成员（direct会话：除自己外的那个人）
        LEFT JOIN chat_members pmb ON pmb.conversation_id = c.id AND pmb.user_id != ?
        LEFT JOIN users pu ON pu.id = pmb.user_id

        -- 取当前用户对对方的备注
        LEFT JOIN user_remarks ur ON ur.owner_user_id = ? AND ur.target_user_id = pu.id

        -- 取最后一条消息
        LEFT JOIN chat_messages lm ON lm.id = (
            SELECT m2.id FROM chat_messages m2
            WHERE m2.conversation_id = c.id
            ORDER BY m2.id DESC
            LIMIT 1
        )

        ORDER BY c.updated_at DESC, c.id DESC
        """,
        (uid, uid, uid, uid, uid)
    ).fetchall()

    data = []
    for r in rows:
        d = dict(r)
        if d.get('last_message_type') == 'image':
            d['last_message'] = '[图片]'
        elif d.get('last_message_type') == 'audio':
            d['last_message'] = '[语音]'
        elif d.get('last_message_type') == 'file':
            d['last_message'] = '[文件]'
        data.append(d)

    return jsonify({'status': 'success', 'data': data})


@chat_bp.route('/api/chat/conversations/create', methods=['POST'])
@limiter.exempt
def chat_create_conversation():
    """创建或复用 1v1 会话（从根源避免重复 direct 会话）"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    data = request.json or {}
    peer_id = int(data.get('peer_user_id') or 0)
    if peer_id <= 0 or peer_id == uid:
        return jsonify({'status': 'error', 'message': '对方用户不合法'}), 400

    conn = get_db()

    # 检查对方是否存在
    peer = conn.execute('SELECT id, username FROM users WHERE id=?', (peer_id,)).fetchone()
    if not peer:
        return jsonify({'status': 'error', 'message': '对方用户不存在'}), 404

    # 数据库层唯一约束：direct_pair_key = "min_uid:max_uid"
    u1, u2 = (uid, peer_id) if uid < peer_id else (peer_id, uid)
    pair_key = f"{u1}:{u2}"

    # 先按 pair_key 复用（最快且唯一）
    row = conn.execute(
        "SELECT id FROM chat_conversations WHERE c_type='direct' AND direct_pair_key=? ORDER BY updated_at DESC, id DESC LIMIT 1",
        (pair_key,)
    ).fetchone()
    if row:
        return jsonify({'status': 'success', 'conversation_id': row['id'], 'reused': True})

    # 新建：直接写入 pair_key，并依赖唯一索引从根源杜绝重复
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO chat_conversations (c_type, title, direct_pair_key) VALUES ('direct', NULL, ?)",
            (pair_key,)
        )
        cid = cur.lastrowid
        cur.execute(
            "INSERT INTO chat_members (conversation_id, user_id, role) VALUES (?, ?, 'member')",
            (cid, uid)
        )
        cur.execute(
            "INSERT INTO chat_members (conversation_id, user_id, role) VALUES (?, ?, 'member')",
            (cid, peer_id)
        )
        conn.commit()
        return jsonify({'status': 'success', 'conversation_id': cid, 'reused': False})
    except Exception:
        # 并发/竞态：可能另一请求已创建成功，回退到查询复用
        conn.rollback()
        row2 = conn.execute(
            "SELECT id FROM chat_conversations WHERE c_type='direct' AND direct_pair_key=? ORDER BY updated_at DESC, id DESC LIMIT 1",
            (pair_key,)
        ).fetchone()
        if row2:
            return jsonify({'status': 'success', 'conversation_id': row2['id'], 'reused': True})
        raise


def _is_member(conn, conversation_id, user_id):
    r = conn.execute(
        'SELECT 1 FROM chat_members WHERE conversation_id=? AND user_id=?',
        (conversation_id, user_id)
    ).fetchone()
    return bool(r)


@chat_bp.route('/api/chat/user_remark', methods=['GET', 'POST'])
@limiter.exempt
def chat_user_remark():
    """读取/设置对某个用户的备注（仅自己可见）

    GET  /api/chat/user_remark?target_user_id=xx
    POST /api/chat/user_remark  JSON: {target_user_id, remark}
      - remark 为空字符串表示清除备注
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    conn = get_db()

    if request.method == 'GET':
        try:
            target_user_id = int(request.args.get('target_user_id') or 0)
        except Exception:
            target_user_id = 0
        if target_user_id <= 0:
            return jsonify({'status': 'error', 'message': 'target_user_id 不合法'}), 400
        # 允许查询“自己”的备注（一般为空），避免前端误传自己 id 时直接报错
        if target_user_id == uid:
            return jsonify({'status': 'success', 'remark': ''})

        row = conn.execute(
            "SELECT remark FROM user_remarks WHERE owner_user_id=? AND target_user_id=?",
            (uid, target_user_id)
        ).fetchone()
        return jsonify({'status': 'success', 'remark': (row['remark'] if row else '')})

    data = request.json or {}
    try:
        target_user_id = int(data.get('target_user_id') or 0)
    except Exception:
        target_user_id = 0
    remark = (data.get('remark') or '').strip()

    if target_user_id <= 0:
        return jsonify({'status': 'error', 'message': 'target_user_id 不合法'}), 400
    # 禁止给自己设置备注（没有意义，也容易误操作）
    if target_user_id == uid:
        return jsonify({'status': 'error', 'message': '不能给自己设置备注'}), 400
    if len(remark) > 30:
        return jsonify({'status': 'error', 'message': '备注过长（最多30字）'}), 400

    # 清除备注
    if remark == '':
        conn.execute(
            "DELETE FROM user_remarks WHERE owner_user_id=? AND target_user_id=?",
            (uid, target_user_id)
        )
        conn.commit()
        return jsonify({'status': 'success', 'remark': ''})

    # UPSERT
    conn.execute(
        """
        INSERT INTO user_remarks (owner_user_id, target_user_id, remark)
        VALUES (?, ?, ?)
        ON CONFLICT(owner_user_id, target_user_id)
        DO UPDATE SET remark=excluded.remark, updated_at=CURRENT_TIMESTAMP
        """,
        (uid, target_user_id, remark)
    )
    conn.commit()
    return jsonify({'status': 'success', 'remark': remark})


@chat_bp.route('/api/chat/user_profile')
@limiter.exempt
def chat_user_profile():
    """聊天页查看对方资料（类似微信好友资料）

    GET /api/chat/user_profile?user_id=xx
    返回：
      - user: {id, username, avatar, contact, college, created_at}
      - remark: 我对TA的备注（可为空）
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    try:
        target_user_id = int(request.args.get('user_id') or 0)
    except Exception:
        target_user_id = 0

    if target_user_id <= 0:
        return jsonify({'status': 'error', 'message': 'user_id 不合法'}), 400

    conn = get_db()
    u = conn.execute(
        'SELECT id, username, avatar, contact, college, created_at FROM users WHERE id=?',
        (target_user_id,)
    ).fetchone()
    if not u:
        return jsonify({'status': 'error', 'message': '用户不存在'}), 404

    # 备注（仅对方时才返回；自己则为空）
    remark = ''
    if target_user_id != uid:
        r = conn.execute(
            'SELECT remark FROM user_remarks WHERE owner_user_id=? AND target_user_id=?',
            (uid, target_user_id)
        ).fetchone()
        remark = (r['remark'] if r else '')

    return jsonify({'status': 'success', 'user': dict(u), 'remark': remark})


@chat_bp.route('/api/chat/messages')
@limiter.exempt
def chat_messages():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    conversation_id = int(request.args.get('conversation_id') or 0)
    after_id = int(request.args.get('after_id') or 0)
    limit = int(request.args.get('limit') or 50)
    limit = max(1, min(limit, 200))

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400

    conn = get_db()
    if not _is_member(conn, conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权访问该会话'}), 403

    rows = conn.execute(
        """
        SELECT m.id, m.conversation_id, m.sender_id, u.username as sender_username,
               u.avatar as sender_avatar, m.content, m.content_type, m.created_at
        FROM chat_messages m
        LEFT JOIN users u ON u.id = m.sender_id
        WHERE m.conversation_id = ?
          AND m.id > ?
        ORDER BY m.id ASC
        LIMIT ?
        """,
        (conversation_id, after_id, limit)
    ).fetchall()

    # 更新已读到最新一条消息
    if rows:
        last_id = rows[-1]['id']
        conn.execute(
            "UPDATE chat_members SET last_read_message_id = MAX(COALESCE(last_read_message_id,0), ?) WHERE conversation_id=? AND user_id=?",
            (last_id, conversation_id, uid)
        )
        conn.commit()

    return jsonify({'status': 'success', 'data': [dict(r) for r in rows]})


@chat_bp.route('/api/chat/messages/send', methods=['POST'])
@limiter.exempt
def chat_send_message():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    data = request.json or {}
    conversation_id = int(data.get('conversation_id') or 0)
    content = (data.get('content') or '').strip()

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400
    if not content:
        return jsonify({'status': 'error', 'message': '消息不能为空'}), 400
    if len(content) > 2000:
        return jsonify({'status': 'error', 'message': '消息过长（最多2000字）'}), 400

    conn = get_db()
    if not _is_member(conn, conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权发送到该会话'}), 403

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO chat_messages (conversation_id, sender_id, content, content_type)
        VALUES (?, ?, ?, 'text')
        """,
        (conversation_id, uid, content)
    )
    mid = cur.lastrowid

    conn.execute(
        "UPDATE chat_conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (conversation_id,)
    )

    # 发送者已读推进
    conn.execute(
        "UPDATE chat_members SET last_read_message_id = MAX(COALESCE(last_read_message_id,0), ?) WHERE conversation_id=? AND user_id=?",
        (mid, conversation_id, uid)
    )

    conn.commit()
    return jsonify({'status': 'success', 'message_id': mid})


@chat_bp.route('/api/chat/messages/upload_image', methods=['POST'])
@limiter.exempt
def chat_upload_image():
    """上传聊天图片并作为一条图片消息写入会话

    multipart/form-data:
      - conversation_id
      - image (file)  主图（建议前端已压缩）
      - thumb (file) 可选缩略图（用于列表展示，减少拉取流量）
      - width/height 可选（主图宽高）

    返回：
      - url: 主图URL
      - thumb: 缩略图URL（如有）
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    try:
        conversation_id = int(request.form.get('conversation_id') or 0)
    except Exception:
        conversation_id = 0

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400

    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': '缺少图片文件'}), 400

    f = request.files['image']
    if not f or not f.filename:
        return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    if not _allowed_image(f.filename):
        return jsonify({'status': 'error', 'message': '不支持的图片类型'}), 400

    thumb_f = request.files.get('thumb')
    if thumb_f and thumb_f.filename and (not _allowed_image(thumb_f.filename)):
        return jsonify({'status': 'error', 'message': '不支持的缩略图类型'}), 400

    try:
        width = int(request.form.get('width') or 0)
    except Exception:
        width = 0
    try:
        height = int(request.form.get('height') or 0)
    except Exception:
        height = 0

    conn = get_db()
    if not _is_member(conn, conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权发送到该会话'}), 403

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    chat_dir = os.path.join(upload_root, 'chat')
    os.makedirs(chat_dir, exist_ok=True)

    # 保存主图
    ext = f.filename.rsplit('.', 1)[1].lower()
    fname = secure_filename(f"chat_{conversation_id}_{uid}_{uuid.uuid4().hex[:10]}.{ext}")
    abs_path = os.path.join(chat_dir, fname)
    f.save(abs_path)
    url = f"/uploads/chat/{fname}"

    # 保存缩略图（可选）
    thumb_url = None
    if thumb_f and thumb_f.filename:
        thumb_ext = thumb_f.filename.rsplit('.', 1)[1].lower()
        thumb_name = secure_filename(f"chat_{conversation_id}_{uid}_{uuid.uuid4().hex[:10]}_thumb.{thumb_ext}")
        thumb_abs = os.path.join(chat_dir, thumb_name)
        thumb_f.save(thumb_abs)
        thumb_url = f"/uploads/chat/{thumb_name}"

    # content：兼容展示与扩展，image 类型存 JSON
    content_obj = {
        'url': url,
        'thumb': thumb_url,
        'w': width if width > 0 else None,
        'h': height if height > 0 else None,
    }
    content_str = json.dumps(content_obj, ensure_ascii=False)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO chat_messages (conversation_id, sender_id, content, content_type)
        VALUES (?, ?, ?, 'image')
        """,
        (conversation_id, uid, content_str)
    )
    mid = cur.lastrowid

    conn.execute(
        "UPDATE chat_conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (conversation_id,)
    )
    conn.execute(
        "UPDATE chat_members SET last_read_message_id = MAX(COALESCE(last_read_message_id,0), ?) WHERE conversation_id=? AND user_id=?",
        (mid, conversation_id, uid)
    )

    conn.commit()
    return jsonify({'status': 'success', 'message_id': mid, 'url': url, 'thumb': thumb_url})


@chat_bp.route('/api/chat/messages/upload_audio', methods=['POST'])
@limiter.exempt
def chat_upload_audio():
    """上传聊天语音并作为一条语音消息写入会话

    multipart/form-data:
      - conversation_id
      - audio (file)  建议 webm/ogg/wav/mp3/m4a
      - duration 可选（秒）

    返回：
      - url: 语音URL
      - duration: 秒
    """
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = session.get('user_id')
    try:
        conversation_id = int(request.form.get('conversation_id') or 0)
    except Exception:
        conversation_id = 0

    if conversation_id <= 0:
        return jsonify({'status': 'error', 'message': 'conversation_id 不合法'}), 400

    if 'audio' not in request.files:
        return jsonify({'status': 'error', 'message': '缺少语音文件'}), 400

    f = request.files['audio']
    if not f or not f.filename:
        return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    if not _allowed_audio(f.filename):
        return jsonify({'status': 'error', 'message': '不支持的语音类型'}), 400

    try:
        duration = float(request.form.get('duration') or 0)
    except Exception:
        duration = 0

    conn = get_db()
    if not _is_member(conn, conversation_id, uid):
        return jsonify({'status': 'forbidden', 'message': '无权发送到该会话'}), 403

    upload_root = current_app.config.get('UPLOAD_FOLDER')
    chat_dir = os.path.join(upload_root, 'chat')
    os.makedirs(chat_dir, exist_ok=True)

    ext = f.filename.rsplit('.', 1)[1].lower()
    base = secure_filename(f"chat_{conversation_id}_{uid}_{uuid.uuid4().hex[:10]}")

    # 1) 先保存原始文件
    raw_name = f"{base}.{ext}"
    raw_abs = os.path.join(chat_dir, raw_name)
    f.save(raw_abs)
    raw_url = f"/uploads/chat/{raw_name}"

    # 2) 尝试转码为 m4a（AAC），以获得 iOS/安卓最佳兼容；失败则回退转 mp3
    m4a_name = f"{base}.m4a"
    m4a_abs = os.path.join(chat_dir, m4a_name)
    m4a_url = f"/uploads/chat/{m4a_name}"

    mp3_name = f"{base}.mp3"
    mp3_abs = os.path.join(chat_dir, mp3_name)
    mp3_url = f"/uploads/chat/{mp3_name}"

    m4a_ok = False
    mp3_ok = False
    transcode_err = ''

    # 先转 m4a
    try:
        ok, err = _transcode_to_m4a(raw_abs, m4a_abs)
        m4a_ok = bool(ok)
        transcode_err = err or ''
    except Exception as e:
        m4a_ok = False
        transcode_err = str(e)

    if not m4a_ok:
        # 清理可能的残留
        try:
            if os.path.exists(m4a_abs):
                os.remove(m4a_abs)
        except Exception:
            pass

        # 回退转 mp3
        try:
            ok2, err2 = _transcode_to_mp3(raw_abs, mp3_abs)
            mp3_ok = bool(ok2)
            transcode_err = err2 or transcode_err
        except Exception as e:
            mp3_ok = False
            transcode_err = str(e)

        if not mp3_ok:
            try:
                if os.path.exists(mp3_abs):
                    os.remove(mp3_abs)
            except Exception:
                pass

        current_app.logger.warning(
            f"audio transcode failed(m4a) fallback(mp3)={'ok' if mp3_ok else 'failed'}: conv={conversation_id} uid={uid} raw={raw_name} err={transcode_err}"
        )

    # content：存 raw + m4a/mp3（如有），前端播放优先：m4a > mp3 > raw
    best_url = m4a_url if m4a_ok else (mp3_url if mp3_ok else raw_url)
    content_obj = {
        'url': best_url,
        'url_raw': raw_url,
        'url_m4a': (m4a_url if m4a_ok else None),
        'url_mp3': (mp3_url if mp3_ok else None),
        'duration': duration if duration > 0 else None,
    }
    content_str = json.dumps(content_obj, ensure_ascii=False)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO chat_messages (conversation_id, sender_id, content, content_type)
        VALUES (?, ?, ?, 'audio')
        """,
        (conversation_id, uid, content_str)
    )
    mid = cur.lastrowid

    conn.execute(
        "UPDATE chat_conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (conversation_id,)
    )
    conn.execute(
        "UPDATE chat_members SET last_read_message_id = MAX(COALESCE(last_read_message_id,0), ?) WHERE conversation_id=? AND user_id=?",
        (mid, conversation_id, uid)
    )

    conn.commit()
    return jsonify({
        'status': 'success',
        'message_id': mid,
        'url': content_obj.get('url'),
        'url_raw': content_obj.get('url_raw'),
        'url_m4a': content_obj.get('url_m4a'),
        'url_mp3': content_obj.get('url_mp3'),
        'duration': duration,
        'transcoded': bool(content_obj.get('url_m4a') or content_obj.get('url_mp3')),
    })


@chat_bp.route('/api/chat/unread_count')
@limiter.exempt
def chat_unread_count():
    """首页角标等（可选）"""
    if not session.get('user_id'):
        return jsonify({'status': 'success', 'count': 0})

    uid = session.get('user_id')
    conn = get_db()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(
            (
              SELECT COUNT(1)
              FROM chat_messages m
              WHERE m.conversation_id = c.id
                AND m.id > COALESCE(cm.last_read_message_id, 0)
                AND m.sender_id != ?
            )
        ),0) AS cnt
        FROM chat_conversations c
        JOIN chat_members cm ON cm.conversation_id=c.id AND cm.user_id=?
        """,
        (uid, uid)
    ).fetchone()

    return jsonify({'status': 'success', 'count': int(row['cnt'] or 0)})
