"""
探微 (Tanwei) - Agent Loop 主程序
EdgeAgent 核心大脑：五阶段工作流执行

API 端点：
- GET /health - 健康检查
- POST /api/detect - 启动检测流程
- GET /api/status/{task_id} - 查询任务状态
- GET /api/result/{task_id} - 获取检测结果
"""

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any

import aiofiles
import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from flow_processor import FlowProcessor, Flow
from traffic_tokenizer import TrafficTokenizer


# ============================================================
# 配置
# ============================================================

SVM_SERVICE_URL = os.environ.get("SVM_SERVICE_URL", "http://svm-filter-service:8001")
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "http://llm-service:8080")
MAX_TIME_WINDOW = int(os.environ.get("MAX_TIME_WINDOW", "60"))
MAX_PACKET_COUNT = int(os.environ.get("MAX_PACKET_COUNT", "10"))
MAX_TOKEN_LENGTH = int(os.environ.get("MAX_TOKEN_LENGTH", "690"))
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/uploads")

# 版本信息
AGENT_VERSION = "1.0.0"


# ============================================================
# 日志配置
# ============================================================

logger.remove()
logger.add(
    sink=lambda msg: print(msg, end=""),
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=os.environ.get("LOG_LEVEL", "INFO")
)


# ============================================================
# 数据模型
# ============================================================

class TaskStage(str, Enum):
    """任务阶段枚举"""
    PENDING = "pending"
    FLOW_RECONSTRUCTION = "flow_reconstruction"
    SVM_FILTERING = "svm_filtering"
    LLM_INFERENCE = "llm_inference"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: TaskStage
    stage: TaskStage
    progress: int
    message: str
    created_at: str
    updated_at: str


@dataclass
class Task:
    """异步任务"""
    task_id: str
    status: TaskStage = TaskStage.PENDING
    stage: TaskStage = TaskStage.PENDING
    progress: int = 0
    message: str = "Task created"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    pcap_path: Optional[str] = None
    pcap_size: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class AnomalyFlow:
    """异常流信息"""
    five_tuple: dict
    label: str
    confidence: float
    timestamp: str
    flow_metadata: dict
    token_info: dict


# ============================================================
# 全局状态
# ============================================================

# 任务存储（生产环境应使用 Redis）
tasks: Dict[str, Task] = {}

# 启动时间
START_TIME = time.time()


# ============================================================
# FastAPI 应用
# ============================================================

app = FastAPI(
    title="Tanwei Agent Loop",
    description="EdgeAgent Core - 五阶段检测工作流",
    version=AGENT_VERSION
)


# ============================================================
# 服务调用客户端
# ============================================================

async def call_svm_service(features: dict) -> dict:
    """
    调用 SVM 过滤服务

    Args:
        features: 流量统计特征

    Returns:
        分类结果
    """
    url = f"{SVM_SERVICE_URL}/api/classify"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json={"features": features})
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.error(f"SVM service timeout: {url}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SVM_SERVICE_UNAVAILABLE",
                "message": "SVM service timeout"
            }
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"SVM service error: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SVM_SERVICE_UNAVAILABLE",
                "message": f"SVM service returned error: {e.response.status_code}"
            }
        )
    except Exception as e:
        logger.error(f"SVM service call failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "SVM_SERVICE_UNAVAILABLE",
                "message": str(e)
            }
        )


async def call_llm_service(prompt: str, max_tokens: int = 64) -> dict:
    """
    调用 LLM 推理服务 (llama.cpp server)

    Args:
        prompt: 提示词
        max_tokens: 最大生成 token 数

    Returns:
        推理结果
    """
    url = f"{LLM_SERVICE_URL}/completion"

    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": 0.1,
        "stop": ["</s>", "\n\n", "Classification:", "<packet>:"]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.error(f"LLM service timeout: {url}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "LLM_SERVICE_UNAVAILABLE",
                "message": "LLM service timeout"
            }
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM service error: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "LLM_SERVICE_UNAVAILABLE",
                "message": f"LLM service returned error: {e.response.status_code}"
            }
        )
    except Exception as e:
        logger.error(f"LLM service call failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "LLM_SERVICE_UNAVAILABLE",
                "message": str(e)
            }
        )


# ============================================================
# 检测工作流
# ============================================================

