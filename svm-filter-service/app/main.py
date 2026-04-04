"""
SVM Filter Service - Main Application
First-stage traffic filter with microsecond-level latency

API Spec: /root/anxun/docs/references/api_specs.md
"""

import os
import sys
import time
import numpy as np
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sklearn.preprocessing import StandardScaler
import joblib

# 添加共享模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.log_config import get_svm_filter_logger

# 初始化日志
logger = get_svm_filter_logger()

# Application metadata
app = FastAPI(
    title="SVM Filter Service",
    description="First-stage traffic filter - filters 99% normal traffic with microsecond latency",
    version="1.0.0"
)

# Model paths
MODEL_DIR = Path("/app/models/saved")
MODEL_PATH = MODEL_DIR / "svm_model.pkl"
SCALER_PATH = MODEL_DIR / "scaler.pkl"

# Global model instances
svm_model = None
scaler = None
start_time = time.time()

# Feature names for 32-dimension feature vector (per dataset-feature-engineering.md)
# A. 基础统计特征 (0-7)
# B. 协议类型特征 (8-11)
# C. TCP 行为特征 (12-19)
# D. 时间特征 (20-23)
# E. 端口特征 (24-27)
# F. 地址特征 (28-31)
FEATURE_NAMES = [
    "avg_packet_len", "std_packet_len", "avg_ip_len", "std_ip_len",
    "avg_tcp_len", "std_tcp_len", "total_bytes", "avg_ttl",
    "ip_proto", "tcp_ratio", "udp_ratio", "other_proto_ratio",
    "avg_window_size", "std_window_size", "syn_count", "ack_count",
    "push_count", "fin_count", "rst_count", "avg_hdr_len",
    "total_duration", "avg_inter_arrival", "std_inter_arrival", "packet_rate",
    "src_port_entropy", "dst_port_entropy", "well_known_port_ratio", "high_port_ratio",
    "unique_dst_ip_count", "internal_ip_ratio", "df_flag_ratio", "avg_ip_id"
]


class TrafficFeatures(BaseModel):
    """Traffic feature vector - 32 dimensions per dataset-feature-engineering.md"""
    # A. 基础统计特征 (0-7)
    avg_packet_len: float = Field(..., ge=0, description="Average frame length")
    std_packet_len: float = Field(..., ge=0, description="Standard deviation of frame lengths")
    avg_ip_len: float = Field(..., ge=0, description="Average IP packet length")
    std_ip_len: float = Field(..., ge=0, description="Standard deviation of IP lengths")
    avg_tcp_len: float = Field(..., ge=0, description="Average TCP payload length")
    std_tcp_len: float = Field(..., ge=0, description="Standard deviation of TCP lengths")
    total_bytes: float = Field(..., ge=0, description="Total bytes across all packets")
    avg_ttl: float = Field(..., ge=0, description="Average TTL value")
    # B. 协议类型特征 (8-11)
    ip_proto: float = Field(..., ge=0, description="IP protocol number (6=TCP, 17=UDP)")
    tcp_ratio: float = Field(..., ge=0, le=1, description="Ratio of TCP packets")
    udp_ratio: float = Field(..., ge=0, le=1, description="Ratio of UDP packets")
    other_proto_ratio: float = Field(..., ge=0, le=1, description="Ratio of other protocol packets")
    # C. TCP 行为特征 (12-19)
    avg_window_size: float = Field(..., ge=0, description="Average TCP window size")
    std_window_size: float = Field(..., ge=0, description="Standard deviation of window sizes")
    syn_count: int = Field(..., ge=0, description="SYN flag count")
    ack_count: int = Field(..., ge=0, description="ACK flag count")
    push_count: int = Field(..., ge=0, description="PSH flag count")
    fin_count: int = Field(..., ge=0, description="FIN flag count")
    rst_count: int = Field(..., ge=0, description="RST flag count")
    avg_hdr_len: float = Field(..., ge=0, description="Average TCP header length")
    # D. 时间特征 (20-23)
    total_duration: float = Field(..., ge=0, description="Total flow duration in seconds")
    avg_inter_arrival: float = Field(..., ge=0, description="Average inter-arrival time")
    std_inter_arrival: float = Field(..., ge=0, description="Standard deviation of inter-arrival times")
    packet_rate: float = Field(..., ge=0, description="Packets per second")
    # E. 端口特征 (24-27)
    src_port_entropy: float = Field(..., ge=0, description="Source port entropy")
    dst_port_entropy: float = Field(..., ge=0, description="Destination port entropy")
    well_known_port_ratio: float = Field(..., ge=0, le=1, description="Ratio of well-known ports (<=1023)")
    high_port_ratio: float = Field(..., ge=0, le=1, description="Ratio of high ports (>1023)")
    # F. 地址特征 (28-31)
    unique_dst_ip_count: int = Field(..., ge=0, description="Number of unique destination IPs")
    internal_ip_ratio: float = Field(..., ge=0, le=1, description="Ratio of internal IP addresses")
    df_flag_ratio: float = Field(..., ge=0, le=1, description="Ratio of DF flags")
    avg_ip_id: float = Field(..., ge=0, le=1, description="Normalized average IP ID")


