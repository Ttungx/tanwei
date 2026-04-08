# 探微 (Tanwei) - Console + Edge-Agent + Central-Agent

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10-green.svg)
![Docker](https://img.shields.io/badge/docker--compose-3.8-blue.svg)
![React](https://img.shields.io/badge/react-18.3-61dafb.svg)

**端云协同安全分析平台** | **Console-Edge-Central 架构** | **核心网上行带宽压降 > 70%**

[快速开始](#快速开始) | [架构概览](#架构概览) | [API 参考](#api-参考) | [文档](#文档目录)

</div>

---

## 项目简介

探微 (Tanwei) 是一个面向 `console + edge-agent + central-agent` 协同架构的仿真与验证系统。第一阶段重点是统一命名、契约和 harness，让边缘检测闭环与中心侧综合分析在同一控制台下协作，并持续守住“核心网上行带宽占用降低 70% 以上”的硬性 KPI。

### 核心特性

| 特性 | 说明 |
| --- | --- |
| **端云协同** | `console` 同时驱动 `edge-agent` 检测与 `central-agent` 分析 |
| **边缘闭环** | `edge-agent -> svm-filter-service / llm-service` 五阶段检测链路 |
| **中心研判** | `central-agent` 支持单 Edge 分析与手动全网综合研判 |
| **带宽压降 > 70%** | 端云之间仅传结构化情报，不上传原始 pcap/payload |

### 技术栈

| 服务 | 技术栈 | 默认端口 | 说明 |
| --- | --- | --- | --- |
| `console` | React 18 + TypeScript + Vite + FastAPI | 3000 | 统一控制台与管理员入口 |
| `edge-agent` | FastAPI + scapy + numpy | 8002 | 边缘侧检测编排与情报生产 |
| `central-agent` | FastAPI + 外部 LLM API | 8003 | 中心侧归档、单 Edge 分析、全网研判 |
| `svm-filter-service` | FastAPI + scikit-learn | 8001 | 边缘侧 SVM 在线过滤 |
| `llm-service` | llama.cpp server | 8080 | 边缘侧本地 LLM 推理 |

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
curl http://localhost:8003/health
curl http://localhost:8001/health
curl http://localhost:8080/health
```

---

## 架构概览

```text
console -> edge-agent -> svm-filter-service / llm-service
console -> central-agent
edge-agent -> central-agent   (仅上报结构化情报，不上传原始证据)
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

```text
console ──► edge-agent ──► svm-filter-service
   │             │
   │             └──────► llm-service
   │
   └──────► central-agent

edge-agent ─────► central-agent
```

- `console` 不能绕过 `edge-agent` 直接调用 `svm-filter-service` / `llm-service`
- `edge-agent -> central-agent` 只允许结构化情报，不允许原始 pcap/payload/完整十六进制包
- `central-agent` 不可用时，不得阻断边缘检测闭环完成

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

## Harness 与 Agent Roster

### 默认执行链

`lead-agent -> specialist -> evaluator-agent -> doc-gardener`

### 本次架构重构的核心 specialist

| Agent | 主要职责 |
| --- | --- |
| `edge-agent-engineer` | `edge-agent/` 编排、边缘情报生成、端云上报契约 |
| `central-agent-engineer` | `central-agent/` 接收归档、单 Edge 分析、全网研判触发 |
| `console-developer` | `console/` 管理员流、展示与触发交互 |
| `docker-expert` | 容器编排与部署边界（涉及 central 外部 LLM 依赖时必需） |

完整 roster 与统一范式见 [`.claude/agents/README.md`](.claude/agents/README.md)。

---

## 文档目录

| 文档                                                                                             | 说明                         |
| ------------------------------------------------------------------------------------------------ | ---------------------------- |
| [CLAUDE.md](CLAUDE.md)                                                                           | 项目全局指引与 AI Agent 路由 |
| [docs/design-docs/architecture.md](docs/design-docs/architecture.md)                             | Console-Edge-Central 架构与边界规范 |
| [docs/design-docs/core-beliefs.md](docs/design-docs/core-beliefs.md)                             | 核心信仰与物理约束红线       |
| [docs/design-docs/traffic-tokenization.md](docs/design-docs/traffic-tokenization.md)             | 流量分词规范                 |
| [docs/references/api_specs.md](docs/references/api_specs.md)                                     | API 接口规范                 |
| [docs/references/deployment.md](docs/references/deployment.md)                                   | 部署指南                     |
| [docs/references/dataset-feature-engineering.md](docs/references/dataset-feature-engineering.md) | 数据集与特征工程             |
| [docs/exec-plans/active-plan.md](docs/exec-plans/active-plan.md)                                 | 当前执行计划                 |
| [docs/exec-plans/tech-debt.md](docs/exec-plans/tech-debt.md)                                     | 技术债务追踪                 |
| [docs/questions/why-svm-for-traffic-filtering.md](docs/questions/why-svm-for-traffic-filtering.md) | SVM 流量初筛技术选型调研报告 |

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
│   ├── questions/              # 技术选型调研（面向人类）
│   └── references/             # API 规范与部署指南
│
├── llm-service/                # 边缘侧本地 LLM 推理服务
├── svm-filter-service/         # 边缘侧 SVM 过滤服务
├── edge-agent/                 # 边缘智能体编排与情报生产
├── central-agent/              # 中心智能体归档与分析
├── console/                    # 统一控制台与管理员入口
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
docker-compose logs -f edge-agent

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 重新构建
docker-compose up --build -d
```

---

## 项目状态

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| `llm-service` | 完成 | 边缘本地 LLM 推理服务可用 |
| `svm-filter-service` | 完成 | 32 维特征在线过滤可用 |
| `edge-agent` | 完成 | 五阶段检测流与边缘闭环可用 |
| `central-agent` | 进行中 | 中心归档与分析接口正在重构 |
| `console` | 完成 | 控制台前后端迁移到新命名 |
| 端到端联调 | 进行中 | 第一阶段不要求真实多 Edge 联调 |

---

## 许可证

Apache 2.0 License

---

<div align="center">

**探微架构团队** | 2026

</div>
