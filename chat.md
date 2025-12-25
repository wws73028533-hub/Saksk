# 站内聊天功能改造总结（用于新对话复用）

## 项目背景
- Flask + SQLite 题库系统
- 需求：新增用户之间聊天，并持续优化（头像/昵称、图片、未读提醒、预览、拖拽粘贴、语音、备注、资料页等）
- 实现策略：不引入 WebSocket，使用轮询；消息持久化到 SQLite

---

## 1. 新增聊天功能（基础版）
### 1.1 后端：新增蓝图与路由
- 新增文件：`app/routes/chat.py`
- 页面路由：
  - `GET /chat`：聊天主页面
- API：
  - `GET /api/chat/users?q=...`：搜索用户（发起聊天）
  - `POST /api/chat/conversations/create`：创建或复用 1v1 会话
  - `GET /api/chat/conversations`：会话列表（含未读数、最后一条消息）
  - `GET /api/chat/messages?conversation_id=...&after_id=...&limit=...`：增量拉取消息并推进已读
  - `POST /api/chat/messages/send`：发送文本消息
  - `GET /api/chat/unread_count`：总未读数（用于首页红点）

### 1.2 注册蓝图
- 修改：`app/routes/__init__.py`
  - `from .chat import chat_bp`
  - `app.register_blueprint(chat_bp)`
  - 蓝图数量日志从 7 → 8

### 1.3 数据库（SQLite）
- 修改：`app/utils/database.py` 的 `init_db()` 创建表
  - `chat_conversations`
  - `chat_members`（含 `last_read_message_id`）
  - `chat_messages`（含 `content_type`，支持 text/image/audio）
- 修改：`app/utils/database.py` 的 `_create_indexes()` 新增索引
  - `idx_chat_members_user (user_id, conversation_id)`
  - `idx_chat_messages_conversation (conversation_id, id DESC)`

### 1.4 前端：聊天页面
- 新增文件：`app/templates/chat.html`
  - 左侧会话列表、右侧消息区
  - 轮询刷新（每 2 秒拉取新消息）

---

## 2. 首页入口 + 未读提醒
- 修改：`app/templates/index.html`
  - 登录后增加“聊天”入口：`/chat`
  - 增加未读角标 `#chatUnreadBadge`
  - 轮询接口：`/api/chat/unread_count`（每 5 秒 + 回到前台时刷新）
  - 修复角标裁切：给 `#chatEntry` 加 `overflow: visible;`，并把角标定位从 `-6px` 调到 `-10px`

---

## 3. 会话列表显示头像/昵称（direct 私聊）
### 3.1 后端
- 修改：`GET /api/chat/conversations`
  - 对 direct 私聊返回对方信息：
    - `peer_user_id`
    - `peer_username`
    - `peer_avatar`
  - last_message 如果是图片类型，前端展示用占位文案 `[图片]`

### 3.2 前端
- `chat.html` 会话列表：
  - 显示对方头像（无头像用首字母圆形占位）
  - 显示对方昵称

---

## 4. 消息区显示头像/昵称（UI）
- `chat.html` 消息渲染：
  - 每条消息旁显示发送者头像
  - 自己消息显示在右侧，对方在左侧
  - 修复过一次“对齐混乱”的 CSS：让 `.msg-wrap` 使用 `flex-direction: column`，并对 `.me` 方向做稳定对齐

---

## 5. 支持发送图片（上传 + 显示）

---

## 6. 支持发送语音（录音 + 播放 + 取消发送 + 单例播放）（已落实到项目）

### 6.1 后端：语音上传接口
- 新增：`POST /api/chat/messages/upload_audio`
  - `multipart/form-data`：
    - `conversation_id`
    - `audio`（webm/ogg/wav/mp3/m4a）
    - `duration`（可选，秒）
  - 保存目录：`uploads/chat/`
  - 写入 `chat_messages`：
    - `content_type='audio'`
    - `content` 存 JSON 字符串：`{"url":"/uploads/chat/xxx.webm","duration":1.2}`

### 6.2 前端：按住说话、松开发送，上滑取消
- `chat.html` 输入区新增语音按钮
- 录音实现：`MediaRecorder + getUserMedia({audio:true})`
- 交互：
  - 按住开始录音
  - 松开发送
  - 上滑到阈值（默认 80px）进入取消态，松开取消
  - 取消态/发送态都有浮层提示文案

### 6.3 语音消息渲染：只保留播放键 + 时长
- 不使用原生 `<audio controls>`（避免控件占位过大且样式不一致）
- 自绘播放/暂停按钮 + 时长文本
- 隐藏 `<audio>` 元素负责实际播放

### 6.4 同一时间只播放一条语音
- 新播放时自动停止并重置上一条正在播放的语音
- 切换会话时自动停止播放

---

