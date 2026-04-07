演示样本库是探微系统中用于快速验证检测能力的流量样本集合，提供了开箱即用的攻击场景演示能力。通过预置的 PCAP 流量样本，用户无需准备复杂的测试数据即可体验完整的五阶段检测工作流，包括 AI 攻击检测、永恒之蓝漏洞利用识别等典型威胁场景。样本库支持 `.pcap` 和 `.pcapng` 两种标准格式，既可以通过 Web 控制台一键启动检测，也可以通过 API 编程调用，为系统演示、功能验证和性能评估提供了标准化的测试基准。

Sources: [main.py](edge-test-console/backend/app/main.py#L67-L71)

## 样本库目录结构

演示样本库位于 `data/test_traffic/` 目录下，包含演示样本和训练数据两个主要部分。演示样本目录 `demo_show/` 专为 Web 控制台展示设计，其中的 PCAP 文件会自动出现在前端界面的样本列表中；而 `tran_data/TrafficLLM_Datasets/` 则存储了用于训练 SVM 模型的大规模流量数据集。这种分离设计确保了演示用途与训练用途的清晰边界，避免生产演示与模型训练相互干扰。

```
data/test_traffic/
├── demo_show/                    # 演示样本库（Web UI 展示）
│   └── .gitkeep                  # 占位文件（用户需添加样本）
├── DC-2_ai攻击.pcapng           # AI 攻击场景样本
├── DC-2_靶机.pcapng             # 靶机环境流量样本
└── 永恒之蓝.pcapng               # EternalBlue 漏洞利用样本
```

演示样本目录 `demo_show/` 默认仅包含 `.gitkeep` 占位文件，用户需要将实际流量样本放置到此目录。系统启动后，后端服务会自动扫描该目录下的所有 `.pcap` 和 `.pcapng` 文件，并生成带有友好显示名称的样本列表。例如，`apt_attack_001.pcap` 会被转换为 "Apt Attack 001" 这样的可读名称，提升用户体验。

Sources: [main.py](edge-test-console/backend/app/main.py#L96-L108)

## 演示样本使用流程

演示样本的使用流程遵循从样本选择到结果查看的完整检测链条，用户只需在 Web 控制台点击演示样本，即可触发后台的五阶段检测工作流。整个流程包括流重组、SVM 初筛、LLM 推理等环节，最终生成包含威胁情报的 JSON 报告，实现带宽压降超过 70% 的核心目标。

```mermaid
graph LR
    A[用户访问控制台] --> B[浏览演示样本列表]
    B --> C[点击样本启动检测]
    C --> D[后端复制样本到工作区]
    D --> E[启动后台检测任务]
    E --> F[五阶段检测工作流]
    F --> G[实时进度反馈]
    G --> H[生成威胁情报 JSON]
    H --> I[查看检测结果]
```

**步骤详解**：

1. **访问控制台**：浏览器打开 `http://localhost:3000`，进入演示界面
2. **浏览样本**：前端调用 `/api/demo-samples` 获取可用样本列表，显示文件名、大小等信息
3. **启动检测**：点击样本卡片，前端调用 `/api/detect-demo` 接口，传递 `sample_id` 参数
4. **后台处理**：后端将样本从 `demo_show/` 复制到上传工作区，启动异步检测任务
5. **进度跟踪**：前端轮询 `/api/status/{task_id}` 获取实时进度，显示当前阶段（流重组/SVM/LLM）
6. **查看结果**：检测完成后调用 `/api/result/{task_id}` 获取威胁情报 JSON，展示攻击类型、置信度等

Sources: [main.py](edge-test-console/backend/app/main.py#L450-L471)

## 演示样本 API 接口

演示样本功能通过两个核心 API 端点实现，遵循 RESTful 设计规范，支持跨域访问。这两个端点与标准检测 API `/api/detect` 共享相同的后台处理逻辑和任务管理机制，区别仅在于文件来源不同：演示样本从预置目录读取，而标准检测从用户上传获取。

### 获取样本列表

```http
GET /api/demo-samples
```

**响应示例**：

```json
[
  {
    "id": "apt_attack_001.pcap",
    "filename": "apt_attack_001.pcap",
    "display_name": "Apt Attack 001",
    "size_bytes": 524288
  },
  {
    "id": "eternalblue_exploit.pcapng",
    "filename": "eternalblue_exploit.pcapng",
    "display_name": "Eternalblue Exploit",
    "size_bytes": 1048576
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 样本文件名（作为 API 调用标识） |
| filename | string | 原始文件名 |
| display_name | string | 友好显示名称（下划线转空格，首字母大写） |
| size_bytes | integer | 文件大小（字节） |

### 启动演示检测

```http
POST /api/detect-demo
Content-Type: application/json

{
  "sample_id": "apt_attack_001.pcap"
}
```

**响应示例**：

```json
{
  "status": "success",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Detection task started"
}
```

该接口内部执行样本文件校验、路径安全检查、工作区复制等操作，确保演示样本的合法性和安全性。样本文件名仅允许字母、数字、下划线和扩展名，禁止包含路径分隔符等危险字符，防止目录遍历攻击。

Sources: [main.py](edge-test-console/backend/app/main.py#L450-L471)

## 添加自定义演示样本

用户可以向演示样本库添加自定义的 PCAP 流量样本，用于测试特定攻击场景或验证检测规则。添加过程需要遵循格式规范和路径要求，确保样本能够被系统正确识别和处理。

### 样本添加步骤

1. **准备 PCAP 文件**：使用 Wireshark、tcpdump 等工具捕获或生成流量样本，保存为 `.pcap` 或 `.pcapng` 格式

2. **命名规范**：采用描述性文件名，例如 `attack_type_scenario.pcap`，避免使用中文或特殊字符

3. **放置文件**：将样本复制到演示目录

```bash
# 示例：添加 Web Shell 攻击样本
cp webshell_attack.pcap data/test_traffic/demo_show/

# 示例：添加横向移动样本
cp lateral_movement.pcapng data/test_traffic/demo_show/
```

4. **重启服务**（可选）：如果服务已运行，需要重启 edge-test-console 容器以刷新样本列表

```bash
docker-compose restart edge-test-console
```

### 样本质量要求

| 要求项 | 说明 | 原因 |
|--------|------|------|
| 文件大小 | 建议 < 50MB | 避免上传超时和内存压力 |
| 包数量 | 建议 10-1000 个包 | 平衡检测效果与处理速度 |
| 协议完整性 | 包含完整 TCP/UDP 会话 | 流重组需要双向流量 |
| 时间跨度 | 建议 < 60 秒 | 符合系统时间窗口约束 |
| 攻击特征 | 包含明确的攻击行为 | 确保 LLM 能准确分类 |

### 示例样本场景

推荐添加以下典型攻击场景样本：

| 场景类型 | 攻击特征 | 检测重点 |
|----------|----------|----------|
| SQL 注入 | 异常 HTTP 请求、长 URL 参数 | LLM 识别注入模式 |
| 命令注入 | 特殊字符序列、系统命令特征 | 协议行为异常 |
| C2 通信 | 定时心跳包、加密负载 | SVM + LLM 协同检测 |
| 横向移动 | SMB/RDP 异常连接、凭证传递 | 多端口扫描特征 |
| 数据渗出 | 大量外连、DNS 隧道特征 | 流量行为异常 |

Sources: [main.py](edge-test-console/backend/app/main.py#L77-L95)

## 训练数据集概览

虽然演示样本用于实时检测演示，但理解训练数据集的构成有助于评估系统的检测能力和适用范围。TrafficLLM 数据集位于 `data/tran_data/TrafficLLM_Datasets/`，包含 12 个子数据集、超过 520,000 条流量样本，覆盖 APT 攻击、僵尸网络、加密恶意软件、VPN/Tor 流量等多种场景。这些数据集用于训练 SVM 过滤模型，确保模型能够在大规模正常流量中准确筛选出异常样本，实现 90% 以上的正常流量过滤率。

### 数据集分类

| 数据集名称 | 训练样本数 | 任务类型 | 标签体系 |
|-----------|-----------|----------|----------|
| DAPT-2020 | 9,500 | APT 攻击检测 | 二分类 |
| CSIC-2010 | 25,953 | HTTP 攻击检测 | 二分类 |
| USTC-TFC-2016 | 48,282 | 加密恶意软件检测 | 20 类 → 二分类映射 |
| ISCX-Botnet-2014 | 23,750 | 僵尸网络检测 | 5 类 → 二分类映射 |
| ISCX-VPN-2016 | 61,609 | VPN 流量分类 | 14 类 |
| ISCX-Tor-2016 | 38,000 | Tor 行为检测 | 8 类 |

训练数据采用统一的 JSON Lines 格式，每条记录包含 `instruction` 字段（任务描述 + 协议字段序列）和 `output` 字段（分类标签）。训练脚本 `train_svm.py` 从 instruction 中提取 32 维特征向量，映射多类标签为二分类标签（正常/异常），最终训练出达到 91.4% 正常流量过滤率和 42.9 微秒平均推理延迟的轻量级模型。

Sources: [dataset-feature-engineering.md](docs/references/dataset-feature-engineering.md#L1-L45)
Sources: [train_svm.py](svm-filter-service/models/train_svm.py#L1-L65)

## 检测结果解读

演示样本检测完成后，系统生成结构化的威胁情报 JSON，包含元数据、统计信息、威胁详情等部分。理解这些字段有助于评估检测效果、定位攻击行为、优化检测规则。

### 结果结构示例

```json
{
  "meta": {
    "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": "2026-03-31T10:30:00Z",
    "processing_time_ms": 1250
  },
  "statistics": {
    "total_flows": 150,
    "normal_flows_dropped": 148,
    "anomaly_flows_detected": 2,
    "svm_filter_rate": "98.67%",
    "bandwidth_reduction": "78.5%"
  },
  "threats": [
    {
      "id": "threat-001",
      "five_tuple": {
        "src_ip": "192.168.1.100",
        "dst_ip": "10.0.0.1",
        "src_port": 54321,
        "dst_port": 443,
        "protocol": "TCP"
      },
      "classification": {
        "primary_label": "Malware",
        "secondary_label": "Botnet",
        "confidence": 0.92,
        "model": "Qwen3.5-0.8B"
      },
      "flow_metadata": {
        "packet_count": 10,
        "byte_count": 5120
      },
      "token_info": {
        "token_count": 156,
        "truncated": false
      }
    }
  ]
}
```

### 关键指标说明

| 指标 | 说明 | 优化方向 |
|------|------|----------|
| svm_filter_rate | SVM 初筛过滤比例 | 目标 > 90%，过低会增加 LLM 负载 |
| bandwidth_reduction | 带宽压降比例 | 目标 > 70%，反映 JSON 化压缩效果 |
| confidence | LLM 分类置信度 | 目标 > 0.8，过低需人工审查 |
| token_count | 流量 Token 数量 | 应 < 690，超出会触发截断 |
| truncated | 是否触发 Token 截断 | 频繁截断需调整时间窗口或包数量限制 |

Sources: [main.py](edge-test-console/backend/app/main.py#L276-L330)

## 最佳实践建议

演示样本库的有效使用需要遵循一定的实践原则，既保证检测效果，又避免系统资源浪费。以下建议基于系统设计和性能约束总结而成。

### 样本准备建议

- **优先使用真实攻击样本**：从漏洞靶机、蜜罐系统或公开数据集获取的真实攻击流量比合成数据更有代表性，能够验证系统在实际场景中的检测能力
- **保持样本多样性**：涵盖不同协议（TCP/UDP）、不同攻击阶段（侦察、入侵、横向移动、数据渗出）的样本，全面测试系统覆盖能力
- **控制样本规模**：单个样本建议包含 10-1000 个数据包，时间跨度 < 60 秒，既满足双重截断保护约束，又能提供足够的特征信息

### 检测优化建议

- **观察 SVM 过滤率**：如果 `svm_filter_rate` 持续低于 85%，说明样本特征与训练数据分布差异较大，可能需要重新训练模型或调整特征工程
- **监控 Token 截断**：频繁出现 `truncated: true` 表示流量序列过长，应考虑减小时间窗口或包数量限制，避免信息丢失
- **验证置信度分布**：正常样本的 LLM 置信度应集中在 0.95 以上，异常样本应在 0.8-0.95 区间，过低置信度可能表示模型不确定性

### 故障排查指南

| 问题现象 | 可能原因 | 排查步骤 |
|----------|----------|----------|
| 样本列表为空 | demo_show 目录无文件或权限问题 | 检查目录权限、确认文件格式 |
| 检测任务失败 | 流量包损坏或格式不兼容 | 使用 Wireshark 验证 PCAP 完整性 |
| 结果无威胁 | 样本为纯正常流量 | 确认样本包含攻击行为特征 |
| 推理延迟过高 | LLM 模型未加载或内存不足 | 检查 llm-service 容器日志和资源配额 |

Sources: [main.py](edge-test-console/backend/app/main.py#L115-L135)

## 下一步学习

掌握演示样本库使用后，建议继续学习以下内容以深入理解系统架构和检测原理：

- [四容器拓扑与微服务架构](4-si-rong-qi-tuo-bu-yu-wei-fu-wu-jia-gou)：理解演示样本如何流转于四个容器之间，以及服务间的通信边界约束
- [五阶段检测工作流](5-wu-jie-duan-jian-ce-gong-zuo-liu)：深入了解演示样本触发的完整检测流程，包括流重组、特征提取、SVM 初筛、Token 分词、LLM 推理等环节
- [32 维特征向量设计](12-32-wei-te-zheng-xiang-liang-she-ji)：学习如何从 PCAP 文件提取特征向量，理解 SVM 模型的输入格式和计算逻辑
- [服务间 API 接口规范](14-fu-wu-jian-api-jie-kou-gui-fan)：了解演示样本检测过程中各服务间的 API 调用细节，为定制开发做准备