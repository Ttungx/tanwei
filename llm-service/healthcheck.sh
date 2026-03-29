#!/bin/sh
# LLM Service Health Check Script
# 用于 Docker 健康检查

set -e

# 检查 llama.cpp server 是否响应
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null || echo "000")

if [ "$response" = "200" ]; then
    echo "healthy"
    exit 0
else
    echo "unhealthy (HTTP $response)"
    exit 1
fi
