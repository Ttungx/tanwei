# 部署指南

本文档详细介绍如何在不同的环境中部署探微 (Tanwei) 系统。

---

## 目录

- [环境要求](#环境要求)
- [本地部署](#本地部署)
- [生产环境部署](#生产环境部署)
- [离线部署](#离线部署)
- [Kubernetes 部署](#kubernetes-部署)
- [配置调优](#配置调优)

---

## 环境要求

### 硬件要求

| 环境 | CPU | 内存 | 磁盘 | 说明 |
|------|-----|------|------|------|
| 开发环境 | 2 核 | 4 GB | 10 GB | 基本运行 |
| 测试环境 | 4 核 | 8 GB | 20 GB | 推荐配置 |
| 生产环境 | 4 核+ | 8 GB+ | 50 GB | 根据负载调整 |

### 软件要求

| 软件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Docker | 20.10 | 24.0+ |
| Docker Compose | 2.0 | 2.20+ |
| Linux Kernel | 4.18 | 5.10+ |

### 网络要求

| 端口 | 服务 | 协议 |
|------|------|------|
| 3000 | Web 控制台 | HTTP |
| 8001 | SVM 服务 | HTTP |
| 8002 | Agent 服务 | HTTP |
| 8080 | LLM 服务 | HTTP |

---

## 本地部署

### 步骤 1：准备模型文件

```bash
# 检查模型文件是否存在
ls -la /root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf

# 预期大小：约 508MB
```

如果模型文件不存在，需要从 HuggingFace 或其他源下载 Qwen3.5-0.8B Q4_K_M 量化版本。

### 步骤 2：配置环境变量（可选）

```bash
# 创建 .env 文件
cat > /root/anxun/.env << EOF
# 服务配置
LOG_LEVEL=INFO
MAX_TIME_WINDOW=60
MAX_PACKET_COUNT=10
MAX_TOKEN_LENGTH=690

# 资源限制
LLM_MEMORY=1G
SVM_MEMORY=300M
AGENT_MEMORY=500M
CONSOLE_MEMORY=512M
EOF
```

### 步骤 3：构建并启动

```bash
cd /root/anxun

# 构建所有镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

### 步骤 4：验证部署

```bash
# 检查容器状态
docker-compose ps

# 健康检查
curl -s http://localhost:8080/health | jq
curl -s http://localhost:8001/health | jq
curl -s http://localhost:8002/health | jq
curl -s http://localhost:3000/health | jq
```

---

## 生产环境部署

### 1. 系统优化

```bash
# 增加文件描述符限制
cat >> /etc/security/limits.conf << EOF
* soft nofile 65535
* hard nofile 65535
EOF

# 优化内核参数
cat >> /etc/sysctl.conf << EOF
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
vm.swappiness = 10
EOF

sysctl -p
```

### 2. Docker 配置

```bash
# 创建 Docker 配置目录
mkdir -p /etc/docker

# 配置 Docker daemon
cat > /etc/docker/daemon.json << EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65535,
      "Soft": 65535
    }
  }
}
EOF

# 重启 Docker
systemctl restart docker
```

### 3. 使用生产配置

创建 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  llm-service:
    image: ghcr.io/ggerganov/llama.cpp:server
    restart: always
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  svm-filter-service:
    restart: always
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  agent-loop:
    restart: always
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  edge-test-console:
    restart: always
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
```

启动生产环境：

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 离线部署

适用于无法连接外网的环境。

### 1. 在有网络的机器上准备镜像

```bash
# 拉取所需镜像
docker pull ghcr.io/ggerganov/llama.cpp:server
docker pull python:3.10-slim

# 构建项目镜像
cd /root/anxun
docker-compose build

# 导出所有镜像
docker save -o tanwei-images.tar \
  ghcr.io/ggerganov/llama.cpp:server \
  python:3.10-slim \
  tanwei_svm-filter-service \
  tanwei_agent-loop \
  tanwei_edge-test-console

# 打包项目文件
tar -czvf tanwei-project.tar.gz \
  /root/anxun \
  --exclude='*.venv' \
  --exclude='*/__pycache__' \
  --exclude='*/node_modules'
```

### 2. 传输到离线环境

```bash
# 使用 U 盘或其他方式传输
# - tanwei-images.tar
# - tanwei-project.tar.gz
```

### 3. 在离线环境部署

```bash
# 解压项目
tar -xzvf tanwei-project.tar.gz -C /

# 导入镜像
docker load -i tanwei-images.tar

# 启动服务
cd /root/anxun
docker-compose up -d
```

---

## Kubernetes 部署

### 1. 创建命名空间

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tanwei
```

### 2. 创建 ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tanwei-config
  namespace: tanwei
data:
  SVM_SERVICE_URL: "http://svm-filter-service:8001"
  LLM_SERVICE_URL: "http://llm-service:8080"
  MAX_TIME_WINDOW: "60"
  MAX_PACKET_COUNT: "10"
  MAX_TOKEN_LENGTH: "690"
  LOG_LEVEL: "INFO"
```

### 3. 创建部署文件

```yaml
# llm-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-service
  namespace: tanwei
spec:
  replicas: 1
  selector:
    matchLabels:
      app: llm-service
  template:
    metadata:
      labels:
        app: llm-service
    spec:
      containers:
      - name: llm-service
        image: ghcr.io/ggerganov/llama.cpp:server
        args:
        - --model
        - /models/Qwen3.5-0.8B-Q4_K_M.gguf
        - --host
        - "0.0.0.0"
        - --port
        - "8080"
        - --ctx-size
        - "2048"
        - --threads
        - "2"
        resources:
          limits:
            memory: "1Gi"
          requests:
            memory: "512Mi"
        volumeMounts:
        - name: model-volume
          mountPath: /models
      volumes:
      - name: model-volume
        hostPath:
          path: /root/anxun/qwen3.5-0.8b
          type: Directory
---
apiVersion: v1
kind: Service
metadata:
  name: llm-service
  namespace: tanwei
spec:
  selector:
    app: llm-service
  ports:
  - port: 8080
    targetPort: 8080
```

### 4. 部署

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f llm-service.yaml
# ... 其他服务
```

---

## 配置调优

### LLM 服务调优

```yaml
# docker-compose.yml 中 llm-service 配置
environment:
  - CTX_SIZE=4096        # 增加上下文窗口
  - THREADS=4            # 增加推理线程
  - N_GPU_LAYERS=0       # GPU 加速（如有）
```

### Agent 服务调优

```yaml
# docker-compose.yml 中 agent-loop 配置
environment:
  - MAX_TIME_WINDOW=30   # 减少时间窗口
  - MAX_PACKET_COUNT=5   # 减少包数量
  - MAX_TOKEN_LENGTH=512 # 减少 Token 长度
```

### SVM 服务调优

训练新的 SVM 模型：

```bash
# 进入容器
docker-compose exec svm-filter-service bash

# 使用真实数据训练
python models/train_svm.py --data /path/to/training/data

# 模型会保存到 /app/models/saved/
```

---

## 故障排除

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs -f agent-loop

# 查看最近 100 行
docker-compose logs --tail=100
```

### 进入容器调试

```bash
docker-compose exec agent-loop bash
```

### 检查资源使用

```bash
docker stats
```

---

## 版本升级

```bash
# 1. 备份数据
docker-compose exec agent-loop tar -czvf /tmp/uploads.tar.gz /app/uploads

# 2. 拉取新代码
git pull

# 3. 重新构建
docker-compose build

# 4. 重启服务
docker-compose up -d

# 5. 验证
curl http://localhost:3000/health
```