async def run_detection_pipeline(task_id: str):
    """
    执行五阶段检测工作流

    阶段1：基于五元组的流重组
    阶段2：双重特征截断
    阶段3：SVM 初筛调用
    阶段4：跨模态对齐与分词
    阶段5：LLM 标签化与 JSON 封装
    """
    task = tasks.get(task_id)
    if not task:
        logger.error(f"Task not found: {task_id}")
        return

    try:
        # 初始化处理器
        flow_processor = FlowProcessor(
            max_time_window=MAX_TIME_WINDOW,
            max_packet_count=MAX_PACKET_COUNT
        )
        tokenizer = TrafficTokenizer(max_token_length=MAX_TOKEN_LENGTH)

        # ============================================================
        # 阶段1：基于五元组的流重组
        # ============================================================
        task.status = TaskStage.FLOW_RECONSTRUCTION
        task.stage = TaskStage.FLOW_RECONSTRUCTION
        task.progress = 10
        task.message = "正在提取五元组、重组流"
        task.updated_at = time.time()
        logger.info(f"[Task {task_id}] Stage 1: Flow reconstruction")

        flows, pcap_stats = flow_processor.process_pcap(task.pcap_path)
        total_flows = len(flows)

        if total_flows == 0:
            task.status = TaskStage.COMPLETED
            task.stage = TaskStage.COMPLETED
            task.progress = 100
            task.message = "No valid flows detected"
            task.result = {
                "meta": {
                    "task_id": task_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent_version": AGENT_VERSION,
                    "processing_time_ms": int((time.time() - task.created_at) * 1000)
                },
                "statistics": {
                    "total_packets": pcap_stats.get("total_packets", 0),
                    "total_flows": 0,
                    "normal_flows_dropped": 0,
                    "anomaly_flows_detected": 0,
                    "svm_filter_rate": "0.00%",
                    "bandwidth_reduction": "0.00%"
                },
                "threats": [],
                "metrics": {
                    "original_pcap_size_bytes": task.pcap_size,
                    "json_output_size_bytes": 0,
                    "bandwidth_saved_percent": 0.0
                }
            }
            task.updated_at = time.time()
            return

        # ============================================================
        # 阶段2 & 3：双重截断 + SVM 初筛
        # ============================================================
        task.status = TaskStage.SVM_FILTERING
        task.stage = TaskStage.SVM_FILTERING
        task.progress = 30
        task.message = "SVM 初筛丢弃正常流量"
        task.updated_at = time.time()
        logger.info(f"[Task {task_id}] Stage 2-3: SVM filtering")

        anomaly_flows: List[AnomalyFlow] = []
        normal_count = 0
        svm_results = []

        for i, flow in enumerate(flows):
            # 提取统计特征
            features = flow_processor.extract_statistical_features(flow)

            # 调用 SVM 服务
            svm_result = await call_svm_service(features)
            svm_results.append(svm_result)

            # 判断是否异常
            if svm_result.get("prediction", 0) == 1:  # 1 = 异常
                # 准备异常流数据
                flow_text = flow_processor.flow_to_text(flow)
                anomaly_flows.append({
                    "flow": flow,
                    "flow_text": flow_text,
                    "svm_confidence": svm_result.get("confidence", 0.5)
                })
            else:
                normal_count += 1

            # 更新进度
            progress = 30 + int((i / total_flows) * 30)
            task.progress = min(progress, 60)
            task.updated_at = time.time()

        logger.info(f"[Task {task_id}] SVM filtering complete: {normal_count} normal, {len(anomaly_flows)} anomaly")

        # ============================================================
        # 阶段4 & 5：跨模态对齐 + LLM 推理
        # ============================================================
        task.status = TaskStage.LLM_INFERENCE
        task.stage = TaskStage.LLM_INFERENCE
        task.progress = 65
        task.message = "大模型正在进行 Token 推理"
        task.updated_at = time.time()
        logger.info(f"[Task {task_id}] Stage 4-5: LLM inference")

        threats = []

        for i, anomaly in enumerate(anomaly_flows):
            flow = anomaly["flow"]
            flow_text = anomaly["flow_text"]

            # 跨模态分词
            prompt, token_count, was_truncated = tokenizer.tokenize_flow(
                flow_text=flow_text,
                five_tuple=flow.five_tuple.to_dict()
            )

            # 调用 LLM 服务
            llm_response = await call_llm_service(prompt, max_tokens=32)

            # 解析 LLM 响应
            content = llm_response.get("content", "")
            classification = tokenizer.parse_llm_response(content)

            # 构建威胁信息
            threat = {
                "id": f"threat-{len(threats) + 1:03d}",
                "five_tuple": flow.five_tuple.to_dict(),
                "classification": {
                    "primary_label": classification.get("primary_label", "Unknown"),
                    "secondary_label": classification.get("secondary_label"),
                    "confidence": anomaly["svm_confidence"],
                    "model": "Qwen3.5-0.8B"
                },
                "flow_metadata": {
                    "start_time": datetime.fromtimestamp(flow.start_time, timezone.utc).isoformat() if flow.start_time else None,
                    "end_time": datetime.fromtimestamp(flow.end_time, timezone.utc).isoformat() if flow.end_time else None,
                    "packet_count": flow.packet_count,
                    "byte_count": flow.total_bytes,
                    "avg_packet_size": flow.total_bytes / flow.packet_count if flow.packet_count > 0 else 0.0
                },
                "token_info": {
                    "token_count": token_count,
                    "truncated": was_truncated
                }
            }
            threats.append(threat)

            # 更新进度
            progress = 65 + int((i / len(anomaly_flows)) * 25) if anomaly_flows else 90
            task.progress = min(progress, 90)
            task.updated_at = time.time()

        # ============================================================
        # 生成最终结果
        # ============================================================
        task.status = TaskStage.COMPLETED
        task.stage = TaskStage.COMPLETED
        task.progress = 100
        task.message = "检测完成"
        task.updated_at = time.time()

        # 计算统计信息
        svm_filter_rate = (normal_count / total_flows * 100) if total_flows > 0 else 0.0

        # 构建 JSON 结果
        result = {
            "meta": {
                "task_id": task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_version": AGENT_VERSION,
                "processing_time_ms": int((time.time() - task.created_at) * 1000)
            },
            "statistics": {
                "total_packets": pcap_stats.get("total_packets", 0),
                "total_flows": total_flows,
                "normal_flows_dropped": normal_count,
                "anomaly_flows_detected": len(threats),
                "svm_filter_rate": f"{svm_filter_rate:.2f}%",
                "bandwidth_reduction": "0.0%"
            },
            "threats": threats,
            "metrics": {
                "original_pcap_size_bytes": task.pcap_size,
                "json_output_size_bytes": 0,
                "bandwidth_saved_percent": 0.0
            }
        }

        # 构建完 JSON 结果后，重新序列化并依据真实物理字节差计算压降率
        json_output_bytes = len(json.dumps(result).encode('utf-8'))
        original_size_bytes = task.pcap_size
        
        if original_size_bytes > 0:
            # 公式: (原始字节 - 生成日志字节) / 原始字节 * 100%
            bandwidth_reduction = ((original_size_bytes - json_output_bytes) / original_size_bytes) * 100
        else:
            bandwidth_reduction = 0.0

        # 正确更新 KPI 看板所需的真实物理指标
        result["metrics"]["json_output_size_bytes"] = json_output_bytes
        result["metrics"]["bandwidth_saved_percent"] = max(0.0, round(bandwidth_reduction, 2))
        result["statistics"]["bandwidth_reduction"] = f"{max(0.0, round(bandwidth_reduction, 2))}%"

        task.result = result

        logger.info(f"[Task {task_id}] Detection complete: {len(threats)} threats found")

    except HTTPException:
        # 已经处理的 HTTP 异常
        task.status = TaskStage.FAILED
        task.stage = TaskStage.FAILED
        task.progress = 0
        task.error = "Service unavailable"
        task.updated_at = time.time()
        raise

    except Exception as e:
        logger.exception(f"[Task {task_id}] Detection failed: {e}")
        task.status = TaskStage.FAILED
        task.stage = TaskStage.FAILED
        task.progress = 0
        task.error = str(e)
        task.updated_at = time.time()


