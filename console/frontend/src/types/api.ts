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
    secondary_label?: string | null
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

export type SampleSource = 'upload' | 'demo'

export interface DemoSample {
  id: string
  filename: string
  display_name: string
  size_bytes: number
}

export interface EdgeRegistryItem {
  edge_id: string
  report_count: number
  latest_report_id: string
  latest_reported_at: string
  latest_analysis_status: string
  latest_threat_level?: string | null
}

export interface EdgeRegistryResponse {
  edges: EdgeRegistryItem[]
}

export interface EdgeThreatReport {
  threat_id: string
  five_tuple: {
    src_ip: string
    dst_ip: string
    src_port: number
    dst_port: number
    protocol: string
  }
  svm_result?: {
    label: string
    confidence: number
  }
  edge_classification?: {
    primary_label: string
    secondary_label?: string | null
    confidence: number
    model: string
  }
  flow_metadata?: {
    start_time?: string
    end_time?: string
    packet_count?: number
    byte_count?: number
    avg_packet_size?: number
  }
  traffic_tokens?: {
    encoding?: string
    sequence?: string[]
    token_count?: number
    truncated?: boolean
  }
}

export interface EdgeIntelligenceReport {
  schema_version: string
  report_id: string
  edge_id: string
  producer: {
    service: string
    agent_version: string
    reported_at: string
  }
  analysis_constraints: {
    max_time_window_s: number
    max_packet_count: number
    max_token_length: number
  }
  meta: Record<string, unknown>
  statistics: Record<string, unknown>
  threats: EdgeThreatReport[]
  metrics: Record<string, unknown>
}

export interface EdgeAnalysis {
  mode: 'single-edge'
  edge_id: string
  threat_level: string
  summary: string
  analysis: string
  recommendations: string[]
  analysis_state: string
}

export interface NetworkAnalysis {
  mode: 'network-wide'
  edge_count: number
  threat_level: string
  summary: string
  analysis: string
  recommendations: string[]
  analysis_state: string
}

export type EdgeSummary = EdgeRegistryItem

export type SingleEdgeAnalysis = EdgeAnalysis
