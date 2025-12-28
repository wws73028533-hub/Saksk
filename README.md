# 题库系统 (Quiz Bank System)

> 一个基于 **Flask 3** 的轻量级在线刷题 / 考试 / 题库管理平台，支持多题型、多科目、用户权限与完整的后台管理。

---

## ✨ 主要特性

| 分类 | 功能 | 说明 |
| ---- | ---- | ---- |
| 用户端 | 账号注册 / 登录 / 退出 | 首次注册的用户自动成为管理员 |
|       | 首页数据统计 | 题目总数、收藏/错题统计等 |
|       | 题库搜索 | 关键字 + 科目 / 题型多条件过滤，分页展示 |
|       | 刷题模式 | 普通刷题 / 背题；支持题目顺序、选项顺序随机打乱与进度保存 |
|       | 多题型支持 | 支持选择题（单选）、**多选题**、判断题、填空题、问答题等多种题型 |
|       | 收藏本 & 错题本 | 一键加入收藏或错题本，随时复习 |
|       | 在线考试 | 自定义科目、时长、题型数量及分值；自动判分、成绩统计（填空题支持多空 + 每空多答案；多选题支持多选项答案） |
|       | 历史记录 | 做题记录、考试记录、答题正确率统计 |
| 用户端 UI | quiz 页答案/解析外置 dock | `#answerCard/#explainCard` 外置展示；桌面端对问答/计算题支持右侧 dock（更适合长答案/长解析） |
| 用户端 UI | 填空题答案结构化展示 | dock 内按“空 1/空 2…”展示；支持“一空多答案/多空多答案” |
| 管理端 | 科目管理 | 增删改查，级联删除题目 |
|       | 题库管理 | 单题增删改查、批量操作（移动科目 / 改题型 / 设难度 / 标签） |
|       | 批量导入 / 导出 | Excel 模板、题目包 (ZIP) 导入导出，含图片资源；支持 **JSON 格式批量导入**（支持选择题、多选题、判断题、填空题、问答题） |
|       | 用户管理 | 权限切换、锁定 / 解锁、强制下线、重置密码、CSV 导出 |
|       | 通知公告 | 站内通知发布、启用 / 禁用、优先级控制 |
| **聊天** | **站内私聊（轮询）** | `/chat` 聊天主页面，支持会话列表、消息拉取与已读推进 |
|        | **图片消息** | 发送图片、弹层预览、拖拽/粘贴发送；支持缩略图以减少流量 |
|        | **语音消息** | 按住说话、松开发送；上滑取消；单次仅播放一条语音；气泡仅显示播放键+时长 |
|        | **用户备注** | 给对方设置仅自己可见的备注；会话列表/标题优先显示备注 |
|        | **好友资料页（类似微信）** | 点击头像/“资料”进入资料页：备注内联编辑、右上角“···”菜单、朋友圈预览（占位）、底部“发消息/音视频通话（占位）” |
|        | **会话去重（强约束）** | direct 私聊使用 `direct_pair_key` + SQLite 唯一索引，从根源杜绝重复会话 |
|        | **题目转发（题目卡片）** | 刷题页可把当前题目转发到聊天；聊天内以题目卡片展示，点击弹层查看详情（选择题显示选项/答案/解析；填空题答案结构化展示） |
| 系统 | 安全 | 密码哈希 (Werkzeug)、会话版本控制、速率限制 (Flask-Limiter) |
|      | 日志 | `logs/app.log` 支持滚动日志文件 |

---

## 🛠️ 技术栈

- Python 3.11+
- Flask 3.1.x 及其生态：Jinja2、Werkzeug、Flask-Limiter 等
- SQLite (默认，亦可替换为 MySQL/PostgreSQL)
- Pandas / OpenPyXL (Excel 导入)
- HTML5 + Bootstrap (Jinja2 模板前端)

---

## 📂 目录结构

