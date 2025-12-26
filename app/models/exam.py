# -*- coding: utf-8 -*-
"""
考试模型
"""
import json
from datetime import datetime
from ..utils.database import get_db


class Exam:
    """考试模型（尽量集中与考试相关的数据库操作与业务规则）"""

    @staticmethod
    def _normalize_subject(subject):
        s = (subject or 'all').strip()
        return s if s else 'all'

    @staticmethod
    def _safe_int(v, default=0, min_v=None, max_v=None):
        try:
            iv = int(v)
        except Exception:
            iv = int(default)
        if min_v is not None:
            iv = max(min_v, iv)
        if max_v is not None:
            iv = min(max_v, iv)
        return iv

    @staticmethod
    def _safe_float(v, default=0.0, min_v=None, max_v=None):
        try:
            fv = float(v)
        except Exception:
            fv = float(default)
        if min_v is not None:
            fv = max(min_v, fv)
        if max_v is not None:
            fv = min(max_v, fv)
        return fv

    @staticmethod
    def create(user_id, subject, duration, types_config, scores_config):
        """创建考试：写入 exams + exam_questions，并返回 exam_id

        规则：
        - subject='all' 表示不限制科目
        - types_config: {题型: 题数}
        - scores_config: {题型: 分值}
        """
        conn = get_db()

        subject = Exam._normalize_subject(subject)
        duration = Exam._safe_int(duration, default=60, min_v=1, max_v=24 * 60)
        types_config = types_config or {}
        scores_config = scores_config or {}

        config_json = json.dumps({
            'subject': subject,
            'duration': duration,
            'types': types_config,
            'scores': scores_config
        }, ensure_ascii=False)

        cur = conn.execute(
            'INSERT INTO exams (user_id, subject, duration_minutes, config_json, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, subject, duration, config_json, 'ongoing')
        )
        exam_id = cur.lastrowid

        order_index = 0
        sub_sql = " AND s.name = ?" if subject != 'all' else ""
        sub_param = [subject] if subject != 'all' else []

        for q_type, count in (types_config or {}).items():
            cnt = Exam._safe_int(count, default=0, min_v=0, max_v=500)
            if cnt <= 0:
                continue

            sql = (
                "SELECT q.* FROM questions q "
                "LEFT JOIN subjects s ON q.subject_id = s.id "
                f"WHERE q.q_type = ?{sub_sql} "
                "ORDER BY RANDOM() LIMIT ?"
            )
            params = [q_type] + sub_param + [cnt]
            rows = conn.execute(sql, params).fetchall()

            for row in rows:
                score_val = Exam._safe_float(scores_config.get(q_type, 1), default=1.0, min_v=0.0, max_v=1000.0)
                conn.execute(
                    'INSERT INTO exam_questions (exam_id, question_id, order_index, score_val) VALUES (?, ?, ?, ?)',
                    (exam_id, row['id'], order_index, score_val)
                )
                order_index += 1

        conn.commit()
        return exam_id

    @staticmethod
    def get_by_id(exam_id, user_id=None):
        """获取考试与题目（含用户作答与判分字段）"""
        conn = get_db()
        exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()

        if not exam:
            return None

        if user_id and exam['user_id'] != user_id:
            return None

        rows = conn.execute('''
            SELECT q.*, eq.score_val, eq.order_index, eq.user_answer, eq.is_correct
            FROM exam_questions eq
            JOIN questions q ON q.id = eq.question_id
            WHERE eq.exam_id=?
            ORDER BY eq.order_index
        ''', (exam_id,)).fetchall()

        questions = []
        for r in rows:
            q = dict(r)
            if q.get('options'):
                try:
                    q['options'] = json.loads(q['options'])
                except Exception:
                    q['options'] = []
            questions.append(q)

        return {'exam': dict(exam), 'questions': questions}

    @staticmethod
    def _grade_answer(q_type, user_ans, std_ans):
        q_type = (q_type or '').strip()
        user_ans = (user_ans or '').strip()
        std_ans = (std_ans or '').strip()

        if q_type in ('选择题', '判断题'):
            if q_type == '选择题':
                ua = ''.join(sorted(list(user_ans)))
                sa = ''.join(sorted(list(std_ans)))
            else:
                ua = user_ans
                sa = std_ans
            return 1 if (ua != '' and ua == sa) else 0

        if q_type == '填空题':
            """填空题判分：支持多空 + 每空多答案

            约定：
            - 标准答案格式：不同空用 ";;" 分隔；每空多答案用 ";" 分隔
              例如：北京;北平;;上海;沪
            - 用户提交：
              - 单空：直接提交字符串
              - 多空：前端提交 JSON 数组字符串，如 "[\"a\",\"b\"]"
            """
            if not user_ans:
                return 0

            # 解析用户答案：可能是 JSON 数组字符串，也可能是普通字符串
            ua_list = None
            try:
                tmp = json.loads(user_ans)
                if isinstance(tmp, list):
                    ua_list = [str(x).strip() for x in tmp]
            except Exception:
                ua_list = None

            # 解析标准答案：
            # - 不同空之间用 ";;" 分隔
            # - 同一空的多个可接受答案用 ";" 分隔
            # 例：北京;北平;;上海;沪
            std = (std_ans or '').strip()
            std_blanks = [s.strip() for s in std.split(';;')] if std else ['']

            # 单空：候选集用 ";" 分隔
            def match_one(user_one, std_one):
                user_one = (user_one or '').strip()
                if not user_one:
                    return False
                cand = [c.strip() for c in (std_one or '').split(';') if c and c.strip()]
                if not cand:
                    cand = [(std_one or '').strip()]
                return any(user_one == c for c in cand)

            # 多空：逐空匹配，空数需一致；多余答案/缺失答案均算错
            if ua_list is not None:
                if len(ua_list) != len(std_blanks):
                    return 0
                return 1 if all(match_one(ua_list[i], std_blanks[i]) for i in range(len(std_blanks))) else 0

            # 非 JSON：按“第一空”处理（兼容历史单输入实现）
            if len(std_blanks) > 1:
                return 1 if match_one(user_ans, std_blanks[0]) else 0
            return 1 if match_one(user_ans, std_blanks[0]) else 0

        # 其它题型（简答等）：当前策略为“只要有作答就算对”
        return 1 if user_ans != '' else 0

    @staticmethod
    def submit(exam_id, user_id, answers):
        """提交考试：写入每题作答与 is_correct，并更新 exams.total_score/status"""
        conn = get_db()

        exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
        if not exam or exam['user_id'] != user_id or exam['status'] == 'submitted':
            return None

        ans_map = {}
        for a in (answers or []):
            try:
                qid = int(a.get('question_id'))
            except Exception:
                continue
            ans_map[qid] = (a.get('user_answer') or '').strip()

        rows = conn.execute('''
            SELECT eq.id as eq_id, eq.question_id, eq.score_val, q.answer, q.q_type
            FROM exam_questions eq
            JOIN questions q ON q.id = eq.question_id
            WHERE eq.exam_id=?
        ''', (exam_id,)).fetchall()

        total = len(rows)
        correct = 0
        total_score = 0.0

        for r in rows:
            qid = r['question_id']
            user_ans = ans_map.get(qid, '')
            std_ans = (r['answer'] or '')
            q_type = r['q_type'] or ''

            is_correct = Exam._grade_answer(q_type, user_ans, std_ans)

            conn.execute(
                'UPDATE exam_questions SET user_answer=?, is_correct=?, answered_at=CURRENT_TIMESTAMP WHERE id=?',
                (user_ans, is_correct, r['eq_id'])
            )

            if is_correct:
                correct += 1
                total_score += float(r['score_val'] or 0)

        conn.execute(
            'UPDATE exams SET total_score=?, status="submitted", submitted_at=CURRENT_TIMESTAMP WHERE id=?',
            (total_score, exam_id)
        )
        conn.commit()

        return {'total': total, 'correct': correct, 'total_score': total_score}

