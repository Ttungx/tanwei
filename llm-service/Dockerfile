# llama.cpp Server Dockerfile
# 用于构建 Qwen3.5-0.8B 本地推理引擎
# 多阶段构建：builder 阶段编译，runtime 阶段运行

# ============================================================
# 构建参数
# ============================================================
ARG UBUNTU_VERSION=22.04
ARG LLAMA_CPP_VERSION=b4000

# ============================================================
# Stage 1: Builder - 编译 llama.cpp server
# ============================================================
FROM ubuntu:${UBUNTU_VERSION} AS builder

# 安装编译依赖（单独一层便于缓存）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# 克隆 llama.cpp（使用构建参数指定版本，便于缓存）
ARG LLAMA_CPP_VERSION
WORKDIR /build
RUN git clone --depth 1 --branch ${LLAMA_CPP_VERSION} \
    https://github.com/ggerganov/llama.cpp.git . \
    && mkdir build

# 编译 llama-server（明确指定输出目录）
WORKDIR /build/build
RUN cmake .. \
    -DLLAMA_BUILD_SERVER=ON \
    -DCMAKE_RUNTIME_OUTPUT_DIRECTORY=/build/bin \
    -DCMAKE_BUILD_TYPE=Release \
    && cmake --build . -j$(nproc) \
    && ls -la /build/bin/ \
    && test -f /build/bin/llama-server

# ============================================================
# Stage 2: Runtime - 最小化运行时镜像
# ============================================================
FROM ubuntu:${UBUNTU_VERSION}

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    # 创建非 root 用户
    && groupadd --gid 1000 llm \
    && useradd --uid 1000 --gid llm --shell /bin/bash --create-home llm

# 从构建阶段复制可执行文件
COPY --from=builder /build/bin/llama-server /usr/local/bin/llama-server

# 验证可执行文件
RUN test -f /usr/local/bin/llama-server && \
    chmod +x /usr/local/bin/llama-server

# 创建模型目录并设置权限
RUN mkdir -p /models && chown -R llm:llm /models

# 复制健康检查脚本
COPY healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh && chown llm:llm /healthcheck.sh

# 切换到非 root 用户
USER llm

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/healthcheck.sh"]

# 默认启动命令
ENTRYPOINT ["/usr/local/bin/llama-server"]
CMD ["--help"]
