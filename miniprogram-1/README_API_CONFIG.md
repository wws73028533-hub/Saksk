# 小程序API配置说明

## 问题说明

小程序在运行时出现域名校验错误，提示 `https://your-domain.com` 不在合法域名列表中。

## 解决步骤

### 1. 修改API地址

需要将 `miniprogram/utils/api.ts` 或 `miniprogram/utils/config.ts` 中的API地址修改为实际的后端服务器地址。

**开发环境：**
- 如果后端运行在本地，使用：`http://localhost:5000/api`
- 如果后端运行在局域网其他机器，使用：`http://192.168.x.x:5000/api`

**生产环境：**
- 使用实际的HTTPS域名：`https://your-actual-domain.com/api`

### 2. 配置微信小程序合法域名

在微信小程序管理后台配置合法域名：

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入「开发」->「开发管理」->「开发设置」
3. 找到「服务器域名」配置
4. 在「request合法域名」中添加你的后端API域名
   - 开发环境：如果是本地测试，可以在开发者工具中勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」
   - 生产环境：必须添加HTTPS域名（如：`https://your-actual-domain.com`）

**注意：**
- 必须是HTTPS协议（生产环境）
- 域名必须备案（如果是国内服务器）
- 需要在小程序管理后台配置后才能使用

### 3. 开发者工具设置

**开发测试时（本地调试）：**
1. 打开微信开发者工具
2. 点击右上角「详情」
3. 在「本地设置」中勾选：
   - ✅ 不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书

这样可以跳过域名校验，方便本地开发调试。

### 4. 修改配置示例

**方式一：直接修改 api.ts（简单）**

```typescript
// miniprogram/utils/api.ts
const API_BASE_URL = 'http://localhost:5000/api';  // 开发环境
// 或
const API_BASE_URL = 'https://your-actual-domain.com/api';  // 生产环境
```

**方式二：使用配置文件（推荐）**

已创建 `miniprogram/utils/config.ts` 配置文件，可以根据环境切换：

```typescript
// miniprogram/utils/config.ts
export const API_BASE_URL = 'http://localhost:5000/api';  // 开发环境
```

然后在 `api.ts` 中导入：
```typescript
import { API_BASE_URL } from './config';
```

### 5. 测试连接

修改配置后：
1. 确保后端服务器正在运行
2. 在微信开发者工具中重新编译
3. 测试API请求是否正常

### 常见问题

**Q: 本地开发时如何测试？**
A: 在开发者工具中勾选「不校验合法域名」，然后使用 `http://localhost:5000/api` 即可。

**Q: 生产环境必须使用HTTPS吗？**
A: 是的，微信小程序要求生产环境必须使用HTTPS协议。

**Q: 域名需要备案吗？**
A: 如果服务器在国内，域名必须备案。如果在海外，不需要备案但需要使用HTTPS。

