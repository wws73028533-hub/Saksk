# -*- coding: utf-8 -*-
"""
应用配置模块
"""
import os


class Config:
    """基础配置类"""
    # 基础路径（项目根目录）
    # __file__ 是 app/core/config.py，需要向上两级到项目根目录
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    # 统一主数据库：submissions.db
    # 数据库文件位于项目根目录的instance文件夹（app文件夹外）
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'submissions.db')
    
    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 日志配置
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Flask配置
    JSON_AS_ASCII = False
    JSONIFY_MIMETYPE = 'application/json; charset=utf-8'
    
    # 会话配置：启用永久会话，默认 7 天
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 天（秒）
    
    # 限流配置
    # 生产环境建议使用 Redis: 'redis://localhost:6379/0'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = "10000 per day;1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True

    # 邮件服务配置
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@example.com'
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME') or '系统通知'
    
    # 邮件服务开关（开发环境可以关闭真实邮件发送）
    MAIL_ENABLED = os.environ.get('MAIL_ENABLED', 'true').lower() in ['true', 'on', '1']
    # 开发环境控制台输出验证码（不发送真实邮件）
    MAIL_CONSOLE_OUTPUT = os.environ.get('MAIL_CONSOLE_OUTPUT', 'false').lower() in ['true', 'on', '1']


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
    # 开发环境默认使用控制台输出
    MAIL_CONSOLE_OUTPUT = os.environ.get('MAIL_CONSOLE_OUTPUT', 'true').lower() in ['true', 'on', '1']


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境必须设置密钥（不允许使用默认值）
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        import warnings
        warnings.warn(
            'SECRET_KEY 未设置！生产环境必须设置 SECRET_KEY 环境变量。'
            '生成方式: python -c "import secrets; print(secrets.token_urlsafe(32))"',
            UserWarning
        )
        # 临时生成，但会显示警告
        SECRET_KEY = os.urandom(24).hex()
    
    # 生产环境禁用控制台输出验证码
    MAIL_CONSOLE_OUTPUT = False


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    
    # 测试数据库
    DATABASE_PATH = os.path.join(Config.BASE_DIR, 'instance', 'test.db')


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

