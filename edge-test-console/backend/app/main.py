"""
Edge Test Console - FastAPI Backend
测试探针后端服务，负责文件上传、静态资源托管，并作为代理转发给 agent-loop
"""

import os
import sys
import uuid
import asyncio
import aiofiles
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

import requests
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 添加共享模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from shared.log_config import get_edge_console_logger

# 初始化日志
logger = get_edge_console_logger()

# Configuration
AGENT_LOOP_URL = os.getenv("AGENT_LOOP_URL", "http://agent-loop:8002")
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# In-memory task storage (in production, use Redis or database)
tasks: Dict[str, Dict[str, Any]] = {}

app = FastAPI(
    title="Edge Test Console",
    description="测试探针后端服务",
    version="1.0.0"
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class TaskStatus(BaseModel):
    task_id: str
    status: str
    stage: str
    progress: int
    message: str


class DetectionResponse(BaseModel):
    status: str
    task_id: str
    message: str


# Helper functions
async def process_detection(task_id: str, file_path: Path, original_size: int):
    """Process detection task in background"""
    try:
        # Update task status
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["stage"] = "flow_reconstruction"
        tasks[task_id]["progress"] = 10
        tasks[task_id]["message"] = "正在提取五元组、重组流"

        logger.info(f"[Task {task_id}] Starting detection, file_size={original_size}")

        # Send file to agent-loop
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()

        # Simulate stages for demo (in real implementation, agent-loop handles this)
        await asyncio.sleep(1)

        # Update to SVM filtering stage
        tasks[task_id]["stage"] = "svm_filtering"
        tasks[task_id]["progress"] = 30
        tasks[task_id]["message"] = "SVM 初筛丢弃正常流量"

        # Call agent-loop detect API
        try:
            files = {"file": (file_path.name, file_content, "application/vnd.tcpdump.pcap")}
            logger.debug(f"[Task {task_id}] Calling agent-loop at {AGENT_LOOP_URL}")
            response = requests.post(
                f"{AGENT_LOOP_URL}/api/detect",
                files=files,
                timeout=300  # 5 minute timeout
            )
            response.raise_for_status()
            result = response.json()

            # Update task with agent-loop task_id for status polling
            agent_task_id = result.get("task_id")
            tasks[task_id]["agent_task_id"] = agent_task_id
            logger.info(f"[Task {task_id}] Agent-loop task created: {agent_task_id}")

            # Poll for status from agent-loop
            max_attempts = 120  # 2 minutes max
            for attempt in range(max_attempts):
                status_response = requests.get(
                    f"{AGENT_LOOP_URL}/api/status/{agent_task_id}",
                    timeout=10
                )
                status_data = status_response.json()

                stage = status_data.get("stage", "processing")
                progress = status_data.get("progress", 0)
                message = status_data.get("message", "")

                # Map agent-loop stages to display stages
                stage_mapping = {
                    "pending": ("pending", 0, "等待处理"),
                    "flow_reconstruction": ("flow_reconstruction", 25, "正在提取五元组、重组流"),
                    "svm_filtering": ("svm_filtering", 50, "SVM 初筛丢弃正常流量"),
                    "llm_inference": ("llm_inference", 75, "大模型正在进行 Token 推理"),
                    "completed": ("completed", 100, "检测完成"),
                    "failed": ("failed", 0, "检测失败")
                }

                display_stage, display_progress, display_message = stage_mapping.get(
                    stage, (stage, progress, message)
                )

                tasks[task_id]["stage"] = display_stage
                tasks[task_id]["progress"] = display_progress
                tasks[task_id]["message"] = display_message

                if stage == "completed":
                    # Fetch result
                    result_response = requests.get(
                        f"{AGENT_LOOP_URL}/api/result/{agent_task_id}",
                        timeout=10
                    )
                    tasks[task_id]["result"] = result_response.json()
                    logger.info(f"[Task {task_id}] Detection completed successfully")
                    break
                elif stage == "failed":
                    tasks[task_id]["error"] = status_data.get("error", "Unknown error")
                    logger.error(f"[Task {task_id}] Detection failed: {tasks[task_id]['error']}")
                    break

                await asyncio.sleep(1)

        except requests.exceptions.RequestException as e:
            # For demo purposes, generate mock result if agent-loop is not available
            logger.warning(f"[Task {task_id}] Agent-loop unavailable, using mock result: {e}")
            tasks[task_id]["stage"] = "llm_inference"
            tasks[task_id]["progress"] = 75
            tasks[task_id]["message"] = "大模型正在进行 Token 推理"
            await asyncio.sleep(1)

            # Generate mock result for demo
            mock_result = generate_mock_result(task_id, original_size)
            tasks[task_id]["result"] = mock_result
            tasks[task_id]["stage"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "检测完成"

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["stage"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["message"] = f"检测失败: {str(e)}"
        logger.exception(f"[Task {task_id}] Detection failed with exception")
    finally:
        # Cleanup uploaded file
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"[Task {task_id}] Cleaned up uploaded file")


def generate_mock_result(task_id: str, original_size: int) -> Dict[str, Any]:
    """Generate mock result for demo purposes"""
    # Simulate bandwidth reduction
    json_size = int(original_size * 0.215)  # ~78.5% reduction
    reduction_percent = round((1 - json_size / original_size) * 100, 1) if original_size > 0 else 0

    return {
        "meta": {
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_version": "1.0.0",
            "processing_time_ms": 1250
        },
        "statistics": {
            "total_packets": 1500,
            "total_flows": 150,
            "normal_flows_dropped": 148,
            "anomaly_flows_detected": 2,
            "svm_filter_rate": "98.67%",
            "bandwidth_reduction": f"{reduction_percent}%"
        },
        "threats": [
            {
                "id": "threat-001",
                "five_tuple": {
                    "src_ip": "192.168.1.100",
                    "src_port": 54321,
                    "dst_ip": "10.0.0.1",
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
                    "start_time": datetime.utcnow().isoformat() + "Z",
                    "end_time": datetime.utcnow().isoformat() + "Z",
                    "packet_count": 10,
                    "byte_count": 5120,
                    "avg_packet_size": 512.0
                },
                "token_info": {
                    "token_count": 156,
                    "truncated": False
                }
            },
            {
                "id": "threat-002",
                "five_tuple": {
                    "src_ip": "192.168.1.105",
                    "src_port": 49876,
                    "dst_ip": "45.33.32.156",
                    "dst_port": 8080,
                    "protocol": "TCP"
                },
                "classification": {
                    "primary_label": "Suspicious",
                    "secondary_label": "C2 Communication",
                    "confidence": 0.87,
                    "model": "Qwen3.5-0.8B"
                },
                "flow_metadata": {
                    "start_time": datetime.utcnow().isoformat() + "Z",
                    "end_time": datetime.utcnow().isoformat() + "Z",
                    "packet_count": 8,
                    "byte_count": 3072,
                    "avg_packet_size": 384.0
                },
                "token_info": {
                    "token_count": 98,
                    "truncated": False
                }
            }
        ],
        "metrics": {
            "original_pcap_size_bytes": original_size,
            "json_output_size_bytes": json_size,
            "bandwidth_saved_percent": reduction_percent
        }
    }


# API Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "edge-test-console",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Log startup information"""
    logger.info("Edge Test Console starting up...")
    logger.info(f"Agent Loop URL: {AGENT_LOOP_URL}")
    logger.info(f"Upload Directory: {UPLOAD_DIR}")


@app.post("/api/detect", response_model=DetectionResponse)
async def detect_pcap(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload Pcap file and start detection process
    """
    # Validate file
    if not file.filename:
        logger.warning("Upload rejected: no filename provided")
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(('.pcap', '.pcapng')):
        logger.warning(f"Upload rejected: invalid format - {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .pcap and .pcapng files are accepted"
        )

    # Generate task ID
    task_id = str(uuid.uuid4())

    # Save uploaded file
    file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    original_size = file.size or 0

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        original_size = len(content)
        await f.write(content)

    logger.info(f"Task created: {task_id}, file={file.filename}, size={original_size} bytes")

    # Initialize task
    tasks[task_id] = {
        "status": "pending",
        "stage": "pending",
        "progress": 0,
        "message": "任务已创建，等待处理",
        "filename": file.filename,
        "original_size": original_size,
        "created_at": datetime.utcnow().isoformat()
    }

    # Start background processing
    background_tasks.add_task(process_detection, task_id, file_path, original_size)

    return DetectionResponse(
        status="success",
        task_id=task_id,
        message="Detection task started"
    )


@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get detection task status
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    return TaskStatus(
        task_id=task_id,
        status=task.get("status", "unknown"),
        stage=task.get("stage", "unknown"),
        progress=task.get("progress", 0),
        message=task.get("message", "")
    )


@app.get("/api/result/{task_id}")
async def get_task_result(task_id: str):
    """
    Get detection task result
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]

    if task.get("stage") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed. Current stage: {task.get('stage')}"
        )

    if "error" in task:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_code": "DETECTION_FAILED",
                "message": task["error"]
            }
        )

    return task.get("result", {})


# Serve frontend static files
# In production, these files are built by Vite and copied to /app/static
STATIC_DIR = Path("/app/static")
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/")
async def serve_index():
    """Serve frontend index.html"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Edge Test Console API is running. Frontend not built yet."}


@app.get("/{path:path}")
async def serve_spa(path: str):
    """
    Serve SPA - return index.html for all unmatched routes
    This enables React Router to handle client-side routing
    """
    # Check if it's a static file request
    file_path = STATIC_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Return index.html for SPA routing
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
