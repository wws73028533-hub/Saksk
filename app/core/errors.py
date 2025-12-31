# -*- coding: utf-8 -*-
"""
统一错误处理模块
提供自定义异常类和错误处理函数
"""
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from typing import Optional, Dict, Any


class APIError(HTTPException):
    """API错误基类"""
    code = 500
    description = 'An unexpected error occurred.'
    
    def __init__(self, message: Optional[str] = None, code: Optional[int] = None, payload: Optional[Dict[str, Any]] = None):
        """
        初始化API错误
        
        Args:
            message: 错误消息
            code: HTTP状态码
            payload: 额外的错误数据
        """
        if message:
            self.description = message
        if code:
            self.code = code
        self.payload = payload
        super().__init__(description=self.description)
    
    def get_response(self, environ=None):
        """获取错误响应"""
        response = jsonify({
            'status': 'error',
            'message': self.description,
            'status_code': self.code,
            'payload': self.payload
        })
        response.status_code = self.code
        return response


class BadRequestError(APIError):
    """400 错误请求"""
    code = 400
    description = 'Invalid request payload.'


class UnauthorizedError(APIError):
    """401 未授权"""
    code = 401
    description = 'Authentication required.'


class ForbiddenError(APIError):
    """403 禁止访问"""
    code = 403
    description = 'Access forbidden.'


class NotFoundError(APIError):
    """404 资源未找到"""
    code = 404
    description = 'Resource not found.'


class ConflictError(APIError):
    """409 冲突"""
    code = 409
    description = 'Resource conflict.'


class TooManyRequestsError(APIError):
    """429 请求过多"""
    code = 429
    description = 'Too many requests.'


class InternalServerError(APIError):
    """500 服务器内部错误"""
    code = 500
    description = 'Internal server error.'


def register_error_handlers(app: Flask) -> None:
    """
    注册错误处理器
    
    Args:
        app: Flask应用实例
    """
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """处理API错误"""
        return error.get_response()
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        """处理HTTP异常"""
        # 判断是否为 API 请求（以 /api 开头或 Accept 头包含 application/json）
        is_api_request = (
            request.path.startswith('/api') or
            request.headers.get('Accept', '').startswith('application/json')
        )
        
        if is_api_request:
            # API 请求返回 JSON 格式错误
            return APIError(message=e.description, code=e.code).get_response()
        else:
            # 页面请求返回 Flask 默认的 HTML 错误页面
            from werkzeug.exceptions import NotFound
            if e.code == 404:
                # 404 错误：返回 Flask 默认的 404 页面
                return app.response_class(
                    response=f'<h1>404 - 页面未找到</h1><p>{e.description}</p>',
                    status=404,
                    mimetype='text/html'
                )
            # 其他 HTTP 错误
            return app.response_class(
                response=f'<h1>{e.code} - {e.name}</h1><p>{e.description}</p>',
                status=e.code,
                mimetype='text/html'
            )
    
    @app.errorhandler(ValueError)
    def handle_value_error(e: ValueError):
        """处理值错误"""
        app.logger.warning(f'ValueError: {str(e)}, IP: {request.remote_addr}')
        is_api_request = (
            request.path.startswith('/api') or
            request.headers.get('Accept', '').startswith('application/json')
        )
        if is_api_request:
            return BadRequestError(message=f'Invalid value: {str(e)}').get_response()
        # 页面请求返回简单错误页面
        from flask import render_template_string
        return render_template_string(
            '<h1>400 - 请求错误</h1><p>无效的值: {{ error }}</p>',
            error=str(e)
        ), 400
    
    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception):
        """处理通用异常"""
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        is_api_request = (
            request.path.startswith('/api') or
            request.headers.get('Accept', '').startswith('application/json')
        )
        if is_api_request:
            return InternalServerError(message="An unexpected server error occurred.").get_response()
        # 页面请求返回简单错误页面
        from flask import render_template_string
        return render_template_string(
            '<h1>500 - 服务器错误</h1><p>发生了一个意外错误，请稍后再试。</p>',
        ), 500

