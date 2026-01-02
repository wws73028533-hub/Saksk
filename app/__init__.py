# -*- coding: utf-8 -*-
"""
应用工厂模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask

# 加载.env文件（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv未安装时忽略

from .core.config import config
from .core.extensions import init_extensions
from .core.utils.database import close_db, init_db


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
    # 显式指定 static_folder，避免在某些运行方式/工作目录下出现 /static 404
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'), static_url_path='/static')
    
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
    
    # 注册错误处理器
    _register_error_handlers(app)
    
    # 初始化数据库
    with app.app_context():
        init_db()
    
    # 启动后台任务
    _start_background_tasks(app)
    
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
        # 根据环境设置日志级别
        log_level = getattr(app.config, 'LOG_LEVEL', logging.INFO)
        if app.config.get('DEBUG'):
            log_level = logging.DEBUG
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level)
        
        # 生产环境日志提示
        if not app.config.get('DEBUG'):
            app.logger.info(f'生产环境已启动，日志级别: {logging.getLevelName(log_level)}')
        
        # 生产环境不显示详细错误信息
        if not app.config.get('DEBUG'):
            app.logger.info(f'生产环境已启动，日志级别: {logging.getLevelName(log_level)}')


def _register_blueprints(app):
    """注册所有蓝图"""
    # 注册所有模块
    from .modules import register_all_modules
    register_all_modules(app)


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
    from .core.utils.database import get_db
    
    @app.before_request
    def enforce_login():
        path = request.path or ''
        
        # 已登录的会话校验
        if session.get('user_id'):
            try:
                uid = session.get('user_id')
                conn = get_db()
                
                # 检查 is_subject_admin 字段是否存在
                try:
                    user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
                    has_subject_admin_field = 'is_subject_admin' in user_cols
                except Exception:
                    has_subject_admin_field = False
                
                if has_subject_admin_field:
                    query = 'SELECT is_locked, is_admin, is_subject_admin, is_notification_admin, session_version FROM users WHERE id=?'
                else:
                    # 检查是否有 is_notification_admin 字段
                    try:
                        user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
                        has_notification_admin_field = 'is_notification_admin' in user_cols
                        if has_notification_admin_field:
                            query = 'SELECT is_locked, is_admin, is_notification_admin, session_version FROM users WHERE id=?'
                        else:
                            query = 'SELECT is_locked, is_admin, session_version FROM users WHERE id=?'
                    except Exception:
                        query = 'SELECT is_locked, is_admin, session_version FROM users WHERE id=?'
                
                row = conn.execute(query, (uid,)).fetchone()
                
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
                
                # 更新session中的权限信息（确保权限同步）
                session['is_admin'] = bool(row['is_admin'])
                session['is_subject_admin'] = bool(row['is_subject_admin']) if has_subject_admin_field and 'is_subject_admin' in row.keys() else False
                
                # 检查用户是否绑定邮箱（排除管理员和绑定邮箱相关的API）
                if not session.get('is_admin'):
                    # 检查邮箱绑定是否必需（从系统配置读取）
                    from app.modules.admin.services.system_config_service import SystemConfigService
                    email_bind_required = SystemConfigService.get_email_bind_required_config()
                    
                    # 如果配置为不需要绑定邮箱，则跳过限制检查
                    if email_bind_required:
                        # 检查邮箱字段是否存在
                        try:
                            user_cols = [r['name'] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
                            has_email_field = 'email' in user_cols
                        except Exception:
                            has_email_field = False
                        
                        if has_email_field:
                            user_email = conn.execute('SELECT email FROM users WHERE id = ?', (uid,)).fetchone()
                            email_bound = user_email and user_email[0] and user_email[0].strip()
                            
                            # 如果未绑定邮箱，限制功能访问（允许的路径）
                            if not email_bound:
                                # 允许访问的路径（绑定邮箱相关）
                                allowed_paths = {
                                    '/',  # 首页（用于显示弹窗）
                                    '/terms',  # 服务协议页面
                                    '/privacy',  # 隐私保护协议页面
                                    '/api/email/send-bind-code',  # 发送绑定验证码
                                    '/api/email/bind',  # 绑定邮箱
                                    '/api/logout',  # 登出
                                    '/logout',  # 登出页面
                                    '/static',  # 静态资源
                                }
                                
                                # 检查是否是允许的路径
                                is_allowed = False
                                for allowed_path in allowed_paths:
                                    if path == allowed_path or path.startswith(allowed_path):
                                        is_allowed = True
                                        break
                                
                                if not is_allowed:
                                    if path.startswith('/api'):
                                        return jsonify({
                                            'status': 'error',
                                            'message': '请先绑定邮箱后才能使用此功能',
                                            'code': 'EMAIL_NOT_BOUND'
                                        }), 403
                                    # 页面请求：重定向到首页（会显示绑定弹窗）
                                    return redirect('/')
                
                # 更新用户最后活动时间（排除静态资源请求）
                if not path.startswith('/static') and not path.endswith('.ico'):
                    conn.execute(
                        'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?',
                        (uid,)
                    )
                    conn.commit()
            except Exception as e:
                # 记录错误但不中断请求
                app.logger.warning(f"会话验证异常: {e}", exc_info=True)
                pass
            
            # 管理后台权限校验
            if path.startswith('/admin') or path.startswith('/admin_'):
                is_admin_user = session.get('is_admin')
                is_subject_admin_user = session.get('is_subject_admin')
                is_notification_admin_user = session.get('is_notification_admin')
                
                # 科目管理员允许访问的路由（科目和题集管理）
                # 匹配规则：
                # 1. /admin/subjects 及其子路径
                # 2. /admin/api/subjects 及其子路径
                # 3. /admin/questions 及其子路径（包括 /admin/questions/import, /admin/questions/export 等）
                # 4. /admin/api/questions 相关路径（通过路径包含判断）
                # 5. /admin/download_template（Excel模板下载）
                is_subject_admin_path = (
                    path.startswith('/admin/subjects') or
                    path.startswith('/admin/api/subjects') or
                    path.startswith('/admin/questions') or
                    path == '/admin/types' or  # 题型列表API
                    path == '/admin/download_template' or
                    '/api/subjects' in path or
                    '/api/questions' in path
                )
                
                # 通知管理员允许访问的路由（通知管理）
                # 匹配规则：
                # 1. /admin/notifications 及其子路径
                # 2. /admin/api/notifications 及其子路径
                # 3. /admin/popups 及其子路径（弹窗管理是通知管理的一部分）
                # 4. /admin/api/popups 及其子路径
                # 5. /admin 和 /admin/dashboard（重定向到通知管理）
                is_notification_admin_path = (
                    path.startswith('/admin/notifications') or
                    path.startswith('/admin/api/notifications') or
                    path.startswith('/admin/popups') or
                    path.startswith('/admin/api/popups') or
                    '/api/notifications' in path or
                    '/api/popups' in path
                )
                
                # 通知管理员访问 /admin 或 /admin/dashboard 时，重定向到通知管理页面
                if (path == '/admin' or path == '/admin/') and is_notification_admin_user and not is_admin_user:
                    return redirect('/admin/notifications')
                if path == '/admin/dashboard' and is_notification_admin_user and not is_admin_user:
                    return redirect('/admin/notifications')
                
                # 如果是科目管理员路径，允许科目管理员和管理员访问
                if is_subject_admin_path:
                    if not (is_admin_user or is_subject_admin_user):
                        if path.startswith('/admin/'):
                            return jsonify({'status': 'forbidden', 'message': '需要管理员或科目管理员权限'}), 403
                        return redirect('/')
                # 如果是通知管理员路径，允许通知管理员和管理员访问
                elif is_notification_admin_path:
                    if not (is_admin_user or is_notification_admin_user):
                        if path.startswith('/admin/'):
                            return jsonify({'status': 'forbidden', 'message': '需要管理员或通知管理员权限'}), 403
                        return redirect('/')
                # 其他管理后台路由需要管理员权限
                elif not is_admin_user:
                    if path.startswith('/admin/'):
                        return jsonify({'status': 'forbidden', 'message': '需要管理员权限'}), 403
                    return redirect('/')
            return

        # 未登录白名单（只允许首页和登录）
        allow_paths = {
            '/', '/login', '/favicon.ico',
            '/terms',  # 服务协议页面
            '/privacy',  # 隐私保护协议页面
            '/api/login',
            '/api/email/send-login-code',  # 发送登录验证码（无需登录，支持自动注册）
            '/api/email/login',  # 验证码登录（无需登录，支持自动注册）
            '/api/forgot-password/send-code',  # 发送忘记密码验证码（无需登录）
            '/api/forgot-password/reset'  # 重置密码（无需登录）
        }
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

        # 通知 API（以及页面）需要登录：历史通知属于用户中心功能
        if path.startswith('/api/notifications') or path == '/notifications':
            return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
        
        # 需要登录的功能路径
        login_required_paths = {
            '/quiz': 'quiz',
            '/exams': 'exams', 
            '/profile': 'profile',
            '/search': 'search',
            '/coding': '编程模式'
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
            '/api/exams',
            '/coding/api'
        ]
        
        for api_path in login_required_apis:
            if path.startswith(api_path):
                return jsonify({'status': 'unauthorized', 'message': '请先登录后使用此功能'}), 401
        
        if path.startswith('/api'):
            return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
        return redirect('/login')


def _register_error_handlers(app):
    """注册错误处理器"""
    from .core.errors import register_error_handlers
    register_error_handlers(app)


def _start_background_tasks(app):
    """启动后台任务"""
    from .core.tasks import start_background_tasks
    start_background_tasks(app)
