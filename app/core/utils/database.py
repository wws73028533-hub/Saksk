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
        # 运行数据迁移
        _run_migrations(conn)
        conn.commit()
        print('[OK] 数据库初始化完成')
    except Exception as e:
        print(f'[ERROR] 数据库初始化失败: {str(e)}')
        conn.rollback()
    finally:
        conn.close()


def _run_migrations(conn):
    """运行数据库迁移"""
    try:
        # 检查has_password_set字段是否存在
        cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if 'has_password_set' in cols:
            # 字段存在，检查是否有需要更新的老用户
            # 更新所有有password_hash但没有email的老用户（has_password_set=0或NULL）
            result = conn.execute('''
                UPDATE users 
                SET has_password_set = 1 
                WHERE password_hash IS NOT NULL 
                AND password_hash != '' 
                AND (email IS NULL OR email = '')
                AND (has_password_set = 0 OR has_password_set IS NULL)
            ''')
            updated_count = result.rowcount
            if updated_count > 0:
                print(f'[迁移] 已为 {updated_count} 个老用户更新 has_password_set=1')
    except Exception as e:
        print(f'[WARN] 迁移has_password_set字段失败: {e}')


def _create_tables(conn):
    """创建数据库表"""
    # 基础表：用户表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_locked INTEGER DEFAULT 0,
            session_version INTEGER DEFAULT 0,
            avatar TEXT,
            contact TEXT,
            college TEXT,
            last_active DATETIME,
            is_subject_admin INTEGER DEFAULT 0,
            is_notification_admin INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 邮箱验证码表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS email_verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            code_type TEXT NOT NULL CHECK(code_type IN ('bind', 'login', 'reset_password')),
            user_id INTEGER,
            is_used INTEGER DEFAULT 0,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            used_at DATETIME,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：科目表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            is_locked INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 基础表：题目表（题库中心专用，不包含编程题字段）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            content TEXT NOT NULL,
            q_type TEXT NOT NULL,
            options TEXT,
            answer TEXT,
            explanation TEXT,
            difficulty INTEGER DEFAULT 1,
            image_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
        )
    ''')
    
    # 编程题专用表：编程题集表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS coding_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            is_locked INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 编程题专用表：编程题目表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS coding_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coding_subject_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            q_type TEXT NOT NULL CHECK(q_type IN ('函数题', '编程题')),
            description TEXT NOT NULL,
            difficulty TEXT NOT NULL CHECK(difficulty IN ('easy', 'medium', 'hard')),
            code_template TEXT,
            programming_language TEXT DEFAULT "python",
            time_limit INTEGER DEFAULT 5,
            memory_limit INTEGER DEFAULT 128,
            test_cases_json TEXT NOT NULL,
            examples TEXT,
            constraints TEXT,
            hints TEXT,
            is_enabled INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(coding_subject_id) REFERENCES coding_subjects(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：收藏表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：错题表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 基础表：用户答题记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            user_answer TEXT,
            is_correct INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE
        )
    ''')
    
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
    
    # 添加用户表列（如果不存在）- 兼容旧数据库
    try:
        cur = conn.cursor()
        # 检查users表是否存在
        table_check = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if table_check:
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
            if 'is_subject_admin' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN is_subject_admin INTEGER DEFAULT 0')
            if 'is_notification_admin' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN is_notification_admin INTEGER DEFAULT 0')
            if 'email' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN email TEXT')
            if 'email_verified' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0')
            if 'email_verified_at' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN email_verified_at DATETIME')
            if 'has_password_set' not in cols:
                cur.execute('ALTER TABLE users ADD COLUMN has_password_set INTEGER DEFAULT 0')
                # 为所有有password_hash但没有email的老用户设置has_password_set=1
                # （老用户通过用户名注册，有真实密码）
                try:
                    cur.execute('''
                        UPDATE users 
                        SET has_password_set = 1 
                        WHERE password_hash IS NOT NULL 
                        AND password_hash != '' 
                        AND (email IS NULL OR email = '')
                    ''')
                    updated_count = cur.rowcount
                    if updated_count > 0:
                        print(f'[迁移] 已为 {updated_count} 个老用户设置 has_password_set=1')
                except Exception as e:
                    print(f'[WARN] 迁移老用户has_password_set字段失败: {e}')
            
            # 创建邮箱唯一索引（如果不存在）
            try:
                index_rows = cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='users'"
                ).fetchall()
                indexes = [row[0] for row in index_rows]
                if 'idx_users_email_unique' not in indexes:
                    # SQLite中，UNIQUE约束通过唯一索引实现
                    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL')
            except Exception as e:
                print(f'[WARN] 创建邮箱唯一索引失败: {e}')

        # 添加 questions 表的字段（如果不存在）- 兼容旧数据库
        # 注意：questions 表只用于题库中心，不包含编程题字段
        table_check = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='questions'").fetchone()
        if table_check:
            question_cols = [r['name'] for r in cur.execute("PRAGMA table_info(questions)").fetchall()]
            if 'image_path' not in question_cols:
                cur.execute('ALTER TABLE questions ADD COLUMN image_path TEXT')
            
            # 不再添加编程题相关字段到 questions 表
            # 编程题应使用 coding_questions 表
        
        # 添加 subjects 表的字段（如果不存在）- 兼容旧数据库
        table_check = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='subjects'").fetchone()
        if table_check:
            subject_cols = [r['name'] for r in cur.execute("PRAGMA table_info(subjects)").fetchall()]
            if 'description' not in subject_cols:
                cur.execute('ALTER TABLE subjects ADD COLUMN description TEXT')
            if 'is_locked' not in subject_cols:
                cur.execute('ALTER TABLE subjects ADD COLUMN is_locked INTEGER DEFAULT 0')
            if 'created_at' not in subject_cols:
                # SQLite不支持带非常量默认值的ALTER TABLE,所以不设置默认值
                cur.execute('ALTER TABLE subjects ADD COLUMN created_at DATETIME')
    except Exception as e:
        print(f'[WARN] 添加字段失败: {e}')
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

    # 聊天：会话表
    # 说明：为从根源杜绝 direct 私聊重复会话，增加 direct_pair_key：
    # - direct 私聊：存 "min_uid:max_uid"（例如 "1:10"）
    # - 非 direct：可为空
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            c_type TEXT NOT NULL DEFAULT 'direct',
            title TEXT,
            direct_pair_key TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 聊天：用户备注表（每个用户对“其他用户”的备注，仅自己可见）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_remarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            target_user_id INTEGER NOT NULL,
            remark TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner_user_id, target_user_id),
            FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 兼容老库：补字段 direct_pair_key（如果不存在）
    try:
        cur = conn.cursor()
        conv_cols = [r['name'] for r in cur.execute("PRAGMA table_info(chat_conversations)").fetchall()]
        if 'direct_pair_key' not in conv_cols:
            cur.execute('ALTER TABLE chat_conversations ADD COLUMN direct_pair_key TEXT')
    except Exception:
        pass

    # 聊天：会话成员表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            last_read_message_id INTEGER DEFAULT 0,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(conversation_id, user_id),
            FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 聊天：消息表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT DEFAULT 'text',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

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
    
    # 弹窗配置表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS popups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            popup_type TEXT NOT NULL DEFAULT 'info' CHECK(popup_type IN ('info', 'warning', 'success', 'error')),
            is_active INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 0,
            start_at DATETIME,
            end_at DATETIME,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 用户关闭弹窗记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS popup_dismissals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            popup_id INTEGER NOT NULL,
            dismissed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, popup_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(popup_id) REFERENCES popups(id) ON DELETE CASCADE
        )
    ''')
    
    # 弹窗显示统计表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS popup_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            popup_id INTEGER NOT NULL,
            user_id INTEGER,
            viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(popup_id) REFERENCES popups(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    # 代码提交历史表（用于记录编程题的提交记录）
    # 注意：question_id 引用 coding_questions 表，不是 questions 表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS code_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            status TEXT NOT NULL,
            passed_cases INTEGER DEFAULT 0,
            total_cases INTEGER DEFAULT 0,
            execution_time REAL,
            error_message TEXT,
            score REAL DEFAULT 0.0,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES coding_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 用户编程统计表（用于快速查询用户对每道题的统计信息）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS coding_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            total_submissions INTEGER DEFAULT 0,
            accepted_submissions INTEGER DEFAULT 0,
            best_time REAL,
            best_score REAL DEFAULT 0.0,
            first_accepted_at DATETIME,
            last_submitted_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES coding_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 用户编程总统计表（用于快速查询用户整体统计）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_coding_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            total_submissions INTEGER DEFAULT 0,
            accepted_submissions INTEGER DEFAULT 0,
            solved_questions INTEGER DEFAULT 0,
            total_score REAL DEFAULT 0.0,
            average_score REAL DEFAULT 0.0,
            acceptance_rate REAL DEFAULT 0.0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 代码草稿表（用于实时保存用户代码）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS code_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            language TEXT DEFAULT 'python',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(question_id) REFERENCES coding_questions(id) ON DELETE CASCADE
        )
    ''')
    
    # 用户-科目限制表（黑名单模式）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            restricted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            restricted_by INTEGER,
            UNIQUE(user_id, subject_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY(restricted_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 系统配置表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY(updated_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 用户刷题统计表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_quiz_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            total_answered INTEGER DEFAULT 0,
            last_reset_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # 查重记录表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS duplicate_check_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            total_pairs INTEGER DEFAULT 0,
            duplicates_json TEXT NOT NULL,
            similarity_threshold REAL DEFAULT 0.8,
            created_by INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')
    
    # 初始化系统配置（如果不存在）
    default_configs = [
        ('quiz_limit_enabled', '0', '刷题数限制功能开关（0=关闭，1=开启）'),
        ('quiz_limit_count', '100', '用户刷题数限制（达到此数量后提示付费）')
    ]
    
    for config_key, config_value, description in default_configs:
        existing = conn.execute(
            'SELECT id FROM system_config WHERE config_key = ?',
            (config_key,)
        ).fetchone()
        
        if not existing:
            conn.execute(
                '''INSERT INTO system_config (config_key, config_value, description)
                   VALUES (?, ?, ?)''',
                (config_key, config_value, description)
            )


def _create_indexes(conn):
    """创建数据库索引"""
    # 检查表是否存在，只对存在的表创建索引
    cur = conn.cursor()
    existing_tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    
    indexes = []
    
    # 用户相关索引（只对存在的表创建）
    if 'favorites' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_favorites_user_question ON favorites(user_id, question_id)')
    if 'mistakes' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_mistakes_user_question ON mistakes(user_id, question_id)')
    if 'user_answers' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_user_answers_user ON user_answers(user_id, created_at)',
            'CREATE INDEX IF NOT EXISTS idx_user_answers_question ON user_answers(question_id)',
        ])
    
    # 题目相关索引（只对存在的表创建）
    if 'questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject_id)',
            'CREATE INDEX IF NOT EXISTS idx_questions_type ON questions(q_type)',
            'CREATE INDEX IF NOT EXISTS idx_questions_subject_type ON questions(subject_id, q_type)',
        ])
    
    # 查重记录相关索引
    if 'duplicate_check_records' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_duplicate_check_subject ON duplicate_check_records(subject_id, created_at DESC)',
        ])
    
    # 考试相关索引（只对存在的表创建）
    if 'exams' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exams_user_status ON exams(user_id, status)',
            'CREATE INDEX IF NOT EXISTS idx_exams_submitted ON exams(submitted_at)',
        ])
    if 'exam_questions' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_exam_questions_exam ON exam_questions(exam_id)',
            'CREATE INDEX IF NOT EXISTS idx_exam_questions_question ON exam_questions(question_id)',
        ])
    
    # 用户进度索引（只对存在的表创建）
    if 'user_progress' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_progress_key ON user_progress(user_id, p_key)')

    # 聊天相关索引（只对存在的表创建）
    if 'chat_members' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_chat_members_user ON chat_members(user_id, conversation_id)')
    if 'chat_messages' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation ON chat_messages(conversation_id, id DESC)')
    if 'chat_conversations' in existing_tables:
        # direct 私聊唯一键：从根源杜绝重复会话（仅当 c_type='direct' 时生效）
        indexes.append("CREATE UNIQUE INDEX IF NOT EXISTS ux_chat_direct_pair ON chat_conversations(direct_pair_key) WHERE c_type='direct' AND direct_pair_key IS NOT NULL")
    if 'user_remarks' in existing_tables:
        # 用户备注：便于查询
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_remarks_owner ON user_remarks(owner_user_id, target_user_id)')

    # 通知相关索引（只对存在的表创建）
    if 'notifications' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_notifications_time ON notifications(start_at, end_at)',
        ])
    if 'notification_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_notification_dismissals_user ON notification_dismissals(user_id, notification_id)')
    
    # 弹窗相关索引（只对存在的表创建）
    if 'popups' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popups_active ON popups(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_popups_time ON popups(start_at, end_at)',
            'CREATE INDEX IF NOT EXISTS idx_popups_type ON popups(popup_type)',
        ])
    if 'popup_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_popup_dismissals_user ON popup_dismissals(user_id, popup_id)')
    if 'popup_views' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popup_views_popup ON popup_views(popup_id, viewed_at)',
            'CREATE INDEX IF NOT EXISTS idx_popup_views_user ON popup_views(user_id, viewed_at)',
        ])
    
    # 代码提交相关索引（只对存在的表创建）
    if 'code_submissions' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_submissions_user_question ON code_submissions(user_id, question_id, submitted_at DESC)')
    
    # 代码草稿相关索引
    if 'code_drafts' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_drafts_user_question ON code_drafts(user_id, question_id)')
    
    # 用户-科目限制表索引
    if 'user_subjects' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_user_id ON user_subjects(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_subject_id ON user_subjects(subject_id)'
        ])
    
    # 系统配置表索引
    if 'system_config' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key)')
    
    # 用户刷题统计表索引
    if 'user_quiz_stats' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_quiz_stats_user_id ON user_quiz_stats(user_id)')
    
    # 邮箱验证码表索引
    if 'email_verification_codes' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_email_codes_email ON email_verification_codes(email, code_type, is_used)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_expires ON email_verification_codes(expires_at)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_user ON email_verification_codes(user_id)',
        ])
    
    for index_sql in indexes:
        conn.execute(index_sql)


    if 'notifications' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_notifications_active ON notifications(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_notifications_time ON notifications(start_at, end_at)',
        ])
    if 'notification_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_notification_dismissals_user ON notification_dismissals(user_id, notification_id)')
    
    # 弹窗相关索引（只对存在的表创建）
    if 'popups' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popups_active ON popups(is_active, priority DESC)',
            'CREATE INDEX IF NOT EXISTS idx_popups_time ON popups(start_at, end_at)',
            'CREATE INDEX IF NOT EXISTS idx_popups_type ON popups(popup_type)',
        ])
    if 'popup_dismissals' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_popup_dismissals_user ON popup_dismissals(user_id, popup_id)')
    if 'popup_views' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_popup_views_popup ON popup_views(popup_id, viewed_at)',
            'CREATE INDEX IF NOT EXISTS idx_popup_views_user ON popup_views(user_id, viewed_at)',
        ])
    
    # 代码提交相关索引（只对存在的表创建）
    if 'code_submissions' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_submissions_user_question ON code_submissions(user_id, question_id, submitted_at DESC)')
    
    # 代码草稿相关索引
    if 'code_drafts' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_code_drafts_user_question ON code_drafts(user_id, question_id)')
    
    # 用户-科目限制表索引
    if 'user_subjects' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_user_id ON user_subjects(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_subjects_subject_id ON user_subjects(subject_id)'
        ])
    
    # 系统配置表索引
    if 'system_config' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_system_config_key ON system_config(config_key)')
    
    # 用户刷题统计表索引
    if 'user_quiz_stats' in existing_tables:
        indexes.append('CREATE INDEX IF NOT EXISTS idx_user_quiz_stats_user_id ON user_quiz_stats(user_id)')
    
    # 邮箱验证码表索引
    if 'email_verification_codes' in existing_tables:
        indexes.extend([
            'CREATE INDEX IF NOT EXISTS idx_email_codes_email ON email_verification_codes(email, code_type, is_used)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_expires ON email_verification_codes(expires_at)',
            'CREATE INDEX IF NOT EXISTS idx_email_codes_user ON email_verification_codes(user_id)',
        ])
    
    for index_sql in indexes:
        conn.execute(index_sql)

