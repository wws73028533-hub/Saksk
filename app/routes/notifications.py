# -*- coding: utf-8 -*-
"""用户侧通知 API

说明：
- 数据来源：notifications 表（由管理端维护）
- 已读/关闭维度：notification_dismissals（每个用户对每条通知）

接口：
- GET  /api/notifications               列表（默认返回未关闭的通知；可通过 ?include_dismissed=1 包含已关闭）
- GET  /api/notifications/<id>          详情（同上）
- POST /api/notifications/<id>/read     标记已读（写入 notification_dismissals）
- POST /api/notifications/<id>/dismiss  关闭通知（写入 notification_dismissals；与旧首页行为一致）
- GET  /api/notifications/unread_count  未读数（用于角标，可选）

注意：
- 由于历史上已有 /api/notifications 的旧实现（在 api.py），已迁移为 /api/notifications_legacy。
"""

from flask import Blueprint, jsonify, session, request, current_app
from ..utils.database import get_db
from ..extensions import limiter

notifications_bp = Blueprint('notifications', __name__)


def _now_expr() -> str:
    # SQLite 当前时间（UTC）
    return "CURRENT_TIMESTAMP"


def _bool_arg(val) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ('1', 'true', 'yes', 'y', 'on')


@notifications_bp.route('/api/notifications')
@limiter.exempt
def api_notifications_list():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    limit = int(request.args.get('limit') or 50)
    limit = max(1, min(limit, 200))
    include_dismissed = _bool_arg(request.args.get('include_dismissed'))

    conn = get_db()

    # 调试：帮助定位“用了哪个数据库/当前登录是谁/返回条数为何为0”
    try:
        current_app.logger.info(
            f"[notifications.list] uid={uid} db={current_app.config.get('DATABASE_PATH')}"
            f" session_user={session.get('username')} include_dismissed={include_dismissed}"
        )
    except Exception:
        pass

    # 说明：notification_dismissals 同时承担“已读/已关闭”的记录。
    # - 首页需要：默认不展示已关闭（否则刷新会再次出现）
    # - 历史页需要：展示全部（所以历史页调用 include_dismissed=1）
    where_dismiss = "" if include_dismissed else " AND d.id IS NULL "

    rows = conn.execute(
        f"""
        SELECT
          n.id, n.title, n.content, n.n_type, n.priority,
          n.start_at, n.end_at, n.created_at,
          CASE WHEN d.id IS NULL THEN 0 ELSE 1 END AS is_read
        FROM notifications n
        LEFT JOIN notification_dismissals d
          ON d.notification_id = n.id AND d.user_id = ?
        WHERE n.is_active = 1
          {where_dismiss}
          AND (n.start_at IS NULL OR datetime(n.start_at) <= datetime({_now_expr()}))
          AND (n.end_at   IS NULL OR datetime(n.end_at)   >= datetime({_now_expr()}))
        ORDER BY n.priority DESC, n.created_at DESC, n.id DESC
        LIMIT ?
        """,
        (uid, limit)
    ).fetchall()

    return jsonify({'status': 'success', 'data': [dict(r) for r in rows]})


@notifications_bp.route('/api/notifications/<int:nid>')
@limiter.exempt
def api_notifications_detail(nid: int):
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    include_dismissed = _bool_arg(request.args.get('include_dismissed'))
    conn = get_db()

    where_dismiss = "" if include_dismissed else " AND d.id IS NULL "

    row = conn.execute(
        f"""
        SELECT
          n.id, n.title, n.content, n.n_type, n.priority,
          n.start_at, n.end_at, n.created_at,
          CASE WHEN d.id IS NULL THEN 0 ELSE 1 END AS is_read
        FROM notifications n
        LEFT JOIN notification_dismissals d
          ON d.notification_id = n.id AND d.user_id = ?
        WHERE n.id = ?
          AND n.is_active = 1
          {where_dismiss}
          AND (n.start_at IS NULL OR datetime(n.start_at) <= datetime({_now_expr()}))
          AND (n.end_at   IS NULL OR datetime(n.end_at)   >= datetime({_now_expr()}))
        LIMIT 1
        """,
        (uid, int(nid))
    ).fetchone()

    if not row:
        return jsonify({'status': 'error', 'message': '通知不存在或已失效'}), 404

    return jsonify({'status': 'success', 'data': dict(row)})


@notifications_bp.route('/api/notifications/<int:nid>/read', methods=['POST'])
@limiter.exempt
def api_notifications_mark_read(nid: int):
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    conn = get_db()

    # 先确认通知存在且可见（避免写垃圾数据）
    n = conn.execute(
        f"""
        SELECT id
        FROM notifications
        WHERE id = ?
          AND is_active = 1
          AND (start_at IS NULL OR datetime(start_at) <= datetime({_now_expr()}))
          AND (end_at   IS NULL OR datetime(end_at)   >= datetime({_now_expr()}))
        """,
        (int(nid),)
    ).fetchone()

    if not n:
        return jsonify({'status': 'error', 'message': '通知不存在或已失效'}), 404

    try:
        conn.execute(
            """
            INSERT INTO notification_dismissals (user_id, notification_id)
            VALUES (?, ?)
            ON CONFLICT(user_id, notification_id)
            DO UPDATE SET dismissed_at=CURRENT_TIMESTAMP
            """,
            (uid, int(nid))
        )
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@notifications_bp.route('/api/notifications/<int:nid>/dismiss', methods=['POST'])
@limiter.exempt
def api_notifications_dismiss(nid: int):
    """关闭通知（刷新不再出现）"""
    # 关闭也要求登录
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    conn = get_db()

    # 同样先确认通知存在且可见
    n = conn.execute(
        f"""
        SELECT id
        FROM notifications
        WHERE id = ?
          AND is_active = 1
          AND (start_at IS NULL OR datetime(start_at) <= datetime({_now_expr()}))
          AND (end_at   IS NULL OR datetime(end_at)   >= datetime({_now_expr()}))
        """,
        (int(nid),)
    ).fetchone()

    if not n:
        return jsonify({'status': 'error', 'message': '通知不存在或已失效'}), 404

    try:
        conn.execute(
            """
            INSERT INTO notification_dismissals (user_id, notification_id)
            VALUES (?, ?)
            ON CONFLICT(user_id, notification_id)
            DO UPDATE SET dismissed_at=CURRENT_TIMESTAMP
            """,
            (uid, int(nid))
        )
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@notifications_bp.route('/api/notifications/unread_count')
@limiter.exempt
def api_notifications_unread_count():
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(session.get('user_id') or 0)
    conn = get_db()

    # 未读：没有 dismissal 记录（当前实现 dismissal 也代表已读）
    row = conn.execute(
        f"""
        SELECT COUNT(1) AS cnt
        FROM notifications n
        LEFT JOIN notification_dismissals d
          ON d.notification_id = n.id AND d.user_id = ?
        WHERE n.is_active = 1
          AND (n.start_at IS NULL OR datetime(n.start_at) <= datetime({_now_expr()}))
          AND (n.end_at   IS NULL OR datetime(n.end_at)   >= datetime({_now_expr()}))
          AND d.id IS NULL
        """,
        (uid,)
    ).fetchone()

    return jsonify({'status': 'success', 'count': int(row['cnt'] or 0)})
