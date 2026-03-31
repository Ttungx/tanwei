"""
SVM Model Training Script for Traffic Classification
Trains a robust, lightweight SVM on multiple datasets to achieve >90% filtering of normal traffic
while preserving anomalies for the LLM second stage.
"""

import argparse
import json
import time
import numpy as np
from collections import Counter
from pathlib import Path
from typing import Tuple, List, Dict

from sklearn.svm import LinearSVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import joblib

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

# Label mappings based on dataset-feature-engineering.md
NORMAL_LABELS = {
    'normal', 'benign', '0', 'irc',
    'bittorrent', 'ftp', 'facetime', 'gmail', 'mysql', 
    'outlook', 'smb', 'skype', 'weibo', 'worldofwarcraft'
}

ANOMALY_LABELS = {
    'apt', 'malicious', '1',
    'virut', 'neris', 'rbot',
    'cridex', 'geodo', 'htbot', 'miuref', 'nsis-ay', 
    'shifu', 'tinba', 'zeus'
}

def _safe_float(value, default=0.0):
    try:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith('0x'):
                return float(int(value, 16))
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default

def _is_internal_ip(ip: str) -> int:
    if not ip:
        return 0
    parts = ip.split('.')
    if len(parts) != 4:
        return 0
    try:
        first = int(parts[0])
        second = int(parts[1])
        if first == 10:
            return 1
        if first == 172 and 16 <= second <= 31:
            return 1
        if first == 192 and second == 168:
            return 1
    except ValueError:
        return 0
    return 0

def _normalize_ip_id(ip_id: str) -> float:
    try:
        if isinstance(ip_id, str) and ip_id.startswith('0x'):
            value = int(ip_id, 16)
        else:
            value = int(ip_id)
        return value / 65535.0
    except (ValueError, TypeError):
        return 0.0

def extract_packet_features(instruction_text: str) -> np.ndarray:
    """Extract 32-dim feature vector from <packet> description"""
    if '<packet>:' not in instruction_text:
        return np.zeros(32)

    packet_content = instruction_text.split('<packet>:')[-1]

    fields = {}
    for item in packet_content.split(', '):
        if ':' in item:
            key, value = item.split(':', 1)
            fields[key.strip()] = value.strip()

    features = np.zeros(32)

    frame_len = _safe_float(fields.get('frame.len', 0))
    ip_len = _safe_float(fields.get('ip.len', 0))
    tcp_len = _safe_float(fields.get('tcp.len', 0))
    ip_ttl = _safe_float(fields.get('ip.ttl', 0))

    features[0] = frame_len           
    features[2] = ip_len              
    features[4] = tcp_len             
    features[6] = frame_len           
    features[7] = ip_ttl              

    ip_proto = _safe_float(fields.get('ip.proto', 0))
    features[8] = ip_proto            
    features[9] = 1 if ip_proto == 6 else 0  
    features[10] = 1 if ip_proto == 17 else 0  
    features[11] = 1 if ip_proto not in [6, 17] else 0  

    window_size = _safe_float(fields.get('tcp.window_size', 0))
    features[12] = window_size        
    features[14] = _safe_float(fields.get('tcp.flags.syn', 0))  
    features[15] = _safe_float(fields.get('tcp.flags.ack', 0))  
    features[16] = _safe_float(fields.get('tcp.flags.push', 0))  
    features[17] = _safe_float(fields.get('tcp.flags.fin', 0))  
    features[18] = _safe_float(fields.get('tcp.flags.reset', 0))  
    features[19] = _safe_float(fields.get('tcp.hdr_len', 0))  

    time_delta = _safe_float(fields.get('frame.time_delta', 0))
    features[20] = time_delta         
    features[21] = time_delta         
    features[23] = 1.0 / max(time_delta, 0.000001)  

    src_port = _safe_float(fields.get('tcp.srcport', fields.get('udp.srcport', 0)))
    dst_port = _safe_float(fields.get('tcp.dstport', fields.get('udp.dstport', 0)))
    features[24] = 0 if src_port == 0 else 1  
    features[25] = 0 if dst_port == 0 else 1  
    features[26] = 1 if dst_port <= 1023 else 0  
    features[27] = 1 if dst_port > 1023 else 0  

    df_flag = _safe_float(fields.get('ip.flags.df', 0))
    features[28] = 1                  
    features[29] = _is_internal_ip(fields.get('ip.dst', ''))  
    features[30] = df_flag            
    features[31] = _normalize_ip_id(fields.get('ip.id', '0'))  

    return features

