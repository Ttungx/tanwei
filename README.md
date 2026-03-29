# 探微 (Tanwei) - EdgeAgent 本地闭环仿真系统

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10-green.svg)
![Docker](https://img.shields.io/badge/docker--compose-3.8-blue.svg)

**边缘智能体本地验证平台** | **四容器微服务架构** | **带宽压降 > 70%**

[快速开始](#快速开始) • [文档](#文档目录) • [架构](#架构概览) • [API](#api参考)

</div>

---

## 项目简介

探微 (Tanwei) 是一个用于边缘智能体（EdgeAgent）本地闭环验证的仿真与测试系统。采用四容器微服务架构，实现基于离线 Pcap 流量包的：

- 🔍 **四级漏斗过滤**：SVM 微秒级初筛 + LLM 深度推理
- 📉 **带宽压降 > 70%**：原始流量 → JSON 威胁情报
- 🧠 **边缘模型**：Qwen3.5-0.8B INT4 量化，CPU 推理
- 🖥️ **可视化控制台**：Vue 3 前端 + 实时流水线状态

---

## 快速开始

### 前置条件

- Docker ≥ 20.10
- Docker Compose ≥ 2.0
- 内存 ≥ 4GB

将[模型文件](https://www.modelscope.cn/models/unsloth/Qwen3.5-0.8B-GGUF/file/view/master/Qwen3.5-0.8B-Q4_K_M.gguf?status=2)放到文件夹qwen3.5-0.8b中：qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf

### 三步启动

```bash
# 1. 进入项目目录
cd /root/anxun

# 2. 启动所有服务
docker-compose up -d

# 3. 访问 Web 控制台
# 浏览器打开: http://localhost:3000
```

### 验证服务

```bash
# 检查服务状态
docker-compose ps

# 健康检查
curl http://localhost:3000/health
curl http://localhost:8002/health
curl http://localhost:8001/health
curl http://localhost:8080/health
```

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    EdgeAgent 仿真四容器拓扑                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐                                           │
│   │ edge-test-console │ ◄── 用户上传 Pcap                        │
│   │   端口: 3000     │                                          │
│   └────────┬────────┘                                           │
│            │                                                    │
│            ▼                                                    │
│   ┌─────────────────┐      ┌─────────────────┐                  │
│   │   agent-loop    │─────►│  llm-service    │                  │
│   │   端口: 8002     │      │   端口: 8080    │                  │
│   └────────┬────────┘      └─────────────────┘                  │
│            │                                                    │
│            ▼                                                    │
│   ┌─────────────────┐                                           │
│   │svm-filter-service│                                          │
│   │   端口: 8001     │                                          │
│   └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 容器说明

| 容器 | 端口 | 内存 | 技术栈 | 功能 |
|------|------|------|--------|------|
| edge-test-console | 3000 | 512MB | Vue 3 + FastAPI | Web 控制台 |
| agent-loop | 8002 | 500MB | FastAPI + scapy | 核心大脑 |
| svm-filter-service | 8001 | 300MB | FastAPI + sklearn | SVM 初筛 |
| llm-service | 8080 | 1GB | llama.cpp | LLM 推理 |

---

## 文档目录

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | 完整项目文档 |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | 快速启动指南 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架构设计文档 |
| [docs/API_SPEC.md](docs/API_SPEC.md) | API 接口规范 |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | 部署指南 |

---

## 项目结构

```
/root/anxun/
├── docker-compose.yml          # 容器编排配置
├── CLAUDE.md                   # 项目全局指引
├── README.md                   # 本文档
│
├── docs/                       # 文档目录
│
├── llm-service/                # 容器1: LLM 推理引擎
├── svm-filter-service/         # 容器2: SVM 过滤服务
├── agent-loop/                 # 容器3: 智能体主控
├── edge-test-console/          # 容器4: 测试控制台
│
├── TrafficLLM-master/          # TrafficLLM 依赖
└── qwen3.5-0.8b/               # 边缘基座模型
```

---

## API 参考

### 核心端点

```bash
# 上传 Pcap 启动检测
POST /api/detect
Response: { "task_id": "uuid", "status": "success" }

# 查询任务状态
GET /api/status/{task_id}
Response: { "stage": "llm_inference", "progress": 75 }

# 获取检测结果
GET /api/result/{task_id}
Response: { "threats": [...], "metrics": {...} }
```

详细 API 规范请参阅 [API_SPEC.md](docs/API_SPEC.md)。

---

## 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f agent-loop

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建
docker-compose up --build -d
```

---

## 许可证

MIT License

---

<div align="center">

**探微架构团队** | 2026

</div>
