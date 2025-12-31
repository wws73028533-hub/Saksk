# Ubuntu 22.04 + Nginx + Gunicorn 部署指南

本文档提供了在 Ubuntu 22.04 服务器上使用 Nginx 和 Gunicorn 部署题库系统的详细步骤。

## 目录结构

```
deployment/
├── README.md              # 本部署指南
└── scripts/
    ├── setup.sh           # 自动化部署脚本
    └── update.sh          # 更新部署脚本
```

## 前置要求

- Ubuntu 22.04 LTS 服务器
- Python 3.10+ 和 pip
- Nginx
- 域名（可选，用于 HTTPS）

## 部署步骤

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx
```

### 2. 创建虚拟环境

```bash
# 进入项目目录
cd /path/to/quiz-app

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件或设置系统环境变量：

```bash
# 在项目根目录创建 .env 文件
cat > .env << EOF
FLASK_ENV=production
ENVIRONMENT=production
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
# 邮件配置（根据实际情况修改）
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=noreply@example.com
# HTTPS 环境
SESSION_COOKIE_SECURE=true
EOF
```

### 4. 配置 Gunicorn

配置文件已创建在项目根目录：`gunicorn_config.py`

根据服务器实际情况修改：
- `bind`: 监听地址和端口（默认 127.0.0.1:8000）
- `workers`: Worker 进程数（默认自动计算）
- `user`/`group`: 运行用户（建议使用 www-data）

### 5. 配置 Nginx

```bash
# 复制 Nginx 配置文件（如果存在）
# sudo cp nginx/quiz_app.conf /etc/nginx/sites-available/quiz_app.conf

# 编辑配置文件，修改以下内容：
# - server_name: 替换为您的域名
# - alias 路径: 替换为项目实际路径（两处：/static 和 /uploads）

# sudo nano /etc/nginx/sites-available/quiz_app.conf

# 创建软链接启用站点
# sudo ln -s /etc/nginx/sites-available/quiz_app.conf /etc/nginx/sites-enabled/

# 测试 Nginx 配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 6. 配置 Systemd 服务

```bash
# 复制 systemd 服务文件
sudo cp systemd/saksk_ti.service /etc/systemd/system/quiz-app.service

# 编辑服务文件，修改以下内容：
# - User/Group: 运行用户（建议 www-data）
# - WorkingDirectory: 项目根目录（如 /var/www/quiz-app）
# - PATH: 虚拟环境路径
# - Environment: 环境变量配置
# - ExecStart: Gunicorn 命令路径

sudo nano /etc/systemd/system/quiz-app.service

# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 设置权限（确保日志目录可写）
sudo mkdir -p /path/to/quiz-app/logs
sudo chown -R www-data:www-data /path/to/quiz-app
sudo chmod -R 755 /path/to/quiz-app
sudo chmod -R 775 /path/to/quiz-app/logs
sudo chmod -R 775 /path/to/quiz-app/uploads
sudo chmod -R 775 /path/to/quiz-app/instance

# 启动服务
sudo systemctl start quiz-app

# 设置开机自启
sudo systemctl enable quiz-app

# 查看服务状态
sudo systemctl status quiz-app
```

### 7. 配置 SSL（可选但推荐）

使用 Let's Encrypt 免费 SSL 证书：

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

配置完成后，取消注释 Nginx 配置文件中的 HTTPS 部分，并注释掉 HTTP 重定向配置。

### 8. 防火墙配置

```bash
# 允许 HTTP 和 HTTPS 流量
sudo ufw allow 'Nginx Full'
# 或者分别配置
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙（如果尚未启用）
sudo ufw enable
```

## 常用管理命令

### Gunicorn 服务管理

```bash
# 启动服务
sudo systemctl start quiz-app

# 停止服务
sudo systemctl stop quiz-app

# 重启服务
sudo systemctl restart quiz-app

# 重新加载配置（不中断服务）
sudo systemctl reload quiz-app

# 查看服务状态
sudo systemctl status quiz-app

# 查看日志
sudo journalctl -u quiz-app -f
```

### Nginx 管理

```bash
# 测试配置
sudo nginx -t

# 重新加载配置
sudo systemctl reload nginx

# 重启 Nginx
sudo systemctl restart nginx

# 查看访问日志
sudo tail -f /var/log/nginx/quiz_app_access.log

# 查看错误日志
sudo tail -f /var/log/nginx/quiz_app_error.log
```

### 应用日志

```bash
# Gunicorn 访问日志
tail -f logs/gunicorn_access.log

# Gunicorn 错误日志
tail -f logs/gunicorn_error.log

# 应用日志
tail -f logs/app.log
```

## 性能优化建议

1. **Worker 进程数**：根据 CPU 核心数调整 `workers` 配置
   ```python
   workers = (2 * CPU核心数) + 1
   ```

2. **数据库连接池**：如果使用数据库，配置连接池大小

3. **静态文件缓存**：Nginx 已配置 30 天缓存，可根据需要调整

4. **Gzip 压缩**：Nginx 已启用 Gzip 压缩

5. **限流配置**：生产环境建议使用 Redis 作为限流存储
   ```bash
   # 安装 Redis
   sudo apt install -y redis-server
   
   # 在 .env 中配置
   RATELIMIT_STORAGE_URL=redis://localhost:6379/0
   ```

## 故障排查

### 服务无法启动

1. 检查 systemd 日志：
   ```bash
   sudo journalctl -u quiz-app -n 50
   ```

2. 检查 Gunicorn 错误日志：
   ```bash
   tail -f logs/gunicorn_error.log
   ```

3. 检查权限：
   ```bash
   ls -la /path/to/quiz-app
   ```

### 502 Bad Gateway

1. 检查 Gunicorn 是否运行：
   ```bash
   sudo systemctl status saksk_ti
   ```

2. 检查端口是否监听：
   ```bash
   sudo netstat -tlnp | grep 8000
   ```

3. 检查 Nginx 错误日志：
   ```bash
   sudo tail -f /var/log/nginx/quiz_app_error.log
   ```

### 静态文件 404

1. 检查 Nginx 配置中的 `alias` 路径是否正确

2. 检查静态文件目录权限：
   ```bash
   ls -la /path/to/quiz-app/static
   ```

## 更新部署

更新应用代码后：

```bash
# 进入项目目录
cd /path/to/quiz-app

# 激活虚拟环境
source venv/bin/activate

# 拉取最新代码
git pull  # 如果使用 Git

# 安装/更新依赖
pip install -r requirements.txt

# 重启服务
sudo systemctl restart quiz-app

# 检查服务状态
sudo systemctl status quiz-app
```

## 安全建议

1. **SECRET_KEY**：必须使用强随机密钥，不要使用默认值

2. **HTTPS**：生产环境必须启用 HTTPS

3. **防火墙**：只开放必要的端口（80, 443）

4. **用户权限**：使用非 root 用户运行应用（www-data）

5. **定期更新**：保持系统和依赖包更新

6. **日志监控**：定期检查日志，发现异常

7. **备份**：定期备份数据库和重要文件

## 监控建议

1. 使用 `systemctl status` 监控服务状态

2. 使用 `htop` 或 `top` 监控系统资源

3. 配置日志轮转，避免日志文件过大

4. 考虑使用监控工具（如 Prometheus + Grafana）

## 联系和支持

如有问题，请查看项目日志或联系技术支持。

