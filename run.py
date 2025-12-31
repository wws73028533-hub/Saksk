# -*- coding: utf-8 -*-
"""
应用启动文件 - 新版模块化结构
"""
import os
from app import create_app

# 从环境变量获取配置名称，默认为开发环境
config_name = os.environ.get('FLASK_ENV', 'development')

# 创建应用实例
app = create_app(config_name=config_name)

if __name__ == '__main__':
    # 从环境变量获取配置
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = app.config.get('DEBUG', False)
    
    print('='*60)
    print('  题库系统 - 模块化版本')
    print('='*60)
    print(f'  环境: {config_name}')
    print(f'  地址: http://{host}:{port}')
    print(f'  调试: {debug}')
    print('='*60)
    
    # 开发环境提示
    if config_name == 'development':
        print('\n💡 开发模式已启用')
        print('   - DEBUG 模式: 已开启')
        print('   - 邮件验证码: 控制台输出（不发送真实邮件）')
        print('   - 热重载: 已启用\n')
    
    # 生产环境警告
    if config_name == 'production':
        if not os.environ.get('SECRET_KEY'):
            print('\n⚠️  警告: SECRET_KEY 未设置，请设置环境变量！')
        if debug:
            print('\n⚠️  警告: 生产环境不应启用 DEBUG 模式！')
        print('\n💡 提示: 生产环境建议使用 Gunicorn 或 uWSGI 部署')
        print('   启动命令: gunicorn -c gunicorn_config.py run:app\n')
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )

