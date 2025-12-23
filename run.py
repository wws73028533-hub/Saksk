# -*- coding: utf-8 -*-
"""
应用启动文件 - 新版模块化结构
"""
import os


from app import create_app

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    # 从环境变量获取配置
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = app.config['DEBUG']
    
    print('='*60)
    print('  题库系统 - 模块化版本')
    print('='*60)
    print(f'  环境: {os.environ.get("FLASK_ENV", "development")}')
    print(f'  地址: http://{host}:{port}')
    print(f'  调试: {debug}')
    print('='*60)
    print()
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )

