# Chat 重构计划清单（不破坏功能）

> 目标：在**不改变现有行为/接口**的前提下，重构 `app/templates/chat.html` 与 `app/routes/chat.py`，提升可维护性、可扩展性与可测试性。
> 指导文件：`chat.md`

---

## 0. 重构原则（必须遵守）

- **零功能回归**：保持路由、请求/响应字段、数据库读写、副作用（已读推进、未读统计、转码策略等）一致。
- **小步提交**：每一步都能运行、能回滚；每一步都只做一类变化（移动/抽取/命名/分层），避免“既重构又加功能”。
- **接口契约固定**：
  - 后端 API 路径与方法不变（例如 `/api/chat/messages/upload_audio` 等）。
  - 前端 DOM id（例如 `#convList` `#composer` `#btnVoice`）尽量保持不变，除非同时做全局替换并验证。
- **兼容历史数据**：
  - `image/audio/question` 的 content 既支持旧的纯字符串，也支持新的 JSON。
- **可观察性不降低**：保留关键日志（例如题目 options 解析日志、转码告警）。

---

## 1. 重构前盘点（冻结现状）

### 1.1 列出“不可破坏点”（检查清单）

- 页面路由：`GET /chat` 未登录返回 401 文本。
- API：
  - `GET /api/chat/users`
  - `GET /api/chat/conversations`
  - `POST /api/chat/conversations/create`
  - `GET /api/chat/messages`（包含“推进已读到 MAX(id)”逻辑）
  - `POST /api/chat/messages/send`
  - `POST /api/chat/messages/upload_image`
  - `POST /api/chat/messages/upload_audio`（含 raw + m4a/mp3 转码回退）
  - `POST /api/chat/messages/send_question`
  - `GET /api/chat/question/<id>`
  - `GET /api/chat/unread_count`（按 pair 去重）
  - 备注/资料：`/api/chat/user_remark`、`/api/chat/user_profile`

### 1.2 建议做一次“手工回归路径”记录

- 新建会话（搜索回车：精确匹配/多匹配弹层/单匹配直建）
- 发送文本
- 上传图片（选择/拖拽/粘贴，压缩+thumb）
- 录音语音（按住、上滑取消、松开发送）
- 语音播放（单例播放、切会话停止）
- 发送题目卡片 + 打开题目弹层（含补全 API）
- 资料页打开、备注修改/清除、会话标题刷新
- 首页未读角标归零验证（读消息后）

---

## 2. 后端 `app/routes/chat.py` 重构计划

### 2.1 第一阶段：纯整理（不改逻辑）

1. **按领域分段**（只移动代码位置，不改逻辑）：
   - 常量与工具：`CHAT_IMAGE_EXTS/CHAT_AUDIO_EXTS`、allowed 判断、转码函数
   - 鉴权/权限：`_is_member`
   - Page route：`/chat`
   - Conversation APIs：users、conversations、create
   - Profile/Remark APIs
   - Message APIs：messages、send、upload_image、upload_audio、send_question、get_question
   - Badge API：unread_count
2. **统一返回风格**：保持字段不变，但把重复的 `unauthorized` JSON 返回抽成函数（例如 `_require_login()`）。
3. **类型与边界统一**：
   - 将 `uid = session.get('user_id')` 统一转为 `int`，并用同一种异常兜底；
   - `conversation_id/peer_id/question_id` 的解析封装为 `parse_int(value, default=0)`。

### 2.2 第二阶段：提取 Service/Repo（建议目录）

> 目标：路由层只做参数校验与响应包装；SQL 与业务流程下沉。

推荐新模块（可逐步落地，不必一次完成）：

- `app/services/chat_service.py`
  - `get_conversations(uid)`
  - `create_or_get_direct_conversation(uid, peer_id)`
  - `fetch_messages_and_advance_read(uid, conversation_id, after_id, limit)`
  - `send_text(uid, conversation_id, content)`
  - `send_image(uid, conversation_id, file, thumb, w, h)`
  - `send_audio(uid, conversation_id, file, duration)`（含转码策略）
  - `send_question(uid, conversation_id, question_id)`
  - `get_question_detail(question_id)`
  - `get_unread_count(uid)`
  - `get_user_profile(uid, target_user_id)` / `set_user_remark(uid, target_user_id, remark)`
- `app/repositories/chat_repo.py`（可选）：封装 SQL
- `app/utils/chat_media.py`：allowed 判断、转码与文件保存

> 关键：先抽“纯函数/无状态工具”（如转码/保存路径），再抽“带 conn 的数据层函数”。

### 2.3 第三阶段：SQL 常量化与可测试化

- 把长 SQL 用三引号字符串放到单独区域（`SQL_CONVERSATIONS_LIST` 等），避免路由函数中混杂。
- 为关键 SQL 增加注释：
  - 未读数计算规则
  - direct_pair_key 去重规则
  - 已读推进规则（MAX(id)）

### 2.4 风险点（重构时重点保护）

- `chat_messages()`：推进已读到 `MAX(id)` 的逻辑不能丢。
- `chat_unread_count()`：窗口函数 + `datetime(updated_at)` 排序逻辑不能变。
- `upload_audio()`：raw 保存 + m4a 优先、mp3 回退 + 日志告警。
- `send_question()`：`parse_options` 解析与日志。

