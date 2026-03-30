"""
SVM Filter Service - Main Application
First-stage traffic filter with microsecond-level latency

API Spec: /root/anxun/docs/references/api_specs.md
"""

import time
import numpy as np
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sklearn.preprocessing import StandardScaler
import joblib

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

# Feature names for 14-dimension feature vector (per API_SPEC.md)
FEATURE_NAMES = [
    "packet_count", "avg_packet_size", "std_packet_size", "flow_duration",
    "avg_inter_arrival_time", "tcp_flag_syn", "tcp_flag_ack", "tcp_flag_fin",
    "tcp_flag_rst", "tcp_flag_psh", "unique_dst_ports", "unique_src_ports",
    "bytes_per_second", "packets_per_second"
]


class TrafficFeatures(BaseModel):
    """Traffic feature vector matching API_SPEC.md"""
    packet_count: int = Field(..., ge=0, description="Number of packets in flow")
    avg_packet_size: float = Field(..., ge=0, description="Average packet size in bytes")
    std_packet_size: float = Field(..., ge=0, description="Standard deviation of packet sizes")
    flow_duration: float = Field(..., ge=0, description="Flow duration in seconds")
    avg_inter_arrival_time: float = Field(..., ge=0, description="Average inter-arrival time in seconds")
    tcp_flag_syn: int = Field(..., ge=0, description="SYN flag count")
    tcp_flag_ack: int = Field(..., ge=0, description="ACK flag count")
    tcp_flag_fin: int = Field(..., ge=0, description="FIN flag count")
    tcp_flag_rst: int = Field(..., ge=0, description="RST flag count")
    tcp_flag_psh: int = Field(..., ge=0, description="PSH flag count")
    unique_dst_ports: int = Field(..., ge=0, description="Number of unique destination ports")
    unique_src_ports: int = Field(..., ge=0, description="Number of unique source ports")
    bytes_per_second: float = Field(..., ge=0, description="Bytes per second rate")
    packets_per_second: float = Field(..., ge=0, description="Packets per second rate")


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
        svm_model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        return True

    # If no saved model, train a simple one for demo
    return train_default_model()


def train_default_model():
    """Train a default SVM model for demo purposes (14 features)"""
    global svm_model, scaler

    from sklearn.svm import LinearSVC

    # Generate synthetic training data for 14-feature model
    # Normal traffic: moderate packet sizes, regular intervals, low flag counts
    # Anomaly traffic: unusual patterns, high variance

    np.random.seed(42)
    n_normal = 1000
    n_anomaly = 100

    # Feature dimensions: 14 (per API_SPEC.md)
    n_features = 14

    # Normal traffic features - typical web/browsing patterns
    normal_features = np.column_stack([
        np.random.randint(5, 50, n_normal),      # packet_count: 5-50 packets
        np.random.uniform(200, 800, n_normal),   # avg_packet_size: 200-800 bytes
        np.random.uniform(50, 200, n_normal),    # std_packet_size
        np.random.uniform(1, 60, n_normal),      # flow_duration: 1-60 seconds
        np.random.uniform(0.1, 2.0, n_normal),   # avg_inter_arrival_time
        np.random.randint(0, 5, n_normal),       # tcp_flag_syn
        np.random.randint(5, 30, n_normal),      # tcp_flag_ack
        np.random.randint(0, 5, n_normal),       # tcp_flag_fin
        np.random.randint(0, 2, n_normal),       # tcp_flag_rst
        np.random.randint(0, 10, n_normal),      # tcp_flag_psh
        np.random.randint(1, 3, n_normal),       # unique_dst_ports
        np.random.randint(1, 3, n_normal),       # unique_src_ports
        np.random.uniform(500, 5000, n_normal),  # bytes_per_second
        np.random.uniform(0.5, 10, n_normal),    # packets_per_second
    ])

    # Anomaly traffic features - unusual patterns (scanning, malware, etc.)
    anomaly_features = np.column_stack([
        np.random.randint(100, 500, n_anomaly),  # packet_count: many packets
        np.random.uniform(800, 1500, n_anomaly), # avg_packet_size: large packets
        np.random.uniform(300, 600, n_anomaly),  # std_packet_size: high variance
        np.random.uniform(0.1, 10, n_anomaly),   # flow_duration: short or long
        np.random.uniform(0.001, 0.1, n_anomaly),# avg_inter_arrival_time: very fast
        np.random.randint(20, 100, n_anomaly),   # tcp_flag_syn: many SYN (scan)
        np.random.randint(50, 200, n_anomaly),   # tcp_flag_ack
        np.random.randint(0, 10, n_anomaly),     # tcp_flag_fin
        np.random.randint(10, 50, n_anomaly),    # tcp_flag_rst: many resets
        np.random.randint(20, 100, n_anomaly),   # tcp_flag_psh
        np.random.randint(10, 100, n_anomaly),   # unique_dst_ports: port scan
        np.random.randint(1, 5, n_anomaly),      # unique_src_ports
        np.random.uniform(10000, 100000, n_anomaly),  # bytes_per_second: high
        np.random.uniform(50, 500, n_anomaly),   # packets_per_second: high rate
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

    return True


def get_confidence(decision_value: float) -> float:
    """Convert SVM decision value to confidence score"""
    # Sigmoid transformation
    confidence = 1 / (1 + np.exp(-abs(decision_value)))
    return float(confidence)


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    load_model()


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
    """Convert TrafficFeatures model to numpy array"""
    return np.array([
        features.packet_count,
        features.avg_packet_size,
        features.std_packet_size,
        features.flow_duration,
        features.avg_inter_arrival_time,
        features.tcp_flag_syn,
        features.tcp_flag_ack,
        features.tcp_flag_fin,
        features.tcp_flag_rst,
        features.tcp_flag_psh,
        features.unique_dst_ports,
        features.unique_src_ports,
        features.bytes_per_second,
        features.packets_per_second
    ]).reshape(1, -1)


@app.post("/api/classify", response_model=ClassifyResponse)
async def classify_traffic(request: ClassifyRequest):
    """
    Classify traffic as normal (0) or anomaly (1)

    Per API_SPEC.md section 2.2:
    - 14-dimension feature vector
    - Returns prediction, label, confidence, and latency
    """
    if svm_model is None:
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
