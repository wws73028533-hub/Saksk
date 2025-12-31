@echo off
REM 生产环境启动脚本 (Windows)

REM 设置环境变量
set FLASK_ENV=production

REM 检查环境变量
if "%SECRET_KEY%"=="" (
    echo 警告: SECRET_KEY 未设置，请设置环境变量
    exit /b 1
)

REM 创建必要的目录
if not exist logs mkdir logs
if not exist instance mkdir instance
if not exist uploads\avatars mkdir uploads\avatars
if not exist uploads\question_images mkdir uploads\question_images

REM 启动应用（Windows下可以使用 waitress）
echo 正在启动生产环境...
python run.py

