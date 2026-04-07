# 探微 (Tanwei) - EdgeAgent 边缘智能终端系统

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10-green.svg)
![Docker](https://img.shields.io/badge/docker--compose-3.8-blue.svg)
![React](https://img.shields.io/badge/react-18.3-61dafb.svg)

**边缘智能体本地闭环验证平台** | **四容器微服务架构** | **带宽压降 > 70%**

[快速开始](#快速开始) | [架构概览](#架构概览) | [API 参考](#api-参考) | [文档](#文档目录)

</div>

---

## 项目简介

探微 (Tanwei) 是一个用于边缘智能体（EdgeAgent）本地闭环验证的仿真与测试系统。系统采用四容器微服务架构，实现基于离线 Pcap 流量包的威胁检测与带宽压降。

### 核心特性

| 特性               | 说明                              |
| ------------------ | --------------------------------- |
| **四级漏斗过滤**   | SVM 微秒级初筛 + LLM 深度推理     |
| **带宽压降 > 70%** | 原始流量转换为 JSON 威胁情报      |
| **边缘模型**       | Qwen3.5-0.8B INT4 量化，CPU 推理  |
| **可视化控制台**   | React 18 + FastAPI 实时流水线状态 |

### 技术栈

| 容器               | 技术栈                                 | 端口 | 内存  |
| ------------------ | -------------------------------------- | ---- | ----- |
| edge-test-console  | React 18 + TypeScript + Vite + FastAPI | 3000 | 512MB |
| agent-loop         | FastAPI + scapy + numpy                | 8002 | 500MB |
| svm-filter-service | FastAPI + scikit-learn                 | 8001 | 300MB |
| llm-service        | llama.cpp server                       | 8080 | 1GB   |

---

## 快速开始

### 前置条件

- Docker >= 20.10
- Docker Compose >= 2.0
- 内存 >= 4GB

### 模型文件准备

将 Qwen3.5-0.8B 量化模型放到指定目录：

```
qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf
```

模型下载：[ModelScope](https://www.modelscope.cn/models/unsloth/Qwen3.5-0.8B-GGUF/file/view/master/Qwen3.5-0.8B-Q4_K_M.gguf)

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
│                    EdgeAgent 四容器拓扑                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌───────────────────┐                                         │
│   │ edge-test-console │ ◄── 用户上传 Pcap                        │
│   │   端口: 3000      │                                         │
│   └────────┬──────────┘                                         │
│            │ HTTP API (唯一入口)                                 │
│            ▼                                                    │
│   ┌─────────────────┐      ┌─────────────────┐                  │
│   │   agent-loop    │─────►│  llm-service    │                  │
│   │   端口: 8002    │      │   端口: 8080     │                  │
│   └────────┬────────┘      └─────────────────┘                  │
│            │                                                    │
│            ▼                                                    │
│   ┌──────────────────┐                                          │
│   │svm-filter-service│ ◄── 微秒级二分类                          │
│   │   端口: 8001      │                                         │
│   └──────────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 五阶段检测工作流

| 阶段 | 名称       | 说明                               |
| ---- | ---------- | ---------------------------------- |
| 1    | 流重组     | 基于五元组的双向流重组             |
| 2    | 双重截断   | 时间窗口 <= 60s，包数量 <= 10      |
| 3    | SVM 初筛   | 微秒级二分类，过滤正常流量         |
| 4    | 跨模态分词 | TrafficLLM 分词，Token 序列 <= 690 |
| 5    | LLM 推理   | Qwen3.5-0.8B 定性标签              |

### 通信边界约束

```
edge-test-console ──► agent-loop ──► svm-filter-service
                           │
                           └──► llm-service
```

**单向调用**：前端只能调用 agent-loop，禁止跨级直接调用 SVM 或 LLM。

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

详细 API 规范请参阅 [api_specs.md](docs/references/api_specs.md)。

---

## 文档目录

| 文档                                                                                             | 说明                         |
| ------------------------------------------------------------------------------------------------ | ---------------------------- |
| [CLAUDE.md](CLAUDE.md)                                                                           | 项目全局指引与 AI Agent 路由 |
| [docs/design-docs/architecture.md](docs/design-docs/architecture.md)                             | 四容器拓扑与边界规范         |
| [docs/design-docs/core-beliefs.md](docs/design-docs/core-beliefs.md)                             | 核心信仰与物理约束红线       |
| [docs/design-docs/traffic-tokenization.md](docs/design-docs/traffic-tokenization.md)             | 流量分词规范                 |
| [docs/references/api_specs.md](docs/references/api_specs.md)                                     | API 接口规范                 |
| [docs/references/deployment.md](docs/references/deployment.md)                                   | 部署指南                     |
| [docs/references/dataset-feature-engineering.md](docs/references/dataset-feature-engineering.md) | 数据集与特征工程             |
| [docs/exec-plans/active-plan.md](docs/exec-plans/active-plan.md)                                 | 当前执行计划                 |
| [docs/exec-plans/tech-debt.md](docs/exec-plans/tech-debt.md)                                     | 技术债务追踪                 |

---

## 项目结构

```
/root/anxun/
├── docker-compose.yml          # 容器编排配置
├── CLAUDE.md                   # 项目全局指引
├── README.md                   # 本文档
│
├── docs/                       # 文档目录
│   ├── design-docs/            # 架构设计
│   ├── exec-plans/             # 执行计划与技术债
│   └── references/             # API 规范与部署指南
│
├── llm-service/                # 容器1: LLM 推理引擎
├── svm-filter-service/         # 容器2: SVM 过滤服务
├── agent-loop/                 # 容器3: 智能体主控
├── edge-test-console/          # 容器4: 测试控制台
│
├── shared/                     # 共享模块 (日志配置等)
├── TrafficLLM-master/          # TrafficLLM 依赖 (外部)
├── qwen3.5-0.8b/               # 边缘基座模型 (外部)
└── data/                       # 数据与训练集
```

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

## 项目状态

| 模块               | 状态   | 说明                               |
| ------------------ | ------ | ---------------------------------- |
| llm-service        | 完成   | llama.cpp server 配置完成          |
| svm-filter-service | 完成   | 32 维特征，TrafficLLM 多数据集训练 |
| agent-loop         | 完成   | 五阶段工作流已实现                 |
| edge-test-console  | 完成   | React 18 前端 + FastAPI 后端代理   |
| 端到端测试         | 进行中 | 需要更多测试 Pcap 文件             |

---

## 许可证

Apache 2.0 License

---

<div align="center">

**探微架构团队** | 2026

</div>
