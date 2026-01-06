# -*- coding: utf-8 -*-
"""
应用启动文件 - 新版模块化结构
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from app import create_app

# 从环境变量获取配置名称
# 支持 FLASK_ENV 和 ENVIRONMENT 环境变量
config_name = os.environ.get('FLASK_ENV') or os.environ.get('ENVIRONMENT', 'development')
# 标准化配置名称（development/production/testing）
if config_name not in ['development', 'production', 'testing']:
    # 如果值不是标准值，尝试映射
    config_name_map = {
        'dev': 'development',
        'prod': 'production',
        'test': 'testing',
        'debug': 'development'
    }
    config_name = config_name_map.get(config_name.lower(), 'development')

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
    
    # 生产环境警告和提示
    if config_name == 'production':
        print('\n🔒 生产模式已启用')
        print('   - DEBUG 模式: 已关闭')
        print('   - 邮件验证码: 发送真实邮件')
        if not os.environ.get('SECRET_KEY'):
            print('\n⚠️  警告: SECRET_KEY 未设置，请设置环境变量！')
            print('   生成方式: python scripts/generate_secret_key.py')
        if debug:
            print('\n⚠️  警告: 生产环境不应启用 DEBUG 模式！')
        print('\n💡 提示: 生产环境建议使用 Gunicorn 部署')
        print('   启动命令: gunicorn -c gunicorn_config.py run:app')
        print('   或使用脚本: ./start_production.sh\n')
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )

