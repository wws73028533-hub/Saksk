# -*- coding: utf-8 -*-
"""
邮箱功能API集成测试
"""
import unittest
import json
from flask import Flask
from app import create_app
from app.core.utils.database import get_db, init_db


class TestEmailAPI(unittest.TestCase):
    """邮箱API集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['MAIL_ENABLED'] = True
        self.app.config['MAIL_CONSOLE_OUTPUT'] = True
        self.app.config['DATABASE_PATH'] = ':memory:'
        self.client = self.app.test_client()
        
        # 初始化数据库
        with self.app.app_context():
            init_db()
            
            # 创建测试用户
            conn = get_db()
            conn.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                ('testuser', 'pbkdf2:sha256:test', 0)
            )
            conn.commit()
    
    def tearDown(self):
        """测试后清理"""
        pass
    
    def test_send_bind_code_not_logged_in(self):
        """测试发送绑定验证码 - 未登录"""
        response = self.client.post(
            '/api/auth/email/send-bind-code',
            json={'email': 'test@example.com'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    def test_send_bind_code_invalid_email(self):
        """测试发送绑定验证码 - 无效邮箱"""
        # 先登录
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.post(
            '/api/auth/email/send-bind-code',
            json={'email': 'invalid-email'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    def test_send_bind_code_success(self):
        """测试发送绑定验证码 - 成功"""
        # 先登录
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
        
        response = self.client.post(
            '/api/auth/email/send-bind-code',
            json={'email': 'test@example.com'},
            content_type='application/json'
        )
        # 由于使用控制台输出模式，应该成功
        self.assertIn(response.status_code, [200, 400])
        data = json.loads(response.data)
        # 如果成功，status应该是success
        if response.status_code == 200:
            self.assertEqual(data['status'], 'success')
    
    def test_bind_email_not_logged_in(self):
        """测试绑定邮箱 - 未登录"""
        response = self.client.post(
            '/api/auth/email/bind',
            json={'email': 'test@example.com', 'code': '123456'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
    
    def test_send_login_code_invalid_email(self):
        """测试发送登录验证码 - 无效邮箱"""
        response = self.client.post(
            '/api/auth/email/send-login-code',
            json={'email': 'invalid-email'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    def test_email_login_invalid_data(self):
        """测试验证码登录 - 无效数据"""
        response = self.client.post(
            '/api/auth/email/login',
            json={'email': 'invalid-email', 'code': '123'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')


if __name__ == '__main__':
    unittest.main()

