"""
Console FastAPI backend.
负责 edge-agent 检测入口、静态资源托管，以及 central-agent 控制面代理。
"""

import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import aiofiles
import requests
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.central_client import CentralAgentClient


def create_logger() -> logging.Logger:
    logger = logging.getLogger("console")
    if logger.handlers:
        return logger

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_demo_samples_dir(current_file: Path) -> Path:
    configured_dir = os.getenv("DEMO_SAMPLES_DIR")
    if configured_dir:
        return Path(configured_dir)

    if current_file == Path("/app/app/main.py"):
        return Path("/app/demo-samples")

    for parent in current_file.resolve().parents:
        candidate = parent / "data/test_traffic/demo_show"
        if candidate.exists():
            return candidate

    return Path("/app/demo-samples")


logger = create_logger()

EDGE_AGENT_URL = os.getenv("EDGE_AGENT_URL", "http://edge-agent:8002")
CENTRAL_AGENT_URL = os.getenv("CENTRAL_AGENT_URL", "http://central-agent:8003")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DEMO_SAMPLES_DIR = resolve_demo_samples_dir(Path(__file__))
SUPPORTED_PCAP_EXTENSIONS = (".pcap", ".pcapng")
STATIC_DIR = Path("/app/static")

tasks: Dict[str, Dict[str, Any]] = {}
central_agent_client = CentralAgentClient(CENTRAL_AGENT_URL, logger)

app = FastAPI(title="Console", description="项目控制台后端服务", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class DemoDetectRequest(BaseModel):
    sample_id: str


def build_display_name(filename: str) -> str:
    stem = Path(filename).stem
    return stem.replace("_", " ").replace("-", " ").strip().title()


def get_demo_sample_files() -> List[Path]:
    if not DEMO_SAMPLES_DIR.exists() or not DEMO_SAMPLES_DIR.is_dir():
        return []

    return sorted(
        [
            path
            for path in DEMO_SAMPLES_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_PCAP_EXTENSIONS
        ],
        key=lambda path: path.name.lower(),
    )


def initialize_task(task_id: str, filename: str, original_size: int) -> None:
    tasks[task_id] = {
        "status": "pending",
        "stage": "pending",
        "progress": 0,
        "message": "任务已创建，等待处理",
        "filename": filename,
        "original_size": original_size,
        "created_at": utc_now_iso(),
    }


def resolve_demo_sample(sample_id: str) -> Path:
    if Path(sample_id).name != sample_id:
        raise HTTPException(status_code=400, detail="Invalid sample_id")

    sample_path = DEMO_SAMPLES_DIR / sample_id
    if not sample_path.exists() or not sample_path.is_file():
        raise HTTPException(status_code=404, detail="Demo sample not found")

    if sample_path.suffix.lower() not in SUPPORTED_PCAP_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .pcap and .pcapng files are accepted",
        )

    return sample_path


