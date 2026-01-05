# 微信小程序配置说明

## 配置步骤

### 1. 环境变量配置

微信小程序的 AppID 和 Secret 已经配置在 `.env` 文件中：

```
WECHAT_APPID=wxfc4c270f007773ab
WECHAT_SECRET=714b6315c5e27cb2689c3c1d5bd54e2d
```

### 2. 验证配置

配置已经生效，应用会自动从 `.env` 文件加载这些配置。

### 3. 重启应用

如果应用正在运行，需要重启才能加载新的环境变量：

```bash
# 停止当前运行的应用（Ctrl+C）
# 然后重新启动
python run.py
```

### 4. 测试微信登录

配置完成后，小程序的微信登录功能应该可以正常工作了。

## 安全提示

⚠️ **重要：** `.env` 文件包含敏感信息（AppSecret），请确保：

1. **不要将 `.env` 文件提交到 Git 仓库**
   - 已在 `.gitignore` 中添加 `.env`（如果存在）
   - 使用 `.env.example` 作为模板（不包含真实密钥）

2. **生产环境配置**
   - 生产环境建议使用环境变量而非 `.env` 文件
   - 可以通过服务器环境变量或容器配置来设置

3. **定期更换 Secret**
   - 如果密钥泄露，立即在微信公众平台重置 AppSecret
   - 更新配置后重启应用

## 获取 AppID 和 AppSecret

如果需要修改配置：

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入「开发」→「开发管理」→「开发设置」
3. 查看「AppID(小程序ID)」和「AppSecret(小程序密钥)」
4. 如果 Secret 未设置，点击「重置」生成新的 Secret

## 故障排查

如果微信登录仍然失败，请检查：

1. **配置是否正确加载**
   ```python
   from app import create_app
   app = create_app('development')
   print(app.config.get('WECHAT_APPID'))
   print(app.config.get('WECHAT_SECRET'))
   ```

2. **AppID 和 Secret 是否正确**
   - 确认没有多余的空格或换行
   - 确认 Secret 是完整的（32位字符）

3. **网络连接**
   - 确保服务器能够访问 `https://api.weixin.qq.com`
   - 检查防火墙设置

4. **日志信息**
   - 查看应用日志（`logs/app.log`）
   - 查看微信 API 返回的错误信息

