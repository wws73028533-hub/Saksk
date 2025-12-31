#!/bin/bash
# -*- coding: utf-8 -*-
# 环境变量设置脚本
# 用于配置生产环境所需的环境变量

set -e

echo "=========================================="
echo "  环境变量配置脚本"
echo "=========================================="

# 项目根目录（根据实际情况修改）
PROJECT_DIR="${PROJECT_DIR:-/var/www/quiz-app}"

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

echo ""
echo "配置步骤："
echo "1. 生成 SECRET_KEY"
echo "2. 配置 systemd 服务文件"
echo "3. 创建 .env 文件（可选）"
echo ""

# 1. 生成 SECRET_KEY
echo "[1/3] 生成 SECRET_KEY..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "生成的 SECRET_KEY:"
echo "$SECRET_KEY"
echo ""

# 2. 配置 systemd 服务文件
echo "[2/3] 配置 systemd 服务文件..."
SERVICE_FILE="/etc/systemd/system/quiz-app.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "⚠ systemd 服务文件不存在: $SERVICE_FILE"
    echo "请先复制 systemd/saksk_ti.service 到 $SERVICE_FILE"
    echo ""
    read -p "是否现在创建服务文件？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$PROJECT_DIR/systemd/saksk_ti.service" ]; then
            cp "$PROJECT_DIR/systemd/saksk_ti.service" "$SERVICE_FILE"
            echo "✓ 已复制服务文件"
        else
            echo "✗ 源文件不存在: $PROJECT_DIR/systemd/saksk_ti.service"
            exit 1
        fi
    else
        exit 1
    fi
fi

# 更新服务文件中的环境变量
echo "更新服务文件中的环境变量..."

# 替换路径（如果服务文件中有占位符）
sed -i "s|/path/to/quiz-app|$PROJECT_DIR|g" "$SERVICE_FILE"
sed -i "s|/path/to/Saksk_1_Ti|$PROJECT_DIR|g" "$SERVICE_FILE"  # 兼容旧路径
sed -i "s|/path/to/venv|$PROJECT_DIR/venv|g" "$SERVICE_FILE"

# 确保环境变量已设置
if ! grep -q "Environment=\"FLASK_ENV=production\"" "$SERVICE_FILE"; then
    # 在 ExecStart 之前添加环境变量
    sed -i "/^ExecStart=/i Environment=\"FLASK_ENV=production\"\nEnvironment=\"ENVIRONMENT=production\"" "$SERVICE_FILE"
fi

# 更新 SECRET_KEY（如果存在占位符）
if grep -q "your-secret-key-here" "$SERVICE_FILE"; then
    sed -i "s|your-secret-key-here|$SECRET_KEY|g" "$SERVICE_FILE"
    echo "✓ 已更新 SECRET_KEY"
else
    # 检查是否已有 SECRET_KEY
    if ! grep -q "Environment=\"SECRET_KEY=" "$SERVICE_FILE"; then
        # 在 FLASK_ENV 之后添加 SECRET_KEY
        sed -i "/^Environment=\"FLASK_ENV=/a Environment=\"SECRET_KEY=$SECRET_KEY\"" "$SERVICE_FILE"
        echo "✓ 已添加 SECRET_KEY"
    else
        echo "⚠ SECRET_KEY 已存在，请手动检查"
    fi
fi

echo "✓ 服务文件已更新"
echo ""

# 3. 创建 .env 文件（可选）
echo "[3/3] 创建 .env 文件..."
ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << EOF
# Flask 环境配置
FLASK_ENV=production
ENVIRONMENT=production

# 密钥配置（请妥善保管）
SECRET_KEY=$SECRET_KEY

# 邮件服务配置（根据实际情况修改）
# MAIL_SERVER=smtp.example.com
# MAIL_PORT=587
# MAIL_USE_TLS=true
# MAIL_USERNAME=your-email@example.com
# MAIL_PASSWORD=your-password
# MAIL_DEFAULT_SENDER=noreply@example.com

# HTTPS 配置（如果使用 HTTPS）
# SESSION_COOKIE_SECURE=true
EOF
    chown www-data:www-data "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "✓ 已创建 .env 文件: $ENV_FILE"
    echo "  ⚠ 请检查并配置邮件服务相关设置"
else
    echo "⚠ .env 文件已存在，跳过创建"
    echo "  如需更新，请手动编辑: $ENV_FILE"
fi

echo ""
echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 检查并编辑服务文件: sudo nano $SERVICE_FILE"
echo "2. 检查并编辑 .env 文件（如需要）: sudo nano $ENV_FILE"
echo "3. 重新加载 systemd 配置: sudo systemctl daemon-reload"
echo "4. 重启服务: sudo systemctl restart quiz-app"
echo "5. 检查服务状态: sudo systemctl status quiz-app"
echo ""
echo "重要提示："
echo "- SECRET_KEY 已生成并配置到服务文件中"
echo "- 请妥善保管 SECRET_KEY，不要泄露"
echo "- 如果服务文件路径不正确，请手动修改"
echo ""

