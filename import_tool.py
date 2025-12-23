import sqlite3
import json
import re
import os

DATA_ROOT = 'questions_data'
DB_FILE = 'submissions.db'

def import_questions():
    if not os.path.exists(DATA_ROOT):
        print(f"❌ 错误：找不到 {DATA_ROOT} 文件夹。请先创建！")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    print("🔄 清空旧题库...")
    c.execute("DELETE FROM questions")
    c.execute("DELETE FROM sqlite_sequence WHERE name='questions'")

    total = 0

    # 遍历所有文件夹
    for root, dirs, files in os.walk(DATA_ROOT):
        for file in files:
            if file.endswith('.json'):
                # === 核心逻辑：文件夹名 = 科目名 ===
                subject = os.path.basename(root)
                if root == DATA_ROOT: subject = "默认科目"

                path = os.path.join(root, file)
                print(f"📂 正在导入科目 [{subject}] - 文件: {file}")

                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    for item in data:
                        q_type = item.get('题型', '未知')
                        raw_content = item.get('题干', '')
                        answer = item.get('答案', '')
                        explain = item.get('解析', '')
                        opts_json = "[]"

                        # 格式处理
                        if q_type == '选择题':
                            opts_json = json.dumps(item.get('选项', []), ensure_ascii=False)
                        
                        elif q_type == '填空题':
                            # 自动把 {答案} 变成 ______
                            matches = re.findall(r'\{(.*?)\}', raw_content)
                            if matches:
                                answer = " ".join(matches) # 存入所有答案
                                raw_content = re.sub(r'\{.*?\}', '______', raw_content)

                        c.execute('''
                            INSERT INTO questions (subject, q_type, content, options, answer, explanation)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (subject, q_type, raw_content, opts_json, answer, explain))
                        total += 1

                except Exception as e:
                    print(f"⚠️ 文件 {file} 格式错误: {e}")

    conn.commit()
    conn.close()
    print(f"\n🎉 导入完成！共 {total} 道题。")

if __name__ == "__main__":
    import_questions()