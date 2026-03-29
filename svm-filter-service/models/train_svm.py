"""
SVM Model Training Script for Traffic Classification

This script trains an SVM model on network traffic features
for the first-stage filtering of normal vs anomaly traffic.

Feature vector (14 dimensions) per API_SPEC.md:
- packet_count, avg_packet_size, std_packet_size, flow_duration
- avg_inter_arrival_time, tcp_flag_syn, tcp_flag_ack, tcp_flag_fin
- tcp_flag_rst, tcp_flag_psh, unique_dst_ports, unique_src_ports
- bytes_per_second, packets_per_second
"""

import argparse
import json
import time
import numpy as np
from pathlib import Path
from typing import Tuple

from sklearn.svm import SVC, LinearSVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib


# Feature names for 14-dimension feature vector
FEATURE_NAMES = [
    "packet_count", "avg_packet_size", "std_packet_size", "flow_duration",
    "avg_inter_arrival_time", "tcp_flag_syn", "tcp_flag_ack", "tcp_flag_fin",
    "tcp_flag_rst", "tcp_flag_psh", "unique_dst_ports", "unique_src_ports",
    "bytes_per_second", "packets_per_second"
]


def generate_synthetic_data(
    n_normal: int = 10000,
    n_anomaly: int = 1000,
    seed: int = 42
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic traffic data for demonstration

    Feature design (14 dimensions) per API_SPEC.md:
    - Packet stats: packet_count, avg_packet_size, std_packet_size
    - Timing stats: flow_duration, avg_inter_arrival_time
    - TCP flags: syn, ack, fin, rst, psh counts
    - Port stats: unique_dst_ports, unique_src_ports
    - Rate stats: bytes_per_second, packets_per_second
    """
    np.random.seed(seed)

    # Normal traffic: typical web/browsing patterns
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

    # Anomaly traffic: unusual patterns (scanning, malware, DDoS, etc.)
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

    # Combine and create labels
    X = np.vstack([normal_features, anomaly_features])
    y = np.hstack([np.zeros(n_normal), np.ones(n_anomaly)])

    # Shuffle
    indices = np.random.permutation(len(X))
    return X[indices], y[indices]


def train_svm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    kernel: str = 'linear',
    C: float = 1.0
) -> Tuple[object, StandardScaler]:
    """
    Train SVM model with feature scaling

    Args:
        X_train: Training features (14 dimensions)
        y_train: Training labels (0=normal, 1=anomaly)
        kernel: 'linear' or 'rbf' (linear is faster for inference)
        C: Regularization parameter

    Returns:
        Trained SVM model and fitted scaler
    """
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    # Train SVM
    if kernel == 'linear':
        # LinearSVC is much faster for linear kernel
        model = LinearSVC(
            C=C,
            class_weight='balanced',
            max_iter=2000,
            dual=False  # Better when n_samples > n_features
        )
    else:
        model = SVC(
            kernel=kernel,
            C=C,
            class_weight='balanced',
            gamma='scale'
        )

    model.fit(X_scaled, y_train)

    return model, scaler


def evaluate_model(
    model: object,
    scaler: StandardScaler,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> dict:
    """Evaluate model performance"""
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)

    return {
        'accuracy': accuracy,
        'classification_report': report,
    }


def measure_inference_latency(
    model: object,
    scaler: StandardScaler,
    X_sample: np.ndarray,
    n_iterations: int = 1000
) -> dict:
    """Measure inference latency in microseconds"""
    X_scaled = scaler.transform(X_sample)

    # Warm-up
    for _ in range(100):
        _ = model.predict(X_scaled[:1])

    # Measure
    latencies = []
    for _ in range(n_iterations):
        start = time.perf_counter()
        _ = model.predict(X_scaled[:1])
        end = time.perf_counter()
        latencies.append((end - start) * 1_000_000)  # Convert to microseconds

    return {
        'mean_us': float(np.mean(latencies)),
        'median_us': float(np.median(latencies)),
        'p99_us': float(np.percentile(latencies, 99)),
        'max_us': float(np.max(latencies)),
        'min_us': float(np.min(latencies))
    }


def main():
    parser = argparse.ArgumentParser(description='Train SVM model for traffic classification')
    parser.add_argument('--output', type=str, default='models/saved', help='Output directory for model')
    parser.add_argument('--kernel', type=str, default='linear', choices=['linear', 'rbf'], help='SVM kernel')
    parser.add_argument('--C', type=float, default=1.0, help='Regularization parameter')
    parser.add_argument('--n-normal', type=int, default=10000, help='Number of normal samples')
    parser.add_argument('--n-anomaly', type=int, default=1000, help='Number of anomaly samples')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set ratio')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')

    args = parser.parse_args()

    print("=" * 60)
    print("SVM Traffic Classifier Training")
    print("=" * 60)

    # Generate synthetic data
    print("\nGenerating synthetic data...")
    X, y = generate_synthetic_data(
        n_normal=args.n_normal,
        n_anomaly=args.n_anomaly,
        seed=args.seed
    )

    print(f"Dataset: {len(X)} samples, {X.shape[1]} features")
    print(f"Normal: {np.sum(y == 0)}, Anomaly: {np.sum(y == 1)}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=y
    )

    print(f"\nTrain set: {len(X_train)}, Test set: {len(X_test)}")

    # Train model
    print(f"\nTraining SVM with {args.kernel} kernel...")
    model, scaler = train_svm(
        X_train, y_train,
        kernel=args.kernel,
        C=args.C
    )

    # Evaluate
    print("\nEvaluating model...")
    results = evaluate_model(model, scaler, X_test, y_test)

    print(f"\nAccuracy: {results['accuracy']:.4f}")
    print("\nClassification Report:")
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    print(classification_report(y_test, y_pred))

    # Measure latency
    print("\nMeasuring inference latency...")
    latency = measure_inference_latency(model, scaler, X_test[:100])
    print(f"Mean: {latency['mean_us']:.2f} us")
    print(f"Median: {latency['median_us']:.2f} us")
    print(f"P99: {latency['p99_us']:.2f} us")

    # Save model
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / 'svm_model.pkl'
    scaler_path = output_dir / 'scaler.pkl'
    metadata_path = output_dir / 'metadata.json'

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    metadata = {
        'kernel': args.kernel,
        'C': args.C,
        'n_features': X.shape[1],
        'feature_names': FEATURE_NAMES,
        'accuracy': results['accuracy'],
        'latency_us': latency,
        'normal_samples': int(np.sum(y == 0)),
        'anomaly_samples': int(np.sum(y == 1)),
        'note': 'Model trained on synthetic data. Replace with real traffic data for production.'
    }

    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {output_dir}")
    print(f"  - {model_path}")
    print(f"  - {scaler_path}")
    print(f"  - {metadata_path}")

    print("\n" + "=" * 60)
    print("Training complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