---

## 3. 前端 `app/templates/chat.html` 重构计划

> 当前 `chat.html` 集成了：CSS、HTML、超长 JS（状态管理 + DOM 渲染 + 多个 modal + 上传/录音/压缩）。建议先**模块化 JS**，再考虑 CSS/HTML 结构。

### 3.1 第一阶段：拆分 JS（推荐不破坏方式）

1. **保持 HTML 结构与 id 不变**，只把 `<script>` 内代码拆成“模块对象 + 分区函数”。
2. 建议按功能切分成对象（仍在同一个 `<script>` 文件中，先不抽到静态文件）：
   - `state`：`currentConversationId/lastMessageId/currentPeerUserId` 等
   - `api`：所有 fetch 封装（`fetchConversations/sendText/uploadImage/uploadAudio/...`）
   - `ui`：DOM 查询缓存、渲染（会话列表、消息渲染、divider、toast）
   - `modals`：imgModal/questionModal/userPickModal/userProfileModal
   - `composer`：输入区（发送按钮切换、Enter 发送）
   - `media`：图片压缩、语音录制、单例播放
   - `polling`：轮询控制（start/stop/reset）
3. 抽取通用工具：
   - `escapeHtml/escapeAttr`
   - `safeParseTime/formatConvTimestamp/formatDividerTime`
   - `setLoading/showToast`

### 3.2 第二阶段：把 JS 抽到静态文件（可选，但强烈建议）

- 新增：`app/static/js/chat/index.js`
- chat.html 中仅保留：
  - `const LOGGED_IN = ...; const MY_ID = ...;`
  - `window.ChatPage.init({ loggedIn, myId })`

> 注意：此阶段要确认你项目的静态资源版本/缓存策略，否则可能出现旧 JS 缓存导致“看似没生效”。

### 3.3 第三阶段：CSS 结构化（不改 UI）

- 按层组织：
  - tokens（`:root` 变量）
  - layout（topbar/sidebar/main）
  - components（button/badge/avatar/bubble/modal）
  - states（dark-mode/active/compact）
- 移除重复样式与“内联 style”逐步归并到 class（优先处理高复用的内联块）。

### 3.4 风险点（重构时重点保护）

- DOM id/事件绑定：`btnVoice`（pointer 录音）、`btnPlus`（菜单定位）、`composer`（输入区）、`messages`（append）
- 消息渲染兼容：
  - `parseImageContent`（旧数据纯 URL）
  - `parseAudioContent`（旧数据纯 URL）
  - `parseQuestionContent`（JSON）
- 语音播放单例逻辑：`currentPlayingAudio` 及切会话 stop。
- 图片压缩：GIF 不压缩（保动画）。
- 已读推进与未读刷新：`pollMessages()` 中 `refreshConversations()` 的调用时机。

---

## 4. 建议的“逐步落地路线”（最少风险顺序）

1. **只整理 chat.py 代码顺序 + 抽工具函数（不动 SQL 与逻辑）**
2. **chat.html 仅做 JS 分区与对象化（不抽文件）**
3. 把 API fetch 统一封装，减少散落 fetch
4. 把渲染（会话列表/消息列表）提取为纯函数，保证输入→输出可预测
5. 再考虑抽离静态 JS/CSS（涉及缓存/部署时机）

---

## 5. 验收标准（重构完成后必须满足）

- [ ] 所有 chat.md 中已实现的能力仍可用（文本/图片/语音/题目/备注/资料/未读角标）
- [ ] 代码结构清晰：后端路由 ≤ 30~50 行/函数，核心逻辑在 service
- [ ] 前端脚本可定位：每个功能块有明确入口与状态来源
- [ ] 发生错误时提示不降低（toast/alert/confirm）
- [ ] 无明显性能退化（轮询间隔不变、列表渲染不抖动）

---

## 6. 后续扩展点（重构后更容易加）

- 文件发送（已留 UI 入口 `文件（未实现）`）
- 会话置顶/免打扰/删除
- 群聊（`c_type != direct` 的标题/成员管理）
- 消息撤回/删除/引用回复
- 更完善的媒体转码队列与异步处理

---

## 7. 前端优先：`chat.html` JS 模块化落地路线（按提交粒度）

> 目标：先在 **同一个 `chat.html` 文件内**完成 JS 模块化（不抽静态文件），降低缓存与部署风险；确认稳定后再可选迁移到 `app/static/js/chat/index.js`。

### 7.1 必须保护的硬契约（禁止破坏）

#### 7.1.1 DOM id（重点）

以下元素 id 在重构期应保持不变（或做到全局替换并回归）：

- `convList` / `convListMobile`
- `messages` / `emptyState`
- `composer`
- `btnVoice` / `btnSendText` / `btnPlus` / `imgInput`
- `plusMenu` / `profileMenu`
- `userProfileModal` / `questionModal` / `imgModal` / `userPickModal`
- `overlay` / `drawer` / `toast` / `dropHint` / `voiceHint`

