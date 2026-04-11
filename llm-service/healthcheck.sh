#!/bin/sh
# LLM Service Health Check Script
# 用于 Docker 健康检查
# 支持 llama.cpp server 的 /health 和 /props 端点

set -e

# 尝试 /health 端点（llama.cpp server 主健康端点）
health_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo "000")

if [ "$health_response" = "200" ]; then
    echo "healthy (via /health)"
    exit 0
fi

# 如果 /health 不可用，尝试 /props 作为备用检查
# /props 返回模型信息，可用于验证服务是否已加载模型
props_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/props 2>/dev/null || echo "000")

if [ "$props_response" = "200" ]; then
    echo "healthy (via /props)"
    exit 0
fi

# 两个端点都不健康
echo "unhealthy (health: $health_response, props: $props_response)"
exit 1