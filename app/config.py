# -*- coding: utf-8 -*-
"""
应用配置模块
"""
import os


class Config:
    """基础配置类"""
    # 基础路径
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
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
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = "10000 per day;1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境应该使用更强的密钥
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24).hex()


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

