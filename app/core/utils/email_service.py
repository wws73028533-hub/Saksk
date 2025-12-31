# -*- coding: utf-8 -*-
"""
邮件服务工具
提供验证码生成和邮件发送功能
"""
import smtplib
import secrets
import string
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from typing import Optional, Dict, Any, Tuple
from flask import current_app
from jinja2 import Template


class EmailService:
    """邮件服务类"""
    
    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """
        生成验证码
        
        Args:
            length: 验证码长度，默认6位
            
        Returns:
            验证码字符串（纯数字）
        """
        # 使用安全的随机数生成器
        # 验证码使用纯数字
        digits = string.digits
        code = ''.join(secrets.choice(digits) for _ in range(length))
        return code
    
    @staticmethod
    def _get_smtp_config() -> Dict[str, Any]:
        """
        获取SMTP配置
        优先从数据库读取，如果不存在则从环境变量读取
        
        Returns:
            SMTP配置字典
        """
        from app.core.utils.database import get_db
        import json
        
        # 尝试从数据库读取配置
        try:
            conn = get_db()
            config_rows = conn.execute(
                'SELECT config_key, config_value FROM system_config WHERE config_key LIKE "mail_%"'
            ).fetchall()
            
            if config_rows:
                db_config = {}
                for row in config_rows:
                    key = row['config_key'].replace('mail_', '').upper()
                    value = row['config_value']
                    # 尝试解析JSON值
                    try:
                        value = json.loads(value)
                    except:
                        # 如果不是JSON，尝试转换为布尔值或整数
                        if value.lower() in ['true', 'false', '1', '0']:
                            value = value.lower() in ['true', '1']
                        elif value.isdigit():
                            value = int(value)
                    db_config[key] = value
                
                # 如果数据库中有配置，使用数据库配置
                if db_config.get('SERVER'):
                    return {
                        'server': db_config.get('SERVER'),
                        'port': db_config.get('PORT', 587),
                        'use_tls': db_config.get('USE_TLS', True),
                        'use_ssl': db_config.get('USE_SSL', False),
                        'username': db_config.get('USERNAME'),
                        'password': db_config.get('PASSWORD'),
                        'sender': db_config.get('DEFAULT_SENDER'),
                        'sender_name': db_config.get('DEFAULT_SENDER_NAME', '系统通知'),
                    }
        except Exception as e:
            current_app.logger.warning(f'从数据库读取邮件配置失败，使用环境变量: {str(e)}')
        
        # 如果数据库中没有配置，使用环境变量
        return {
            'server': current_app.config.get('MAIL_SERVER'),
            'port': current_app.config.get('MAIL_PORT', 587),
            'use_tls': current_app.config.get('MAIL_USE_TLS', True),
            'use_ssl': current_app.config.get('MAIL_USE_SSL', False),
            'username': current_app.config.get('MAIL_USERNAME'),
            'password': current_app.config.get('MAIL_PASSWORD'),
            'sender': current_app.config.get('MAIL_DEFAULT_SENDER'),
            'sender_name': current_app.config.get('MAIL_DEFAULT_SENDER_NAME', '系统通知'),
        }
    
    @staticmethod
    def _render_email_template(template_type: str, **kwargs) -> Tuple[str, str]:
        """
        渲染邮件模板
        
        Args:
            template_type: 模板类型（bind_code, login_code, reset_password）
            **kwargs: 模板变量
            
        Returns:
            (subject, body) 元组
        """
        templates = {
            'bind_code': {
                'subject': '邮箱绑定验证码',
                'body': '''
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                        .content { padding: 20px; background-color: #f9f9f9; }
                        .code-box { background-color: #fff; border: 2px dashed #4CAF50; padding: 20px; text-align: center; margin: 20px 0; }
                        .code { font-size: 32px; font-weight: bold; color: #4CAF50; letter-spacing: 5px; }
                        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                        .warning { color: #ff9800; font-weight: bold; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>邮箱绑定验证</h1>
                        </div>
                        <div class="content">
                            <p>您好！</p>
                            <p>您正在绑定邮箱 <strong>{{ email }}</strong>，验证码为：</p>
                            <div class="code-box">
                                <div class="code">{{ code }}</div>
                            </div>
                            <p class="warning">验证码有效期为10分钟，请勿泄露给他人。</p>
                            <p>如果这不是您的操作，请忽略此邮件。</p>
                        </div>
                        <div class="footer">
                            <p>此邮件由系统自动发送，请勿回复。</p>
                        </div>
                    </div>
                </body>
                </html>
                '''
            },
            'login_code': {
                'subject': '登录验证码',
                'body': '''
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #2196F3; color: white; padding: 20px; text-align: center; }
                        .content { padding: 20px; background-color: #f9f9f9; }
                        .code-box { background-color: #fff; border: 2px dashed #2196F3; padding: 20px; text-align: center; margin: 20px 0; }
                        .code { font-size: 32px; font-weight: bold; color: #2196F3; letter-spacing: 5px; }
                        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                        .warning { color: #ff9800; font-weight: bold; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>登录验证</h1>
                        </div>
                        <div class="content">
                            <p>您好！</p>
                            <p>您正在使用邮箱 <strong>{{ email }}</strong> 登录，验证码为：</p>
                            <div class="code-box">
                                <div class="code">{{ code }}</div>
                            </div>
                            <p class="warning">验证码有效期为10分钟，请勿泄露给他人。</p>
                            <p>如果这不是您的操作，请立即修改密码。</p>
                        </div>
                        <div class="footer">
                            <p>此邮件由系统自动发送，请勿回复。</p>
                        </div>
                    </div>
                </body>
                </html>
                '''
            },
            'reset_password': {
                'subject': '密码重置验证码',
                'body': '''
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                        .header { background-color: #f44336; color: white; padding: 20px; text-align: center; }
                        .content { padding: 20px; background-color: #f9f9f9; }
                        .code-box { background-color: #fff; border: 2px dashed #f44336; padding: 20px; text-align: center; margin: 20px 0; }
                        .code { font-size: 32px; font-weight: bold; color: #f44336; letter-spacing: 5px; }
                        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                        .warning { color: #ff9800; font-weight: bold; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>密码重置</h1>
                        </div>
                        <div class="content">
                            <p>您好！</p>
                            <p>您正在重置账户密码，验证码为：</p>
                            <div class="code-box">
                                <div class="code">{{ code }}</div>
                            </div>
                            <p class="warning">验证码有效期为10分钟，请勿泄露给他人。</p>
                            <p>如果这不是您的操作，请立即联系管理员。</p>
                        </div>
                        <div class="footer">
                            <p>此邮件由系统自动发送，请勿回复。</p>
                        </div>
                    </div>
                </body>
                </html>
                '''
            }
        }
        
        if template_type not in templates:
            raise ValueError(f"未知的模板类型: {template_type}")
        
        template_data = templates[template_type]
        subject_template = Template(template_data['subject'])
        body_template = Template(template_data['body'])
        
        subject = subject_template.render(**kwargs)
        body = body_template.render(**kwargs)
        
        return subject, body
    
    @staticmethod
    def _send_email_smtp(to_email: str, subject: str, body_html: str) -> bool:
        """
        通过SMTP发送邮件
        
        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            body_html: 邮件正文（HTML格式）
            
        Returns:
            是否发送成功
        """
        config = EmailService._get_smtp_config()
        
        # 详细检查配置
        missing_fields = []
        if not config['server']:
            missing_fields.append('server')
        if not config['username']:
            missing_fields.append('username')
        if not config['password']:
            missing_fields.append('password')
        
        if missing_fields:
            current_app.logger.error(f'邮件服务配置不完整，缺少字段: {", ".join(missing_fields)}, to_email={to_email}')
            return False
        
        current_app.logger.debug(f'SMTP配置检查通过: server={config["server"]}, port={config["port"]}, username={config["username"]}, sender={config["sender"]}')
        
        # QQ邮箱要求From地址必须与SMTP登录用户名一致
        # 如果MAIL_DEFAULT_SENDER未设置，使用MAIL_USERNAME作为发件人
        sender_email = config['sender'] or config['username']
        if not sender_email:
            current_app.logger.error('发件人邮箱未配置')
            return False
        
        server = None
        try:
            # 创建邮件消息
            msg = MIMEMultipart('alternative')
            # 使用 formataddr 正确格式化 From 头，符合 RFC5322 标准
            # formataddr 会自动处理非 ASCII 字符的编码（RFC2047）
            from_header = formataddr((config['sender_name'], sender_email))
            msg['From'] = from_header
            msg['To'] = to_email
            msg['Subject'] = Header(subject, 'utf-8')
            
            # 记录From头用于调试
            current_app.logger.debug(f'邮件From头: {from_header}')
            
            # 添加HTML内容
            html_part = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 连接SMTP服务器并发送
            # 设置连接超时（30秒）和读取超时（60秒）
            timeout = 30
            current_app.logger.debug(f'连接SMTP服务器: {config["server"]}:{config["port"]}, timeout={timeout}')
            
            if config['use_ssl']:
                server = smtplib.SMTP_SSL(config['server'], config['port'], timeout=timeout)
            else:
                server = smtplib.SMTP(config['server'], config['port'], timeout=timeout)
            
            # 启用调试模式（仅在DEBUG级别时）
            if current_app.logger.level <= 10:  # DEBUG level
                server.set_debuglevel(1)
            
            # 设置读取超时
            server.timeout = 60
            
            # 如果使用TLS，启动TLS加密
            if config['use_tls'] and not config['use_ssl']:
                current_app.logger.debug('启动TLS加密')
                server.starttls()
            
            # 登录SMTP服务器
            current_app.logger.debug(f'尝试登录SMTP服务器: username={config["username"]}')
            server.login(config['username'], config['password'])
            current_app.logger.debug('SMTP登录成功')
            
            # 发送邮件
            current_app.logger.debug(f'发送邮件到: {to_email}')
            server.send_message(msg)
            current_app.logger.debug('邮件发送命令执行成功')
            
            # 正确关闭连接
            server.quit()
            server = None
            
            current_app.logger.info(f'邮件发送成功: {to_email}')
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f'SMTP认证失败: {str(e)}'
            current_app.logger.error(f'{error_msg}, to_email={to_email}, username={config["username"]}')
            if hasattr(e, 'smtp_code'):
                current_app.logger.error(f'SMTP错误代码: {e.smtp_code}')
            if hasattr(e, 'smtp_error'):
                current_app.logger.error(f'SMTP错误信息: {e.smtp_error}')
            return False
        except (smtplib.SMTPException, ConnectionError, OSError) as e:
            error_msg = f'SMTP连接错误: {str(e)}'
            error_type = type(e).__name__
            current_app.logger.error(f'{error_msg} ({error_type}), to_email={to_email}, server={config["server"]}:{config["port"]}')
            # 记录更详细的错误信息
            if hasattr(e, 'smtp_code'):
                current_app.logger.error(f'SMTP错误代码: {e.smtp_code}')
            if hasattr(e, 'smtp_error'):
                current_app.logger.error(f'SMTP错误信息: {e.smtp_error}')
            # 提供可能的解决方案提示
            if 'Connection unexpectedly closed' in str(e) or 'Connection closed' in str(e):
                current_app.logger.error('可能的原因: 1) 授权码错误或已过期 2) SMTP服务未开启 3) 163邮箱需要验证码登录 4) 网络连接问题')
            return False
        except Exception as e:
            error_msg = f'邮件发送失败: {str(e)}'
            error_type = type(e).__name__
            current_app.logger.error(f'{error_msg} ({error_type}), to_email={to_email}', exc_info=True)
            return False
        finally:
            # 确保连接被正确关闭
            if server is not None:
                try:
                    server.quit()
                except:
                    try:
                        server.close()
                    except:
                        pass
    
    @staticmethod
    def _console_output_code(to_email: str, code: str, template_type: str) -> None:
        """
        在控制台输出验证码（开发环境使用）
        
        Args:
            to_email: 收件人邮箱
            code: 验证码
            template_type: 模板类型
        """
        print('\n' + '=' * 60)
        print('邮件服务（开发模式 - 控制台输出）')
        print('=' * 60)
        print(f'收件人: {to_email}')
        print(f'类型: {template_type}')
        print(f'验证码: {code}')
        print('=' * 60 + '\n')
        current_app.logger.info(f'[开发模式] 验证码已输出到控制台: {to_email} -> {code}')
    
    @staticmethod
    def send_verification_code(
        to_email: str,
        code_type: str,
        code: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        发送验证码邮件
        
        Args:
            to_email: 收件人邮箱
            code_type: 验证码类型（bind, login, reset_password）
            code: 验证码（如果为None则自动生成）
            
        Returns:
            (是否成功, 验证码) 元组
        """
        # 生成验证码
        if code is None:
            code = EmailService.generate_verification_code()
        
        # 检查是否启用邮件服务（优先从数据库读取）
        mail_enabled = True
        console_output = False
        
        try:
            from app.core.utils.database import get_db
            conn = get_db()
            enabled_row = conn.execute(
                'SELECT config_value FROM system_config WHERE config_key = ?',
                ('mail_enabled',)
            ).fetchone()
            if enabled_row:
                mail_enabled = enabled_row['config_value'].lower() in ['true', '1', 'yes', 'on']
            
            console_row = conn.execute(
                'SELECT config_value FROM system_config WHERE config_key = ?',
                ('mail_console_output',)
            ).fetchone()
            if console_row:
                console_output = console_row['config_value'].lower() in ['true', '1', 'yes', 'on']
        except Exception:
            # 如果从数据库读取失败，使用环境变量配置
            mail_enabled = current_app.config.get('MAIL_ENABLED', True)
            console_output = current_app.config.get('MAIL_CONSOLE_OUTPUT', False)
        
        if not mail_enabled:
            current_app.logger.warning(f'邮件服务未启用: to_email={to_email}, code_type={code_type}')
            return False, None
        
        # 如果启用控制台输出，则只输出到控制台，不发送真实邮件
        if console_output:
            EmailService._console_output_code(to_email, code, code_type)
            return True, code
        
        # 渲染邮件模板
        template_type_map = {
            'bind': 'bind_code',
            'login': 'login_code',
            'reset_password': 'reset_password'
        }
        
        template_type = template_type_map.get(code_type)
        if not template_type:
            current_app.logger.error(f'未知的验证码类型: {code_type}, to_email={to_email}')
            return False, None
        
        try:
            subject, body_html = EmailService._render_email_template(
                template_type,
                email=to_email,
                code=code
            )
        except Exception as e:
            current_app.logger.error(f'邮件模板渲染失败: {str(e)}', exc_info=True)
            return False, None
        
        # 发送邮件
        success = EmailService._send_email_smtp(to_email, subject, body_html)
        
        if success:
            current_app.logger.info(f'验证码邮件发送成功: {to_email}, code_type={code_type}')
            return True, code
        else:
            current_app.logger.error(f'验证码邮件发送失败: {to_email}, code_type={code_type}')
            return False, None
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否为有效邮箱格式
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

