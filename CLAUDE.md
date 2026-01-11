# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Common Commands

```bash
# 启动开发服务器 (Flask)
python run.py                        # 默认 development 模式
FLASK_ENV=production python run.py   # 生产模式

# 生产环境 (Gunicorn)
gunicorn -c gunicorn_config.py run:app

# 安装依赖
pip install -r requirements.txt

# 小程序构建 (在 miniprogram-1 目录)
npm install
```

---

## Architecture Overview

### Backend (Flask 3)

- **入口**: `run.py` → `app/__init__.py:create_app()` 应用工厂
- **模块化**: 所有业务模块位于 `app/modules/`，通过 Blueprint 注册
  - `auth/` - 认证（密码登录、邮箱验证码、微信登录）
  - `quiz/` - 刷题模块
  - `exam/` - 考试模块
  - `admin/` - 管理后台
  - `chat/` - 站内聊天
  - `coding/` - 编程题
  - `user/` - 用户中心
  - `notifications/` - 通知系统
  - `popups/` - 弹窗管理
- **核心工具**: `app/core/utils/`
  - `database.py` - SQLite 数据库操作 (`get_db()`)
  - `decorators.py` - 权限装饰器
  - `jwt_utils.py` - JWT token 处理
- **数据库**: SQLite (`instance/submissions.db`)，启动时自动初始化

### Mini Program (WeChat)

- **位置**: `miniprogram-1/miniprogram/`
- **页面**: `pages/<name>/<name>.{ts,wxml,less,json}`
- **工具**: `utils/api.ts` (API 请求), `utils/auth.ts` (认证), `utils/config.ts` (配置)

### Authentication (双认证机制)

- **Web 端**: Flask session，使用 `@login_required`
- **小程序**: JWT token (`Authorization: Bearer <token>`)，使用 `@jwt_required`
- **兼容接口**: 使用 `@auth_required` + `current_user_id()` 同时支持两端

### Key Decorators (`app/core/utils/decorators.py`)

```python
@login_required      # Web session 验证
@jwt_required        # 小程序 JWT 验证
@auth_required       # 兼容两端
@admin_required      # 管理员权限
@subject_admin_required     # 科目管理员权限
@notification_admin_required # 通知管理员权限
current_user_id()    # 获取当前用户 ID（兼容两端）
```

---

## Project Rules

## Non-negotiable response format
- Always respond in Simplified Chinese.
- Every assistant message must start with:
  1) `【model】`（必须填写本次实际使用的模型名）
  2) `亲爱的Wang`

## Scope / Allowed changes
- Allowed: modify backend (Flask) code, add new mini program pages, add new backend endpoints, refactor code for maintainability.
- Default: do not change DB schema unless explicitly requested. If a feature requires schema change, propose an alternative first.
- Keep compatibility: mini program and web must share the same data and semantics for favorites/mistakes/user_answers/user_progress/exams.

## Coding style and structure
- Keep changes minimal and targeted; avoid unrelated refactors.
- Prefer modular design: avoid giant files; split by domain/service/util where appropriate.
- Follow existing project patterns and naming; do not introduce new frameworks unless explicitly requested.

### Backend (Flask)
- Use existing Blueprint/module layout under `app/modules/**`.
- New endpoints must be backward compatible and return stable JSON contracts.
- Authentication:
  - Mini program uses JWT `Authorization: Bearer <token>`.
  - Web may use session; endpoints used by both must support both (use existing `auth_required/current_user_id` helpers).
- Security: validate inputs; never trust query/body blindly.

### Mini program (WeChat)
- Page structure: `pages/<name>/<name>.{ts,wxml,less,json}`.
- Layout rule: fixed top nav + (if present) fixed bottom action area; content scroll only when overflow (no full-page scroll by default).
- Cards must be responsive and fill available width; avoid overlapping; prefer flex/grid with `min-width:0` and `box-sizing:border-box`.
- Avoid global CSS that breaks per-page layout; if adding global styles, keep them neutral.

## UI rules (high priority)
- iOS 18 minimal aesthetic: monochrome (white/light gray), no vivid colors or strong gradients.
- Soft rounded corners, subtle shadows, glassmorphism where appropriate.
- Use whitespace; keep typography clean.

## When requirements are unclear
- Ask a short clarification question before implementing.
