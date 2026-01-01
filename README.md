# 题库系统 (Quiz Bank System)

> 一个基于 **Flask 3** 的现代化、模块化在线刷题/考试/题库管理平台，支持多题型、多科目、用户权限管理、站内聊天、编程题练习等完整功能。

---

## 📋 目录

- [主要特性](#-主要特性)
- [技术栈](#️-技术栈)
- [项目架构](#-项目架构)
- [功能模块](#-功能模块)
- [快速开始](#-快速开始)
- [配置说明](#️-配置说明)
- [数据库设计](#-数据库设计)
- [API 文档](#-api-文档)
- [开发指南](#-开发指南)
- [部署说明](#-部署说明)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)

---

## ✨ 主要特性

### 🎯 核心功能

| 分类 | 功能 | 说明 |
| ---- | ---- | ---- |
| **用户认证** | 密码登录/验证码登录/退出 | 支持用户名或邮箱+密码登录；支持邮箱验证码免密登录；验证码登录时自动注册新用户 |
| **邮箱功能** | 邮箱绑定/验证码登录 | 绑定邮箱后可使用邮箱登录；验证码登录支持自动注册；未绑定邮箱用户需先绑定才能使用全部功能 |
| **首页** | 数据统计 | 题目总数、收藏/错题统计、最近活动等 |
| **题库搜索** | 多条件过滤 | 关键字 + 科目/题型筛选，支持分页展示 |
| **刷题模式** | 多种模式 | 普通刷题/背题模式；支持题目顺序、选项顺序随机打乱与进度保存 |
| **多题型支持** | 丰富题型 | 支持**选择题**（单选）、**多选题**、**判断题**、**填空题**（多空、每空多答案）、**问答题**等多种题型 |
| **收藏与错题** | 学习管理 | 一键加入收藏或错题本，随时复习 |
| **在线考试** | 自定义考试 | 自定义科目、时长、题型数量及分值；自动判分、成绩统计 |
| **历史记录** | 学习追踪 | 做题记录、考试记录、答题正确率统计 |
| **编程题** | 在线编程 | 支持在线代码编辑、执行、自动判题（Python） |
| **站内聊天** | 实时通信 | 1v1 私聊、图片/语音消息、题目转发、用户备注 |
| **通知系统** | 站内通知 | 通知公告发布、启用/禁用、优先级控制 |
| **收费功能** | 会员订阅/按量付费/题集购买 | 支持会员订阅制（管理员可自定义套餐）、按量付费、题集购买；支持微信支付、支付宝；后台可开启/关闭收费功能 |

### 🎨 用户界面

- **iOS 18 风格设计**：毛玻璃效果、圆角卡片、流畅动画
- **响应式布局**：完美适配桌面端和移动端
- **答案/解析外置 Dock**：桌面端对问答/计算题支持右侧 dock（更适合长答案/长解析）
- **填空题答案结构化展示**：dock 内按"空 1/空 2…"展示；支持"一空多答案/多空多答案"
- **快捷键支持**：刷题页面支持丰富的键盘快捷键操作

### 🔐 权限管理

- **管理员**：拥有所有权限，可管理所有功能模块
- **科目管理员**：可管理科目和题集，但无法访问用户管理、聊天管理等
- **普通用户**：只能使用前台功能（刷题、考试、收藏、错题本等）

### 💰 收费功能（可选）

- **会员订阅制**：支持管理员自定义会员套餐（名称、价格、权益、限制）
- **按量付费**：额外考试次数、编程题、数据导出等
- **题集购买**：单科目题集、专题题集、考试真题集、编程题集
- **支付方式**：微信支付、支付宝
- **灵活控制**：后台可开启/关闭收费功能，关闭时所有功能免费使用
- **会员折扣**：会员用户购买题集享受 8 折优惠

### 🛡️ 安全特性

- 密码哈希（Werkzeug）
- 会话版本控制
- 速率限制（Flask-Limiter）
- 用户锁定/解锁机制
- 强制下线功能
- 邮箱验证码登录（免密登录）
- 邮箱绑定验证（保障账户安全）
- 服务协议和隐私保护协议（用户同意机制）

---

## 🛠️ 技术栈

### 后端

- **Python 3.11+**
- **Flask 3.1.x**：Web 框架
- **Flask-Limiter**：API 速率限制
- **Pydantic 2.5.0**：数据验证和序列化
- **SQLite**：默认数据库（可替换为 MySQL/PostgreSQL）
- **Pandas / OpenPyXL**：Excel 导入导出
- **Werkzeug**：密码哈希、安全工具
- **SMTP 邮件服务**：验证码发送、邮件通知
- **Gunicorn**：生产环境 WSGI 服务器

### 前端

- **HTML5 + CSS3**：现代 Web 标准
- **JavaScript (ES6+)**：原生 JavaScript，无框架依赖
- **Bootstrap 5**：响应式 UI 框架
- **Monaco Editor**：代码编辑器（编程题模块）
- **Jinja2**：模板引擎

### 开发工具

- **类型提示**：Python 3.11+ 类型系统
- **日志系统**：滚动日志文件（`logs/app.log`）
- **模块化架构**：Flask Blueprints 组织代码

---

## 🏗️ 项目架构

### 模块化设计

项目采用**完全模块化**的架构设计，每个功能模块都是独立的、可插拔的组件。

```
Saksk_1_Ti/
├── app/                          # 主应用包
│   ├── __init__.py              # 应用工厂 (create_app)
│   ├── core/                    # 核心共享代码
│   │   ├── config.py           # 多环境配置
│   │   ├── extensions.py       # Flask 扩展初始化
│   │   ├── models/             # 数据模型（SQLAlchemy/SQLModel）
│   │   │   ├── user.py         # 用户模型
│   │   │   ├── question.py     # 题目模型
│   │   │   └── exam.py         # 考试模型
│   │   └── utils/              # 核心工具函数
│   │       ├── database.py     # 数据库操作
│   │       ├── decorators.py   # 装饰器（登录、权限检查）
│   │       ├── validators.py   # 数据验证
│   │       ├── options_parser.py    # 选项解析器
│   │       └── fill_blank_parser.py # 填空题解析器
│   │
│   └── modules/                  # 功能模块（核心）
│       ├── __init__.py         # 模块注册入口
│       │
│       ├── auth/               # 认证模块
│       │   ├── routes/         # 路由层
│       │   │   ├── pages.py   # 页面路由（登录/注册页）
│       │   │   └── api.py      # API 路由（登录/注册接口）
│       │   └── templates/      # 模板文件
│       │       └── auth/
│       │           └── login.html
│       │
│       ├── main/               # 主页模块
│       │   ├── routes/
│       │   │   └── pages.py   # 首页、搜索、关于、历史等
│       │   └── templates/
│       │       └── main/
│       │           ├── index.html
│       │           ├── search.html
│       │           ├── about.html
│       │           ├── history.html
│       │           └── ...
│       │
│       ├── quiz/               # 刷题模块
│       │   ├── routes/
│       │   │   ├── pages.py   # 刷题页面路由
│       │   │   └── api.py      # 刷题 API（进度、收藏、记录等）
│       │   └── templates/
│       │       └── quiz/
│       │           ├── quiz.html
│       │           └── partials/quiz/  # 部分模板
│       │               ├── _sidebar.html
│       │               ├── _question.html
│       │               └── ...
│       │
│       ├── exam/               # 考试模块
│       │   ├── routes/
│       │   │   ├── pages.py   # 考试列表/详情页
│       │   │   └── api.py      # 考试 API（创建、提交、判分等）
│       │   └── templates/
│       │       └── exam/
│       │           ├── exams.html
│       │           └── exam_detail.html
│       │
│       ├── user/               # 用户中心模块
│       │   ├── routes/
│       │   │   ├── pages.py   # 用户中心页面
│       │   │   └── api.py      # 用户信息 API
│       │   └── templates/
│       │       └── user/
│       │           ├── user_hub.html
│       │           └── user_profile.html
│       │
│       ├── chat/               # 聊天模块
│       │   ├── routes/
│       │   │   ├── pages.py   # 聊天页面
│       │   │   └── api.py      # 聊天 API（消息、会话、用户搜索等）
│       │   └── templates/
│       │       └── chat/
│       │           └── chat.html
│       │
│       ├── notifications/      # 通知模块
│       │   ├── routes/
│       │   │   ├── pages.py   # 通知列表页
│       │   │   └── api.py      # 通知 API
│       │   └── templates/
│       │       └── notifications/
│       │           └── notifications.html
│       │
│       ├── coding/             # 编程题模块
│       │   ├── routes/
│       │   │   ├── pages.py   # 编程题列表/详情页
│       │   │   └── api.py      # 编程题 API（执行、提交、判题等）
│       │   ├── services/       # 服务层
│       │   │   └── code_executor.py  # 代码执行服务
│       │   └── templates/
│       │       └── coding/
│       │           └── index.html
│       │
│       └── admin/              # 管理后台模块
│           ├── routes/
│           │   ├── pages.py    # 管理后台页面路由
│           │   ├── api.py      # 管理后台 API（新版）
│           │   └── api_legacy.py  # 向后兼容的旧 API 路径
│           └── templates/
│               └── admin/
│                   ├── admin_base.html
│                   ├── admin_dashboard.html
│                   ├── admin_subjects.html
│                   ├── admin_questions.html
│                   ├── admin_users.html
│                   └── ...
│       └── payment/            # 支付模块（可选）
│           ├── routes/
│           │   ├── pages.py    # 支付页面路由
│           │   └── api.py      # 支付 API
│           └── templates/
│               └── payment/
│                   ├── membership.html
│                   ├── question_sets.html
│                   └── ...
│
├── instance/                   # 运行时文件
│   ├── submissions.db         # 主数据库（用户、题目、考试等）
│   ├── quiz.db                # 刷题进度数据库（可选）
│   └── question_import_template.xlsx  # Excel 导入模板
│
├── uploads/                    # 用户上传文件
│   ├── avatars/               # 用户头像
│   ├── question_images/       # 题目图片
│   └── chat/                  # 聊天图片/语音
│
├── static/                     # 静态资源
│   └── icons/                 # 图标文件
│
├── logs/                       # 日志文件
│   └── app.log                # 应用日志（滚动）
│
├── scripts/                    # 实用脚本
│   ├── generate_template.py   # 生成 Excel 模板
│   └── test_code_execution.py # 测试代码执行
│
├── run.py                      # 应用启动入口
├── requirements.txt            # Python 依赖列表
└── README.md                   # 项目说明文档
```

### 模块注册机制

所有模块通过 `app/modules/__init__.py` 统一注册：

```python
def register_all_modules(app: Flask):
    """注册所有功能模块"""
    from .auth import init_auth_module
    from .main import init_main_module
    from .quiz import init_quiz_module
    from .exam import init_exam_module
    from .user import init_user_module
    from .chat import init_chat_module
    from .notifications import init_notifications_module
    from .coding import init_coding_module
    from .admin import init_admin_module
    
    init_auth_module(app)
    init_main_module(app)
    init_main_module(app)
    # ... 其他模块
```

每个模块的 `__init__.py` 负责：
1. 创建模块蓝图（Blueprint）
2. 注册子蓝图（页面路由、API 路由）
3. 配置模板文件夹
4. 注册到 Flask 应用

---

## 📦 功能模块

### 1. 认证模块 (`auth`)

**功能**：
- 密码登录/验证码登录/退出
- 邮箱绑定与验证
- 会话管理（临时会话/永久会话）
- 密码哈希与验证
- 会话版本控制（强制下线）
- 服务协议和隐私保护协议

**路由**：
- `GET /login`：登录页面（支持密码登录和验证码登录）
- `POST /api/login`：密码登录接口（支持用户名或邮箱）
- `POST /api/email/send-login-code`：发送登录验证码
- `POST /api/email/login`：验证码登录接口（自动注册）
- `POST /api/email/send-bind-code`：发送绑定验证码
- `POST /api/email/bind`：绑定邮箱接口
- `GET /api/logout`：退出登录
- `GET /terms`：服务协议页面
- `GET /privacy`：隐私保护协议页面

**特性**：
- **验证码登录自动注册**：使用验证码登录时，如果邮箱未注册，系统会自动创建账户
- **邮箱绑定强制**：未绑定邮箱的用户登录后需先绑定邮箱才能使用全部功能
- **双登录方式**：支持密码登录和验证码登录两种方式
- **协议同意机制**：登录前需同意服务协议和隐私保护协议
- 支持"记住密码"（保持登录状态 7 天）
- 会话失效检测与自动重定向

---

### 2. 主页模块 (`main`)

**功能**：
- 首页数据统计
- 题库搜索
- 关于页面
- 联系管理员
- 用户历史记录

**路由**：
- `GET /`：首页
- `GET /search`：搜索页面
- `GET /about`：关于页面
- `GET /history`：历史记录
- `GET /contact_admin`：联系管理员

**API**：
- `GET /api/questions/count`：获取题目统计（支持模式：all/favorites/mistakes）

---

### 3. 刷题模块 (`quiz`)

**功能**：
- 多种刷题模式（普通刷题/背题）
- 题目顺序/选项顺序随机打乱
- 进度保存与恢复
- 收藏/错题本
- 题目转发到聊天

**路由**：
- `GET /quiz`：刷题页面
  - 参数：`mode`（quiz/memo/favorites/mistakes/exam）
  - 参数：`subject`（科目筛选）
  - 参数：`exam_id`（考试模式）

**API**：
- `GET /api/quiz/progress`：获取刷题进度
- `POST /api/quiz/progress`：保存刷题进度
- `POST /api/favorite`：收藏/取消收藏题目
- `POST /api/record_result`：记录答题结果
- `GET /api/questions/<id>`：获取题目详情

**UI 特性**：
- 答案/解析外置 Dock（桌面端）
- 填空题答案结构化展示
- 快捷键支持（见 `quiz/templates/quiz/partials/quiz/HOTKEYS_GUIDE.md`）

---

### 4. 考试模块 (`exam`)

**功能**：
- 自定义考试（科目、时长、题型、分值）
- 自动判分
- 成绩统计与回顾
- 错题加入错题本

**路由**：
- `GET /exams`：考试列表页
- `GET /exams/<exam_id>`：考试详情页（成绩）
- `GET /quiz?mode=exam&exam_id=<id>`：考试作答页

**API**：
- `POST /api/exams/create`：创建考试
- `POST /api/exams/submit`：提交考试
- `POST /api/exams/save_draft`：保存草稿
- `DELETE /api/exams/<exam_id>`：删除考试
- `POST /api/exams/<exam_id>/mistakes`：错题加入错题本

**判分规则**：
- 选择题/多选题：答案排序后比较
- 判断题：字符串相等
- 填空题：多空、每空多答案支持
- 问答题：手动判分（管理员）

---

### 5. 用户中心模块 (`user`)

**功能**：
- 用户资料查看/编辑
- 个人中心首页
- 学习统计

**路由**：
- `GET /user/hub`：用户中心首页
- `GET /user/profile`：用户资料页
- `GET /profile`：个人资料页（别名）

**API**：
- `GET /api/user/profile`：获取用户资料
- `POST /api/user/profile`：更新用户资料

---

### 6. 聊天模块 (`chat`)

**功能**：
- 1v1 私聊会话
- 文本/图片/语音消息
- 题目转发（题目卡片）
- 用户备注
- 好友资料页

**路由**：
- `GET /chat`：聊天主页面

**API**：
- `GET /api/chat/users?q=...`：搜索用户
- `POST /api/chat/conversations/create`：创建/复用会话
- `GET /api/chat/conversations`：会话列表
- `GET /api/chat/messages?conversation_id=...&after_id=...&limit=...`：增量拉取消息
- `POST /api/chat/messages/send`：发送文本
- `POST /api/chat/messages/upload_image`：上传图片消息
- `POST /api/chat/messages/upload_audio`：上传语音消息
- `POST /api/chat/messages/send_question`：发送题目卡片
- `GET /api/chat/question/<question_id>`：获取题目完整信息
- `GET /api/chat/unread_count`：总未读数
- `GET/POST /api/chat/user_remark`：读取/设置备注
- `GET /api/chat/user_profile?user_id=...`：好友资料

**特性**：
- 会话去重（`direct_pair_key` + 唯一索引）
- 图片缩略图支持
- 语音消息时长显示
- 题目卡片展示（点击弹层查看详情）
- 时间显示兼容（UTC → 本地时间）

---

### 7. 通知模块 (`notifications`)

**功能**：
- 站内通知发布
- 通知列表查看
- 通知启用/禁用
- 优先级控制

**路由**：
- `GET /notifications`：通知列表页

**API**：
- `GET /api/notifications`：获取通知列表
- `POST /api/notifications`：创建通知（管理员）
- `PUT /api/notifications/<id>`：更新通知
- `DELETE /api/notifications/<id>`：删除通知

---

### 8. 编程题模块 (`coding`)

**功能**：
- 编程题目浏览与筛选
- 在线代码编辑（Monaco Editor）
- 代码执行与自动判题
- 提交历史与统计

**路由**：
- `GET /coding`：编程题列表页
- `GET /coding/<question_id>`：编程题详情页

**API**：
- `GET /coding/api/questions`：获取题目列表
- `GET /coding/api/questions/<id>`：获取题目详情
- `POST /coding/api/execute`：运行代码（不判题）
- `POST /coding/api/submit`：提交代码（自动判题）
- `GET /coding/api/submissions`：获取提交历史

**技术**：
- Monaco Editor 集成
- Python subprocess 执行代码（开发环境）
- Docker 容器隔离（生产环境，待实现）
- 测试用例验证

---

### 9. 管理后台模块 (`admin`)

**功能**：
- 仪表盘（数据统计）
- 科目管理（增删改查）
- 题库管理（单题/批量操作）
- 用户管理（权限、锁定、重置密码）
- 聊天管理
- 通知管理
- 编程题管理

**路由**：
- `GET /admin`：管理后台首页（仪表盘/科目管理）
- `GET /admin/subjects`：科目管理
- `GET /admin/questions`：题库管理
- `GET /admin/users`：用户管理
- `GET /admin/chat`：聊天管理
- `GET /admin/notifications`：通知管理
- `GET /admin/coding`：编程题管理

**API**：
- 新版 API：`/admin/api/*`（RESTful 风格）
- 旧版 API：`/admin/*`（向后兼容，见 `api_legacy.py`）

**权限控制**：
- 管理员：所有功能
- 科目管理员：科目管理、题集管理、Excel 模板下载、题目导入/导出

**批量操作**：
- Excel 导入/导出
- ZIP 题包导入/导出（含图片资源）
- JSON 格式批量导入
- 批量移动科目、改题型、设难度、标签

**收费管理**（可选）：
- 收费功能开关控制
- 会员套餐管理（创建/编辑/删除套餐，自定义价格、权益、限制）
- 支付订单管理
- 收入统计

---

### 10. 收费/支付模块 (`payment`)（可选）

**功能**：
- 会员订阅管理（基础会员、高级会员等，管理员可自定义套餐）
- 按量付费（额外考试次数、编程题、数据导出）
- 题集购买（单科目题集、专题题集、考试真题集、编程题集）
- 支付集成（微信支付、支付宝）
- 系统配置管理（开启/关闭收费功能）

**路由**：
- `GET /membership`：会员购买页面
- `GET /question-sets`：题集商城页面
- `GET /question-sets/<set_id>`：题集详情页
- `GET /user/question-sets`：我的题集页面
- `GET /admin/settings/payment`：收费功能配置页面
- `GET /admin/membership-plans`：会员套餐管理页面

**API**：
- `GET /api/membership-plans`：获取会员套餐列表
- `POST /api/payment/create`：创建支付订单
- `POST /api/payment/callback/alipay`：支付宝回调
- `POST /api/payment/callback/wechat`：微信支付回调
- `GET /api/payment/status`：查询支付状态
- `GET /api/question-sets`：获取题集列表
- `POST /api/question-sets/<set_id>/purchase`：购买题集
- `GET /api/user/subscription`：获取用户订阅信息
- `GET /admin/api/settings/payment`：获取收费配置
- `POST /admin/api/settings/payment`：更新收费配置
- `GET /admin/api/membership-plans`：获取套餐列表（管理员）
- `POST /admin/api/membership-plans`：创建套餐（管理员）
- `PUT /admin/api/membership-plans/<plan_id>`：更新套餐（管理员）

**特性**：
- **灵活控制**：后台可开启/关闭收费功能，关闭时所有功能免费使用
- **自定义套餐**：管理员可创建、编辑会员套餐，自定义名称、价格、权益、使用限制
- **会员折扣**：会员用户购买题集享受 8 折优惠
- **使用限制**：支持每日/每月使用次数限制（可配置）
- **支付安全**：支付回调签名验证，订单状态同步

---

## 🚀 快速开始

### 环境要求

- Python 3.11 或更高版本
- pip（Python 包管理器）

### 安装步骤

1. **克隆项目并进入目录**

   ```bash
   git clone <repo_url>
   cd Saksk_1_Ti
   ```

2. **创建虚拟环境**

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **安装依赖**

   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量（可选）**

   ```bash
   # Windows (PowerShell)
   $env:FLASK_ENV="development"
   $env:SECRET_KEY="your-secret-key-here"

   # Linux / macOS
   export FLASK_ENV=development
   export SECRET_KEY=your-secret-key-here
   ```

5. **启动应用**

   ```bash
   python run.py
   ```

   或者使用 Flask CLI：

   ```bash
   flask run --host 0.0.0.0 --port 5000
   ```

6. **访问应用**

   打开浏览器访问 `http://localhost:5000`

   - 首次注册的用户自动成为管理员
   - 登录后即可使用所有功能

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
| ------ | ---- | ------ |
| `FLASK_ENV` | 运行环境（development/production/testing） | `production` |
| `SECRET_KEY` | Flask 会话密钥（生产环境必须设置） | `dev-secret-key-change-in-production` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `5000` |
| `MAIL_SERVER` | SMTP 服务器地址 | `smtp.example.com` |
| `MAIL_PORT` | SMTP 端口 | `587` |
| `MAIL_USE_TLS` | 是否使用 TLS | `true` |
| `MAIL_USERNAME` | 邮箱用户名 | - |
| `MAIL_PASSWORD` | 邮箱授权码 | - |
| `MAIL_DEFAULT_SENDER` | 默认发件人 | - |
| `MAIL_DEFAULT_SENDER_NAME` | 默认发件人名称 | `系统通知` |
| `MAIL_ENABLED` | 是否启用邮件服务 | `true` |
| `RATELIMIT_STORAGE_URL` | 限流存储（生产环境建议使用 Redis） | `memory://` |
| `ALIPAY_APP_ID` | 支付宝应用ID（收费功能） | - |
| `ALIPAY_PRIVATE_KEY` | 支付宝私钥（收费功能） | - |
| `ALIPAY_PUBLIC_KEY` | 支付宝公钥（收费功能） | - |
| `WECHAT_APP_ID` | 微信支付应用ID（收费功能） | - |
| `WECHAT_MCH_ID` | 微信支付商户号（收费功能） | - |
| `WECHAT_API_KEY` | 微信支付API密钥（收费功能） | - |

### 配置文件

主要配置在 `app/core/config.py` 中：

```python
class Config:
    # 数据库路径
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'submissions.db')
    
    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 天
    
    # 限流配置
    RATELIMIT_DEFAULT = "10000 per day;1000 per hour"
```

### 生产环境配置

将 `FLASK_ENV` 设为 `production` 后，应用将使用 `ProductionConfig`：
- 关闭 Debug 模式
- 使用更强的密钥（**必须**设置 `SECRET_KEY` 环境变量）
- 启用日志记录
- 禁用控制台输出验证码（仅发送真实邮件）

**详细部署说明**：请参考 `生产环境部署指南.md` 和 `快速部署说明.md`

---

## 🗄️ 数据库设计

### 主要数据表

#### 1. `users` 表

用户信息表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `username` | TEXT | 用户名（唯一） |
| `password_hash` | TEXT | 密码哈希 |
| `email` | TEXT | 邮箱地址（唯一，可为空） |
| `email_verified` | INTEGER | 邮箱是否已验证（0/1） |
| `email_verified_at` | DATETIME | 邮箱验证时间 |
| `is_admin` | INTEGER | 是否管理员（0/1） |
| `is_subject_admin` | INTEGER | 是否科目管理员（0/1） |
| `is_locked` | INTEGER | 是否锁定（0/1） |
| `session_version` | INTEGER | 会话版本（用于强制下线） |
| `created_at` | DATETIME | 创建时间 |
| `last_active` | DATETIME | 最后活动时间 |

#### 2. `subjects` 表

科目表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `name` | TEXT | 科目名称 |
| `description` | TEXT | 科目描述 |
| `created_at` | DATETIME | 创建时间 |

#### 3. `questions` 表

题目表（支持所有题型）。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `q_type` | TEXT | 题型（选择题/多选题/判断题/填空题/问答题/编程题） |
| `subject_id` | INTEGER | 科目ID |
| `title` | TEXT | 题目标题 |
| `content` | TEXT | 题目内容 |
| `options` | TEXT | 选项（JSON 格式，选择题/多选题） |
| `answer` | TEXT | 答案 |
| `explanation` | TEXT | 解析 |
| `difficulty` | TEXT | 难度（easy/medium/hard，编程题） |
| `code_template` | TEXT | 代码模板（编程题） |
| `test_cases_json` | TEXT | 测试用例（JSON 格式，编程题） |
| `created_at` | DATETIME | 创建时间 |

#### 4. `exam_sessions` 表

考试会话表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `user_id` | INTEGER | 用户ID |
| `subject_id` | INTEGER | 科目ID |
| `duration` | INTEGER | 考试时长（分钟） |
| `started_at` | DATETIME | 开始时间 |
| `submitted_at` | DATETIME | 提交时间 |
| `total_score` | REAL | 总分 |
| `score` | REAL | 得分 |

#### 5. `exam_answers` 表

考试答案表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `exam_id` | INTEGER | 考试ID |
| `question_id` | INTEGER | 题目ID |
| `user_answer` | TEXT | 用户答案 |
| `is_correct` | INTEGER | 是否正确（0/1） |
| `score` | REAL | 得分 |
| `answered_at` | DATETIME | 答题时间 |

#### 6. `code_submissions` 表

编程题提交记录表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `user_id` | INTEGER | 用户ID |
| `question_id` | INTEGER | 题目ID |
| `code` | TEXT | 提交的代码 |
| `language` | TEXT | 编程语言 |
| `status` | TEXT | 提交状态（accepted/wrong_answer/time_limit_exceeded/...） |
| `passed_cases` | INTEGER | 通过的测试用例数 |
| `total_cases` | INTEGER | 总测试用例数 |
| `execution_time` | REAL | 执行时间（秒） |
| `submitted_at` | DATETIME | 提交时间 |

#### 7. `chat_conversations` 表

聊天会话表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `direct_pair_key` | TEXT | 会话唯一键（user1_id_user2_id，排序后） |
| `user1_id` | INTEGER | 用户1 ID |
| `user2_id` | INTEGER | 用户2 ID |
| `created_at` | DATETIME | 创建时间 |

#### 8. `chat_messages` 表

聊天消息表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `conversation_id` | INTEGER | 会话ID |
| `sender_id` | INTEGER | 发送者ID |
| `message_type` | TEXT | 消息类型（text/image/audio/question） |
| `content` | TEXT | 消息内容（文本/JSON） |
| `created_at` | DATETIME | 创建时间 |

#### 9. `system_config` 表（收费功能）

系统配置表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `config_key` | TEXT | 配置键（唯一） |
| `config_value` | TEXT | 配置值 |
| `config_type` | TEXT | 配置类型（string/boolean/number/json） |
| `description` | TEXT | 配置描述 |
| `updated_by` | INTEGER | 最后更新人（管理员ID） |
| `updated_at` | DATETIME | 更新时间 |

#### 10. `membership_plans` 表（收费功能）

会员套餐表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `name` | TEXT | 套餐名称 |
| `plan_code` | TEXT | 套餐代码（唯一） |
| `description` | TEXT | 套餐描述 |
| `monthly_price` | DECIMAL(10,2) | 月付价格 |
| `yearly_price` | DECIMAL(10,2) | 年付价格 |
| `features_json` | TEXT | 功能权益（JSON格式） |
| `limits_json` | TEXT | 使用限制（JSON格式） |
| `sort_order` | INTEGER | 排序 |
| `is_active` | BOOLEAN | 是否启用 |
| `is_default` | BOOLEAN | 是否为默认套餐 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

#### 11. `subscriptions` 表（收费功能）

会员订阅表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `user_id` | INTEGER | 用户ID |
| `plan_id` | INTEGER | 套餐ID |
| `plan_code` | TEXT | 套餐代码 |
| `status` | TEXT | 状态（active/expired/cancelled） |
| `start_date` | DATETIME | 开始时间 |
| `end_date` | DATETIME | 结束时间 |
| `auto_renew` | BOOLEAN | 是否自动续费 |
| `payment_method` | TEXT | 支付方式（alipay/wechat） |
| `payment_id` | TEXT | 支付订单ID |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

#### 12. `payment_orders` 表（收费功能）

支付订单表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `user_id` | INTEGER | 用户ID |
| `order_no` | TEXT | 订单号（唯一） |
| `order_type` | TEXT | 订单类型（subscription/addon/question_set） |
| `plan_type` | TEXT | 会员类型或购买类型 |
| `amount` | DECIMAL(10,2) | 订单金额 |
| `currency` | TEXT | 货币（默认CNY） |
| `payment_method` | TEXT | 支付方式（alipay/wechat） |
| `payment_id` | TEXT | 支付订单ID |
| `status` | TEXT | 订单状态（pending/paid/failed/refunded） |
| `paid_at` | DATETIME | 支付时间 |
| `created_at` | DATETIME | 创建时间 |

#### 13. `question_sets` 表（收费功能）

题集表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `name` | TEXT | 题集名称 |
| `description` | TEXT | 题集描述 |
| `set_type` | TEXT | 题集类型（subject/topic/exam_paper/coding） |
| `subject_id` | INTEGER | 科目ID（单科目题集） |
| `price` | DECIMAL(10,2) | 价格 |
| `original_price` | DECIMAL(10,2) | 原价（用于显示折扣） |
| `is_free` | BOOLEAN | 是否免费 |
| `question_count` | INTEGER | 题目数量 |
| `cover_image` | TEXT | 封面图片 |
| `sort_order` | INTEGER | 排序 |
| `status` | TEXT | 状态（active/inactive） |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

#### 14. `user_question_sets` 表（收费功能）

用户题集购买记录表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `user_id` | INTEGER | 用户ID |
| `set_id` | INTEGER | 题集ID |
| `purchase_price` | DECIMAL(10,2) | 购买价格 |
| `discount_amount` | DECIMAL(10,2) | 折扣金额 |
| `order_id` | INTEGER | 订单ID |
| `purchased_at` | DATETIME | 购买时间 |

#### 15. `usage_records` 表（收费功能）

用户使用记录表。

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | INTEGER | 主键 |
| `user_id` | INTEGER | 用户ID |
| `feature_type` | TEXT | 功能类型（quiz/exam/coding/chat/export） |
| `count` | INTEGER | 使用次数 |
| `date` | DATE | 日期 |
| `created_at` | DATETIME | 创建时间 |

### 数据库初始化

应用启动时会自动检测并创建所需的数据库表。若需手动重置：

```python
from app.core.utils.database import init_db
init_db()
```

---

## 📡 API 文档

### 通用响应格式

**成功响应**：
```json
{
  "status": "success",
  "data": { ... }
}
```

**错误响应**：
```json
{
  "status": "error",
  "message": "错误信息"
}
```

### 认证 API

#### 密码登录
```
POST /api/login
Content-Type: application/json

{
  "username": "user123",  // 支持用户名或邮箱
  "password": "password123",
  "remember_me": true
}

Response: 200 OK
{
  "status": "success",
  "message": "登录成功"
}
```

#### 发送登录验证码
```
POST /api/email/send-login-code
Content-Type: application/json

{
  "email": "user@example.com"
}

Response: 200 OK
{
  "status": "success",
  "message": "验证码已发送，请查收邮件"
}
```

#### 验证码登录（自动注册）
```
POST /api/email/login
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456"
}

Response: 200 OK
{
  "status": "success",
  "message": "登录成功",
  "data": {
    "auto_registered": true  // 如果是新用户自动注册
  }
}
```

#### 绑定邮箱
```
POST /api/email/bind
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "123456"
}

Response: 200 OK
{
  "status": "success",
  "message": "邮箱绑定成功"
}
```

### 刷题 API

#### 获取题目详情
```
GET /api/questions/<question_id>

Response: 200 OK
{
  "status": "success",
  "data": {
    "id": 1,
    "q_type": "选择题",
    "title": "题目标题",
    "content": "题目内容",
    "options": ["A、选项1", "B、选项2", ...],
    "answer": "A",
    "explanation": "解析内容"
  }
}
```

#### 记录答题结果
```
POST /api/record_result
Content-Type: application/json

{
  "question_id": 1,
  "user_answer": "A",
  "is_correct": true
}

Response: 200 OK
{
  "status": "success"
}
```

### 考试 API

#### 创建考试
```
POST /api/exams/create
Content-Type: application/json

{
  "subject": "数学",
  "duration": 60,
  "types": {
    "选择题": 10,
    "判断题": 5
  },
  "scores": {
    "选择题": 2,
    "判断题": 1
  }
}

Response: 200 OK
{
  "status": "success",
  "exam_id": 123
}
```

#### 提交考试
```
POST /api/exams/submit
Content-Type: application/json

{
  "exam_id": 123,
  "answers": [
    {"question_id": 1, "user_answer": "A"},
    {"question_id": 2, "user_answer": "B"}
  ]
}

Response: 200 OK
{
  "status": "success",
  "exam_id": 123,
  "total": 15,
  "correct": 12,
  "total_score": 30,
  "score": 24
}
```

### 聊天 API

#### 获取会话列表
```
GET /api/chat/conversations

Response: 200 OK
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "peer_id": 2,
      "peer_username": "user2",
      "peer_remark": "备注名",
      "last_message": "最后一条消息",
      "unread_count": 5,
      "updated_at": "2025-01-29 10:30:00"
    }
  ]
}
```

#### 发送消息
```
POST /api/chat/messages/send
Content-Type: application/json

{
  "conversation_id": 1,
  "content": "消息内容"
}

Response: 200 OK
{
  "status": "success",
  "message_id": 456
}
```

### 管理后台 API

#### 获取题目列表（管理员）
```
GET /admin/api/questions?page=1&per_page=20&subject_id=1

Response: 200 OK
{
  "status": "success",
  "data": {
    "questions": [...],
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

#### 导入题目
```
POST /admin/questions/import
Content-Type: multipart/form-data

file: <Excel文件或JSON文件>

Response: 200 OK
{
  "status": "success",
  "message": "成功导入 50 道题目"
}
```

### 收费/支付 API（可选）

#### 获取会员套餐列表
```
GET /api/membership-plans

Response: 200 OK
{
  "status": "success",
  "data": {
    "plans": [
      {
        "id": 1,
        "name": "基础会员",
        "plan_code": "basic",
        "monthly_price": 29.00,
        "yearly_price": 299.00,
        "features": {...},
        "limits": {...}
      }
    ]
  }
}
```

#### 创建支付订单
```
POST /api/payment/create
Content-Type: application/json

{
  "order_type": "subscription",
  "plan_type": "basic",
  "amount": 29.00,
  "payment_method": "alipay"
}

Response: 200 OK
{
  "status": "success",
  "data": {
    "order_no": "202501291234567890",
    "payment_url": "https://...",
    "expires_at": "2025-01-29 12:00:00"
  }
}
```

#### 查询支付状态
```
GET /api/payment/status?order_no=xxx

Response: 200 OK
{
  "status": "success",
  "data": {
    "order_no": "202501291234567890",
    "status": "paid",
    "paid_at": "2025-01-29 10:30:00"
  }
}
```

#### 获取题集列表
```
GET /api/question-sets?type=subject

Response: 200 OK
{
  "status": "success",
  "data": {
    "sets": [
      {
        "id": 1,
        "name": "数学基础题集",
        "price": 29.90,
        "member_price": 23.90,
        "question_count": 150,
        "is_purchased": false
      }
    ]
  }
}
```

#### 购买题集
```
POST /api/question-sets/<set_id>/purchase
Content-Type: application/json

{
  "payment_method": "alipay"
}

Response: 200 OK
{
  "status": "success",
  "data": {
    "order_no": "202501291234567890",
    "payment_url": "https://...",
    "amount": 23.90
  }
}
```

#### 获取用户订阅信息
```
GET /api/user/subscription

Response: 200 OK
{
  "status": "success",
  "data": {
    "plan_code": "basic",
    "plan_name": "基础会员",
    "end_date": "2025-02-29 10:00:00",
    "auto_renew": true
  }
}
```

---

## 💻 开发指南

### 代码规范

1. **遵循 PEP 8**：Python 代码风格指南
2. **使用类型提示**：所有函数、方法、变量都应使用类型提示
3. **模块化设计**：每个功能模块独立，不相互依赖（除核心工具）
4. **错误处理**：使用统一的错误响应格式

### 添加新模块

1. **创建模块目录结构**：
   ```
   app/modules/new_module/
   ├── __init__.py
   ├── routes/
   │   ├── __init__.py
   │   ├── pages.py
   │   └── api.py
   └── templates/
       └── new_module/
   ```

2. **实现模块初始化**（`__init__.py`）：
   ```python
   def init_new_module(app: Flask):
       from .routes.pages import new_module_pages_bp
       from .routes.api import new_module_api_bp
       
       module_dir = os.path.dirname(os.path.abspath(__file__))
       template_dir = os.path.join(module_dir, 'templates')
       
       new_module_bp = Blueprint('new_module', __name__, template_folder=template_dir)
       new_module_bp.register_blueprint(new_module_pages_bp)
       new_module_bp.register_blueprint(new_module_api_bp, url_prefix='/api')
       app.register_blueprint(new_module_bp)
   ```

3. **注册模块**（`app/modules/__init__.py`）：
   ```python
   from .new_module import init_new_module
   init_new_module(app)
   ```

### 数据库操作

使用 `app/core/utils/database.py` 中的 `get_db()` 函数：

```python
from app.core.utils.database import get_db

def some_function():
    conn = get_db()
    cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    # 使用 row['column_name'] 访问字段
    conn.commit()
```

### 权限装饰器

使用 `app/core/utils/decorators.py` 中的装饰器：

```python
from app.core.utils.decorators import login_required, admin_required

@login_required
def user_function():
    # 需要登录
    pass

@admin_required
def admin_function():
    # 需要管理员权限
    pass
```

### 模板路径

在模块的模板中：
- 使用 `render_template('module_name/template.html', ...)` 渲染模板
- 使用 `{% extends "module_name/base.html" %}` 继承模板
- 使用 `{% include "module_name/partials/_file.html" %}` 包含部分模板

### URL 生成

使用 `url_for` 时，端点名称格式为：`模块名.蓝图名.函数名`

```python
# 例如：main 模块的 pages 蓝图中的 index 函数
url_for('main.main_pages.index')

# API 端点
url_for('main.main_api.some_api')
```

---

## 🚢 部署说明

### 生产环境部署

**快速部署**：请参考 `快速部署说明.md`

**详细部署指南**：请参考 `生产环境部署指南.md`

#### 基本步骤

1. **设置环境变量**：
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY="your-strong-secret-key-here"
   # 生成密钥: python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **配置邮件服务**（必需）：
   ```bash
   export MAIL_SERVER=smtp.qq.com
   export MAIL_PORT=587
   export MAIL_USE_TLS=true
   export MAIL_USERNAME=your_email@qq.com
   export MAIL_PASSWORD=your_authorization_code
   export MAIL_DEFAULT_SENDER=your_email@qq.com
   export MAIL_DEFAULT_SENDER_NAME=系统通知
   ```

3. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

4. **使用 Gunicorn 启动**（推荐）：
   ```bash
   # 使用配置文件
   gunicorn -c gunicorn_config.py run:app
   
   # 或直接启动
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   ```

5. **使用启动脚本**：
   ```bash
   # Linux/Mac
   chmod +x start_production.sh
   ./start_production.sh
   
   # Windows
   start_production.bat
   ```

6. **使用 Nginx 作为反向代理**（可选）：
   参考 `生产环境部署指南.md` 中的 Nginx 配置示例

7. **配置 HTTPS**（推荐）：
   使用 Let's Encrypt 配置 SSL 证书

#### 重要提示

- ⚠️ **必须设置 SECRET_KEY**：生产环境必须设置强随机密钥
- ⚠️ **必须配置邮件服务**：邮箱功能需要正确的 SMTP 配置
- ✅ **使用 Gunicorn**：生产环境建议使用 Gunicorn 而不是 Flask 内置服务器
- ✅ **定期备份**：定期备份 `instance/submissions.db` 数据库文件
- ✅ **监控日志**：检查 `logs/app.log` 和 `logs/error.log`

### Docker 部署（待实现）

未来版本将支持 Docker 容器化部署，包括：
- 应用容器
- 数据库容器（可选）
- Nginx 反向代理容器

---

## ❓ 常见问题

### Q: 如何注册新账户？

A: 系统已移除传统注册功能。新用户可以通过**验证码登录**自动注册：使用邮箱验证码登录时，如果该邮箱未绑定任何账户，系统会自动创建新账户并绑定该邮箱。

### Q: 首次注册后如何成为管理员？

A: 系统会自动检测：如果数据库中没有任何用户，第一个通过验证码登录自动注册的用户会自动获得管理员权限。

### Q: 如何重置数据库？

A: 删除 `instance/submissions.db` 文件，重启应用即可自动重新创建。

### Q: 如何修改会话过期时间？

A: 在 `app/core/config.py` 中修改 `PERMANENT_SESSION_LIFETIME` 的值（单位：秒）。

### Q: 如何添加新的题型？

A: 在 `app/core/utils/` 中添加对应的解析器，并在题目导入/导出逻辑中支持新题型。

### Q: 编程题模块支持哪些语言？

A: 目前仅支持 Python。未来版本将支持 Java、C++ 等。

### Q: 聊天消息的时间显示不正确？

A: 数据库使用 UTC 时间，前端会自动转换为本地时间。如果仍有问题，请检查浏览器时区设置。

### Q: 如何配置邮件服务？

A: 设置以下环境变量：
- `MAIL_SERVER`：SMTP 服务器地址（如 smtp.qq.com）
- `MAIL_PORT`：SMTP 端口（通常为 587）
- `MAIL_USERNAME`：邮箱地址
- `MAIL_PASSWORD`：邮箱授权码（不是登录密码）
- `MAIL_DEFAULT_SENDER`：默认发件人地址

详细配置请参考 `邮箱配置示例.env` 文件。

### Q: 未绑定邮箱的用户可以使用哪些功能？

A: 未绑定邮箱的用户登录后，系统会弹出绑定提示，并限制访问大部分功能。用户必须先绑定邮箱才能正常使用系统。允许访问的路径包括：首页、邮箱绑定相关 API、登出功能、服务协议和隐私保护协议页面。

### Q: 验证码有效期是多久？

A: 邮箱验证码有效期为 10 分钟，过期后需要重新发送。

### Q: 如何开启收费功能？

A: 登录管理后台，进入"收费设置"页面，开启收费功能开关。开启后，系统将启用所有收费逻辑；关闭时，所有功能免费使用。

### Q: 如何自定义会员套餐？

A: 在管理后台的"会员套餐管理"页面，可以创建、编辑会员套餐，自定义套餐名称、月付/年付价格、功能权益和使用限制。

### Q: 收费功能关闭后，已付费用户会受影响吗？

A: 不会。关闭收费功能时，所有用户（包括已付费用户）都可以免费使用全部功能。重新开启收费功能后，已付费用户的订阅仍然有效。

### Q: 支持哪些支付方式？

A: 目前支持微信支付和支付宝两种支付方式。需要在环境变量中配置相应的支付参数。

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. **Fork 项目**
2. **创建功能分支**：`git checkout -b feature/AmazingFeature`
3. **提交更改**：`git commit -m 'Add some AmazingFeature'`
4. **推送到分支**：`git push origin feature/AmazingFeature`
5. **提交 Pull Request**

### 代码提交规范

- 提交信息应清晰描述变更内容
- 遵循 PEP 8 代码规范
- 添加必要的类型提示
- 更新相关文档（如 README、API 文档）

### 测试

在提交 PR 前，请确保：
- 代码可以正常运行
- 不破坏现有功能
- 通过基本的功能测试

---

## 📄 License

MIT License (c) 2025

---

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送 Pull Request
- 联系项目维护者

---

**最后更新**：2025-01-29  
**项目版本**：v2.2.0（模块化版本 + 邮箱功能 + 收费功能）

### 版本更新记录

#### v2.2.0 (2025-01-29)
- ✨ 新增收费功能模块（可选）
- ✨ 新增会员订阅制（管理员可自定义套餐）
- ✨ 新增按量付费功能（额外考试次数、编程题、数据导出）
- ✨ 新增题集购买功能（单科目/专题/考试真题/编程题集）
- ✨ 新增支付集成（微信支付、支付宝）
- ✨ 新增系统配置管理（可开启/关闭收费功能）
- 🎛️ 管理员可自定义会员套餐（名称、价格、权益、限制）
- 💰 会员用户购买题集享受 8 折优惠
- 📊 新增收入统计和使用记录功能

#### v2.1.0 (2025-01-29)
- ✨ 新增邮箱绑定功能
- ✨ 新增验证码登录功能（支持自动注册）
- ✨ 新增服务协议和隐私保护协议
- 🔄 移除传统注册功能，改为验证码登录自动注册
- 🔒 强制邮箱绑定：未绑定邮箱用户需先绑定才能使用全部功能
- 🚀 完善生产环境部署配置（Gunicorn、Nginx、systemd）
- 📝 更新依赖列表和部署文档

#### v2.0.0 (2025-01-XX)
- 🎉 模块化架构重构
- 📦 完整功能模块化设计