#### 7.1.2 行为契约（重点）

- 轮询：打开会话后 `setInterval(..., 2000)`；切会话必须清理旧 timer。
- `pollMessages(force)`：有新消息才 append + refreshConversations；force 时即使没消息也 refresh。
- 图片：压缩生成 main+thumb；GIF 不压缩；拖拽/粘贴/选择入口均保留。
- 语音：按住录音、上滑取消、松开发送；失败 confirm 重试；大小/时长限制保留。
- 语音播放：单例播放；切会话 stop。
- 题目弹层：必要时请求 `/api/chat/question/<id>` 补全。
- 资料页：备注保存后刷新会话列表与标题。

---

### 7.2 推荐模块划分（同文件内，先不拆静态文件）

建议最终收敛为以下命名空间（对象模块即可，不强制 class）：

- `ChatState`：页面状态（conversation_id、lastMessageId、pollTimer、currentPeerUserId 等）
- `Chat.utils`：纯工具函数（escape/time/format/loading 等）
- `Chat.api`：所有 fetch 封装（只做请求与 JSON 解析，不做 alert/confirm）
- `Chat.ui`：toast、DOM 缓存、通用 UI 更新
- `Chat.conversations`：会话列表渲染与打开会话
- `Chat.messages`：消息解析/渲染（image/audio/question/text）与音频单例播放
- `Chat.polling`：轮询 start/stop/tick
- `Chat.composer`：输入区（Enter 发送、按钮互斥）
- `Chat.image`：图片压缩 + 上传 + drag/drop + paste
- `Chat.voice`：录音 + 上传（MediaRecorder）
- `Chat.modals`：img/question/userPick/userProfile 统一管理

---

### 7.3 按提交粒度的落地步骤（最少风险顺序）

> 每一步都建议做一次最小回归：能打开聊天页、能切会话、能发一条文本。

#### Commit 1：建立模块骨架 + 状态容器

- 新增 `const Chat = {}; const ChatState = {...}`
- 先把 `currentConversationId/lastMessageId/pollTimer/currentPeerUserId` 这类全局变量集中到 `ChatState`
- 不改函数逻辑，只替换变量引用

#### Commit 2：抽出 `Chat.utils`（纯函数）

- `escapeHtml/escapeAttr`、`safeParseTime`、时间格式化、`prefersReducedMotion`、`setLoading`
- 全局调用点统一改为 `Chat.utils.*`

#### Commit 3：抽出 `Chat.ui`（DOM 缓存 + Toast）

- 新增 `Chat.ui`：
  - `Chat.ui.dom.get(id)`：带缓存的 `getElementById`（避免重复查询）
  - `Chat.ui.toast.show(msg)`：封装 toast 显示（本次先保留旧 `showToast` 名称作为兼容层，内部转调）
- 本 commit **不改业务流程**：只抽离 DOM 查询与 toast 基础能力。

#### Commit 4：抽出 `Chat.api`（统一 fetch 封装）

- conversations/messages/send/upload/search/profile/remark/question 等全部封装
- API 层只返回数据与错误，不直接弹窗

#### Commit 5：抽出 `Chat.conversations`

- `refresh()` + `render()`（包含 direct 按 `peer_user_id` 去重规则）
- `open(conversationId)`：负责切会话状态重置 + 标题更新 + 启动轮询

#### Commit 6：抽出 `Chat.messages`

- `parseImageContent/parseAudioContent/parseQuestionContent`
- `append(msgs)` + `maybeInsertTimeDivider()` + `renderAvatarDiv()`
- `audioPlayer`：单例播放状态与 stopCurrentAudio

#### Commit 7：抽出 `Chat.polling`

- `start/stop/tick(force)`
- 保持 2s 轮询与 force 行为一致

#### Commit 8：抽出 `Chat.composer`

- `updateActions()`（发送/语音互斥）
- `bind()`（input/keydown）
- `sendText()`（保留 confirm 重试策略）

#### Commit 9：抽出 `Chat.image`

- 图片压缩与 thumb 生成
- 统一入口：选择/拖拽/粘贴

#### Commit 10：抽出 `Chat.voice`

- MediaRecorder 录音、上滑取消、上传
- 与 UI 浮层/按钮状态解耦

#### Commit 11：抽出 `Chat.modals`

- `imgModal/questionModal/userPickModal/userProfileModal` 的 open/close/menu/复制 等
- Esc 关闭逻辑集中到一个 handler

#### Commit 12（可选）：抽离到静态文件

- 迁移到 `app/static/js/chat/index.js`
- `chat.html` 只保留初始化参数与 `Chat.init()`

---

### 7.4 每步验收清单（建议最小回归）

- [ ] 会话列表正常渲染，未读 badge 正常
- [ ] 切会话正常，轮询不重复（无多重 timer）
- [ ] 发送文本成功
- [ ] 图片：选择/拖拽/粘贴 任一方式可发送
- [ ] 语音：按住录音，上滑取消，松开发送
- [ ] 语音播放：单例播放，切会话停止
- [ ] 题目卡片可点开弹层，必要时可补全
- [ ] 资料页可打开，备注保存后标题/列表刷新
