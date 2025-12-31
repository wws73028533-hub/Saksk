# -*- coding: utf-8 -*-
"""
部署诊断脚本 - 检查生产环境部署问题
在服务器上运行: python scripts/diagnose_deployment.py
"""
import sys
import os
import traceback

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def check_imports():
    """检查关键模块导入"""
    print("=" * 60)
    print("检查模块导入")
    print("=" * 60)
    
    modules_to_check = [
        'app',
        'app.modules.auth',
        'app.modules.auth.routes.pages',
        'app.modules.auth.routes.api',
        'app.modules.auth.__init__',
    ]
    
    for module_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"✓ {module_name}")
        except Exception as e:
            print(f"✗ {module_name}: {e}")
            traceback.print_exc()

def check_app_creation():
    """检查应用创建"""
    print("\n" + "=" * 60)
    print("检查应用创建")
    print("=" * 60)
    
    try:
        from app import create_app
        app = create_app('production')
        print("✓ 应用创建成功")
        return app
    except Exception as e:
        print(f"✗ 应用创建失败: {e}")
        traceback.print_exc()
        return None

def check_routes(app):
    """检查路由"""
    if not app:
        return
    
    print("\n" + "=" * 60)
    print("检查路由注册")
    print("=" * 60)
    
    # 检查登录路由
    login_found = False
    all_routes = []
    
    for rule in app.url_map.iter_rules():
        all_routes.append(rule.rule)
        if '/login' in rule.rule:
            login_found = True
            methods = ','.join(sorted(rule.methods - {'OPTIONS', 'HEAD'}))
            print(f"✓ 找到登录路由: {rule.rule} [{methods}] -> {rule.endpoint}")
    
    if not login_found:
        print("✗ 未找到 /login 路由！")
        print("\n当前已注册的路由:")
        for route in sorted(set(all_routes))[:20]:  # 显示前20个
            print(f"  - {route}")
        if len(all_routes) > 20:
            print(f"  ... 还有 {len(all_routes) - 20} 个路由")
    
    # 检查蓝图
    print("\n已注册的蓝图:")
    for name, blueprint in app.blueprints.items():
        print(f"  - {name}: {blueprint}")

def check_templates(app):
    """检查模板文件"""
    if not app:
        return
    
    print("\n" + "=" * 60)
    print("检查模板文件")
    print("=" * 60)
    
    template_dirs = []
    for blueprint_name, blueprint in app.blueprints.items():
        if hasattr(blueprint, 'template_folder') and blueprint.template_folder:
            template_dirs.append((blueprint_name, blueprint.template_folder))
    
    login_template_path = None
    for blueprint_name, template_dir in template_dirs:
        if blueprint_name == 'auth':
            login_template_path = os.path.join(template_dir, 'auth', 'login.html')
            print(f"Auth 蓝图模板目录: {template_dir}")
            if os.path.exists(login_template_path):
                print(f"✓ 登录模板存在: {login_template_path}")
            else:
                print(f"✗ 登录模板不存在: {login_template_path}")
                # 检查其他可能的位置
                alt_path = os.path.join(project_root, 'app', 'modules', 'auth', 'templates', 'auth', 'login.html')
                if os.path.exists(alt_path):
                    print(f"  但找到在: {alt_path}")
    
    # 检查模板加载
    try:
        from flask import render_template_string
        with app.app_context():
            # 尝试加载模板
            from flask import render_template
            try:
                # 只检查模板是否存在，不实际渲染（避免需要上下文变量）
                template_path = os.path.join(project_root, 'app', 'modules', 'auth', 'templates', 'auth', 'login.html')
                if os.path.exists(template_path):
                    print("✓ 可以通过路径访问模板文件")
                else:
                    print(f"✗ 模板文件不存在: {template_path}")
            except Exception as e:
                print(f"⚠ 模板加载检查失败: {e}")
    except Exception as e:
        print(f"⚠ 无法检查模板: {e}")