def load_multi_dataset(base_dir: str, max_per_dataset: int = 15000) -> Tuple[np.ndarray, np.ndarray]:
    """Load from multiple curated datasets to build a robust model"""
    datasets = [
        "dapt-2020/dapt-2020_detection_packet_train.json",
        "csic-2010/csic-2010_detection_packet_train.json", 
        "iscx-botnet-2014/iscx-botnet_detection_packet_train.json",
        "ustc-tfc-2016/ustc-tfc-2016_detection_packet_train.json"
    ]
    
    X_list = []
    y_list = []
    
    base_path = Path(base_dir)
    print(f"Loading data from {base_dir} ...")
    
    for rel_path in datasets:
        file_path = base_path / rel_path
        if not file_path.exists():
            print(f"  [X] Not found: {rel_path}")
            continue
            
        print(f"  [+] Loading {rel_path} ...")
        count = 0
        normal_count = 0
        anomaly_count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if count >= max_per_dataset:
                    break
                try:
                    data = json.loads(line)
                    out_label = data.get("output", "").strip().lower()
                    
                    if out_label in NORMAL_LABELS:
                        label = 0
                        normal_count += 1
                    elif out_label in ANOMALY_LABELS:
                        label = 1
                        anomaly_count += 1
                    else:
                        continue # Skip unknown labels
                        
                    feature = extract_packet_features(data.get("instruction", ""))
                    X_list.append(feature)
                    y_list.append(label)
                    count += 1
                except Exception as e:
                    continue
        print(f"      Loaded {count} samples (Normal: {normal_count}, Anomaly: {anomaly_count})")

    return np.array(X_list), np.array(y_list)

def measure_inference_latency(model: object, scaler: StandardScaler, X_sample: np.ndarray, n_iter: int = 1000) -> dict:
    """Measure inference latency in microseconds"""
    X_scaled = scaler.transform(X_sample)
    # Warm-up
    for _ in range(100):
        _ = model.predict(X_scaled[:1])
    
    latencies = []
    for _ in range(n_iter):
        start = time.perf_counter()
        _ = model.predict(X_scaled[:1])
        end = time.perf_counter()
        latencies.append((end - start) * 1_000_000)
        
    return {
        'mean_us': float(np.mean(latencies)),
        'median_us': float(np.median(latencies)),
        'p99_us': float(np.percentile(latencies, 99))
    }

def adjust_threshold_for_recall(model: LinearSVC, X_val: np.ndarray, y_val: np.ndarray, target_normal_recall: float = 0.90):
    """
    Adjust SVM intercept to ensure we filter out AT LEAST target_normal_recall (e.g. 90%) of normal traffic.
    Normal is class 0. Since SVM predicts 0 when decision_function < 0, 
    we want more things to be < 0 if our normal recall is too low.
    """
    decisions = model.decision_function(X_val)
    # y_val == 0 is normal. We want 90% of these to have decision < adjusted_threshold
    normal_decisions = decisions[y_val == 0]
    
    # Current threshold is 0.
    current_recall = np.sum(normal_decisions < 0) / len(normal_decisions)
    print(f"Default Normal Filtering Rate (TNR): {current_recall*100:.2f}%")
    
    if current_recall < target_normal_recall:
        print(f"Adjusting threshold to enforce >= {target_normal_recall*100:.0f}% Normal filtering...")
        # Find the threshold where 90% of normal samples fall below it
        adjusted_threshold = np.percentile(normal_decisions, target_normal_recall * 100)
        # Shift the model intercept space. 
        # By subtracting this threshold from the intercept, dec < threshold becomes dec < 0
        model.intercept_ -= adjusted_threshold
        print(f"Threshold shifted by {-adjusted_threshold:.4f}")
    else:
        print("Model already meets the >90% normal filtering target without adjustment.")
        
    return model