## 7. 体验优化：图片预览/失败重试/拖拽粘贴
### 7.1 图片弹层预览（不跳新窗口）
- `chat.html`：
  - 增加图片预览 Modal
  - 点击图片：打开弹层
  - Esc / 点击背景关闭

### 7.2 发送中状态 + 失败重试
- `chat.html`：
  - “发送/图片”按钮支持 loading（`data-loading="true"` + spinner）
  - 发送失败：`confirm()` 询问是否重试

### 7.3 拖拽/粘贴图片发送
- `chat.html`：
  - drag & drop：拖到页面出现提示层，松开即发送
  - paste：Ctrl+V 粘贴图片自动发送
  - 简单限制：图片 <= 5MB（可调整）

---

## 8. 新增：图片发送前压缩 / 生成缩略图（减少流量）（已落实到项目）
- 方案：前端压缩生成 main + thumb；后端 upload_image 接口支持 `thumb`，image 类型 content 存 JSON
- `content_type='image'` 时：
  ```json
  {"url":"/uploads/chat/xxx.jpg","thumb":"/uploads/chat/xxx_thumb.jpg","w":1200,"h":900}
  ```

---

## 9. 会话去重：从根源杜绝 direct 私聊重复（已落实到项目）
### 9.1 问题现象
- 会话列表里同一用户出现多次（原因：同一对用户被创建了多个 `direct` 会话）

### 9.2 数据库层修复与强约束
- DB：`instance/submissions.db`
- 在 `chat_conversations` 增加字段：`direct_pair_key`（`min_uid:max_uid`）
- 增加唯一索引（partial unique index）：
  - `ux_chat_direct_pair` on `chat_conversations(direct_pair_key)`
  - 条件：`c_type='direct' AND direct_pair_key IS NOT NULL`

### 9.3 代码层创建逻辑
- `POST /api/chat/conversations/create`
  - 优先按 `direct_pair_key` 复用
  - 新建时写入 `direct_pair_key`
  - 捕获唯一索引冲突（并发竞态）并回退为查询复用

---

## 10. 新增：用户名搜索体验优化（避免 wxr / wxr2 误选）
### 10.1 前端
- 搜索回车创建会话：优先精确匹配用户名；当匹配多个用户时提供“选择列表”弹层。

### 10.2 后端
- `/api/chat/users?q=...` 排序优化：精确命中优先、前缀命中其次，再按活跃度与用户名。

---

## 11. 新增：用户备注（只对自己可见）+ 会话/标题优先展示备注
### 11.1 数据库
- 新增表：`user_remarks (owner_user_id, target_user_id, remark, updated_at, created_at)`
- 唯一约束：`UNIQUE(owner_user_id, target_user_id)`

### 11.2 后端
- 新增：`GET/POST /api/chat/user_remark`
  - GET：读取备注
  - POST：设置备注，空字符串表示清除
- `GET /api/chat/conversations` 返回 `peer_remark`

### 11.3 前端
- 会话列表/聊天标题显示名：`peer_remark || peer_username`

---

## 12. 新增：好友资料页（类似微信好友资料）+ 备注内联编辑
### 12.1 后端
- 新增：`GET /api/chat/user_profile?user_id=...`
  - 返回用户公开字段：`username/avatar/contact/college/created_at`
  - 返回当前用户对 TA 的 `remark`

### 12.2 前端
- 点击入口：
  - 会话列表头像
  - 消息列表中对方头像
  - 聊天头部按钮从“备注”改为“资料”，点击进入资料页
- 资料页能力：
  - 顶部导航（返回箭头 + 右上角“···”）
  - 备注内联编辑（输入框 + 保存/清除/取消）
  - “···”菜单支持：设置备注 / 清除备注 / 复制用户名 / 复制 ID
  - 朋友圈预览区块（占位）
  - 底部按钮：发消息（回到聊天）/ 音视频通话（占位提示）
- 头像修复：资料页头像使用 `.profile-avatar` 强制 `cover + center`，避免显示异常

---

## 13. 输入区 UI 迭代（更像移动端 IM）
- 输入区改为：左侧 “+” 圆按钮 + 中间胶囊输入框 + 右侧（语音/发送互斥）
- 有文字时显示“绿色圆形上箭头发送”，无文字时显示麦克风
- “+” 支持弹出菜单（图片/文件占位）

---

## 14. 常见注意点
- `read_lints` 对 `chat.html` 中 Jinja 语法（如 `{{ user_id }}`）可能误报 JS 错误：属静态解析误判。
- UI 改动后建议 Ctrl+F5 强制刷新，避免缓存导致样式不生效。

---

## 15. 关键文件列表（便于新对话定位）
- `app/routes/chat.py`
- `app/routes/__init__.py`
- `app/utils/database.py`
- `app/templates/chat.html`
- `app/templates/index.html`
