# -*- coding: utf-8 -*-
"""一次性脚本：为历史 direct 会话填充 direct_pair_key

在增加唯一约束前，必须先为存量数据生成 pair key。
"""
import sqlite3
import os

# 从项目配置确定 DB 路径
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'submissions.db')

def populate_keys():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # 1. 确认字段已存在（init_db 应该已添加）
        conv_cols = [r['name'] for r in cur.execute("PRAGMA table_info(chat_conversations)").fetchall()]
        if 'direct_pair_key' not in conv_cols:
            print("字段 direct_pair_key 不存在，请先运行应用让 init_db() 创建它。")
            return

        # 2. 找出所有需要填充的 direct 会话
        cur.execute("SELECT id FROM chat_conversations WHERE c_type='direct' AND (direct_pair_key IS NULL OR direct_pair_key = '')")
        conv_ids_to_fill = [r['id'] for r in cur.fetchall()]

        if not conv_ids_to_fill:
            print("所有 direct 会话已有 pair key，无需填充。")
            return

        print(f"发现 {len(conv_ids_to_fill)} 个 direct 会话需要填充 pair key...")
        updated_count = 0
        for cid in conv_ids_to_fill:
            cur.execute("SELECT user_id FROM chat_members WHERE conversation_id=? ORDER BY user_id", (cid,))
            uids = [r['user_id'] for r in cur.fetchall()]
            if len(uids) == 2:
                pair_key = f"{uids[0]}:{uids[1]}"
                cur.execute("UPDATE chat_conversations SET direct_pair_key = ? WHERE id = ?", (pair_key, cid))
                updated_count += 1
            else:
                print(f"  - [警告] 会话 {cid} 成员数不为2，已跳过。")

        conn.commit()
        print(f"\n填充完成，共更新 {updated_count} 条记录。")

    except Exception as e:
        print(f"[ERROR] 填充失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在于: {DB_PATH}")
    else:
        populate_keys()

