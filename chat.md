# 站内聊天功能改造总结（用于新对话复用）

## 项目背景
- Flask + SQLite 题库系统
- 需求：新增用户之间聊天，并持续优化（头像/昵称、图片、未读提醒、预览、拖拽粘贴等）
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
  - `chat_messages`（含 `content_type`，支持 text/image）
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

## 7. 体验优化（按你指定的 3 项）
### 5.1 后端上传接口
- 新增：`POST /api/chat/messages/upload_image`
  - `multipart/form-data`：`conversation_id` + `image`
  - 保存目录：`uploads/chat/`
  - 写入 `chat_messages`：
    - `content_type='image'`
    - `content='/uploads/chat/xxx.ext'`

### 5.2 前端
- 聊天输入区新增“图片”按钮（file input）
- 图片消息渲染为 `<img>`（点击可预览，后续升级为弹层）

---

## 6. 体验优化（按你指定的 3 项）
### 6.1 图片弹层预览（不跳新窗口）
- `chat.html`：
  - 增加图片预览 Modal
  - 点击图片：打开弹层
  - Esc / 点击背景关闭

### 6.2 发送中状态 + 失败重试
- `chat.html`：
  - “发送/图片”按钮支持 loading（`data-loading="true"` + spinner）
  - 发送失败：`confirm()` 询问是否重试

### 6.3 拖拽/粘贴图片发送
- `chat.html`：
  - drag & drop：拖到页面出现提示层，松开即发送
  - paste：Ctrl+V 粘贴图片自动发送
  - 简单限制：图片 <= 5MB（可调整）

---

## 7. 新增：图片发送前压缩 / 生成缩略图（减少流量）（已落实到项目）

### 7.1 现状（未压缩）
- 前端：`chat.html` 直接把用户选择/拖拽/粘贴得到的 `File/Blob` 原样上传。
- 后端：`POST /api/chat/messages/upload_image`
  - 仅做扩展名白名单校验（png/jpg/jpeg/gif/webp）
  - 直接 `f.save()` 落盘到 `uploads/chat/`
  - `chat_messages.content` 存储图片 URL（如 `/uploads/chat/xxx.jpg`）
- 问题：手机拍照图/截图动辄数 MB，上传与拉取都浪费流量，渲染列表/预览也更慢。

### 7.2 已实现方案（优先前端压缩 + 缩略图）
> 原则：**上传前就变小**，让“上传流量”和“后续拉取流量”同时下降。

本项目已按“**content 存 JSON 字符串**”方案落地（不改 DB 表结构）。

#### A. 前端压缩（主路径）
- 在 `sendImageFile()` / 拖拽 / 粘贴发送前，先把 `File` 处理成：
  - **thumb（缩略图）**：用于消息气泡内展示（小图，加载快）
  - **image（压缩后原图）**：用于点击弹层查看（质量更好，但仍比原始小很多）
- 实现方式（浏览器端）：
  - 用 `createImageBitmap(file)` 或 `<img>` 解码
  - 用 `<canvas>` 按最长边缩放、导出 `toBlob('image/jpeg', quality)`
  - 生成两个 Blob：thumb 与 main

建议参数（可按业务再调）：
- main：最长边 `maxSide = 1600`，`jpegQuality = 0.82`，目标大小建议 `< 600~900KB`
- thumb：最长边 `thumbSide = 360`，`jpegQuality = 0.70`，目标大小建议 `< 60~120KB`
- 若原图已经很小（例如 `< 200KB` 且边长不大），可直接跳过压缩，thumb 仍可生成。

#### B. 后端兜底（可选，但更稳）
- 防止“旧浏览器/异常图片/绕过前端”上传大图：
  - 后端对上传文件再做一次最大边限制与重新编码
  - 同时生成缩略图（thumb）

### 7.3 接口与数据结构调整建议（兼容显示）
当前 `chat_messages` 只有 `content` 单字段，不方便同时存 main+thumb。
建议二选一：

1）**最小改动：content 存 JSON 字符串**（已采用）
- `content_type='image'`
- `content` 实际存（JSON 字符串）：
  ```json
  {"url":"/uploads/chat/xxx.jpg","thumb":"/uploads/chat/xxx_thumb.jpg","w":1200,"h":900}
  ```
  - `thumb` 可能为 `null`（例如 GIF 或压缩失败退化直传）
  - `w/h` 为可选（前端提交，未提交则为 `null`）
- 前端渲染逻辑：
  - 气泡图：`thumb || url`
  - 弹层预览：`url`
- 兼容旧数据：若 `content` 不是 JSON（纯 URL），前端按旧格式渲染。

2）**数据库加字段**
- `chat_messages` 新增列：`thumb_url`（以及可选 `width/height`）
- 代码更直观，但需要 DB 迁移脚本/升级逻辑。

### 7.4 前端展示策略
- 消息列表：显示 thumb（快）
- 弹层预览：加载 main url
- 可选：`loading="lazy"`，并给图片加一个占位背景色，减少抖动。

### 7.5 注意点
- GIF：前端 canvas 压缩会丢动画；建议：
  - 若是 gif：只生成静态 thumb（可选），main 保持原 gif 或转 webp（取决于需求）
- 透明背景 PNG：转 JPEG 会丢透明；可按策略：
  - 有透明则输出 PNG/WebP；否则 JPEG
- 体积控制：不要无限压缩导致糊；建议以“最长边 + 质量”双阈值控制。

---

## 8. 会话去重：从根源杜绝 direct 私聊重复（已落实到项目）

### 8.1 问题现象
- 会话列表里同一用户出现多次（原因：同一对用户被创建了多个 `direct` 会话）

### 8.2 数据库层修复与强约束
- DB：`instance/submissions.db`
- 已对存量重复会话做过合并清理（将消息合并到保留会话，删除多余会话）
- 在 `chat_conversations` 增加字段：`direct_pair_key`
  - 格式：`min_uid:max_uid`（例如 `1:10`）
- 增加唯一索引（partial unique index）：
  - `ux_chat_direct_pair` on `chat_conversations(direct_pair_key)`
  - 条件：`c_type='direct' AND direct_pair_key IS NOT NULL`

### 8.3 代码层创建逻辑
- `POST /api/chat/conversations/create`
  - 优先按 `direct_pair_key` 复用
  - 新建时写入 `direct_pair_key`
  - 捕获唯一索引冲突（并发竞态）并回退为查询复用

---

## 9. 常见注意点
- `read_lints` 对 `chat.html` 中 Jinja 语法（如 `{{ user_id }}`）可能误报 JS 错误：属静态解析误判，渲染后浏览器执行正常。
- UI 改动后建议 Ctrl+F5 强制刷新，避免缓存导致样式不生效。

---

## 10. 关键文件列表（便于新对话定位）
- `app/routes/chat.py`
- `app/routes/__init__.py`
- `app/utils/database.py`
- `app/templates/chat.html`
- `app/templates/index.html`