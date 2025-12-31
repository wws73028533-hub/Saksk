# -*- coding: utf-8 -*-
"""
Gunicorn 配置文件
用于生产环境部署
"""
import multiprocessing
import os

# 服务器配置
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:5000')
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get('GUNICORN_WORKER_CLASS', 'sync')
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', 1000))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 120))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', 5))

# 日志配置
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', 'logs/access.log')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', 'logs/error.log')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# 进程配置
daemon = False
pidfile = os.environ.get('GUNICORN_PIDFILE', 'gunicorn.pid')
user = os.environ.get('GUNICORN_USER', None)
group = os.environ.get('GUNICORN_GROUP', None)
umask = 0o007

# 性能配置
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', 50))
preload_app = True

# 安全配置
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