# ============================================================
# API 端点
# ============================================================

@app.get("/health")
async def health_check():
    """
    健康检查端点
    """
    uptime = int(time.time() - START_TIME)

    return {
        "status": "healthy",
        "service": "agent-loop",
        "version": AGENT_VERSION,
        "uptime_seconds": uptime
    }


@app.post("/api/detect")
async def start_detection(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    上传 Pcap 文件并启动检测流程
    """
    # 验证文件类型
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_PCAP_FILE",
                "message": "No filename provided"
            }
        )

    filename = file.filename.lower()
    if not (filename.endswith(".pcap") or filename.endswith(".pcapng")):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_PCAP_FILE",
                "message": "File must be .pcap or .pcapng format",
                "details": {"filename": file.filename}
            }
        )

    # 生成任务 ID
    task_id = str(uuid.uuid4())

    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 保存文件
    pcap_path = os.path.join(UPLOAD_DIR, f"{task_id}.pcap")
    pcap_size = 0

    try:
        async with aiofiles.open(pcap_path, "wb") as f:
            content = await file.read()
            await f.write(content)
            pcap_size = len(content)
    except Exception as e:
        logger.error(f"Failed to save pcap file: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to save uploaded file: {e}"
            }
        )

    # 创建任务
    task = Task(
        task_id=task_id,
        status=TaskStage.PENDING,
        stage=TaskStage.PENDING,
        progress=0,
        message="Detection task started",
        created_at=time.time(),
        updated_at=time.time(),
        pcap_path=pcap_path,
        pcap_size=pcap_size
    )
    tasks[task_id] = task

    # 在后台启动检测流程
    background_tasks.add_task(run_detection_pipeline, task_id)

    logger.info(f"Task created: {task_id}, file: {file.filename}, size: {pcap_size} bytes")

    return {
        "status": "success",
        "task_id": task_id,
        "message": "Detection task started"
    }


@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """
    查询检测任务状态
    """
    task = tasks.get(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "TASK_NOT_FOUND",
                "message": f"Task {task_id} not found"
            }
        )

    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "stage": task.stage.value,
        "progress": task.progress,
        "message": task.message
    }


@app.get("/api/result/{task_id}")
async def get_task_result(task_id: str):
    """
    获取检测结果
    """
    task = tasks.get(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "TASK_NOT_FOUND",
                "message": f"Task {task_id} not found"
            }
        )

    if task.status == TaskStage.PENDING:
        return {
            "task_id": task.task_id,
            "status": "pending",
            "message": "Task is waiting to be processed"
        }

    if task.status == TaskStage.FAILED:
        return {
            "task_id": task.task_id,
            "status": "failed",
            "error": task.error
        }

    if task.status != TaskStage.COMPLETED:
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "progress": task.progress,
            "message": task.message
        }

    # 返回完整结果
    return task.result


@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务（可选功能）
    """
    task = tasks.get(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "TASK_NOT_FOUND",
                "message": f"Task {task_id} not found"
            }
        )

    # 删除上传的文件
    if task.pcap_path and os.path.exists(task.pcap_path):
        try:
            os.remove(task.pcap_path)
        except Exception as e:
            logger.warning(f"Failed to delete pcap file: {e}")

    # 从内存中移除任务
    del tasks[task_id]

    return {
        "status": "success",
        "message": f"Task {task_id} deleted"
    }


# ============================================================
# 异常处理
# ============================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            **exc.detail
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理器"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": "An internal error occurred"
        }
    )


# ============================================================
# 启动事件
# ============================================================

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"Agent Loop starting...")
    logger.info(f"Version: {AGENT_VERSION}")
    logger.info(f"SVM Service: {SVM_SERVICE_URL}")
    logger.info(f"LLM Service: {LLM_SERVICE_URL}")
    logger.info(f"Max Time Window: {MAX_TIME_WINDOW}s")
    logger.info(f"Max Packet Count: {MAX_PACKET_COUNT}")
    logger.info(f"Max Token Length: {MAX_TOKEN_LENGTH}")
    logger.info(f"Upload Directory: {UPLOAD_DIR}")

    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    logger.info("Agent Loop started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Agent Loop shutting down...")

    # 清理上传的文件
    try:
        for task in tasks.values():
            if task.pcap_path and os.path.exists(task.pcap_path):
                os.remove(task.pcap_path)
    except Exception as e:
        logger.warning(f"Error cleaning up: {e}")

    logger.info("Agent Loop shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
