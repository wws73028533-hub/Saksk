# -*- coding: utf-8 -*-
"""考试页面路由"""
import json
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.core.utils.database import get_db
from app.core.utils.validators import parse_int

exam_pages_bp = Blueprint('exam_pages', __name__)


def _parse_exam_config(config_json: str) -> dict:
    try:
        cfg = json.loads(config_json or '{}')
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _exam_source_from_cfg(cfg: dict) -> str:
    src = (cfg or {}).get('source') or 'public'
    src = str(src).strip().lower()
    return src if src in ('public', 'user_bank') else 'public'


@exam_pages_bp.route('/exams')
def page_exams():
    """考试列表页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))

    tab = (request.args.get('tab') or 'new').strip().lower()
    if tab not in ('new', 'records', 'data', 'settings'):
        tab = 'new'

    filter_source = (request.args.get('source') or 'all').strip().lower()
    if filter_source not in ('all', 'public', 'user_bank'):
        filter_source = 'all'

    subject = request.args.get('subject', 'all')
    page = parse_int(request.args.get('page'), 1, 1)
    size = parse_int(request.args.get('size'), 10, 5, 50)

    bank_id = parse_int(request.args.get('bank_id'), 0, 0)
    if bank_id <= 0:
        bank_id = None
    
    conn = get_db()
    
    # 科目列表（按权限 + 锁定状态过滤）
    from app.core.utils.subject_permissions import get_user_accessible_subjects

    subjects_meta = []
    subjects = []
    subject_q_types = {}

    try:
        accessible_subject_ids = [int(x) for x in (get_user_accessible_subjects(int(uid)) or [])]
    except Exception:
        accessible_subject_ids = []

    if accessible_subject_ids:
        placeholders = ','.join(['?'] * len(accessible_subject_ids))
        rows = conn.execute(
            f"""
            SELECT id, name
            FROM subjects
            WHERE id IN ({placeholders})
              AND (is_locked=0 OR is_locked IS NULL)
            ORDER BY id
            """,
            accessible_subject_ids,
        ).fetchall()
        subjects_meta = [dict(r) for r in rows]
        subjects = [r['name'] for r in subjects_meta]

        subject_ids = [int(r['id']) for r in subjects_meta if r.get('id') is not None]
        if subject_ids:
            placeholders = ','.join(['?'] * len(subject_ids))
            rows = conn.execute(
                f"""
                SELECT s.name as name, GROUP_CONCAT(DISTINCT q.q_type) as q_types
                FROM subjects s
                LEFT JOIN questions q ON s.id = q.subject_id
                WHERE s.id IN ({placeholders})
                GROUP BY s.name
                ORDER BY s.id
                """,
                subject_ids,
            ).fetchall()
            for row in rows:
                name = row['name']
                types_str = row['q_types']
                if not name:
                    continue
                if not types_str:
                    subject_q_types[name] = []
                    continue
                subject_q_types[name] = sorted(list(set([t for t in types_str.split(',') if t and t.strip()])))

    # 所有题型（备用：全部题库）
    q_types = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT q_type FROM questions WHERE q_type IS NOT NULL AND TRIM(q_type) != '' ORDER BY q_type"
        ).fetchall()
    ]

    if subject != 'all' and subject not in subjects:
        subject = 'all'

    # 个人题库列表（用于新建/偏好/筛选）
    banks_meta = [
        dict(r)
        for r in conn.execute(
            """
            SELECT id, name, COALESCE(question_count, 0) as question_count
            FROM user_question_banks
            WHERE user_id = ? AND status = 1
            ORDER BY updated_at DESC, id DESC
            """,
            (uid,),
        ).fetchall()
    ]

    bank_q_types: dict[str, list[str]] = {}
    bank_ids = [int(b.get('id')) for b in banks_meta if b.get('id') is not None]
    if bank_ids:
        placeholders = ','.join(['?'] * len(bank_ids))
        rows = conn.execute(
            f"""
            SELECT bank_id, GROUP_CONCAT(DISTINCT q_type) as q_types
            FROM user_bank_questions
            WHERE bank_id IN ({placeholders})
              AND q_type IS NOT NULL AND TRIM(q_type) != ''
            GROUP BY bank_id
            """,
            bank_ids,
        ).fetchall()
        for r in rows:
            bid = r['bank_id']
            types_str = r['q_types']
            if bid is None:
                continue
            if not types_str:
                bank_q_types[str(int(bid))] = []
                continue
            bank_q_types[str(int(bid))] = sorted(list(set([t for t in types_str.split(',') if t and t.strip()])))

    # 进行中的考试：新建页展示全部；记录页按筛选展示
    ongoing_params = [uid]
    ongoing_where = 'WHERE user_id=? AND status="ongoing"'

    if tab == 'records':
        if filter_source == 'user_bank':
            ongoing_where += ' AND config_json LIKE ?'
            ongoing_params.append('%"source": "user_bank"%')
        elif filter_source == 'public':
            ongoing_where += ' AND (config_json IS NULL OR config_json NOT LIKE ?)'
            ongoing_params.append('%"source": "user_bank"%')

        if subject != 'all':
            ongoing_where += ' AND subject = ?'
            ongoing_params.append(subject)

        if bank_id:
            ongoing_where += ' AND (config_json LIKE ? OR config_json LIKE ?)'
            ongoing_params.append(f'%"bank_id": {int(bank_id)},%')
            ongoing_params.append('%"bank_id": ' + str(int(bank_id)) + '}%')

    ongoing = conn.execute(
        f'SELECT * FROM exams {ongoing_where} ORDER BY started_at DESC',
        ongoing_params,
    ).fetchall()

    # 已提交的考试：仅记录页分页查询
    submitted = []
    total = 0
    if tab == 'records':
        where = 'WHERE user_id=? AND status="submitted"'
        params = [uid]

        if filter_source == 'user_bank':
            where += ' AND config_json LIKE ?'
            params.append('%"source": "user_bank"%')
        elif filter_source == 'public':
            where += ' AND (config_json IS NULL OR config_json NOT LIKE ?)'
            params.append('%"source": "user_bank"%')

        if subject != 'all':
            where += ' AND subject = ?'
            params.append(subject)

        if bank_id:
            where += ' AND (config_json LIKE ? OR config_json LIKE ?)'
            params.append(f'%"bank_id": {int(bank_id)},%')
            params.append('%"bank_id": ' + str(int(bank_id)) + '}%')

        total = conn.execute(f'SELECT COUNT(1) FROM exams {where}', params).fetchone()[0]
        offset = (page - 1) * size
        submitted = conn.execute(
            f'SELECT * FROM exams {where} ORDER BY submitted_at DESC LIMIT ? OFFSET ?',
            params + [size, offset],
        ).fetchall()

    # exam_questions 统计（用于列表/最近考试）
    stats_map: dict[int, dict[str, int]] = {}
    stat_exam_ids = [int(r['id']) for r in ongoing] + [int(r['id']) for r in submitted]
    if stat_exam_ids:
        placeholders = ','.join(['?'] * len(stat_exam_ids))
        rows = conn.execute(
            f"""
            SELECT exam_id,
                   COUNT(1) as total,
                   SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) as correct
            FROM exam_questions
            WHERE exam_id IN ({placeholders})
            GROUP BY exam_id
            """,
            stat_exam_ids,
        ).fetchall()
        for r in rows:
            ex_id = int(r['exam_id'])
            stats_map[ex_id] = {
                'total': int(r['total'] or 0),
                'correct': int(r['correct'] or 0),
            }

    def _enrich_exam(row_dict: dict) -> dict:
        cfg = _parse_exam_config(row_dict.get('config_json'))
        source_val = _exam_source_from_cfg(cfg)
        ex_id = int(row_dict.get('id') or 0)
        st = stats_map.get(ex_id, {'total': 0, 'correct': 0})
        total_q = int(st.get('total') or 0)
        correct_q = int(st.get('correct') or 0)
        acc = round(correct_q * 100.0 / total_q, 1) if total_q else 0.0
        row_dict['source'] = source_val
        row_dict['bank_id'] = cfg.get('bank_id') if source_val == 'user_bank' else None
        row_dict['q_total'] = total_q
        row_dict['q_correct'] = correct_q
        row_dict['accuracy'] = acc
        return row_dict

    ongoing_payload = [_enrich_exam(dict(r)) for r in ongoing]
    submitted_payload = [_enrich_exam(dict(r)) for r in submitted]

    # 数据页
    stats_overview = {
        'submitted_count': 0,
        'avg_score': 0,
        'avg_accuracy': 0,
        'last7_count': 0,
        'last7_avg_accuracy': 0,
    }
    recent_exams = []
    type_dist = []

    if tab == 'data':
        stats_overview['submitted_count'] = int(
            conn.execute(
                'SELECT COUNT(1) FROM exams WHERE user_id=? AND status="submitted"',
                (uid,),
            ).fetchone()[0]
            or 0
        )

        avg_score = conn.execute(
            'SELECT AVG(total_score) FROM exams WHERE user_id=? AND status="submitted"',
            (uid,),
        ).fetchone()[0]
        stats_overview['avg_score'] = round(float(avg_score or 0), 2)

        avg_acc = conn.execute(
            """
            SELECT AVG(acc) FROM (
              SELECT e.id as id,
                     CASE WHEN COUNT(eq.id)=0 THEN 0
                          ELSE (SUM(CASE WHEN eq.is_correct=1 THEN 1 ELSE 0 END) * 100.0 / COUNT(eq.id))
                     END as acc
              FROM exams e
              LEFT JOIN exam_questions eq ON eq.exam_id = e.id
              WHERE e.user_id=? AND e.status="submitted"
              GROUP BY e.id
            ) t
            """,
            (uid,),
        ).fetchone()[0]
        stats_overview['avg_accuracy'] = round(float(avg_acc or 0), 1)

        stats_overview['last7_count'] = int(
            conn.execute(
                'SELECT COUNT(1) FROM exams WHERE user_id=? AND status="submitted" AND submitted_at >= datetime("now", "-7 day")',
                (uid,),
            ).fetchone()[0]
            or 0
        )

        recent_rows = conn.execute(
            'SELECT * FROM exams WHERE user_id=? AND status="submitted" ORDER BY submitted_at DESC LIMIT 7',
            (uid,),
        ).fetchall()
        recent_exams = [dict(r) for r in recent_rows]

        recent_ids = [int(r['id']) for r in recent_exams if r.get('id') is not None]
        if recent_ids:
            placeholders = ','.join(['?'] * len(recent_ids))
            rows = conn.execute(
                f"""
                SELECT exam_id,
                       COUNT(1) as total,
                       SUM(CASE WHEN is_correct=1 THEN 1 ELSE 0 END) as correct
                FROM exam_questions
                WHERE exam_id IN ({placeholders})
                GROUP BY exam_id
                """,
                recent_ids,
            ).fetchall()
            rstats = {int(r['exam_id']): {'total': int(r['total'] or 0), 'correct': int(r['correct'] or 0)} for r in rows}
            for e in recent_exams:
                ex_id = int(e.get('id') or 0)
                cfg = _parse_exam_config(e.get('config_json'))
                src = _exam_source_from_cfg(cfg)
                st = rstats.get(ex_id, {'total': 0, 'correct': 0})
                total_q = int(st.get('total') or 0)
                correct_q = int(st.get('correct') or 0)
                e['source'] = src
                e['q_total'] = total_q
                e['q_correct'] = correct_q
                e['accuracy'] = round(correct_q * 100.0 / total_q, 1) if total_q else 0.0

            if recent_exams:
                stats_overview['last7_avg_accuracy'] = round(
                    sum(float(e.get('accuracy') or 0) for e in recent_exams) / len(recent_exams),
                    1,
                )

        # 题型分布：最近 30 天（公共 + 个人题库合并）
        public_rows = conn.execute(
            """
            SELECT q.q_type as q_type, COUNT(1) as cnt
            FROM exams e
            JOIN exam_questions eq ON eq.exam_id = e.id
            JOIN questions q ON q.id = eq.question_id
            WHERE e.user_id=?
              AND e.status="submitted"
              AND e.submitted_at >= datetime("now", "-30 day")
              AND (e.config_json IS NULL OR e.config_json NOT LIKE ?)
              AND q.q_type IS NOT NULL AND TRIM(q.q_type) != ''
            GROUP BY q.q_type
            """,
            (uid, '%"source": "user_bank"%'),
        ).fetchall()

        bank_rows = conn.execute(
            """
            SELECT q.q_type as q_type, COUNT(1) as cnt
            FROM exams e
            JOIN exam_questions eq ON eq.exam_id = e.id
            JOIN user_bank_questions q ON q.id = eq.question_id
            WHERE e.user_id=?
              AND e.status="submitted"
              AND e.submitted_at >= datetime("now", "-30 day")
              AND e.config_json LIKE ?
              AND q.q_type IS NOT NULL AND TRIM(q.q_type) != ''
            GROUP BY q.q_type
            """,
            (uid, '%"source": "user_bank"%'),
        ).fetchall()

        merged: dict[str, int] = {}
        for r in list(public_rows) + list(bank_rows):
            qt = (r['q_type'] or '').strip()
            if not qt:
                continue
            merged[qt] = merged.get(qt, 0) + int(r['cnt'] or 0)

        if merged:
            max_cnt = max(merged.values()) if merged else 0
            type_dist = [
                {
                    'q_type': k,
                    'count': int(v),
                    'pct': round((float(v) * 100.0 / float(max_cnt)) if max_cnt else 0.0, 1),
                }
                for k, v in sorted(merged.items(), key=lambda kv: kv[1], reverse=True)
            ]
    
    return render_template(
        'exam/exams_v3.html',
        tab=tab,
        ongoing=ongoing_payload,
        submitted=submitted_payload,
        subjects=subjects,
        subjects_meta=subjects_meta,
        q_types=q_types,
        subject_q_types_json=json.dumps(subject_q_types, ensure_ascii=False),
        filter_subject=subject,
        filter_source=filter_source,
        filter_bank_id=bank_id,
        banks_meta=banks_meta,
        bank_q_types_json=json.dumps(bank_q_types, ensure_ascii=False),
        stats_overview=stats_overview,
        recent_exams=recent_exams,
        type_dist=type_dist,
        page=page,
        size=size,
        total=total,
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
    )


@exam_pages_bp.route('/exams/<int:exam_id>')
def page_exam_detail(exam_id):
    """考试详情页面"""
    uid = session.get('user_id')
    if not uid:
        return redirect(url_for('auth.login_page'))
    
    conn = get_db()
    exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
    
    # 管理员可查看任意用户的考试
    if not exam:
        return "考试不存在或无权限", 403
    if exam['user_id'] != uid and not session.get('is_admin'):
        return "考试不存在或无权限", 403
    
    # 统计每题对错
    cfg = _parse_exam_config(exam['config_json'] if exam else None)
    source = _exam_source_from_cfg(cfg)

    if source == 'user_bank':
        rows = conn.execute(
            """
            SELECT eq.*, q.content, q.answer, q.q_type
            FROM exam_questions eq
            JOIN user_bank_questions q ON q.id = eq.question_id
            WHERE eq.exam_id=?
            ORDER BY eq.order_index
            """,
            (exam_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT eq.*, q.content, q.answer, q.q_type
            FROM exam_questions eq
            JOIN questions q ON q.id = eq.question_id
            WHERE eq.exam_id=?
            ORDER BY eq.order_index
            """,
            (exam_id,),
        ).fetchall()
    
    total = len(rows)
    correct = sum(1 for r in rows if (r['is_correct'] or 0) == 1)
    acc = round(correct*100.0/total, 1) if total else 0.0
    
    data = {
        'exam': dict(exam),
        'total': total,
        'correct': correct,
        'accuracy': acc,
        'items': [dict(r) for r in rows],
        'exam_source': source,
        'exam_bank_id': cfg.get('bank_id') if source == 'user_bank' else None,
    }
    
    return render_template(
        'exam/exam_detail_v2.html',
        **data,
        is_subject_admin=session.get('is_subject_admin', False),
        is_notification_admin=session.get('is_notification_admin', False),
    )


