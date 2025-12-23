import sqlite3
import json
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

PROBLEM = {
    "title": "A + B 问题",
    "description": "输入两个整数，输出它们的和。",
    "test_cases": [{"input": "3 5", "output": "8"}]
}

def get_db():
    conn = sqlite3.connect('submissions.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM questions")
    quiz_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM favorites")
    fav_count = c.fetchone()[0]
    c.execute("SELECT DISTINCT subject FROM questions")
    subjects = [row[0] for row in c.fetchall()]
    c.execute("SELECT DISTINCT q_type FROM questions")
    q_types = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('index.html', problem=PROBLEM, quiz_count=quiz_count, fav_count=fav_count, subjects=subjects, q_types=q_types)

@app.route('/quiz')
def quiz_page():
    subject = request.args.get('subject', 'all')
    q_type = request.args.get('type', 'all')
    mode = request.args.get('mode', 'quiz') # 默认为刷题模式
    
    conn = get_db()
    
    # 收藏本逻辑
    if subject == 'favorites':
        sql = "SELECT q.*, 1 as is_fav FROM questions q JOIN favorites f ON q.id = f.question_id WHERE 1=1"
        params = []
    else:
        sql = "SELECT q.*, CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_fav FROM questions q LEFT JOIN favorites f ON q.id = f.question_id WHERE 1=1"
        params = []
        if subject != 'all':
            sql += " AND q.subject = ?"
            params.append(subject)
    
    if q_type != 'all':
        sql += " AND q.q_type = ?"
        params.append(q_type)
        
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    
    questions = []
    for row in rows:
        q = dict(row)
        if q['options']: q['options'] = json.loads(q['options'])
        questions.append(q)
        
    # 将 mode 传给前端
    return render_template('quiz.html', questions=questions, mode=mode)

@app.route('/api/favorite', methods=['POST'])
def toggle_favorite():
    data = request.json
    q_id = data.get('question_id')
    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM favorites WHERE question_id = ?", (q_id,)).fetchone()
        if exists:
            conn.execute("DELETE FROM favorites WHERE question_id = ?", (q_id,))
        else:
            conn.execute("INSERT INTO favorites (question_id) VALUES (?)", (q_id,))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error"})
    finally:
        conn.close()

@app.route('/api/submit', methods=['POST'])
def submit_code():
    return jsonify({"final_status": "Accepted", "details": []})

if __name__ == '__main__':
    # 生产环境务必关闭 debug
    app.run(host='0.0.0.0', port=80, debug=False)