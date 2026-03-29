# 探微 (Tanwei) - Agent Loop 容器
# EdgeAgent 核心大脑：五阶段工作流执行
# 技术栈：Python 3.10-slim + scapy + FastAPI

FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（scapy 需要 tcpdump，其他为网络工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tcpdump \
    tshark \
    libpcap-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# 注意：禁止引入 PyTorch、TensorFlow
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 创建上传目录
RUN mkdir -p /app/uploads

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 8002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