class ClassifyRequest(BaseModel):
    """Request model for traffic classification per API_SPEC.md"""
    features: TrafficFeatures


class ClassifyResponse(BaseModel):
    """Response model for traffic classification per API_SPEC.md"""
    prediction: int = Field(..., description="0 for normal, 1 for anomaly")
    label: str = Field(..., description="'normal' or 'anomaly'")
    confidence: float = Field(..., description="Confidence score [0.0, 1.0]")
    latency_ms: float = Field(..., description="Inference latency in milliseconds")


class HealthResponse(BaseModel):
    """Health check response per API_SPEC.md"""
    status: str
    service: str = "svm-filter-service"
    version: str = "1.0.0"
    uptime_seconds: float


def load_model():
    """Load SVM model and scaler from disk"""
    global svm_model, scaler

    if MODEL_PATH.exists() and SCALER_PATH.exists():
        logger.info(f"Loading model from {MODEL_PATH}")
        svm_model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        logger.info(f"Model loaded successfully, features={svm_model.n_features_in_ if hasattr(svm_model, 'n_features_in_') else 'unknown'}")
        return True

    # If no saved model, train a simple one for demo
    logger.warning("No saved model found, training default model...")
    return train_default_model()


def train_default_model():
    """Train a default SVM model for demo purposes (32 features)"""
    global svm_model, scaler

    from sklearn.svm import LinearSVC

    # Generate synthetic training data for 32-feature model
    # Normal traffic: moderate packet sizes, regular intervals, low flag counts
    # Anomaly traffic: unusual patterns, high variance

    np.random.seed(42)
    n_normal = 1000
    n_anomaly = 100

    # Feature dimensions: 32 (per dataset-feature-engineering.md)
    n_features = 32

    # Normal traffic features - typical web/browsing patterns
    normal_features = np.column_stack([
        # A. 基础统计特征 (0-7)
        np.random.uniform(200, 800, n_normal),   # avg_packet_len
        np.random.uniform(50, 200, n_normal),    # std_packet_len
        np.random.uniform(200, 800, n_normal),   # avg_ip_len
        np.random.uniform(50, 200, n_normal),    # std_ip_len
        np.random.uniform(100, 600, n_normal),   # avg_tcp_len
        np.random.uniform(30, 150, n_normal),    # std_tcp_len
        np.random.uniform(2000, 8000, n_normal), # total_bytes
        np.random.uniform(32, 128, n_normal),    # avg_ttl
        # B. 协议类型特征 (8-11)
        np.full(n_normal, 6),                    # ip_proto (TCP=6)
        np.ones(n_normal),                       # tcp_ratio
        np.zeros(n_normal),                      # udp_ratio
        np.zeros(n_normal),                      # other_proto_ratio
        # C. TCP 行为特征 (12-19)
        np.random.uniform(1000, 65000, n_normal),# avg_window_size
        np.random.uniform(1000, 10000, n_normal),# std_window_size
        np.random.randint(0, 5, n_normal),       # syn_count
        np.random.randint(5, 30, n_normal),      # ack_count
        np.random.randint(0, 10, n_normal),      # push_count
        np.random.randint(0, 5, n_normal),       # fin_count
        np.random.randint(0, 2, n_normal),       # rst_count
        np.random.uniform(20, 32, n_normal),     # avg_hdr_len
        # D. 时间特征 (20-23)
        np.random.uniform(1, 60, n_normal),      # total_duration
        np.random.uniform(0.1, 2.0, n_normal),   # avg_inter_arrival
        np.random.uniform(0.05, 0.5, n_normal),  # std_inter_arrival
        np.random.uniform(0.5, 10, n_normal),    # packet_rate
        # E. 端口特征 (24-27)
        np.random.uniform(0, 2, n_normal),       # src_port_entropy
        np.random.uniform(0, 2, n_normal),       # dst_port_entropy
        np.random.uniform(0, 1, n_normal),       # well_known_port_ratio
        np.random.uniform(0, 1, n_normal),       # high_port_ratio
        # F. 地址特征 (28-31)
        np.ones(n_normal),                       # unique_dst_ip_count
        np.random.uniform(0, 1, n_normal),       # internal_ip_ratio
        np.random.uniform(0.5, 1, n_normal),     # df_flag_ratio
        np.random.uniform(0, 1, n_normal),       # avg_ip_id
    ])

    # Anomaly traffic features - unusual patterns (scanning, malware, etc.)
    anomaly_features = np.column_stack([
        # A. 基础统计特征 (0-7)
        np.random.uniform(800, 1500, n_anomaly), # avg_packet_len: large
        np.random.uniform(300, 600, n_anomaly),  # std_packet_len: high variance
        np.random.uniform(800, 1500, n_anomaly), # avg_ip_len
        np.random.uniform(300, 600, n_anomaly),  # std_ip_len
        np.random.uniform(600, 1400, n_anomaly), # avg_tcp_len
        np.random.uniform(200, 500, n_anomaly),  # std_tcp_len
        np.random.uniform(10000, 100000, n_anomaly), # total_bytes: high
        np.random.uniform(1, 64, n_anomaly),     # avg_ttl: varied
        # B. 协议类型特征 (8-11)
        np.full(n_anomaly, 6),                   # ip_proto (TCP=6)
        np.ones(n_anomaly),                      # tcp_ratio
        np.zeros(n_anomaly),                     # udp_ratio
        np.zeros(n_anomaly),                     # other_proto_ratio
        # C. TCP 行为特征 (12-19)
        np.random.uniform(100, 10000, n_anomaly),# avg_window_size
        np.random.uniform(5000, 50000, n_anomaly),# std_window_size: high variance
        np.random.randint(20, 100, n_anomaly),   # syn_count: many SYN (scan)
        np.random.randint(50, 200, n_anomaly),   # ack_count
        np.random.randint(20, 100, n_anomaly),   # push_count
        np.random.randint(0, 10, n_anomaly),     # fin_count
        np.random.randint(10, 50, n_anomaly),    # rst_count: many resets
        np.random.uniform(20, 60, n_anomaly),    # avg_hdr_len
        # D. 时间特征 (20-23)
        np.random.uniform(0.1, 10, n_anomaly),   # total_duration
        np.random.uniform(0.001, 0.1, n_anomaly),# avg_inter_arrival: very fast
        np.random.uniform(0.001, 0.05, n_anomaly),# std_inter_arrival
        np.random.uniform(50, 500, n_anomaly),   # packet_rate: high rate
        # E. 端口特征 (24-27)
        np.random.uniform(2, 5, n_anomaly),      # src_port_entropy: high
        np.random.uniform(2, 5, n_anomaly),      # dst_port_entropy: high (port scan)
        np.random.uniform(0, 1, n_anomaly),      # well_known_port_ratio
        np.random.uniform(0, 1, n_anomaly),      # high_port_ratio
        # F. 地址特征 (28-31)
        np.random.randint(10, 100, n_anomaly),   # unique_dst_ip_count: many (scan)
        np.random.uniform(0, 1, n_anomaly),      # internal_ip_ratio
        np.random.uniform(0, 0.5, n_anomaly),    # df_flag_ratio
        np.random.uniform(0, 1, n_anomaly),      # avg_ip_id
    ])

    X = np.vstack([normal_features, anomaly_features])
    y = np.hstack([np.zeros(n_normal), np.ones(n_anomaly)])

    # Train scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train linear SVM (fastest for inference)
    svm_model = LinearSVC(
        C=1.0,
        class_weight='balanced',
        max_iter=1000,
        dual=False  # Better for n_samples > n_features
    )
    svm_model.fit(X_scaled, y)

    # Save models
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(svm_model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    logger.info(f"Default model saved to {MODEL_PATH}")

    return True


def get_confidence(decision_value: float) -> float:
    """Convert SVM decision value to confidence score"""
    # Sigmoid transformation
    confidence = 1 / (1 + np.exp(-abs(decision_value)))
    return float(confidence)


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    logger.info("SVM Filter Service starting up...")
    load_model()
    logger.info("SVM Filter Service ready")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint per API_SPEC.md"""
    uptime = time.time() - start_time
    return HealthResponse(
        status="healthy" if svm_model is not None else "degraded",
        service="svm-filter-service",
        version="1.0.0",
        uptime_seconds=uptime
    )


@app.get("/ready")
async def readiness_check():
    """Readiness probe for Kubernetes"""
    if svm_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "ready"}


def features_to_array(features: TrafficFeatures) -> np.ndarray:
    """Convert TrafficFeatures model to numpy array (32 dimensions)"""
    return np.array([
        # A. 基础统计特征 (0-7)
        features.avg_packet_len,
        features.std_packet_len,
        features.avg_ip_len,
        features.std_ip_len,
        features.avg_tcp_len,
        features.std_tcp_len,
        features.total_bytes,
        features.avg_ttl,
        # B. 协议类型特征 (8-11)
        features.ip_proto,
        features.tcp_ratio,
        features.udp_ratio,
        features.other_proto_ratio,
        # C. TCP 行为特征 (12-19)
        features.avg_window_size,
        features.std_window_size,
        features.syn_count,
        features.ack_count,
        features.push_count,
        features.fin_count,
        features.rst_count,
        features.avg_hdr_len,
        # D. 时间特征 (20-23)
        features.total_duration,
        features.avg_inter_arrival,
        features.std_inter_arrival,
        features.packet_rate,
        # E. 端口特征 (24-27)
        features.src_port_entropy,
        features.dst_port_entropy,
        features.well_known_port_ratio,
        features.high_port_ratio,
        # F. 地址特征 (28-31)
        features.unique_dst_ip_count,
        features.internal_ip_ratio,
        features.df_flag_ratio,
        features.avg_ip_id
    ]).reshape(1, -1)


@app.post("/api/classify", response_model=ClassifyResponse)
async def classify_traffic(request: ClassifyRequest):
    """
    Classify traffic as normal (0) or anomaly (1)

    Per dataset-feature-engineering.md:
    - 32-dimension feature vector
    - Returns prediction, label, confidence, and latency
    """
    if svm_model is None:
        logger.error("Model not loaded")
        raise HTTPException(status_code=503, detail="Model not loaded")

    start = time.perf_counter()

    # Convert features to numpy array
    features = features_to_array(request.features)

    # Scale features
    features_scaled = scaler.transform(features)

    # Predict
    prediction = int(svm_model.predict(features_scaled)[0])

    # Get decision value for confidence
    decision_value = float(svm_model.decision_function(features_scaled)[0])
    confidence = get_confidence(decision_value)

    end = time.perf_counter()
    latency_ms = (end - start) * 1000

    logger.debug(f"Classification: prediction={prediction}, confidence={confidence:.3f}, latency={latency_ms:.3f}ms")

    return ClassifyResponse(
        prediction=prediction,
        label="anomaly" if prediction == 1 else "normal",
        confidence=confidence,
        latency_ms=latency_ms
    )


@app.post("/api/batch_classify")
async def batch_classify_traffic(requests: list[ClassifyRequest]):
    """
    Batch classification for multiple flows

    More efficient for processing multiple flows at once
    """
    if svm_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    start = time.perf_counter()

    # Convert to numpy array
    features = np.vstack([features_to_array(req.features) for req in requests])

    # Scale features
    features_scaled = scaler.transform(features)

    # Predict
    predictions = svm_model.predict(features_scaled)
    decision_values = svm_model.decision_function(features_scaled)

    end = time.perf_counter()
    latency_ms = (end - start) * 1000

    results = []
    for i, (pred, dv) in enumerate(zip(predictions, decision_values)):
        results.append({
            "index": i,
            "prediction": int(pred),
            "label": "anomaly" if pred == 1 else "normal",
            "confidence": get_confidence(dv)
        })

    return {
        "results": results,
        "total_latency_ms": latency_ms,
        "avg_latency_ms": latency_ms / len(requests)
    }


@app.get("/model/info")
async def model_info():
    """Get information about the loaded model"""
    if svm_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return {
        "model_type": type(svm_model).__name__,
        "n_features": svm_model.n_features_in_ if hasattr(svm_model, 'n_features_in_') else "unknown",
        "classes": svm_model.classes_.tolist() if hasattr(svm_model, 'classes_') else "unknown",
        "feature_names": FEATURE_NAMES
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