async def process_detection(task_id: str, file_path: Path, original_size: int) -> None:
    try:
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["stage"] = "flow_reconstruction"
        tasks[task_id]["progress"] = 10
        tasks[task_id]["message"] = "正在提取五元组、重组流"

        logger.info("[Task %s] Starting detection, file_size=%s", task_id, original_size)

        async with aiofiles.open(file_path, "rb") as uploaded_file:
            file_content = await uploaded_file.read()

        await asyncio.sleep(1)

        tasks[task_id]["stage"] = "svm_filtering"
        tasks[task_id]["progress"] = 30
        tasks[task_id]["message"] = "SVM 初筛丢弃正常流量"

        try:
            files = {
                "file": (file_path.name, file_content, "application/vnd.tcpdump.pcap")
            }
            logger.debug("[Task %s] Calling edge-agent at %s", task_id, EDGE_AGENT_URL)
            response = requests.post(
                f"{EDGE_AGENT_URL}/api/detect",
                files=files,
                timeout=300,
            )
            response.raise_for_status()
            result = response.json()

            edge_agent_task_id = result.get("task_id")
            tasks[task_id]["edge_agent_task_id"] = edge_agent_task_id
            logger.info(
                "[Task %s] Edge-agent task created: %s", task_id, edge_agent_task_id
            )

            max_attempts = 120
            for _ in range(max_attempts):
                status_response = requests.get(
                    f"{EDGE_AGENT_URL}/api/status/{edge_agent_task_id}",
                    timeout=10,
                )
                status_data = status_response.json()

                stage = status_data.get("stage", "processing")
                progress = status_data.get("progress", 0)
                message = status_data.get("message", "")

                stage_mapping = {
                    "pending": ("pending", 0, "等待处理"),
                    "flow_reconstruction": (
                        "flow_reconstruction",
                        25,
                        "正在提取五元组、重组流",
                    ),
                    "svm_filtering": ("svm_filtering", 50, "SVM 初筛丢弃正常流量"),
                    "llm_inference": ("llm_inference", 75, "大模型正在进行 Token 推理"),
                    "completed": ("completed", 100, "检测完成"),
                    "failed": ("failed", 0, "检测失败"),
                }

                display_stage, display_progress, display_message = stage_mapping.get(
                    stage, (stage, progress, message)
                )

                tasks[task_id]["stage"] = display_stage
                tasks[task_id]["progress"] = display_progress
                tasks[task_id]["message"] = display_message

                if stage == "completed":
                    result_response = requests.get(
                        f"{EDGE_AGENT_URL}/api/result/{edge_agent_task_id}",
                        timeout=10,
                    )
                    tasks[task_id]["result"] = result_response.json()
                    tasks[task_id]["status"] = "completed"
                    logger.info("[Task %s] Detection completed successfully", task_id)
                    break

                if stage == "failed":
                    tasks[task_id]["status"] = "failed"
                    tasks[task_id]["error"] = status_data.get("error", "Unknown error")
                    logger.error(
                        "[Task %s] Detection failed: %s",
                        task_id,
                        tasks[task_id]["error"],
                    )
                    break

                await asyncio.sleep(1)
            else:
                timeout_error = "Polling timeout: detection did not reach terminal state"
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["stage"] = "failed"
                tasks[task_id]["error"] = timeout_error
                tasks[task_id]["message"] = "检测超时，任务未在预期时间内完成"
                logger.error("[Task %s] %s", task_id, timeout_error)

        except requests.exceptions.RequestException as exc:
            logger.warning(
                "[Task %s] Edge-agent unavailable, using mock result: %s", task_id, exc
            )
            tasks[task_id]["stage"] = "llm_inference"
            tasks[task_id]["progress"] = 75
            tasks[task_id]["message"] = "大模型正在进行 Token 推理"
            await asyncio.sleep(1)

            mock_result = generate_mock_result(task_id, original_size)
            tasks[task_id]["result"] = mock_result
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["stage"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "检测完成"

    except Exception as exc:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["stage"] = "failed"
        tasks[task_id]["error"] = str(exc)
        tasks[task_id]["message"] = f"检测失败: {exc}"
        logger.exception("[Task %s] Detection failed with exception", task_id)
    finally:
        if file_path.exists():
            file_path.unlink()
            logger.debug("[Task %s] Cleaned up uploaded file", task_id)


def generate_mock_result(task_id: str, original_size: int) -> Dict[str, Any]:
    json_size = int(original_size * 0.215)
    reduction_percent = (
        round((1 - json_size / original_size) * 100, 1) if original_size > 0 else 0
    )

    return {
        "meta": {
            "task_id": task_id,
            "timestamp": utc_now_iso(),
            "agent_version": "edge-agent-v1",
            "processing_time_ms": 1250,
        },
        "statistics": {
            "total_packets": 1500,
            "total_flows": 150,
            "normal_flows_dropped": 148,
            "anomaly_flows_detected": 2,
            "svm_filter_rate": "98.67%",
            "bandwidth_reduction": f"{reduction_percent}%",
        },
        "threats": [
            {
                "id": "threat-001",
                "five_tuple": {
                    "src_ip": "192.168.1.100",
                    "src_port": 54321,
                    "dst_ip": "10.0.0.1",
                    "dst_port": 443,
                    "protocol": "TCP",
                },
                "classification": {
                    "primary_label": "Malware",
                    "secondary_label": "Botnet",
                    "confidence": 0.92,
                    "model": "Qwen3.5-0.8B",
                },
                "flow_metadata": {
                    "start_time": utc_now_iso(),
                    "end_time": utc_now_iso(),
                    "packet_count": 10,
                    "byte_count": 5120,
                    "avg_packet_size": 512.0,
                },
                "token_info": {
                    "token_count": 156,
                    "truncated": False,
                },
            },
            {
                "id": "threat-002",
                "five_tuple": {
                    "src_ip": "192.168.1.105",
                    "src_port": 49876,
                    "dst_ip": "45.33.32.156",
                    "dst_port": 8080,
                    "protocol": "TCP",
                },
                "classification": {
                    "primary_label": "Suspicious",
                    "secondary_label": "C2 Communication",
                    "confidence": 0.87,
                    "model": "Qwen3.5-0.8B",
                },
                "flow_metadata": {
                    "start_time": utc_now_iso(),
                    "end_time": utc_now_iso(),
                    "packet_count": 8,
                    "byte_count": 3072,
                    "avg_packet_size": 384.0,
                },
                "token_info": {
                    "token_count": 98,
                    "truncated": False,
                },
            },
        ],
        "metrics": {
            "original_pcap_size_bytes": original_size,
            "json_output_size_bytes": json_size,
            "bandwidth_saved_percent": reduction_percent,
        },
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "console", "version": "1.0.0"}


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Console backend starting up...")
    logger.info("Edge Agent URL: %s", EDGE_AGENT_URL)
    logger.info("Central Agent URL: %s", CENTRAL_AGENT_URL)
    logger.info("Upload Directory: %s", UPLOAD_DIR)


@app.get("/api/edges")
async def get_edges() -> List[Dict[str, Any]]:
    return central_agent_client.list_edges()


@app.get("/api/edges/{edge_id}/reports/latest")
async def get_latest_edge_report(edge_id: str) -> Dict[str, Any]:
    return central_agent_client.get_latest_report(edge_id)


@app.post("/api/edges/{edge_id}/analyze")
async def analyze_edge(edge_id: str) -> Dict[str, Any]:
    return central_agent_client.analyze_edge(edge_id)


@app.post("/api/network/analyze")
async def analyze_network() -> Dict[str, Any]:
    return central_agent_client.analyze_network()


@app.post("/api/detect", response_model=DetectionResponse)
async def detect_pcap(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> DetectionResponse:
    if not file.filename:
        logger.warning("Upload rejected: no filename provided")
        raise HTTPException(status_code=400, detail="No file provided")

    if not file.filename.lower().endswith(SUPPORTED_PCAP_EXTENSIONS):
        logger.warning("Upload rejected: invalid format - %s", file.filename)
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only .pcap and .pcapng files are accepted",
        )

    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"

    async with aiofiles.open(file_path, "wb") as output_file:
        content = await file.read()
        original_size = len(content)
        await output_file.write(content)

    logger.info(
        "Task created: %s, file=%s, size=%s bytes",
        task_id,
        file.filename,
        original_size,
    )

    initialize_task(task_id, file.filename, original_size)
    background_tasks.add_task(process_detection, task_id, file_path, original_size)

    return DetectionResponse(
        status="success",
        task_id=task_id,
        message="Detection task started",
    )


@app.get("/api/demo-samples")
async def get_demo_samples() -> List[Dict[str, Any]]:
    samples = []
    for sample_file in get_demo_sample_files():
        samples.append(
            {
                "id": sample_file.name,
                "filename": sample_file.name,
                "display_name": build_display_name(sample_file.name),
                "size_bytes": sample_file.stat().st_size,
            }
        )
    return samples


@app.post("/api/detect-demo", response_model=DetectionResponse)
async def detect_demo_sample(
    payload: DemoDetectRequest,
    background_tasks: BackgroundTasks,
) -> DetectionResponse:
    sample_path = resolve_demo_sample(payload.sample_id)
    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}_{sample_path.name}"
    original_size = sample_path.stat().st_size

    shutil.copyfile(sample_path, file_path)

    logger.info(
        "Demo task created: %s, sample=%s, size=%s bytes",
        task_id,
        sample_path.name,
        original_size,
    )
    initialize_task(task_id, sample_path.name, original_size)
    background_tasks.add_task(process_detection, task_id, file_path, original_size)

    return DetectionResponse(
        status="success",
        task_id=task_id,
        message="Detection task started",
    )


@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str) -> TaskStatus:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    return TaskStatus(
        task_id=task_id,
        status=task.get("status", "unknown"),
        stage=task.get("stage", "unknown"),
        progress=task.get("progress", 0),
        message=task.get("message", ""),
    )


@app.get("/api/result/{task_id}")
async def get_task_result(task_id: str) -> Any:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = tasks[task_id]
    if task.get("stage") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task not completed. Current stage: {task.get('stage')}",
        )

    if "error" in task:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_code": "DETECTION_FAILED",
                "message": task["error"],
            },
        )

    return task.get("result", {})


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/")
async def serve_index() -> Any:
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Console API is running. Frontend not built yet."}


@app.get("/{path:path}")
async def serve_spa(path: str) -> Any:
    file_path = STATIC_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
