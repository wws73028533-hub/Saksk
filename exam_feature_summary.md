# 考试功能总结

> 本文总结当前项目中的“考试（Exam）”相关功能：数据模型、路由/API、页面与交互、判分规则、错题本联动等。

## 1. 功能概览

考试模块提供以下能力：

- **考试列表**：展示当前用户的进行中考试、已提交历史考试；支持科目筛选与分页。
- **考试详情/成绩单**：展示单次考试统计（总分、正确率、开始/提交时间）与每题对错。
- **创建考试（API）**：基于科目与题型配置随机抽题生成考试。
- **提交考试（API）**：保存用户作答、自动判分、汇总得分并将考试置为已提交。
- **保存草稿（API）**：考试进行中保存当前作答（便于刷新/中断恢复）。
- **删除考试（API）**：删除某次考试记录。
- **错题本联动（API）**：将已提交考试的错题批量加入错题本（mistakes 表）。
- **管理员查看**：管理员可查看任意用户的考试成绩页 `/exams/<id>`。

---

## 2. 相关文件

- `app/models/exam.py`：考试模型与核心业务逻辑（创建/获取/提交/判分）。
- `app/routes/exam.py`：考试页面路由与考试 API。
- `app/templates/exams.html`：考试列表页（进行中 + 已提交）。
- `app/templates/exam_detail.html`：考试成绩详情页。
- `app/templates/quiz.html`：考试作答页面（与练习共用，mode=exam）。

---

## 3. 数据结构（数据库表概念）

> 表结构以代码使用到的字段为准（具体建表 SQL 以项目实际为准）。

### 3.1 exams

- `id`
- `user_id`
- `subject`：科目名称或 `all`
- `duration_minutes`
- `config_json`：创建考试时的配置（题型数量、分值等）
- `status`：`ongoing` / `submitted`
- `started_at`
- `submitted_at`
- `total_score`

### 3.2 exam_questions

- `id`
- `exam_id`
- `question_id`
- `order_index`
- `score_val`
- `user_answer`
- `is_correct`
- `answered_at`

---

## 4. 页面与交互

### 4.1 考试列表页 `/exams`

- 展示：
  - **进行中考试**：可“继续”或“删除”。
  - **已提交考试**：可“成绩”、“回顾”、“错题加入错题本”、“删除”。
- 支持：
  - 科目筛选：`?subject=xxx`
  - 分页：`?page=1&size=10`

模板：`app/templates/exams.html`

### 4.2 考试成绩页 `/exams/<exam_id>`

- 统计信息：总分、正确/总题数、正确率、开始/提交时间。
- 列表：每题题型、分值、作答、正确答案、结果。
- 操作：回顾题目、错题加入错题本、删除考试。
- 权限：
  - 普通用户：只能看自己的考试。
  - 管理员：可看任意用户考试。

模板：`app/templates/exam_detail.html`

### 4.3 考试作答页 `/quiz?mode=exam&exam_id=<id>`

- 与练习共用页面：`app/templates/quiz.html`
- 考试模式下提供：
  - 下一题/上一题
  - 交卷（提交考试）
  - 草稿保存（若页面逻辑触发）
  - 交卷后回顾

---

## 5. 路由与 API

### 5.1 页面路由

- `GET /exams`：考试列表页
- `GET /exams/<int:exam_id>`：考试详情页

### 5.2 API

- `POST /api/exams/create`
  - 入参：`{subject, duration, types, scores}`
  - 返回：`{status, exam_id}`

- `POST /api/exams/submit`
  - 入参：`{exam_id, answers:[{question_id, user_answer}]}`
  - 返回：`{status, exam_id, total, correct, total_score}`

- `POST /api/exams/save_draft`
  - 入参：`{exam_id, answers:[{question_id, user_answer}]}`
  - 返回：`{status}`

- `DELETE /api/exams/<int:exam_id>`
  - 返回：`{status}`

- `POST /api/exams/<int:exam_id>/mistakes`
  - 将错题加入错题本
  - 返回：`{status, count}`

---

## 6. 判分规则

判分逻辑集中在 `app/models/exam.py -> Exam._grade_answer()`。

### 6.1 选择题 / 判断题

- 选择题：对答案进行排序后比较（支持多选）。
- 判断题：字符串相等（且不能为空）。

### 6.2 填空题（支持多空 + 每空多答案）

当前约定（与你现有题库格式一致）：

- **不同空之间**用 `;;` 分隔
- **同一空的多个可接受答案**用 `;` 分隔

示例：

- 题目：`中国的首都是__，最大城市是__。`
- 标准答案：`北京;北平;;上海;沪`

用户提交：

- 单空：直接提交字符串
- 多空：前端提交 JSON 数组字符串，如：
  - `[
    "北京",
    "沪"
  ]`

判分：

- 多空题要求用户答案数量与空数一致。
- 每一空：只要命中该空任意一个候选答案即判该空正确。
- 所有空都正确，该题才算正确。

> 注：目前比较策略为严格相等（忽略前后空白），如需大小写/全半角/同义词更宽松，可在 `_grade_answer` 中扩展。

### 6.3 其它题型

- 当前策略：只要有作答就算正确（用于问答题/简答题等占位逻辑）。

---

## 7. 管理员权限

- `/exams/<id>`：管理员（`session['is_admin'] == True`）可查看任意用户考试。
- 非管理员仍严格限制只能查看自己考试。

---

## 8. 已知/可优化点（后续迭代建议）

- **答案格式可视化**：✅ 已实现。在题库管理端（`/admin/subjects/<id>/questions`）为“填空题”提供“多空/多答案”结构化输入（可切换手写模式），保存时自动序列化为 `北京;北平;;上海;沪` 格式，避免手写分隔符。
- **更宽松的填空匹配**：支持大小写不敏感、中文全半角、去除多余空格、同义词库等。
- **多空回顾展示**：成绩单页面可按空拆分显示“用户答案/正确候选答案”，提升可读性。
- **考试创建入口**：目前创建考试主要依赖 API 或其他页面入口，可在 `/exams` 增加显式“新建考试”面板。


