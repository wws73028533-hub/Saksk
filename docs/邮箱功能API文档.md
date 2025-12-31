# 邮箱功能 API 文档

## 概述

本文档描述了邮箱相关功能的 REST API 接口，包括：
- 绑定邮箱
- 邮箱验证码登录
- 邮箱密码登录（扩展现有登录接口）

所有 API 使用 JSON 格式进行数据交换。

## 基础信息

- **Base URL**: `/api/auth`
- **Content-Type**: `application/json`
- **响应格式**: JSON

## 通用响应格式

### 成功响应
```json
{
    "status": "success",
    "message": "操作成功消息",
    "data": {}  // 可选，包含额外数据
}
```

### 错误响应
```json
{
    "status": "error",
    "message": "错误描述信息",
    "status_code": 400  // HTTP状态码
}
```

## API 接口

### 1. 发送绑定邮箱验证码

发送验证码到指定邮箱，用于绑定邮箱功能。

**接口**: `POST /api/auth/email/send-bind-code`

**认证**: 需要登录

**请求体**:
```json
{
    "email": "user@example.com"
}
```

**参数说明**:
- `email` (string, required): 要绑定的邮箱地址

**响应示例**:
```json
{
    "status": "success",
    "message": "验证码已发送到邮箱"
}
```

**错误响应**:
- `400`: 邮箱格式不正确、发送频率过高
- `401`: 用户未登录
- `409`: 邮箱已被其他用户使用

**限流规则**:
- 同一邮箱：1分钟内最多发送1次
- 同一用户：1小时内最多发送5次

---

### 2. 绑定邮箱

使用验证码绑定邮箱到当前账户。

**接口**: `POST /api/auth/email/bind`

**认证**: 需要登录

**请求体**:
```json
{
    "email": "user@example.com",
    "code": "123456"
}
```

**参数说明**:
- `email` (string, required): 要绑定的邮箱地址
- `code` (string, required): 6位数字验证码

**响应示例**:
```json
{
    "status": "success",
    "message": "邮箱绑定成功",
    "data": {
        "email": "user@example.com",
        "email_verified": true
    }
}
```

**错误响应**:
- `400`: 验证码错误或已过期、验证码已使用、验证码错误次数过多
- `401`: 用户未登录
- `409`: 邮箱已被其他用户使用

**限流规则**:
- 每分钟最多10次请求（防止暴力破解）

**验证规则**:
- 验证码有效期：10分钟
- 验证码只能使用一次
- 验证码错误5次后需要重新发送

---

### 3. 发送登录验证码

发送验证码到已绑定的邮箱，用于验证码登录。

**接口**: `POST /api/auth/email/send-login-code`

**认证**: 无需登录

**请求体**:
```json
{
    "email": "user@example.com"
}
```

**参数说明**:
- `email` (string, required): 已绑定的邮箱地址

**响应示例**:
```json
{
    "status": "success",
    "message": "验证码已发送，请查收邮件"
}
```

**注意**: 出于安全考虑，即使邮箱未绑定也会返回成功消息，防止邮箱枚举攻击。

**错误响应**:
- `400`: 邮箱格式不正确、发送频率过高

**限流规则**:
- 同一邮箱：1分钟内最多发送1次
- 同一IP：1小时内最多发送10次

---

### 4. 验证码登录

使用邮箱和验证码进行免密登录。

**接口**: `POST /api/auth/email/login`

**认证**: 无需登录

**请求体**:
```json
{
    "email": "user@example.com",
    "code": "123456",
    "redirect": "/"  // 可选，登录后跳转地址
}
```

**参数说明**:
- `email` (string, required): 已绑定的邮箱地址
- `code` (string, required): 6位数字验证码
- `redirect` (string, optional): 登录后跳转的URL，默认为 `/`

**响应示例**:
```json
{
    "status": "success",
    "redirect": "/"
}
```

**错误响应**:
- `400`: 验证码错误或已过期、验证码已使用、验证码错误次数过多、邮箱未绑定
- `403`: 账户被锁定

