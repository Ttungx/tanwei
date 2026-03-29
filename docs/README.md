# 探微 (Tanwei) - EdgeAgent 本地闭环仿真与测试系统

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10-green.svg)
![Docker](https://img.shields.io/badge/docker-compose-3.8-blue.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**边缘智能体本地验证平台 | 四容器微服务架构 | 带宽压降 > 70%**

</div>

---

## 📖 目录

- [项目简介](#项目简介)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [环境要求](#环境要求)
- [部署指南](#部署指南)
- [使用说明](#使用说明)
- [API 参考](#api-参考)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

---

## 项目简介

**探微 (Tanwei)** 是一个用于边缘智能体（EdgeAgent）本地闭环验证的仿真与测试系统。本项目采用四容器微服务架构，在 WSL 环境下实现基于离线 Pcap 流量包的本地提取、微秒级初筛、跨模态 Token 转换与 LLM 推理定性流程。

### 核心特性

| 特性 | 说明 |
|------|------|
| 🔍 **四级漏斗过滤** | SVM 微秒级初筛 + LLM 深度推理 |
| 📉 **带宽压降 > 70%** | 原始流量 → JSON 威胁情报，大幅减少上行带宽 |
| 🧠 **边缘模型** | Qwen3.5-0.8B INT4 量化，CPU 推理 |
| 🔄 **跨模态对齐** | 复用 TrafficLLM 分词逻辑 |
| 🖥️ **可视化控制台** | Vue 3 前端 + 实时流水线状态 |

---

## 系统架构

### 四容器拓扑

```
┌─────────────────────────────────────────────────────────────────┐
│                    EdgeAgent 仿真四容器拓扑                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────┐                                           │
│   │ edge-test-console │ ◄── 用户上传 Pcap 文件                   │
│   │ (Vue3 + FastAPI)  │     端口: 3000                           │
│   └────────┬────────┘                                           │
│            │ HTTP API                                           │
│            ▼                                                     │
│   ┌─────────────────┐      ┌─────────────────┐                  │
│   │   agent-loop    │─────►│  llm-service    │                  │
│   │   (核心大脑)     │      │ (Qwen3.5-0.8B)  │                  │
│   │   端口: 8002    │      │   端口: 8080    │                  │
│   └────────┬────────┘      └─────────────────┘                  │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐                                           │
│   │svm-filter-service│ ◄── 微秒级二分类                          │
│   │   端口: 8001    │                                          │
│   └─────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 五阶段工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                     Agent-Loop 五阶段工作流                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  阶段 1: 流重组                                                  │
│  ├── 读取 .pcap 文件                                            │
│  └── 按 (src_ip, dst_ip, src_port, dst_port, proto) 重组会话     │
│                                                                 │
│  阶段 2: 双重截断                                                │
│  ├── 时间窗口 ≤ 60 秒                                           │
│  └── 提取包数量 ≤ 前 10 个                                       │
│                                                                 │
│  阶段 3: SVM 初筛                                                │
│  ├── 提取 14 维统计特征                                          │
│  ├── 调用 svm-filter-service                                    │
│  └── 正常流 Drop，异常流进入阶段 4                                │
│                                                                 │
│  阶段 4: 跨模态分词                                              │
│  ├── 构建 TrafficLLM 格式指令                                    │
│  └── Token 序列长度 ≤ 690                                        │
│                                                                 │
│  阶段 5: LLM 推理                                                │
│  ├── 调用 llama.cpp server                                      │
│  └── 生成 JSON 威胁情报                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 一键启动

```bash
# 1. 克隆项目
cd /root/anxun

# 2. 构建并启动所有服务
docker-compose up --build -d

# 3. 查看服务状态
docker-compose ps

# 4. 访问 Web 界面
# 浏览器打开: http://localhost:3000
```

### 验证服务

```bash
# 检查所有服务健康状态
curl http://localhost:8080/health    # LLM 服务
curl http://localhost:8001/health    # SVM 服务
curl http://localhost:8002/health    # Agent 服务
curl http://localhost:3000/health    # 控制台

# 预期输出: {"status": "healthy", ...}
```

---

## 环境要求

### 硬件要求

| 资源 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 5 GB | 10 GB |

### 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Docker | ≥ 20.10 | 容器运行时 |
| Docker Compose | ≥ 2.0 | 容器编排 |
| OS | Linux/WSL2 | 推荐 Ubuntu 20.04+ |

### 端口占用

| 端口 | 服务 | 说明 |
|------|------|------|
| 3000 | edge-test-console | Web 控制台 |
| 8001 | svm-filter-service | SVM 过滤服务 |
| 8002 | agent-loop | 主控程序 |
| 8080 | llm-service | LLM 推理服务 |

---

## 部署指南

### 本地部署

#### 1. 准备模型文件

```bash
# 确保 GGUF 模型文件存在
ls -la /root/anxun/qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf

# 预期输出: 文件大小约 508MB
```

#### 2. 构建镜像

```bash
cd /root/anxun

# 构建所有镜像
docker-compose build

# 或单独构建
docker-compose build svm-filter-service
docker-compose build agent-loop
docker-compose build edge-test-console
```

#### 3. 启动服务

```bash
# 前台启动（查看日志）
docker-compose up

# 后台启动
docker-compose up -d

# 查看日志
docker-compose logs -f agent-loop
```

#### 4. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并清理数据
docker-compose down -v
```

---

### 另一台设备部署

#### 方法一：完整迁移

```bash
# 1. 打包项目
cd /root
tar -czvf anxun.tar.gz anxun/ \
  --exclude='anxun/.venv' \
  --exclude='anxun/TrafficLLM-master/models' \
  --exclude='anxun/.claude'

# 2. 传输到目标设备
scp anxun.tar.gz user@target-host:/root/

# 3. 在目标设备解压
ssh user@target-host
cd /root
tar -xzvf anxun.tar.gz

# 4. 下载模型文件（如果未包含）
# 模型需单独下载或传输
```

#### 方法二：Git + Docker Hub

```bash
# 1. 在开发机构建并推送镜像
docker login
docker-compose build
docker tag tanwei-svm-filter your-registry/tanwei-svm-filter:v1.0
docker push your-registry/tanwei-svm-filter:v1.0

# 2. 在目标设备拉取
docker pull your-registry/tanwei-svm-filter:v1.0
docker-compose up -d
```

#### 方法三：离线部署

```bash
# 1. 导出镜像
docker save -o tanwei-images.tar \
  ghcr.io/ggerganov/llama.cpp:server \
  tanwei-svm-filter \
  tanwei-agent-loop \
  tanwei-edge-test-console

# 2. 在目标设备导入
docker load -i tanwei-images.tar

# 3. 启动服务
docker-compose up -d
```

---

## 使用说明

### Web 控制台

1. 打开浏览器访问 `http://localhost:3000`
2. 点击上传区域选择 `.pcap` 或 `.pcapng` 文件
3. 观察实时流水线状态：
   - 🔄 正在提取五元组、重组流
   - 🔄 SVM 初筛丢弃正常流量
   - 🔄 大模型正在进行 Token 推理
   - ✅ 检测完成
4. 查看检测结果：
   - 威胁列表（五元组、分类、置信度）
   - 带宽压降指标

### API 调用

```bash
# 上传 Pcap 文件
curl -X POST http://localhost:3000/api/detect \
  -F "file=@test.pcap"

# 响应: {"status": "success", "task_id": "uuid", ...}

# 查询状态
curl http://localhost:3000/api/status/{task_id}

# 获取结果
curl http://localhost:3000/api/result/{task_id}
```

---

## API 参考

详细 API 规范请参阅 [API_SPEC.md](./API_SPEC.md)。

### 核心端点

| 端点 | 方法 | 服务 | 说明 |
|------|------|------|------|
| `/api/detect` | POST | agent-loop | 上传 Pcap 启动检测 |
| `/api/status/{task_id}` | GET | agent-loop | 查询任务状态 |
| `/api/result/{task_id}` | GET | agent-loop | 获取检测结果 |
| `/api/classify` | POST | svm-filter | SVM 二分类 |
| `/completion` | POST | llm-service | LLM 文本补全 |

---

## 开发指南

### 项目结构

```
/root/anxun/
├── docker-compose.yml          # 容器编排配置
├── CLAUDE.md                   # 项目全局指引
│
├── docs/                       # 文档目录
│   ├── README.md               # 本文档
│   ├── ARCHITECTURE.md         # 架构设计文档
│   └── API_SPEC.md             # API 接口规范
│
├── llm-service/                # 容器1: LLM 推理引擎
│   ├── README.md
│   ├── healthcheck.sh
│   └── test_llm.py
│
├── svm-filter-service/         # 容器2: SVM 过滤服务
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py             # FastAPI 主程序
│   └── models/
│       ├── train_svm.py        # 模型训练脚本
│       └── saved/              # 预训练模型
│
├── agent-loop/                 # 容器3: 智能体主控
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI 主程序
│       ├── flow_processor.py   # 流重组与特征提取
│       └── traffic_tokenizer.py # 跨模态分词
│
├── edge-test-console/          # 容器4: 测试控制台
│   ├── Dockerfile
│   ├── backend/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/main.py         # FastAPI 后端代理
│   └── frontend/
│       ├── package.json
│       └── src/
│           ├── App.vue
│           ├── main.js
│           └── components/
│
├── TrafficLLM-master/          # TrafficLLM 依赖（只读）
│   ├── preprocess/             # 流量预处理模块
│   └── tokenization/           # 分词器
│
└── qwen3.5-0.8b/               # 边缘基座模型
    └── Qwen3.5-0.8B-Q4_K_M.gguf
```

### 本地开发

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -r agent-loop/requirements.txt

# 运行单个服务
cd agent-loop
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 资源约束

| 容器 | CPU | 内存 | 说明 |
|------|-----|------|------|
| llm-service | 2 线程 | 1GB | 量化模型推理 |
| svm-filter-service | 1 核 | 300MB | 轻量级 ML |
| agent-loop | 2 核 | 500MB | 主控逻辑 |
| edge-test-console | 1 核 | 512MB | Web 服务 |

---

## 常见问题

### Q1: LLM 服务启动失败

**原因**：模型文件不存在或路径错误

**解决**：
```bash
# 检查模型文件
ls -la ./qwen3.5-0.8b/Qwen3.5-0.8B-Q4_K_M.gguf

# 如果缺失，下载模型
# (从 HuggingFace 或其他源下载 Qwen3.5-0.8B Q4_K_M 量化版本)
```

### Q2: 容器内存不足

**原因**：系统内存不足

**解决**：
```bash
# 检查 Docker 资源限制
docker info | grep Memory

# 调整 docker-compose.yml 中的内存限制
deploy:
  resources:
    limits:
      memory: 512M
```

### Q3: 端口冲突

**原因**：端口已被占用

**解决**：
```bash
# 检查端口占用
netstat -tlnp | grep -E '3000|8001|8002|8080'

# 修改 docker-compose.yml 中的端口映射
ports:
  - "3001:80"  # 将 3000 改为 3001
```

### Q4: SVM 模型未找到

**原因**：预训练模型未生成

**解决**：
```bash
# 进入容器训练模型
docker-compose exec svm-filter-service bash
python -c "from app.main import train_default_model; train_default_model()"
```

### Q5: Pcap 文件解析失败

**原因**：文件格式不支持或损坏

**解决**：
```bash
# 验证 Pcap 文件
tcpdump -r test.pcap -c 5

# 或使用 tshark
tshark -r test.pcap -Y "tcp" -c 5
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-03-29 | 初始版本，四容器架构完成 |

---

## 许可证

MIT License

---

## 联系方式

- 项目维护：探微架构团队
- 问题反馈：提交 Issue 或联系开发团队