def check_environment():
    """检查环境变量"""
    print("\n" + "=" * 60)
    print("检查环境变量")
    print("=" * 60)
    
    env_vars = ['FLASK_ENV', 'ENVIRONMENT', 'SECRET_KEY']
    missing_vars = []
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # 对 SECRET_KEY 只显示长度
            if var == 'SECRET_KEY':
                print(f"✓ {var}: {'*' * min(len(value), 20)} (长度: {len(value)})")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: 未设置")
            missing_vars.append(var)
    
    # 如果缺少关键环境变量，给出修复建议
    if missing_vars:
        print("\n" + "-" * 60)
        print("⚠ 缺少关键环境变量！")
        print("-" * 60)
        print("这可能导致应用运行在错误的模式（开发模式而非生产模式）")
        print("\n快速修复方法：")
        print("1. 运行自动配置脚本（推荐）：")
        print("   sudo bash scripts/setup_environment.sh")
        print("\n2. 手动配置 systemd 服务文件：")
        print("   sudo nano /etc/systemd/system/quiz-app.service")
        print("   添加以下环境变量：")
        print("   Environment=\"FLASK_ENV=production\"")
        print("   Environment=\"ENVIRONMENT=production\"")
        if 'SECRET_KEY' in missing_vars:
            print("   Environment=\"SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')\"")
        print("\n3. 然后重新加载并重启服务：")
        print("   sudo systemctl daemon-reload")
        print("   sudo systemctl restart quiz-app")
        print("\n详细说明请参考: deployment/ENVIRONMENT_SETUP.md")

def test_login_route(app):
    """测试登录路由"""
    if not app:
        return
    
    print("\n" + "=" * 60)
    print("测试登录路由")
    print("=" * 60)
    
    with app.test_client() as client:
        try:
            response = client.get('/login')
            print(f"GET /login")
            print(f"  状态码: {response.status_code}")
            print(f"  内容类型: {response.content_type}")
            
            if response.status_code == 200:
                print("  ✓ 路由响应正常")
                content = response.get_data(as_text=True)
                if len(content) > 0:
                    if '<html' in content.lower() or '<!doctype' in content.lower():
                        print(f"  ✓ 返回了 HTML 内容 (长度: {len(content)} 字符)")
                        # 检查是否包含登录相关关键字
                        keywords = ['login', '登录', 'email', '邮箱']
                        found_keywords = [kw for kw in keywords if kw.lower() in content.lower()]
                        if found_keywords:
                            print(f"  ✓ 包含关键字: {', '.join(found_keywords)}")
                    else:
                        print(f"  ⚠ 内容可能不是 HTML")
                        print(f"  前 200 字符: {content[:200]}")
                else:
                    print("  ⚠ 响应内容为空")
            elif response.status_code == 404:
                print("  ✗ 路由返回 404")
                # 尝试查看响应内容
                content = response.get_data(as_text=True)
                print(f"  响应内容: {content[:300]}")
            else:
                print(f"  ⚠ 意外状态码: {response.status_code}")
                content = response.get_data(as_text=True)
                print(f"  响应内容: {content[:300]}")
        except Exception as e:
            print(f"  ✗ 测试失败: {e}")
            traceback.print_exc()

def main():
    """主函数"""
    print("=" * 60)
    print("部署诊断工具")
    print("=" * 60)
    print(f"项目根目录: {project_root}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python 版本: {sys.version}")
    print()
    
    # 检查导入
    check_imports()
    
    # 检查环境变量
    check_environment()
    
    # 检查应用创建
    app = check_app_creation()
    
    if app:
        # 检查路由
        check_routes(app)
        
        # 检查模板
        check_templates(app)
        
        # 测试登录路由
        test_login_route(app)
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)
    
    # 检查是否缺少环境变量
    missing_env = []
    if not os.environ.get('FLASK_ENV') and not os.environ.get('ENVIRONMENT'):
        missing_env.append('FLASK_ENV 或 ENVIRONMENT')
    if not os.environ.get('SECRET_KEY'):
        missing_env.append('SECRET_KEY')
    
    if missing_env:
        print("\n⚠ 重要提示：发现缺少环境变量！")
        print(f"缺少: {', '.join(missing_env)}")
        print("这可能是导致路由 404 错误的主要原因。")
        print("请优先配置环境变量，然后重新运行诊断。")
        print()
    
    print("\n一般建议:")
    print("1. 如果环境变量未设置，请先配置（见上方提示）")
    print("2. 如果路由未注册，检查应用启动日志")
    print("3. 如果模板不存在，检查文件路径和权限")
    print("4. 检查 Gunicorn/systemd 配置中的工作目录是否正确")
    print("5. 确认所有依赖已正确安装")
    print("\n详细文档:")
    print("- 环境变量配置: deployment/ENVIRONMENT_SETUP.md")
    print("- 故障排查: deployment/TROUBLESHOOTING.md")
    print()

if __name__ == '__main__':
    main()


