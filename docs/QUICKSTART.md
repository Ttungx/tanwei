# 快速启动指南

本文档提供探微 (Tanwei) 系统的快速启动步骤。

## 前置条件

- Docker 已安装（≥ 20.10）
- Docker Compose 已安装（≥ 2.0）
- 至少 4GB 可用内存

## 三步启动

### 步骤 1：进入项目目录

```bash
cd /root/anxun
```

### 步骤 2：启动所有服务

```bash
docker-compose up -d
```

首次启动会自动构建镜像，约需 5-10 分钟。

### 步骤 3：验证服务状态

```bash
# 查看容器状态
docker-compose ps

# 预期输出：所有服务状态为 "healthy" 或 "running"
```

## 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| Web 控制台 | http://localhost:3000 | 上传 Pcap 文件，查看检测结果 |
| SVM API | http://localhost:8001/docs | Swagger 文档 |
| Agent API | http://localhost:8002/docs | Swagger 文档 |
| LLM API | http://localhost:8080 | llama.cpp server |

## 测试检测流程@

### 方法一：Web 界面

1. 打开浏览器访问 `http://localhost:3000`
2. 点击上传区域选择 `.pcap` 文件
3. 等待检测完成
4. 查看威胁检测结果和带宽压降指标

### 方法二：API 调用

```bash
# 1. 上传 Pcap 文件
curl -X POST http://localhost:3000/api/detect \
  -F "file=@your-file.pcap"

# 记录返回的 task_id

# 2. 查询状态（轮询直到 completed）
curl http://localhost:3000/api/status/{task_id}

# 3. 获取结果
curl http://localhost:3000/api/result/{task_id}
```

## 常用命令

```bash
# 查看日志
docker-compose logs -f agent-loop

# 重启单个服务
docker-compose restart agent-loop

# 停止所有服务
docker-compose down

# 重新构建镜像
docker-compose up --build -d
```

## 下一步

- 阅读完整文档：[README.md](./README.md)
- 了解架构设计：[ARCHITECTURE.md](./ARCHITECTURE.md)
- 查看 API 规范：[API_SPEC.md](./API_SPEC.md)
