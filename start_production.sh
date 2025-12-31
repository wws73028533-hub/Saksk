#!/bin/bash
# 生产环境启动脚本

# 设置环境变量
export FLASK_ENV=production

# 检查环境变量
if [ -z "$SECRET_KEY" ]; then
    echo "警告: SECRET_KEY 未设置，请设置环境变量"
    exit 1
fi

# 创建必要的目录
mkdir -p logs
mkdir -p instance
mkdir -p uploads/avatars
mkdir -p uploads/question_images

# 启动 Gunicorn
exec gunicorn -c gunicorn_config.py run:app

