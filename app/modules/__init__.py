# -*- coding: utf-8 -*-
"""
功能模块注册入口
"""
from flask import Flask

def register_all_modules(app: Flask):
    """注册所有功能模块（渐进式迁移，只注册已迁移的模块）"""
    # 按依赖顺序注册（只注册已迁移的模块）
    
    # 已迁移的模块
    try:
        from .auth import init_auth_module
        init_auth_module(app)
        app.logger.info('✓ auth模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ auth模块注册失败: {e}')
    
    try:
        from .main import init_main_module
        init_main_module(app)
        app.logger.info('✓ main模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ main模块注册失败: {e}')
    
    try:
        from .quiz import init_quiz_module
        init_quiz_module(app)
        app.logger.info('✓ quiz模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ quiz模块注册失败: {e}')
    
    try:
        from .exam import init_exam_module
        init_exam_module(app)
        app.logger.info('✓ exam模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ exam模块注册失败: {e}')
    
    try:
        from .user import init_user_module
        init_user_module(app)
        app.logger.info('✓ user模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ user模块注册失败: {e}')
    
    try:
        from .chat import init_chat_module
        init_chat_module(app)
        app.logger.info('✓ chat模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ chat模块注册失败: {e}')
    
    try:
        from .notifications import init_notifications_module
        init_notifications_module(app)
        app.logger.info('✓ notifications模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ notifications模块注册失败: {e}')
    
    try:
        from .coding import init_coding_module
        init_coding_module(app)
        app.logger.info('✓ coding模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ coding模块注册失败: {e}')
    
    try:
        from .admin import init_admin_module
        init_admin_module(app)
        app.logger.info('✓ admin模块已注册')
    except ImportError as e:
        app.logger.warning(f'✗ admin模块注册失败: {e}')
    
    # 所有模块已迁移完成
    # try:
    #     from .main import init_main_module
    #     init_main_module(app)
    # except ImportError:
    #     pass
    # 
    # try:
    #     from .quiz import init_quiz_module
    #     init_quiz_module(app)
    # except ImportError:
    #     pass
    # 
    # try:
    #     from .exam import init_exam_module
    #     init_exam_module(app)
    # except ImportError:
    #     pass
    # 
    # try:
    #     from .user import init_user_module
    #     init_user_module(app)
    # except ImportError:
    #     pass
    # 
    # try:
    #     from .chat import init_chat_module
    #     init_chat_module(app)
    # except ImportError:
    #     pass
    # 
    # try:
    #     from .coding import init_coding_module
    #     init_coding_module(app)
    # except ImportError:
    #     pass
    # 
    # try:
    #     from .notifications import init_notifications_module
    #     init_notifications_module(app)
    # except ImportError:
    #     pass
    # 
    # try:
    #     from .admin import init_admin_module
    #     init_admin_module(app)
    # except ImportError:
    #     pass
    
    app.logger.info('模块注册完成')

