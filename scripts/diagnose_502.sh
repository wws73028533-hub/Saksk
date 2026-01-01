#!/bin/bash
# 502 Bad Gateway 快速诊断脚本

echo "=========================================="
echo "502 Bad Gateway 诊断工具"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查 Gunicorn 服务状态
echo "【1】检查 Gunicorn 服务状态..."
SERVICE_NAME="quiz-app.service"
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    SERVICE_STATUS=$(systemctl is-active $SERVICE_NAME 2>/dev/null)
    if [ "$SERVICE_STATUS" = "active" ]; then
        echo -e "${GREEN}✓${NC} Gunicorn 服务正在运行"
    else
        echo -e "${RED}✗${NC} Gunicorn 服务未运行 (状态: $SERVICE_STATUS)"
        echo "  运行以下命令启动: sudo systemctl start $SERVICE_NAME"
    fi
else
    echo -e "${YELLOW}⚠${NC} 未找到 systemd 服务: $SERVICE_NAME"
    echo "  请检查服务名称是否正确"
fi
echo ""

# 2. 检查端口 8000 监听情况
echo "【2】检查端口 8000 监听情况..."
PORT_CHECK=$(sudo netstat -tlnp 2>/dev/null | grep :8000 || sudo ss -tlnp 2>/dev/null | grep :8000)
if [ -n "$PORT_CHECK" ]; then
    echo -e "${GREEN}✓${NC} 端口 8000 正在监听"
    echo "  详情: $PORT_CHECK"
else
    echo -e "${RED}✗${NC} 端口 8000 未监听"
    echo "  这通常意味着 Gunicorn 未正常启动"
fi
echo ""

# 3. 检查 Gunicorn 进程
echo "【3】检查 Gunicorn 进程..."
PROCESSES=$(ps aux | grep -E "gunicorn.*run:app" | grep -v grep)
if [ -n "$PROCESSES" ]; then
    PROCESS_COUNT=$(echo "$PROCESSES" | wc -l)
    echo -e "${GREEN}✓${NC} 找到 $PROCESS_COUNT 个 Gunicorn 进程"
    echo "$PROCESSES" | head -3
else
    echo -e "${RED}✗${NC} 未找到 Gunicorn 进程"
fi
echo ""

# 4. 测试本地连接
echo "【4】测试本地连接 (127.0.0.1:8000)..."
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://127.0.0.1:8000 2>/dev/null)
if [ "$HTTP_RESPONSE" = "200" ] || [ "$HTTP_RESPONSE" = "302" ] || [ "$HTTP_RESPONSE" = "301" ]; then
    echo -e "${GREEN}✓${NC} 本地连接成功 (HTTP $HTTP_RESPONSE)"
elif [ -z "$HTTP_RESPONSE" ]; then
    echo -e "${RED}✗${NC} 无法连接到 127.0.0.1:8000"
    echo "  可能原因: Gunicorn 未运行或未监听该地址"
else
    echo -e "${YELLOW}⚠${NC} 连接成功但返回异常状态码: HTTP $HTTP_RESPONSE"
fi
echo ""

# 5. 检查 Nginx 错误日志（最近 10 行）
echo "【5】检查 Nginx 错误日志（最近 10 行）..."
if [ -f "/var/log/nginx/error.log" ]; then
    echo "  最近的错误:"
    sudo tail -10 /var/log/nginx/error.log | grep -i "502\|upstream\|connect" || echo "  未发现相关错误"
elif [ -f "/var/log/nginx/quiz-app-error.log" ]; then
    echo "  最近的错误:"
    sudo tail -10 /var/log/nginx/quiz-app-error.log | grep -i "502\|upstream\|connect" || echo "  未发现相关错误"
else
    echo -e "${YELLOW}⚠${NC} 未找到 Nginx 错误日志文件"
fi
echo ""

# 6. 检查 Gunicorn 错误日志（如果服务文件存在）
echo "【6】检查 Gunicorn 错误日志..."
if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    JOURNAL_LOGS=$(sudo journalctl -u $SERVICE_NAME -n 20 --no-pager 2>/dev/null | tail -10)
    if [ -n "$JOURNAL_LOGS" ]; then
        echo "  最近的 systemd 日志:"
        echo "$JOURNAL_LOGS" | grep -i "error\|fail\|exception" || echo "  未发现错误"
    fi
fi

# 检查日志文件
if [ -f "logs/gunicorn_error.log" ]; then
    echo "  最近的错误日志:"
    tail -10 logs/gunicorn_error.log | grep -i "error\|fail\|exception" || echo "  未发现错误"
fi
echo ""

# 7. 检查 Nginx 配置
echo "【7】检查 Nginx 配置..."
NGINX_CONFIG_ERROR=$(sudo nginx -t 2>&1)
if echo "$NGINX_CONFIG_ERROR" | grep -q "successful"; then
    echo -e "${GREEN}✓${NC} Nginx 配置语法正确"
else
    echo -e "${RED}✗${NC} Nginx 配置有错误:"
    echo "$NGINX_CONFIG_ERROR"
fi
echo ""

# 总结和建议
echo "=========================================="
echo "诊断总结"
echo "=========================================="
echo ""
echo "快速修复步骤："
echo ""
echo "1. 如果 Gunicorn 服务未运行:"
echo "   sudo systemctl start $SERVICE_NAME"
echo "   sudo systemctl status $SERVICE_NAME"
echo ""
echo "2. 查看详细错误信息:"
echo "   sudo journalctl -u $SERVICE_NAME -n 50"
echo ""
echo "3. 检查服务配置文件:"
echo "   sudo systemctl cat $SERVICE_NAME"
echo ""
echo "4. 手动测试 Gunicorn 启动:"
echo "   cd /path/to/quiz-app"
echo "   source venv/bin/activate"
echo "   gunicorn -c gunicorn_config.py run:app"
echo ""
echo "5. 如果以上都正常，重启 Nginx:"
echo "   sudo systemctl restart nginx"
echo ""

