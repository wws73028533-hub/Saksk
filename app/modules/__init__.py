# -*- coding: utf-8 -*-
"""
功能模块注册入口
"""
from flask import Flask


def register_all_modules(app: Flask):
    """注册所有功能模块（渐进式迁移，只注册已迁移的模块）"""

    def _init_module(import_path: str, init_name: str, label: str):
        """初始化模块：开发环境失败直接抛出，避免服务以缺失模块的状态继续运行。"""
        try:
            module = __import__(import_path, fromlist=[init_name])
            init_func = getattr(module, init_name)
            init_func(app)
            app.logger.info(f'✓ {label}模块已注册')
        except Exception as e:
            # 记录完整堆栈，方便定位 import 或初始化失败原因
            app.logger.exception(f'✗ {label}模块注册失败: {e}')
            if app.config.get('DEBUG'):
                raise

    # 按依赖顺序注册
    _init_module('app.modules.auth', 'init_auth_module', 'auth')
    _init_module('app.modules.main', 'init_main_module', 'main')
    _init_module('app.modules.quiz', 'init_quiz_module', 'quiz')
    _init_module('app.modules.exam', 'init_exam_module', 'exam')
    _init_module('app.modules.user', 'init_user_module', 'user')
    _init_module('app.modules.chat', 'init_chat_module', 'chat')
    _init_module('app.modules.notifications', 'init_notifications_module', 'notifications')
    _init_module('app.modules.popups', 'init_popups_module', 'popups')
    _init_module('app.modules.coding', 'init_coding_module', 'coding')
    _init_module('app.modules.admin', 'init_admin_module', 'admin')

    app.logger.info('模块注册完成')