**限流规则**:
- 每分钟最多10次请求（防止暴力破解）

**验证规则**:
- 验证码有效期：10分钟
- 验证码只能使用一次
- 验证码错误5次后需要重新发送

---

### 5. 邮箱密码登录（扩展）

使用邮箱和密码进行登录（扩展了现有的登录接口）。

**接口**: `POST /api/auth/login`

**认证**: 无需登录

**请求体**:
```json
{
    "username": "user@example.com",  // 支持邮箱或用户名
    "password": "password123",
    "remember": false,  // 可选，是否保持登录
    "redirect": "/"  // 可选，登录后跳转地址
}
```

**参数说明**:
- `username` (string, required): 用户名或邮箱地址
- `password` (string, required): 密码
- `remember` (boolean, optional): 是否保持登录状态，默认 `false`
- `redirect` (string, optional): 登录后跳转的URL，默认为 `/`

**响应示例**:
```json
{
    "status": "success",
    "redirect": "/",
    "remember": false
}
```

**错误响应**:
- `400`: 用户名或密码错误、数据验证失败
- `403`: 账户被锁定

**限流规则**:
- 每分钟最多5次请求

**实现逻辑**:
- 系统会自动判断输入是邮箱格式还是用户名
- 如果是邮箱，使用邮箱查询用户
- 如果是用户名，使用用户名查询用户
- 其余逻辑与现有登录一致

---

## 错误码说明

| HTTP状态码 | 错误类型 | 说明 |
|-----------|---------|------|
| 400 | Bad Request | 请求参数错误、验证码错误等 |
| 401 | Unauthorized | 未登录或会话失效 |
| 403 | Forbidden | 账户被锁定 |
| 409 | Conflict | 邮箱已被其他用户使用 |
| 429 | Too Many Requests | 请求频率过高 |
| 500 | Internal Server Error | 服务器内部错误 |

## 安全特性

1. **验证码安全**:
   - 验证码有效期限制（10分钟）
   - 验证码使用后立即失效
   - 验证码错误次数限制（5次）
   - 验证码存储在数据库中，使用后标记为已使用

2. **限流保护**:
   - 发送验证码频率限制
   - 验证码验证频率限制
   - 登录尝试频率限制

3. **防攻击**:
   - 防止邮箱枚举攻击（未绑定时也返回相同消息）
   - 验证码不记录在日志中
   - 敏感操作记录审计日志

4. **数据安全**:
   - 邮箱地址唯一性约束
   - 使用TLS/SSL加密发送邮件
   - 验证码有效期明确告知用户

## 注意事项

1. 验证码有效期为10分钟，请及时使用
2. 验证码只能使用一次，使用后立即失效
3. 验证码错误5次后需要重新发送
4. 发送验证码有频率限制，请勿频繁请求
5. 绑定邮箱后，可以使用邮箱进行登录
6. 一个邮箱只能绑定一个账户

## 示例代码

### JavaScript (Fetch API)

```javascript
// 发送绑定验证码
async function sendBindCode(email) {
    const response = await fetch('/api/auth/email/send-bind-code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email })
    });
    return await response.json();
}

// 绑定邮箱
async function bindEmail(email, code) {
    const response = await fetch('/api/auth/email/bind', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, code })
    });
    return await response.json();
}

// 验证码登录
async function emailLogin(email, code) {
    const response = await fetch('/api/auth/email/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, code })
    });
    return await response.json();
}
```

### Python (requests)

```python
import requests

# 发送绑定验证码
def send_bind_code(email, session):
    url = 'http://localhost:5000/api/auth/email/send-bind-code'
    response = session.post(url, json={'email': email})
    return response.json()

# 绑定邮箱
def bind_email(email, code, session):
    url = 'http://localhost:5000/api/auth/email/bind'
    response = session.post(url, json={'email': email, 'code': code})
    return response.json()

# 验证码登录
def email_login(email, code):
    url = 'http://localhost:5000/api/auth/email/login'
    response = requests.post(url, json={'email': email, 'code': code})
    return response.json()
```

