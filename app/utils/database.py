# -*- coding: utf-8 -*-
"""
数据库工具函数
"""
import sqlite3
from flask import g, current_app


def get_db():
    """获取数据库连接（使用Flask g对象实现连接池）"""
    if 'db' not in g:
        db = sqlite3.connect(current_app.config['DATABASE_PATH'])
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        g.db = db
    return g.db


def close_db(error=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """初始化数据库（创建表和索引）"""
    conn = sqlite3.connect(current_app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    
    try:
        # 创建表
        _create_tables(conn)
        # 创建索引
        _create_indexes(conn)
        conn.commit()
        print('[OK] 数据库初始化完成')
    except Exception as e:
        print(f'[ERROR] 数据库初始化失败: {str(e)}')
        conn.rollback()
    finally:
        conn.close()


def _create_tables(conn):
    """创建数据库表"""
    # 用户进度表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            p_key TEXT NOT NULL,
            data TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, p_key),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 考试表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT,
            duration_minutes INTEGER NOT NULL,
            config_json TEXT,
            total_score REAL DEFAULT 0,
            status TEXT DEFAULT 'ongoing',
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            submitted_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # 考试题目表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            order_index INTEGER NOT NULL,
            score_val REAL DEFAULT 1,
            user_answer TEXT,
            is_correct INTEGER,
            answered_at DATETIME,
            FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
        )
    ''')
    
    # 添加用户表列（如果不存在）
    try:
        cur = conn.cursor()
        cols = [r['name'] for r in cur.execute("PRAGMA table_info(users)").fetchall()]
        if 'is_locked' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN is_locked INTEGER DEFAULT 0')
        if 'session_version' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN session_version INTEGER DEFAULT 0')
        if 'avatar' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN avatar TEXT')
        if 'contact' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN contact TEXT')
        if 'college' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN college TEXT')
        if 'last_active' not in cols:
            cur.execute('ALTER TABLE users ADD COLUMN last_active DATETIME')
    except Exception:
        pass
    
    # 添加user_progress表的created_at字段（如果不存在）
    try:
        cur = conn.cursor()
        progress_cols = [r['name'] for r in cur.execute("PRAGMA table_info(user_progress)").fetchall()]
        if 'created_at' not in progress_cols:
            # SQLite不支持带非常量默认值的ALTER TABLE,所以不设置默认值
            cur.execute('ALTER TABLE user_progress ADD COLUMN created_at TIMESTAMP')
    except Exception:
        pass

    # 通知表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            n_type TEXT NOT NULL DEFAULT 'info',
            priority INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            start_at DATETIME,
            end_at DATETIME,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 用户关闭通知记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notification_dismissals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            notification_id INTEGER NOT NULL,
            dismissed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, notification_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(notification_id) REFERENCES notifications(id) ON DELETE CASCADE
        )
    ''')


def _create_indexes(conn):
    """创建数据库索引"""
    indexes = [
        # 用户相关索引
        'CREATE INDEX IF NOT EXISTS idx_favorites_user_question ON favorites(user_id, question_id)',
        'CREATE INDEX IF NOT EXISTS idx_mistakes_user_question ON mistakes(user_id, question_id)',
        'CREATE INDEX IF NOT EXISTS idx_user_answers_user ON user_answers(user_id, created_at)',
        'CREATE INDEX IF NOT EXISTS idx_user_answers_question ON user_answers(question_id)',
        
        # 题目相关索引
        'CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject_id)',
        'CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(q_type)',
        'CREATE INDEX IF NOT EXISTS idx_questions_subject_type ON questions(subject_id, q_type)',
        
        # 考试相关索引
        'CREATE INDEX IF NOT EXISTS idx_exams_user_status ON exams(user_id, status)',
        'CREATE INDEX IF NOT EXISTS idx_exams_submitted ON exams(submitted_at)',
        'CREATE INDEX IF NOT EXISTS idx_exam_questions_exam ON exam_questions(exam_id)',
        'CREATE INDEX IF NOT EXISTS idx_exam_questions_question ON exam_questions(question_id)',
        
        # 用户进度索引
        'CREATE INDEX IF NOT EXISTS idx_user_progress_key ON user_progress(user_id, p_key)',

        # 通知相关索引
        'CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications(is_active, priority DESC)',
        'CREATE INDEX IF NOT EXISTS idx_notifications_time ON notifications(start_at, end_at)',
        'CREATE INDEX IF NOT EXISTS idx_notification_dismissals_user ON notification_dismissals(user_id, notification_id)',
    ]
    
    for index_sql in indexes:
        conn.execute(index_sql)

