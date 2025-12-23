# -*- coding: utf-8 -*-
"""
考试模型
"""
import json
from datetime import datetime
from ..utils.database import get_db


class Exam:
    """考试模型"""
    
    @staticmethod
    def create(user_id, subject, duration, types_config, scores_config):
        """创建考试"""
        conn = get_db()
        
        # 创建考试记录
        config_json = json.dumps({
            'subject': subject,
            'duration': duration,
            'types': types_config,
            'scores': scores_config
        }, ensure_ascii=False)
        
        conn.execute(
            'INSERT INTO exams (user_id, subject, duration_minutes, config_json, status) VALUES (?, ?, ?, ?, ?)',
            (user_id, subject, duration, config_json, 'ongoing')
        )
        exam_id = conn.lastrowid
        
        # 添加题目
        order_index = 0
        sub_sql = " AND s.name = ?" if subject != 'all' else ""
        sub_param = [subject] if subject != 'all' else []
        
        for q_type, count in types_config.items():
            count = int(count or 0)
            if count <= 0:
                continue
            
            sql = f"SELECT q.* FROM questions q LEFT JOIN subjects s ON q.subject_id = s.id WHERE q.q_type = ?{sub_sql} ORDER BY RANDOM() LIMIT ?"
            params = [q_type] + sub_param + [count]
            rows = conn.execute(sql, params).fetchall()
            
            for row in rows:
                score_val = float(scores_config.get(q_type, 1))
                conn.execute(
                    'INSERT INTO exam_questions (exam_id, question_id, order_index, score_val) VALUES (?, ?, ?, ?)',
                    (exam_id, row['id'], order_index, score_val)
                )
                order_index += 1
        
        conn.commit()
        return exam_id
    
    @staticmethod
    def get_by_id(exam_id, user_id=None):
        """获取考试详情"""
        conn = get_db()
        exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
        
        if not exam:
            return None
        
        if user_id and exam['user_id'] != user_id:
            return None
        
        # 获取题目
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
                except:
                    q['options'] = []
            questions.append(q)
        
        return {
            'exam': dict(exam),
            'questions': questions
        }
    
    @staticmethod
    def submit(exam_id, user_id, answers):
        """提交考试"""
        conn = get_db()
        
        # 验证权限
        exam = conn.execute('SELECT * FROM exams WHERE id=?', (exam_id,)).fetchone()
        if not exam or exam['user_id'] != user_id or exam['status'] == 'submitted':
            return None
        
        # 答案映射
        ans_map = {int(a['question_id']): a['user_answer'].strip() for a in answers if a.get('question_id')}
        
        # 获取题目并判分
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
            std_ans = (r['answer'] or '').strip()
            q_type = r['q_type'] or ''
            
            is_correct = 0
            if q_type in ('选择题', '判断题'):
                ua = ''.join(sorted(list(user_ans))) if q_type == '选择题' else user_ans
                sa = ''.join(sorted(list(std_ans))) if q_type == '选择题' else std_ans
                if ua == sa and ua != '':
                    is_correct = 1
            elif q_type == '填空题':
                if user_ans and user_ans == std_ans:
                    is_correct = 1
            else:
                if user_ans:
                    is_correct = 1
            
            conn.execute(
                'UPDATE exam_questions SET user_answer=?, is_correct=?, answered_at=CURRENT_TIMESTAMP WHERE id=?',
                (user_ans, is_correct, r['eq_id'])
            )
            
            if is_correct:
                correct += 1
                total_score += float(r['score_val'] or 0)
        
        # 更新考试状态
        conn.execute(
            'UPDATE exams SET total_score=?, status="submitted", submitted_at=CURRENT_TIMESTAMP WHERE id=?',
            (total_score, exam_id)
        )
        conn.commit()
        
        return {
            'total': total,
            'correct': correct,
            'total_score': total_score
        }

