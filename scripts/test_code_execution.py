# -*- coding: utf-8 -*-
"""
测试代码执行功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.code_executor import PythonExecutor
from app.utils.code_validator import validate_python_code


def test_code_validator():
    """测试代码验证器"""
    print("=" * 60)
    print("测试代码验证器")
    print("=" * 60)
    
    test_cases = [
        # (代码, 期望结果, 描述)
        ("print('Hello')", True, "正常代码"),
        ("import os", False, "禁止导入 os 模块"),
        ("eval('1+1')", False, "禁止使用 eval"),
        ("open('file.txt')", False, "禁止使用 open"),
        ("x = 1\nprint(x)", True, "多行正常代码"),
        ("", False, "空代码"),
        ("print(x)", True, "运行时错误但语法正确"),  # 语法正确，运行时错误
    ]
    
    all_passed = True
    for code, expected_valid, desc in test_cases:
        is_valid, error_msg = validate_python_code(code)
        if is_valid == expected_valid:
            status = "[OK]"
        else:
            status = "[FAIL]"
            all_passed = False
        
        print(f"{status} {desc}")
        if not is_valid and error_msg:
            print(f"     错误信息: {error_msg}")
    
    return all_passed


def test_code_executor():
    """测试代码执行器"""
    print("\n" + "=" * 60)
    print("测试代码执行器")
    print("=" * 60)
    
    test_cases = [
        # (代码, 输入, 描述)
        ("print('Hello, World!')", "", "简单输出"),
        ("a = int(input())\nprint(a * 2)", "5", "带输入的代码"),
        ("for i in range(3):\n    print(i)", "", "循环输出"),
        ("print(x)", "", "运行时错误"),
        ("import os\nos.system('ls')", "", "危险代码（应被拦截）"),
    ]
    
    executor = PythonExecutor(time_limit=5, memory_limit=128)
    all_passed = True
    
    for code, input_data, desc in test_cases:
        print(f"\n测试: {desc}")
        print(f"代码: {code[:50]}...")
        
        result = executor.execute(code, input_data)
        
        print(f"状态: {result.get('status')}")
        if result.get('output'):
            output_preview = result['output'][:100].replace('\n', '\\n')
            print(f"输出: {output_preview}")
        if result.get('error'):
            error_preview = result['error'][:100].replace('\n', '\\n')
            print(f"错误: {error_preview}")
        if result.get('execution_time'):
            print(f"执行时间: {result['execution_time']} 秒")
        
        # 检查危险代码是否被拦截
        if 'import os' in code or 'os.system' in code:
            if result.get('status') == 'error' and result.get('error'):
                print("[OK] 危险代码被正确拦截")
            else:
                print("[FAIL] 危险代码未被拦截")
                all_passed = False
        elif result.get('status') == 'success' or result.get('status') == 'error':
            # 正常代码或运行时错误都是可以接受的
            print("[OK] 执行完成")
    
    return all_passed


def test_api_endpoint():
    """测试 API 端点（需要 Flask 应用上下文）"""
    print("\n" + "=" * 60)
    print("测试 API 端点")
    print("=" * 60)
    
    app = create_app('development')
    
    with app.test_client() as client:
        # 模拟登录（创建会话）
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'test_user'
        
        # 测试代码执行 API
        response = client.post('/api/coding/execute', json={
            'code': "print('Hello from API')",
            'language': 'python'
        })
        
        print(f"状态码: {response.status_code}")
        data = response.get_json()
        print(f"响应: {data}")
        
        if response.status_code == 200 and data.get('status') == 'success':
            print("[OK] API 端点正常工作")
            return True
        else:
            print("[FAIL] API 端点测试失败")
            return False


if __name__ == '__main__':
    try:
        print("开始测试代码执行功能...\n")
        
        # 测试代码验证器
        validator_ok = test_code_validator()
        
        # 测试代码执行器
        executor_ok = test_code_executor()
        
        # 测试 API 端点
        api_ok = test_api_endpoint()
        
        # 总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"代码验证器: {'[PASS]' if validator_ok else '[FAIL]'}")
        print(f"代码执行器: {'[PASS]' if executor_ok else '[FAIL]'}")
        print(f"API 端点: {'[PASS]' if api_ok else '[FAIL]'}")
        
        all_passed = validator_ok and executor_ok and api_ok
        if all_passed:
            print("\n[SUCCESS] 所有测试通过！")
        else:
            print("\n[FAIL] 部分测试失败")
        
        sys.exit(0 if all_passed else 1)
        
    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



































