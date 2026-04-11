# LLM Service - Qwen3.5-0.8B 推理引擎

## 服务概述

本容器使用 llama.cpp server 模式运行 Qwen3.5-0.8B INT4 量化模型，为 EdgeAgent 提供 LLM 推理能力。

## 技术规格

| 属性 | 值 |
|------|-----|
| 基础镜像 | ubuntu:22.04（多阶段构建） |
| llama.cpp 版本 | b4000（可通过环境变量覆盖） |
| 模型 | Qwen3.5-0.8B-Q4_K_M.gguf |
| 模型大小 | ~508MB |
| 量化方式 | INT4 (Q4_K_M) |
| 上下文长度 | 2048 tokens |
| 服务端口 | 8080 |
| 运行用户 | llm（非 root） |

## 构建配置

### 构建参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `UBUNTU_VERSION` | 22.04 | Ubuntu 基础镜像版本 |
| `LLAMA_CPP_VERSION` | b4000 | llama.cpp Git 分支/标签 |

可通过 `docker-compose build --build-arg LLAMA_CPP_VERSION=<version>` 覆盖。

### Dockerfile 特性

- **多阶段构建**：分离编译与运行时，最小化镜像体积
- **层缓存优化**：依赖安装单独分层，版本参数化支持缓存
- **非 root 用户**：使用 `llm` 用户（UID 1000）运行，提升安全性
- **健康检查内置**：Dockerfile 中定义 HEALTHCHECK，使用 healthcheck.sh 脚本

## 启动参数说明

```bash
llama-server \
  --model /models/Qwen3.5-0.8B-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  --ctx-size 2048 \        # 上下文窗口大小
  --n-gpu-layers 0 \       # CPU 推理（边缘设备无 GPU）
  --threads 2 \            # 推理线程数
  --batch-size 512 \       # 批处理大小（影响吞吐）
  --n-keep 0 \             # KV cache 保留 token 数
  --memory-f32 0           # 使用半精度节省内存
```

## API 调用示例

### 文本补全

```bash
curl http://localhost:8080/completion \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Given the following traffic data, classify the threat:",
    "n_predict": 64,
    "temperature": 0.1,
    "stop": ["</s>", "\n"]
  }'
```

### 健康检查

```bash
curl http://localhost:8080/health
```

### 获取模型信息

```bash
curl http://localhost:8080/props
```

## 资源约束

| 资源 | 限制 | 预留 |
|------|------|------|
| 内存 | 1536M | 768M |
| CPU | 2 核 | 1 核 |
| 推理速度 | ~15-30 tokens/s (CPU) | - |

内存限制考虑了模型加载（~500-600MB）和推理运行时的额外开销。

## 健康检查

容器使用 `healthcheck.sh` 脚本进行健康检查：

1. 优先检查 `/health` 端点
2. 备用检查 `/props` 端点（验证模型已加载）
3. 检查间隔：30s，超时：10s
4. 启动等待：60s（模型加载时间）
5. 重试次数：3 次

## 安全特性

- 非 root 用户运行（UID 1000）
- 模型文件只读挂载（`:ro`）
- 最小化运行时依赖（仅 curl 和 ca-certificates）
- 无 Python 运行时，纯 C/C++ 实现

## 注意事项

1. 首次启动需加载模型，约需 5-10 秒
2. 内存限制根据实际运行情况可调整
3. 模型文件通过 docker-compose.yml 挂载，路径：`./qwen3.5-0.8b:/models:ro`
4. 构建时如 cmake 选项有弃用警告，需检查 llama.cpp 版本是否更新命名约定

## 版本兼容性

llama.cpp 版本 b4000 使用 cmake 选项 `-DLLAMA_BUILD_SERVER=ON`。后续版本可能改用 `-DGGML_BUILD_SERVER=ON`，构建时注意检查输出警告。