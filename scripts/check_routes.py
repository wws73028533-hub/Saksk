# -*- coding: utf-8 -*-
"""
路由检查脚本 - 用于诊断路由注册问题
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

def check_routes():
    """检查路由注册情况"""
    print("=" * 60)
    print("路由检查报告")
    print("=" * 60)
    
    # 创建应用实例
    try:
        app = create_app('production')
        print(f"✓ 应用创建成功")
    except Exception as e:
        print(f"✗ 应用创建失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 获取所有路由
    print("\n所有已注册的路由:")
    print("-" * 60)
    routes = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'OPTIONS', 'HEAD'}))
        routes.append((rule.rule, methods, rule.endpoint))
        print(f"{rule.rule:30} [{methods:20}] -> {rule.endpoint}")
    
    # 检查登录路由
    print("\n" + "=" * 60)
    print("登录相关路由检查:")
    print("-" * 60)
    login_routes = [r for r in routes if '/login' in r[0]]
    if login_routes:
        print("✓ 找到登录路由:")
        for rule, methods, endpoint in login_routes:
            print(f"  {rule} [{methods}] -> {endpoint}")
    else:
        print("✗ 未找到登录路由！")
    
    # 检查蓝图注册
    print("\n" + "=" * 60)
    print("已注册的蓝图:")
    print("-" * 60)
    for name, blueprint in app.blueprints.items():
        print(f"✓ {name}: {blueprint}")
    
    # 测试登录路由
    print("\n" + "=" * 60)
    print("测试登录路由:")
    print("-" * 60)
    with app.test_client() as client:
        try:
            response = client.get('/login')
            print(f"GET /login")
            print(f"  状态码: {response.status_code}")
            print(f"  内容类型: {response.content_type}")
            if response.status_code == 200:
                print(f"  ✓ 路由正常")
                # 检查响应内容
                content = response.get_data(as_text=True)
                if 'login' in content.lower() or '<html' in content.lower():
                    print(f"  ✓ 返回了 HTML 内容")
                else:
                    print(f"  ⚠ 响应内容可能不正确")
                    print(f"  前 200 字符: {content[:200]}")
            elif response.status_code == 404:
                print(f"  ✗ 路由返回 404 - 路由未注册或路径不正确")
            else:
                print(f"  ⚠ 意外状态码: {response.status_code}")
                print(f"  响应内容: {response.get_data(as_text=True)[:200]}")
        except Exception as e:
            print(f"  ✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 检查模块注册日志
    print("\n" + "=" * 60)
    print("建议检查:")
    print("-" * 60)
    print("1. 检查应用启动日志，确认 auth 模块是否成功注册")
    print("2. 检查服务器日志，查看是否有模块注册错误")
    print("3. 确认生产环境配置是否正确")
    print("4. 如果使用 Gunicorn，确认工作目录和 Python 路径正确")
    print("=" * 60)

if __name__ == '__main__':
    check_routes()


