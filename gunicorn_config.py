# -*- coding: utf-8 -*-
"""
Gunicorn 配置文件 - 生产环境 WSGI 服务器配置
"""
import os
import multiprocessing

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 服务器套接字
bind = "127.0.0.1:8000"  # 只监听本地，通过 Nginx 代理
backlog = 2048  # 挂起连接的最大数量

# Worker 进程配置
workers = multiprocessing.cpu_count() * 2 + 1  # 推荐的 worker 数量
worker_class = "sync"  # 同步 worker，适合 I/O 密集型应用
worker_connections = 1000  # 每个 worker 的最大并发连接数
timeout = 30  # Worker 超时时间（秒）
keepalive = 2  # Keep-alive 连接时间（秒）

# 进程命名
proc_name = "quiz_app_gunicorn"

# 日志配置
accesslog = os.path.join(BASE_DIR, "logs", "gunicorn_access.log")
errorlog = os.path.join(BASE_DIR, "logs", "gunicorn_error.log")
loglevel = "info"  # debug, info, warning, error, critical
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程文件（用于 systemd 管理）
pidfile = os.path.join(BASE_DIR, "logs", "gunicorn.pid")

# 用户和组（生产环境建议使用非 root 用户运行）
# user = "www-data"
# group = "www-data"

# 工作目录
chdir = BASE_DIR

# Python 路径
pythonpath = BASE_DIR

# 预加载应用（提升性能，但会占用更多内存）
preload_app = True

# 最大请求数（防止内存泄漏，达到后重启 worker）
max_requests = 1000
max_requests_jitter = 50  # 随机抖动，避免所有 worker 同时重启

# 优雅重启超时时间
graceful_timeout = 30

# 进程守护模式（由 systemd 管理时设为 False）
daemon = False

# 环境变量（这些会被 systemd 服务文件中的环境变量覆盖）
# 但可以作为备用
import os
if not os.environ.get('FLASK_ENV') and not os.environ.get('ENVIRONMENT'):
    os.environ['FLASK_ENV'] = 'production'
    os.environ['ENVIRONMENT'] = 'production'

# Worker 临时目录（用于临时文件）
tmp_upload_dir = os.path.join(BASE_DIR, "tmp")
if not os.path.exists(tmp_upload_dir):
    os.makedirs(tmp_upload_dir, exist_ok=True)