```
├─app                     # 主应用包
│   ├─models              # 数据模型 (SQL 定义)
│   ├─routes              # 视图与 API 蓝图
│   ├─templates           # Jinja2 页面模板
│   ├─utils               # 通用帮助函数 / 装饰器 / 校验器
│   ├─config.py           # 多环境配置
│   ├─extensions.py       # 第三方扩展集中初始化
│   └─__init__.py         # 应用工厂 (create_app)
├─instance                # 模板文件 / SQLite 数据库等运行时文件
├─uploads                 # 用户上传(头像 / 题目图片 / 聊天图片)
├─static                  # 静态资源(与 uploads 分离)
├─scripts                 # 实用脚本，如生成 Excel 模板
├─run.py                  # 启动入口 (python run.py)
├─requirements.txt        # 依赖列表
└─README.md               # 项目说明
```

---

## 🚀 快速开始

1. 克隆项目并进入目录

   ```bash
   git clone <repo_url>
   cd ti
   ```

2. 创建虚拟环境并安装依赖

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 可选：配置环境变量（默认为开发模式）

   ```bash
   # Linux / macOS
   export FLASK_ENV=development
   export SECRET_KEY="change-me"
   # Windows (PowerShell)
   set FLASK_ENV=development
   set SECRET_KEY=change-me
   ```

4. 启动应用

   ```bash
   python run.py
   # 或者
   flask run --host 0.0.0.0 --port 5000
   ```

5. 打开浏览器访问 `http://localhost:5000`，注册首个账号 => 自动拥有管理员权限。

---

## 💬 站内聊天（新增）

### 入口
- 登录后：
  - 首页入口：`/` 页面中的“聊天”
  - 聊天主页面：`/chat`

### 主要能力
- 1v1 私聊会话（direct）
- 会话列表显示：对方头像/显示名（备注优先）、最后一条消息、未读数
- 消息类型：
  - 文本消息
  - 图片消息（列表优先显示缩略图，点击弹层查看大图）
  - 语音消息（按住说话，松开发送，上滑取消）
  - **题目卡片消息（题目转发）**

### 题目转发（题目卡片）
- 刷题页面（`/quiz`）：点击“转发题目”按钮 → 搜索选择用户 → 自动创建/复用会话并发送题目卡片。
- 聊天页面（`/chat`）：
  - 题目以卡片形式展示（默认隐藏题目 ID）
  - 点击卡片：弹层展示题目详情（不跳转页面）
    - 选择题/多选题：展示选项/答案/解析
    - 填空题：题干 `__` 以占位块展示，答案按“空1/空2…”结构化展示
  - 历史题目卡片：若消息体字段不全，前端会调用接口补全后再展示

### 后端关键路由（`app/routes/chat.py`）
- `GET  /chat`：聊天页面
- `GET  /api/chat/users?q=...`：搜索用户（排序：精确命中优先、前缀命中其次）
- `POST /api/chat/conversations/create`：创建/复用会话
- `GET  /api/chat/conversations`：会话列表（含未读数、最后消息摘要、对方备注 `peer_remark`）
- `GET  /api/chat/messages?conversation_id=...&after_id=...&limit=...`：增量拉取消息并推进已读
- `POST /api/chat/messages/send`：发送文本
- `POST /api/chat/messages/upload_image`：上传图片并发为消息（支持 `thumb` 缩略图）
- `POST /api/chat/messages/upload_audio`：上传语音并发为消息（支持 `duration` 秒）
- `POST /api/chat/messages/send_question`：发送题目卡片（参数：`conversation_id`,`question_id`）
- `GET  /api/chat/question/<question_id>`：获取题目完整信息（用于历史卡片补全）
- `GET  /api/chat/unread_count`：总未读数（首页角标）
- `GET/POST /api/chat/user_remark`：读取/设置备注（空字符串表示清除）
- `GET  /api/chat/user_profile?user_id=...`：好友资料（公开字段 + 我对TA的备注）