def main():
    parser = argparse.ArgumentParser(description='Train robust lightweight SVM on multiple datasets')
    parser.add_argument('--output', type=str, default='models/saved', help='Output directory for model')
    parser.add_argument('--data-dir', type=str, default='/root/anxun/data/tran_data/TrafficLLM_Datasets')
    parser.add_argument('--max-per-dataset', type=int, default=15000, help='Max samples per dataset folder')
    parser.add_argument('--C', type=float, default=0.5, help='Regularization parameter')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set ratio')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')

    args = parser.parse_args()

    print("=" * 60)
    print("SVM Traffic Classifier - Multi-Dataset Robust Training")
    print("=" * 60)

    X, y = load_multi_dataset(args.data_dir, max_per_dataset=args.max_per_dataset)

    if len(X) == 0:
        print("Failed to load data. Please check data path and format.")
        return

    print(f"\nTotal Dataset: {len(X)} samples, {X.shape[1]} features")
    print(f"Total Normal (0): {np.sum(y == 0)}, Total Anomaly (1): {np.sum(y == 1)}")

    stratify = y if min(Counter(y).values()) > 1 else None
    
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed, stratify=stratify
    )
    
    # Further split temp into val and test for threshold tuning
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=args.seed, stratify=y_temp
    )

    print(f"Train set: {len(X_train)}, Val set: {len(X_val)}, Test set: {len(X_test)}")

    print(f"\nTraining LinearSVC ...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    model = LinearSVC(
        C=args.C,
        class_weight='balanced',
        max_iter=5000,
        dual=False
    )
    model.fit(X_train_scaled, y_train)

    X_val_scaled = scaler.transform(X_val)
    
    # Adjust threshold to guarantee strictly >= 90% filtering of class 0
    model = adjust_threshold_for_recall(model, X_val_scaled, y_val, target_normal_recall=0.92)

    print("\n--- Final Evaluation on Test Set ---")
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    
    print(f"Overall Accuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    normal_filter_rate = tn / (tn + fp)
    anomaly_detect_rate = tp / (tp + fn)
    print(f"Normal Breakdown (Class 0):")
    print(f"  Filtered (True Negative): {tn}")
    print(f"  Passed to LLM (FP)      : {fp}")
    print(f"  => Current Normal Filtering Rate: {normal_filter_rate*100:.2f}%")
    print(f"Anomaly Breakdown (Class 1):")
    print(f"  Correctly Passed (TP)   : {tp}")
    print(f"  Erroneously Dropped(FN) : {fn}")
    print(f"  => Current Anomaly Detection Rate: {anomaly_detect_rate*100:.2f}%")

    print("\nMeasuring inference latency...")
    latency = measure_inference_latency(model, scaler, X_test[:100])
    print(f"Mean: {latency['mean_us']:.2f} us")
    print(f"P99:  {latency['p99_us']:.2f} us")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / 'svm_model.pkl'
    scaler_path = output_dir / 'scaler.pkl'
    metadata_path = output_dir / 'metadata.json'

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    metadata = {
        'kernel': 'linear',
        'C': args.C,
        'n_features': X.shape[1],
        'feature_names': FEATURE_NAMES,
        'accuracy': acc,
        'normal_filter_rate': normal_filter_rate,
        'anomaly_detect_rate': anomaly_detect_rate,
        'latency_us': latency,
        'total_samples_trained': len(X_train),
        'note': 'Model trained on DAPT, CSIC, ISCX, USTC mixed datasets with strict >= 90% normal filtering target.'
    }

    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSaved models and metadata to: {output_dir}")
    print("=" * 60)

if __name__ == '__main__':
    main()
