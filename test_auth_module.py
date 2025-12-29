# -*- coding: utf-8 -*-
"""测试auth模块"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    print("[OK] Successfully imported create_app")
    
    app = create_app()
    print("[OK] Successfully created app")
    
    # 检查auth相关路由
    auth_routes = [str(rule) for rule in app.url_map.iter_rules() 
                   if 'auth' in str(rule) or 'login' in str(rule) or 'register' in str(rule)]
    
    print(f"\n[OK] Found {len(auth_routes)} auth-related routes:")
    for route in auth_routes[:10]:
        print(f"  - {route}")
    
    print("\n[OK] Auth module test passed!")
    
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

