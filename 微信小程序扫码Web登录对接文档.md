# 微信小程序扫码 Web 登录（账号互通）对接文档

目标：实现「微信用户可在 Web 登录、Web 用户也可在小程序登录」，并保证两端数据天然互通（同一 `user_id`），且默认不修改数据库结构。

---

## 0. 总体设计

- **Web 登录态**：继续使用 **Session（Cookie）**
- **小程序登录态**：继续使用 **JWT（Authorization: Bearer …）**
- **账号互通核心**：所有登录方式最终映射到同一个 `users.id`（即 `user_id`）
- **扫码登录核心**：Web 生成一次性扫码会话（`sid`），小程序扫码后用户点击“确认登录”，后端将该 `sid` 绑定到小程序登录的 `user_id`，Web 轮询并换取 session。

---

## 1. 用户流程（必须点确认）

### 1.1 Web → 小程序 → Web（扫码登录 Web）
1) Web 登录页展示二维码（小程序码）  
2) 用户扫码进入小程序 “网页登录确认页”  
3) 用户在小程序点击「确认登录」  
4) Web 自动变为登录态（session 写入）并跳转/刷新  

### 1.2 小程序首次微信登录未绑定（用户选择）
当小程序首次微信登录发现未绑定 Web 账号时，提示用户选择：
- A 创建新账号（微信账号）  
- B 绑定已有账号（默认：账号密码；可切换邮箱验证码）  

---

## 2. 状态机与时效

### 2.1 Web 扫码会话状态机
- `pending`：二维码已生成，等待小程序确认
- `confirmed`：小程序已确认，Web 可换取 session
- `exchanged`：Web 已换取 session（完成）
- `expired`：会话过期

### 2.2 建议有效期
- `sid`（扫码会话）：120 秒
- `nonce`（防重放）：跟随 `sid` 过期
- `web_login_token`（一次性换 session）：30 秒
- `wechat_temp_token`（未绑定临时票据）：300 秒

> 所有票据必须 **短过期 + 一次性**。任何 token 被使用后应立即失效（删除存储记录）。

---

## 3. 数据存储（不改 DB）

复用现有表：`user_progress(user_id, p_key, data, updated_at, created_at)` 作为 KV 存储。

- 扫码会话：`p_key = "web_login_session:<sid>"`
- 一次性换取票据：`p_key = "web_login_token:<token>"`

### 3.1 `web_login_session` data JSON（示例）
```json
{
  "sid": "WS_xxx",
  "nonce": "N_xxx",
  "state": "pending",
  "user_id": null,
  "created_at": 1730000000000,
  "expires_at": 1730000120000,
  "confirmed_at": null,
  "exchanged_at": null,
  "meta": {
    "ua": "optional",
    "ip": "optional"
  }
}
```

### 3.2 `web_login_token` data JSON（示例）
```json
{
  "token": "T_xxx",
  "sid": "WS_xxx",
  "user_id": 123,
  "expires_at": 1730000030000
}
```

> 存储时使用 `user_id = 0`（或管理员用户）作为 KV 的 owner 也可以；但建议独立约定一个固定 owner（例如 `user_id = 1` 或 `0`），避免污染真实用户的进度 key。

---

## 4. 后端接口（Web 扫码登录）

建议放置位置：`app/modules/auth/routes/api.py`（或新建 `app/modules/web_login/routes/api.py`）。

### 4.1 生成二维码（后端生成小程序码）【你选择：1=A】
`POST /api/web_login/qrcode`

**请求（可选）**
```json
{ "width": 280 }
```

**响应**
```json
{
  "status": "success",
  "data": {
    "sid": "WS_xxx",
    "expires_in": 120,
    "qrcode_url": "/uploads/web_login_qrcodes/WS_xxx.png"
  }
}
```

**实现要点**
- 调用微信接口：`wxa/getwxacodeunlimit`（推荐），`scene` 放入 `sid`（可选加 `nonce`）
  - `scene` 示例：`sid=WS_xxx&nonce=N_xxx`
  - `page` 固定：`pages/web-login/web-login`
- 图片落盘到 `uploads/web_login_qrcodes/` 并通过现有静态路由提供：
  - 你项目已有：`GET /uploads/<path:filename>`（Flask `send_from_directory`）

### 4.2 Web 查询扫码会话状态（轮询）
`GET /api/web_login/sessions/<sid>`

**响应（pending）**
```json
{ "status": "success", "data": { "state": "pending", "expires_in": 87 } }
```

**响应（confirmed）**
```json
{
  "status": "success",
  "data": { "state": "confirmed", "web_login_token": "T_xxx", "expires_in": 30 }
}
```

**响应（expired/exchanged）**
```json
{ "status": "success", "data": { "state": "expired" } }
```

**轮询建议**
- 800~1200ms/次，最多 120 秒。超时提示用户刷新二维码。

### 4.3 小程序确认登录（必须登录，JWT）
`POST /api/web_login/confirm`

**Header**
- `Authorization: Bearer <mini_jwt>`

**请求**
```json
{ "sid": "WS_xxx", "nonce": "N_xxx" }
```

**响应**
```json
{ "status": "success", "data": { "state": "confirmed" } }
```

**校验点**
- `sid` 存在且未过期
- `nonce` 匹配（防重放）
- 写入 `user_id = 当前 JWT 用户`，并把 session state 改为 `confirmed`

### 4.4 Web 换取 session（一次性 token）
`POST /api/web_login/exchange`

**请求**
```json
{ "web_login_token": "T_xxx" }
```

**响应（后端 Set-Cookie 写 session）**
```json
{ "status": "success", "data": { "logged_in": true } }
```

**实现要点**
- 校验 token 存在、未过期、未使用
- `session['user_id']=user_id`（以及必要的 `username/is_admin` 等）
- 将 `web_login_session` 标记为 `exchanged` 并清理 `web_login_token`

---

## 5. 小程序侧页面（扫码确认）

新增页面建议：`miniprogram/pages/web-login/web-login`

### 5.1 页面参数
- 扫码进入时获得 `sid`、`nonce`（从 `scene` 或 query）

### 5.2 页面逻辑
1) 检测小程序是否已登录（JWT）
2) 未登录：先走小程序登录流程
3) 展示确认页：
   - 文案：你正在登录网页，确认后网页将自动登录（可展示时间/设备信息可选）
4) 用户点击「确认登录」→ 调用 `POST /api/web_login/confirm`
5) 成功后提示“已确认，请回到网页”，并可自动 `navigateBack()` 或停留

---

## 6. 小程序首次微信登录未绑定：创建/绑定（你选择：C）

### 6.1 接口与行为
你已有：`POST /api/wechat/login`（小程序微信登录）

建议扩展返回：
- 已绑定：返回 `token + user_info`
- 未绑定：返回 `need_bind: true` + `wechat_temp_token`（短过期）

### 6.2 绑定已有账号（你选择：默认账号密码，可切邮箱验证码）

新增/扩展接口：

#### A) 账号/邮箱 + 密码（默认 UI）
`POST /api/wechat/bind`
```json
{
  "wechat_temp_token": "WT_xxx",
  "bind_mode": "password",
  "account": "用户名或邮箱",
  "password": "***"
}
```

#### B) 邮箱验证码（切换 UI）
1) 发验证码：`POST /api/wechat/bind/send_code`
```json
{ "wechat_temp_token": "WT_xxx", "email": "a@b.com" }
```
2) 绑定：`POST /api/wechat/bind`
```json
{
  "wechat_temp_token": "WT_xxx",
  "bind_mode": "email_code",
  "email": "a@b.com",
  "code": "123456"
}
```

#### 绑定成功统一响应
```json
{
  "status": "success",
  "data": { "token": "<mini_jwt>", "user_info": { "id": 123, "username": "..." } }
}
```

### 6.3 创建新账号（微信用户）
推荐复用现有微信登录入口，增加 `allow_create=true` 或新增 `POST /api/wechat/create`：
- 成功后写入新 `users.id`，绑定 openid，签发 JWT。

---

## 7. 错误码/异常处理建议

### 7.1 扫码会话
- 400：缺参数（sid/nonce/token）
- 401：未登录（confirm 需要 JWT）
- 404：sid 不存在
- 409：状态冲突（已确认/已兑换）
- 410：过期
- 429：频率限制（可对轮询 exempt 或设置更宽松）

### 7.2 绑定
- 400：参数不完整
- 401：`wechat_temp_token` 过期/无效
- 403：账号密码错误 / 验证码错误
- 409：该微信已绑定其他账号（防止重复绑定）

---

## 8. 安全要求（必须）

- 所有票据短过期 + 一次性
- `confirm` 必须 JWT；后端以 JWT user_id 为准绑定
- `exchange` 必须校验一次性 token，并立刻失效
- 可选增强：
  - 记录 `ua/ip` 并在小程序确认页展示“你正在登录：xxx”
  - 二维码刷新按钮（Web）

---

## 9. 联调与验收清单

- [ ] Web 登录页可显示二维码（后端生成、可访问）
- [ ] 扫码进入小程序确认页（能拿到 sid/nonce）
- [ ] 未登录时小程序会先登录再显示“确认”
- [ ] 点击确认后 Web 轮询能拿到 confirmed，并能 exchange 成功写 session
- [ ] Web 登录后访问收藏/错题/刷题进度等数据与小程序一致（同 user_id）
- [ ] 小程序首次未绑定时能选择：创建新账号 / 绑定已有账号
- [ ] 绑定已有账号支持：账号密码（默认）+ 邮箱验证码（切换）

---

## 10. 开发任务拆分（建议）

1) 后端：实现 `web_login` 四个接口（qrcode/session/confirm/exchange）+ KV 存储（user_progress）
2) 小程序：新增 `web-login` 页面（确认/取消）并接入 confirm API
3) Web：登录页新增二维码区域 + 轮询 + exchange + 登录态刷新
4) 小程序：实现“未绑定选择”与“绑定已有账号（两种方式）”UI + 接口对接

