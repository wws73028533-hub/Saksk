import sqlite3
import os

DB_FILE = 'submissions.db'

def init():
    # 注意：为了保护你的题目数据，这次我们【不删除】旧数据库文件
    # 只创建新表。如果你想彻底重置，请手动删除 submissions.db
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 1. 历史记录表
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            status TEXT,
            submit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. 题库表
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            q_type TEXT,
            content TEXT,
            options TEXT, 
            answer TEXT,
            explanation TEXT
        )
    ''')

    # 3. 【新增】收藏表
    # 关联 question_id，用于记录收藏状态
    c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER UNIQUE, -- 确保每道题只能收藏一次
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    print("✅ 数据库升级成功！已添加收藏功能的支持。")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init()