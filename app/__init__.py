# -*- coding: utf-8 -*-
"""
应用工厂模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask

from .config import config
from .extensions import init_extensions
from .utils.database import close_db, init_db


def create_app(config_name=None):
    """
    应用工厂函数
    
    Args:
        config_name: 配置名称 ('development', 'production', 'testing')
        
    Returns:
        Flask: Flask应用实例
    """
    # 如果没有指定配置，从环境变量获取
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # 创建Flask应用
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 确保必要的目录存在
    _ensure_directories(app)
    
    # 初始化扩展
    init_extensions(app)
    
    # 配置日志
    _setup_logging(app)
    
    # 注册数据库关闭函数
    app.teardown_appcontext(close_db)
    
    # 注册蓝图
    _register_blueprints(app)
    
    # 注册上下文处理器
    _register_context_processors(app)
    
    # 注册请求钩子
    _register_before_request(app)
    
    # 初始化数据库
    with app.app_context():
        init_db()
    
    app.logger.info('应用启动完成')
    
    return app


def _ensure_directories(app):
    """确保必要的目录存在"""
    dirs = [
        app.config['LOG_DIR'],
        app.config['UPLOAD_FOLDER'],
        os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'),
        os.path.join(app.config['UPLOAD_FOLDER'], 'question_images'),
        os.path.dirname(app.config['DATABASE_PATH'])
    ]
    
    for dir_path in dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)


def _setup_logging(app):
    """配置日志系统"""
    if not app.debug and not app.testing:
        file_handler = RotatingFileHandler(
            os.path.join(app.config['LOG_DIR'], 'app.log'),
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)


def _register_blueprints(app):
    """注册所有蓝图"""
    from .routes import register_all_routes
    register_all_routes(app)


def _register_context_processors(app):
    """注册上下文处理器"""
    from flask import session
    
    @app.context_processor
    def inject_user():
        return {
            'logged_in': bool(session.get('user_id')),
            'username': session.get('username'),
            'user_id': session.get('user_id'),
            'is_admin': bool(session.get('is_admin'))
        }


def _register_before_request(app):
    """注册请求前钩子"""
    from flask import request, session, redirect, url_for, jsonify
    from .utils.database import get_db
    
    @app.before_request
    def enforce_login():
        path = request.path or ''
        
        # 已登录的会话校验
        if session.get('user_id'):
            try:
                uid = session.get('user_id')
                conn = get_db()
                row = conn.execute(
                    'SELECT is_locked, session_version FROM users WHERE id=?',
                    (uid,)
                ).fetchone()
                
                if not row or row['is_locked']:
                    session.clear()
                    if path.startswith('/api'):
                        return jsonify({'status':'unauthorized','message':'会话无效或已被锁定'}), 401
                    return redirect('/login')
                
                if session.get('session_version') is not None and \
                   session.get('session_version') != row['session_version']:
                    session.clear()
                    if path.startswith('/api'):
                        return jsonify({'status':'unauthorized','message':'会话已失效，请重新登录'}), 401
                    return redirect('/login')
                
                # 更新用户最后活动时间（排除静态资源请求）
                if not path.startswith('/static') and not path.endswith('.ico'):
                    conn.execute(
                        'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?',
                        (uid,)
                    )
                    conn.commit()
            except Exception:
                pass
            
            # 管理后台权限校验
            if path.startswith('/admin') or path.startswith('/admin_'):
                if not session.get('is_admin'):
                    if path.startswith('/admin/'):
                        return jsonify({'status': 'forbidden', 'message': '需要管理员权限'}), 403
                    return redirect('/')
            return

        # 未登录白名单（只允许首页和登录注册）
        allow_paths = {'/', '/login', '/register', '/api/login', '/api/register', '/favicon.ico'}
        if path in allow_paths or path.startswith('/static'):
            return

        # 公开API（需要检查参数）
        if path == '/api/questions/count':
            # 检查 mode 参数，如果是 favorites 或 mistakes 模式，需要登录
            mode = request.args.get('mode', '').lower()
            if mode in ('favorites', 'mistakes'):
                # 这些模式需要登录
                if path.startswith('/api'):
                    return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能'}), 401
                from urllib.parse import quote
                mode_name = '收藏本' if mode == 'favorites' else '错题本'
                login_url = f'/login?from={mode}&redirect={quote(path)}'
                return redirect(login_url)
            # 其他模式允许未登录访问
            return

        if path == '/api/questions/user_counts':
            # 这个 API 允许未登录访问（返回0）
            return

        # 通知 API 允许未登录访问（游客也能看通知）
        if path == '/api/notifications':
            return
        
        # 需要登录的功能路径
        login_required_paths = {
            '/quiz': 'quiz',
            '/exams': 'exams', 
            '/profile': 'profile',
            '/search': 'search'
        }
        
        for required_path, tip_key in login_required_paths.items():
            if path.startswith(required_path):
                if path.startswith('/api'):
                    return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能'}), 401
                # 页面请求：重定向到登录页并显示提示
                # 构建登录URL，包含来源和跳转信息
                from urllib.parse import quote
                # 根据路径确定提示信息
                if required_path == '/quiz':
                    mode = request.args.get('mode', 'quiz').lower()
                    if mode == 'memo':
                        tip_key = '背题'
                    elif mode == 'favorites':
                        tip_key = '收藏本'
                    elif mode == 'mistakes':
                        tip_key = '错题本'
                    elif mode == 'exam':
                        tip_key = '考试'
                    else:
                        tip_key = '刷题'
                login_url = f'/login?from={tip_key}&redirect={quote(path)}'
                return redirect(login_url)
        
        # 需要登录的 API 路径
        login_required_apis = [
            '/api/favorite',
            '/api/record_result',
            '/api/progress',
            '/api/exams'
        ]
        
        for api_path in login_required_apis:
            if path.startswith(api_path):
                return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能'}), 401
        
        if path.startswith('/api'):
            return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
        return redirect('/login')
