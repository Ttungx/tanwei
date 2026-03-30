export interface TaskStatus {
  task_id: string
  status: string
  stage: PipelineStage
  progress: number
  message: string
}

export type PipelineStage =
  | 'pending'
  | 'flow_reconstruction'
  | 'svm_filtering'
  | 'llm_inference'
  | 'completed'
  | 'failed'

export interface Threat {
  id: string
  five_tuple: {
    src_ip: string
    src_port: number
    dst_ip: string
    dst_port: number
    protocol: string
  }
  classification: {
    primary_label: string
    secondary_label: string
    confidence: number
    model: string
  }
  flow_metadata: {
    start_time: string
    end_time: string
    packet_count: number
    byte_count: number
    avg_packet_size: number
  }
  token_info: {
    token_count: number
    truncated: boolean
  }
}

export interface DetectionResult {
  meta: {
    task_id: string
    timestamp: string
    agent_version: string
    processing_time_ms: number
  }
  statistics: {
    total_packets: number
    total_flows: number
    normal_flows_dropped: number
    anomaly_flows_detected: number
    svm_filter_rate: string
    bandwidth_reduction: string
  }
  threats: Threat[]
  metrics: {
    original_pcap_size_bytes: number
    json_output_size_bytes: number
    bandwidth_saved_percent: number
  }
}

export interface DetectionResponse {
  status: string
  task_id: string
  message: string
}
