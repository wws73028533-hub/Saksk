# -*- coding: utf-8 -*-
"""
认证模块Schema定义
使用Pydantic进行数据验证和序列化
"""
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional


class SendBindCodeSchema(BaseModel):
    """发送绑定邮箱验证码Schema"""
    email: EmailStr = Field(..., description="邮箱地址")


class BindEmailSchema(BaseModel):
    """绑定邮箱Schema"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证验证码格式"""
        if not v.isdigit():
            raise ValueError('验证码必须是6位数字')
        return v


class SendLoginCodeSchema(BaseModel):
    """发送登录验证码Schema"""
    email: EmailStr = Field(..., description="邮箱地址")


class EmailLoginSchema(BaseModel):
    """邮箱验证码登录Schema"""
    email: EmailStr = Field(..., description="邮箱地址")
    code: str = Field(..., min_length=6, max_length=6, description="验证码")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证验证码格式"""
        if not v.isdigit():
            raise ValueError('验证码必须是6位数字')
        return v


class LoginSchema(BaseModel):
    """登录Schema（支持用户名或邮箱）"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., min_length=1, description="密码")
    remember: bool = Field(default=False, description="保持登录")
    redirect: Optional[str] = Field(default=None, description="登录后重定向地址")


class BindEmailResponseSchema(BaseModel):
    """绑定邮箱响应Schema"""
    email: str = Field(..., description="绑定的邮箱地址")
    email_verified: bool = Field(..., description="是否已验证")
    
    class Config:
        from_attributes = True

