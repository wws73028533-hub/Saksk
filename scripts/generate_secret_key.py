# -*- coding: utf-8 -*-
"""
生成安全的 SECRET_KEY
用于生产环境配置
"""
import secrets

def generate_secret_key():
    """生成一个安全的随机密钥"""
    key = secrets.token_urlsafe(32)
    print("=" * 60)
    print("生成的 SECRET_KEY:")
    print("=" * 60)
    print(key)
    print("=" * 60)
    print("\n请将此密钥添加到 .env 文件中：")
    print(f"SECRET_KEY={key}")
    print("\n或设置为环境变量：")
    print(f"export SECRET_KEY={key}")
    print("=" * 60)
    return key

if __name__ == '__main__':
    generate_secret_key()