### 时间显示说明（重要）
- 数据库 `CURRENT_TIMESTAMP` 在 SQLite 中通常为 **UTC**。
- 前端消息时间已做兼容解析：将 `YYYY-MM-DD HH:mm:ss` 按 UTC 解析后再转为本地时间显示，避免出现与系统时间不一致的问题。

---

## ⚙️ 数据库初始化

应用启动时会自动检测并在 `instance/` 目录创建所需的 SQLite 数据库 (`submissions.db`, `quiz.db` 等)。

若需手动重置，可删除对应文件或在 Flask Shell 中运行：

```python
from app.utils.database import init_db
init_db()
```

---

## 👑 管理后台

- 登录后访问 `/admin` 即可进入后台仪表盘。
- 支持 **题库导入**：
  1. Excel 导入：下载模板 `题目示例`，填写后上传（支持选择题、多选题、判断题、填空题、问答题）；
  2. ZIP 题包：包含 `data.json` + `images/` 目录按规范打包；
  3. JSON 批量导入：支持标准的 JSON 格式批量导入题目（API：`POST /admin/questions/import`）。
- **题型说明**：
  - **选择题**：单选题，选择一个答案，选择后自动显示结果
  - **多选题**：多选题，选择多个答案（至少两个），需要点击"查看结果"按钮才能看到答案
  - **判断题**：正确/错误，选择后自动显示结果
  - **填空题**：支持多空，每空可接受多个答案（用分号分隔）
  - **问答题**：自由文本作答
- 批量操作与导出功能可极大提高题库维护效率。

### JSON 批量导入格式示例

```json
[
    {
        "题型": "选择题",
        "题干": "题干内容",
        "选项": ["A、内容", "B、内容", "C、内容", "D、内容"],
        "答案": "A",
        "解析": "内容"
    },
    {
        "题型": "多选题",
        "题干": "题干内容",
        "选项": ["A、内容", "B、内容", "C、内容", "D、内容"],
        "答案": "AB",
        "解析": "内容"
    },
    {
        "题型": "判断题",
        "题干": "题干内容",
        "答案": "正确",
        "解析": "内容"
    },
    {
        "题型": "填空题",
        "题干": "题干内容和{答案}",
        "解析": "内容"
    },
    {
        "题型": "问答题",
        "题干": "题干内容",
        "答案": "答案内容",
        "解析": "内容"
    }
]
```

**注意事项**：
- 多选题答案必须至少包含两个选项（如 "AB"、"ABC"）
- 多选题答案中的所有字母必须在选项范围内
- 填空题支持题干中用 `{答案}` 标记空位，系统会自动提取答案

---

## 🔐 配置

如需生产部署，可在 `app/config.py` 中自定义：

- `SECRET_KEY`        ‑ 加密会话，请更换为安全随机值
- `DATABASE_PATH`     ‑ 修改为其他数据库 URI
- `PERMANENT_SESSION_LIFETIME` ‑ **“保持登录”** 的有效期（默认 7 天）
- `RATELIMIT_*`       ‑ 速率限制策略
- `LOG_DIR`           ‑ 日志目录

### ✅ 记住密码 / 保持登录（新增）

- 登录页新增“记住密码 / 保持登录”勾选项。
- 勾选后后端会将 `session.permanent=True`，并使用 `PERMANENT_SESSION_LIFETIME` 控制会话 Cookie 过期时间；关闭浏览器后再次打开仍可保持登录状态。
- 不勾选则为临时会话（浏览器关闭后通常会失效）。

> 说明：出于安全考虑，本项目并**不会在前端或后端明文保存用户密码**；“记住密码”在本实现中等价于“记住登录状态”。

将环境变量 `FLASK_ENV` 设为 `production` 后，应用将使用 `ProductionConfig`，自动关闭 Debug 并使用更强的密钥。

---

## 🤝 贡献指南

欢迎提出 Issue 或 PR：

1. 请先在本地跑通测试，确保不破坏现有功能；
2. 遵循 PEP8 代码规范；
3. 提交前请注明变更动机与效果。

---

## 📄 License

MIT (c) 2025
