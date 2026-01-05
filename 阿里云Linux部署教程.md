# 题库系统 - 阿里云 Linux 3.21.04 部署教程

本教程将指导您将题库系统部署到阿里云 Linux 3.21.04 服务器上。

---

## 📋 目录

- [前置要求](#前置要求)
- [系统准备](#系统准备)
- [Python 环境安装](#python-环境安装)
- [项目部署](#项目部署)
- [环境配置](#环境配置)
- [Gunicorn 配置](#gunicorn-配置)
- [systemd 服务配置](#systemd-服务配置)
- [Nginx 反向代理配置（可选）](#nginx-反向代理配置可选)
- [防火墙配置](#防火墙配置)
- [启动服务](#启动服务)
- [验证部署](#验证部署)
- [维护和监控](#维护和监控)
- [常见问题](#常见问题)

---

## 前置要求

- 阿里云 Linux 3.21.04 服务器（已配置 root 或具有 sudo 权限的用户）
- 服务器可以访问互联网（用于下载依赖）
- 域名（可选，如使用 HTTPS）
- 邮件服务账号（用于发送验证码邮件）

---

## 系统准备

### 1. 更新系统

```bash
# 更新系统包
sudo yum update -y

# 安装必要的工具
sudo yum install -y git wget curl vim
```

### 2. 创建应用用户（推荐）

为了安全，建议创建一个专门的用户来运行应用：

```bash
# 创建用户（如果不存在）
sudo useradd -m -s /bin/bash saksk

# 或者如果用户已存在，设置密码
sudo passwd saksk
```

---

## Python 环境安装

项目需要 Python 3.11 或更高版本。阿里云 Linux 3.21.04 默认可能不包含 Python 3.11，我们需要从源码编译安装或使用 pyenv。

### 方法一：使用 pyenv（推荐）

```bash
# 切换到应用用户
sudo su - saksk

# 安装编译依赖
sudo yum groupinstall -y "Development Tools"
sudo yum install -y openssl-devel bzip2-devel libffi-devel readline-devel sqlite-devel xz-devel

# 安装 pyenv
curl https://pyenv.run | bash

# 配置环境变量
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# 重新加载 shell 配置
source ~/.bashrc

# 安装 Python 3.11.9（或最新版本）
pyenv install 3.11.9

# 设置为全局默认版本
pyenv global 3.11.9

# 验证安装
python --version  # 应该显示 Python 3.11.9
pip --version
```

### 方法二：使用编译安装（如果 pyenv 不可用）

```bash
# 安装编译依赖
sudo yum groupinstall -y "Development Tools"
sudo yum install -y openssl-devel bzip2-devel libffi-devel readline-devel sqlite-devel xz-devel

# 下载 Python 3.11.9 源码
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar xzf Python-3.11.9.tgz
cd Python-3.11.9

# 配置和编译（以用户身份）
./configure --prefix=$HOME/python3.11 --enable-optimizations
make -j$(nproc)
make altinstall

# 添加到 PATH
echo 'export PATH="$HOME/python3.11/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证安装
python3.11 --version
pip3.11 --version
```

---

## 项目部署

### 1. 创建项目目录

```bash
# 切换到应用用户（如果还没切换）
sudo su - saksk

# 创建项目目录
mkdir -p ~/projects
cd ~/projects
```

### 2. 上传项目代码

您可以选择以下任一方式上传代码：

#### 方式 A：使用 Git（推荐）

```bash
# 克隆项目（替换为您的仓库地址）
git clone <your-repo-url> Saksk_1_Ti
cd Saksk_1_Ti
```

#### 方式 B：使用 SCP 上传

在本地机器上执行：

```bash
# 将项目目录压缩
tar -czf saksk_ti.tar.gz Saksk_1_Ti/

# 上传到服务器
scp saksk_ti.tar.gz saksk@your-server-ip:~/

# 在服务器上解压
ssh saksk@your-server-ip
cd ~
tar -xzf saksk_ti.tar.gz
mv Saksk_1_Ti ~/projects/
cd ~/projects/Saksk_1_Ti
```

#### 方式 C：使用 FTP/SFTP

使用 FileZilla 或其他 SFTP 工具将项目文件上传到 `~/projects/Saksk_1_Ti/`

### 3. 创建虚拟环境

```bash
# 进入项目目录
cd ~/projects/Saksk_1_Ti

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

### 4. 安装项目依赖

```bash
# 安装依赖（确保虚拟环境已激活）
pip install -r requirements.txt
```

---

## 环境配置

### 1. 创建环境变量文件

```bash
# 在项目根目录创建 .env 文件（可选，用于开发环境）
# 生产环境建议使用 systemd 环境变量配置

# 生成 SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 复制输出的密钥，稍后使用
```

### 2. 创建必要的目录

```bash
# 确保必要的目录存在
mkdir -p instance logs uploads/avatars uploads/question_images uploads/chat static/icons

# 设置目录权限
chmod -R 755 uploads
chmod -R 755 logs
```

### 3. 初始化数据库

应用会在首次启动时自动创建数据库。您也可以手动初始化：

```bash
# 激活虚拟环境（如果还没激活）
source venv/bin/activate

# 运行应用一次以初始化数据库（可选）
# python run.py
# 然后按 Ctrl+C 停止
```

---

## Gunicorn 配置

### 1. 创建 Gunicorn 配置文件

在项目根目录创建 `gunicorn_config.py`：

```bash
cd ~/projects/Saksk_1_Ti
vim gunicorn_config.py
```

配置文件内容：

```python
# -*- coding: utf-8 -*-
"""
Gunicorn 配置文件
"""
import multiprocessing
import os

# 服务器 socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker 进程
workers = multiprocessing.cpu_count() * 2 + 1  # 推荐公式
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 日志
accesslog = os.path.join(os.path.dirname(__file__), "logs", "gunicorn_access.log")
errorlog = os.path.join(os.path.dirname(__file__), "logs", "gunicorn_error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "saksk_ti"

# 服务器机制
daemon = False
pidfile = os.path.join(os.path.dirname(__file__), "logs", "gunicorn.pid")
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL（如果使用 HTTPS，取消注释并配置）
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
```

保存并退出（`:wq`）。

### 2. 测试 Gunicorn 启动

```bash
# 激活虚拟环境
source venv/bin/activate

# 设置环境变量（临时测试）
export FLASK_ENV=production
export SECRET_KEY="your-generated-secret-key-here"

# 测试启动 Gunicorn
gunicorn -c gunicorn_config.py run:app

# 如果成功，应该看到 Gunicorn 启动信息
# 在另一个终端测试访问
curl http://127.0.0.1:8000

# 测试完成后按 Ctrl+C 停止
```

---

## systemd 服务配置

### 1. 创建 systemd 服务文件

```bash
# 使用 root 权限创建服务文件
sudo vim /etc/systemd/system/saksk-ti.service
```

服务文件内容：

```ini
[Unit]
Description=Saksk TI Quiz Application (Gunicorn)
After=network.target

[Service]
Type=notify
User=saksk
Group=saksk
WorkingDirectory=/home/saksk/projects/Saksk_1_Ti
Environment="PATH=/home/saksk/projects/Saksk_1_Ti/venv/bin"
Environment="FLASK_ENV=production"
Environment="ENVIRONMENT=production"

# 生产环境必须设置 SECRET_KEY（请替换为实际生成的密钥）
Environment="SECRET_KEY=your-secret-key-here"

# 邮件配置（根据实际情况修改）
Environment="MAIL_SERVER=smtp.qq.com"
Environment="MAIL_PORT=587"
Environment="MAIL_USE_TLS=true"
Environment="MAIL_USERNAME=your_email@qq.com"
Environment="MAIL_PASSWORD=your_email_authorization_code"
Environment="MAIL_DEFAULT_SENDER=your_email@qq.com"
Environment="MAIL_DEFAULT_SENDER_NAME=系统通知"

# HTTPS 环境设置（如果使用 HTTPS，设置为 true）
# Environment="SESSION_COOKIE_SECURE=true"

# Gunicorn 启动命令
ExecStart=/home/saksk/projects/Saksk_1_Ti/venv/bin/gunicorn -c gunicorn_config.py run:app

# 重启命令
ExecReload=/bin/kill -s HUP $MAINPID

# 优雅停止
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

# 资源限制
LimitNOFILE=65535

# 自动重启配置
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**重要提示：**
- 将 `your-secret-key-here` 替换为之前生成的 SECRET_KEY
- 修改邮件配置为您的实际邮箱信息
- 确认 `WorkingDirectory` 和 `PATH` 路径正确

### 2. 重载 systemd 并启动服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable saksk-ti.service

# 启动服务
sudo systemctl start saksk-ti.service

# 检查服务状态
sudo systemctl status saksk-ti.service

# 查看日志
sudo journalctl -u saksk-ti.service -f
```

### 3. 常用 systemd 命令

```bash
# 启动服务
sudo systemctl start saksk-ti

# 停止服务
sudo systemctl stop saksk-ti

# 重启服务
sudo systemctl restart saksk-ti

# 重新加载配置（不中断服务）
sudo systemctl reload saksk-ti

# 查看状态
sudo systemctl status saksk-ti

# 查看日志
sudo journalctl -u saksk-ti -n 100  # 查看最后 100 行
sudo journalctl -u saksk-ti -f      # 实时查看日志
```

---

## Nginx 反向代理配置（可选）

使用 Nginx 作为反向代理可以提供更好的性能、静态文件服务和 HTTPS 支持。

### 1. 安装 Nginx

```bash
sudo yum install -y nginx
```

### 2. 配置 Nginx

```bash
# 创建配置文件
sudo vim /etc/nginx/conf.d/saksk-ti.conf
```

配置文件内容（HTTP）：

```nginx
upstream saksk_ti {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;  # 替换为您的域名或 IP

    client_max_body_size 16M;

    # 静态文件服务
    location /static {
        alias /home/saksk/projects/Saksk_1_Ti/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件服务
    location /uploads {
        alias /home/saksk/projects/Saksk_1_Ti/uploads;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 反向代理到 Gunicorn
    location / {
        proxy_pass http://saksk_ti;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

如果使用 HTTPS，配置文件示例：

```nginx
upstream saksk_ti {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS 配置
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置（使用 Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 16M;

    # 静态文件服务
    location /static {
        alias /home/saksk/projects/Saksk_1_Ti/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件服务
    location /uploads {
        alias /home/saksk/projects/Saksk_1_Ti/uploads;
        expires 7d;
        add_header Cache-Control "public";
    }

    # 反向代理到 Gunicorn
    location / {
        proxy_pass http://saksk_ti;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3. 配置 SSL 证书（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo yum install -y certbot python3-certbot-nginx

# 获取证书（需要域名已解析到服务器）
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

### 4. 启动 Nginx

```bash
# 测试配置
sudo nginx -t

# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# 重启 Nginx（如果已运行）
sudo systemctl restart nginx
```

### 5. 如果使用 HTTPS，更新 systemd 服务

```bash
# 编辑服务文件
sudo vim /etc/systemd/system/saksk-ti.service

# 在 Environment 部分添加：
Environment="SESSION_COOKIE_SECURE=true"

# 重载并重启服务
sudo systemctl daemon-reload
sudo systemctl restart saksk-ti
```

---

## 防火墙配置

### 使用 firewalld（阿里云 Linux 默认）

```bash
# 查看防火墙状态
sudo systemctl status firewalld

# 如果防火墙未启用，可以启用（可选）
sudo systemctl enable firewalld
sudo systemctl start firewalld

# 开放 HTTP 端口
sudo firewall-cmd --permanent --add-service=http

# 开放 HTTPS 端口（如果使用）
sudo firewall-cmd --permanent --add-service=https

# 重新加载防火墙规则
sudo firewall-cmd --reload

# 查看开放的端口
sudo firewall-cmd --list-all
```

### 使用 iptables（如果未使用 firewalld）

```bash
# 开放 HTTP 端口
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT

# 开放 HTTPS 端口（如果使用）
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 保存规则（根据系统选择）
# CentOS/RHEL 7+
sudo service iptables save
# 或者
sudo iptables-save > /etc/iptables/rules.v4
```

### 阿里云安全组配置

如果使用阿里云 ECS，还需要在阿里云控制台配置安全组：

1. 登录阿里云控制台
2. 进入 ECS 实例管理
3. 选择您的实例，点击"安全组"
4. 添加规则：
   - 方向：入方向
   - 协议类型：TCP
   - 端口范围：80/80（HTTP）或 443/443（HTTPS）
   - 授权对象：0.0.0.0/0（或限制为特定 IP）

---

## 启动服务

### 1. 确保所有服务启动

```bash
# 启动应用服务
sudo systemctl start saksk-ti

# 如果使用 Nginx，启动 Nginx
sudo systemctl start nginx

# 检查服务状态
sudo systemctl status saksk-ti
sudo systemctl status nginx  # 如果使用
```

### 2. 验证服务运行

```bash
# 检查 Gunicorn 进程
ps aux | grep gunicorn

# 检查端口监听
sudo netstat -tlnp | grep 8000  # Gunicorn
sudo netstat -tlnp | grep 80    # Nginx（如果使用）

# 测试本地访问
curl http://127.0.0.1:8000
# 或如果使用 Nginx
curl http://127.0.0.1
```

---

## 验证部署

### 1. 浏览器访问

- 如果使用 Nginx：访问 `http://your-domain.com` 或 `http://your-server-ip`
- 如果直接使用 Gunicorn：访问 `http://your-server-ip:8000`（需要开放防火墙端口 8000）

### 2. 检查日志

```bash
# 应用日志
tail -f /home/saksk/projects/Saksk_1_Ti/logs/app.log

# Gunicorn 访问日志
tail -f /home/saksk/projects/Saksk_1_Ti/logs/gunicorn_access.log

# Gunicorn 错误日志
tail -f /home/saksk/projects/Saksk_1_Ti/logs/gunicorn_error.log

# systemd 日志
sudo journalctl -u saksk-ti -f

# Nginx 日志（如果使用）
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 3. 测试功能

1. **访问首页**：确认可以正常访问
2. **邮箱登录**：测试验证码登录功能（需要邮件服务正常配置）
3. **注册新用户**：第一个用户会自动成为管理员
4. **管理后台**：登录后访问 `/admin` 测试管理功能

---

## 维护和监控

### 1. 日志管理

```bash
# 设置日志轮转（可选）
sudo vim /etc/logrotate.d/saksk-ti
```

内容：

```
/home/saksk/projects/Saksk_1_Ti/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 saksk saksk
    sharedscripts
    postrotate
        systemctl reload saksk-ti > /dev/null 2>&1 || true
    endscript
}
```

### 2. 数据库备份

```bash
# 创建备份脚本
vim ~/backup_db.sh
```

内容：

```bash
#!/bin/bash
BACKUP_DIR="/home/saksk/backups"
PROJECT_DIR="/home/saksk/projects/Saksk_1_Ti"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp $PROJECT_DIR/instance/submissions.db $BACKUP_DIR/submissions_$DATE.db

# 保留最近 30 天的备份
find $BACKUP_DIR -name "submissions_*.db" -mtime +30 -delete

echo "备份完成: submissions_$DATE.db"
```

```bash
# 设置执行权限
chmod +x ~/backup_db.sh

# 添加到 crontab（每天凌晨 2 点备份）
crontab -e
# 添加行：
# 0 2 * * * /home/saksk/backup_db.sh >> /home/saksk/backup.log 2>&1
```

### 3. 性能监控

```bash
# 查看进程资源使用
top -p $(pgrep -f gunicorn | head -1)

# 查看系统资源
htop

# 查看网络连接
sudo netstat -anp | grep 8000
```

### 4. 更新代码

```bash
# 切换到应用用户
sudo su - saksk
cd ~/projects/Saksk_1_Ti

# 如果使用 Git
git pull origin main

# 激活虚拟环境
source venv/bin/activate

# 更新依赖（如果有变更）
pip install -r requirements.txt

# 重启服务
sudo systemctl restart saksk-ti

# 检查状态
sudo systemctl status saksk-ti
```

---

## 常见问题

### Q1: Python 版本不匹配

**问题**：系统 Python 版本低于 3.11

**解决**：
- 使用 pyenv 安装 Python 3.11+（推荐）
- 或从源码编译安装 Python 3.11+

### Q2: 服务启动失败

**排查步骤**：
```bash
# 查看详细错误日志
sudo journalctl -u saksk-ti -n 100 --no-pager

# 检查配置文件路径是否正确
ls -la /home/saksk/projects/Saksk_1_Ti/gunicorn_config.py

# 检查虚拟环境
ls -la /home/saksk/projects/Saksk_1_Ti/venv/bin/gunicorn

# 手动测试启动
cd /home/saksk/projects/Saksk_1_Ti
source venv/bin/activate
export FLASK_ENV=production
export SECRET_KEY="test-key"
gunicorn -c gunicorn_config.py run:app
```

### Q3: 端口被占用

**问题**：8000 端口已被其他程序占用

**解决**：
```bash
# 查找占用端口的进程
sudo lsof -i :8000

# 修改 gunicorn_config.py 中的 bind 端口
# 或停止占用端口的程序
```

### Q4: 数据库权限错误

**问题**：无法创建或写入数据库文件

**解决**：
```bash
# 检查目录权限
ls -la /home/saksk/projects/Saksk_1_Ti/instance/

# 设置正确的权限
chmod 755 /home/saksk/projects/Saksk_1_Ti/instance
chown -R saksk:saksk /home/saksk/projects/Saksk_1_Ti/instance
```

### Q5: 邮件发送失败

**问题**：验证码邮件无法发送

**排查步骤**：
1. 检查邮件配置环境变量是否正确
2. 确认邮箱授权码（不是登录密码）正确
3. 测试邮件服务连接：
```python
# 在 Python 环境中测试
python
>>> from app.core.utils.email_service import send_email
>>> send_email('test@example.com', '测试', '测试内容')
```

### Q6: Nginx 502 Bad Gateway

**问题**：Nginx 返回 502 错误

**排查步骤**：
```bash
# 检查 Gunicorn 是否运行
sudo systemctl status saksk-ti

# 检查端口是否正确
sudo netstat -tlnp | grep 8000

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/error.log

# 检查 Nginx 配置
sudo nginx -t
```

### Q7: 静态文件无法加载

**问题**：CSS、JS 等静态资源 404

**解决**：
1. 检查 Nginx 配置中的静态文件路径是否正确
2. 检查文件权限：
```bash
ls -la /home/saksk/projects/Saksk_1_Ti/static
sudo chown -R saksk:saksk /home/saksk/projects/Saksk_1_Ti/static
```

### Q8: 内存不足

**问题**：服务器内存不足导致服务崩溃

**解决**：
1. 减少 Gunicorn worker 数量（在 `gunicorn_config.py` 中）
2. 增加服务器内存
3. 使用 swap 空间（临时方案）

### Q9: 首次访问需要绑定邮箱

**说明**：这是正常行为。系统要求用户绑定邮箱后才能使用全部功能。

### Q10: 如何重置管理员密码

**方法**：
1. 如果是第一个用户，重新注册会自动成为管理员
2. 通过数据库直接修改（需要 SQLite 访问权限）
3. 删除数据库文件重新初始化（会丢失所有数据）

---

## 安全建议

1. **定期更新系统**：
   ```bash
   sudo yum update -y
   ```

2. **使用强 SECRET_KEY**：生产环境必须设置强随机密钥

3. **配置 HTTPS**：使用 Let's Encrypt 配置 SSL 证书

4. **限制 SSH 访问**：配置 SSH 密钥认证，禁用密码登录

5. **配置防火墙**：只开放必要的端口

6. **定期备份数据库**：设置自动备份任务

7. **监控日志**：定期检查错误日志，及时发现异常

8. **使用非 root 用户运行服务**：本教程已使用 `saksk` 用户

---

## 总结

完成以上步骤后，您的题库系统应该已经在阿里云 Linux 3.21.04 服务器上成功部署。如果遇到问题，请参考常见问题部分或查看日志文件进行排查。

**部署检查清单**：
- [ ] Python 3.11+ 已安装
- [ ] 项目代码已上传
- [ ] 虚拟环境已创建并安装依赖
- [ ] 环境变量已配置（SECRET_KEY、邮件等）
- [ ] Gunicorn 配置文件已创建
- [ ] systemd 服务已配置并启动
- [ ] Nginx 已配置（如果使用）
- [ ] 防火墙端口已开放
- [ ] 服务可以正常访问
- [ ] 数据库备份已设置

---

**最后更新**：2025-01-29  
**适用版本**：Saksk TI v2.2.0










