import type {
  DemoSample,
  DetectionResponse,
  DetectionResult,
  EdgeAnalysis,
  EdgeIntelligenceReport,
  EdgeRegistryItem,
  EdgeRegistryResponse,
  NetworkAnalysis,
  TaskStatus,
} from '../types/api'

const API_BASE = '/api'

async function readJson<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: fallbackMessage }))
    throw new Error(error.detail || fallbackMessage)
  }

  return response.json() as Promise<T>
}

export async function uploadPcap(file: File): Promise<DetectionResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/detect`, {
    method: 'POST',
    body: formData,
  })

  return readJson<DetectionResponse>(response, 'Upload failed')
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE}/status/${taskId}`)
  return readJson<TaskStatus>(response, 'Task not found')
}

export async function getTaskResult(taskId: string): Promise<DetectionResult> {
  const response = await fetch(`${API_BASE}/result/${taskId}`)
  return readJson<DetectionResult>(response, 'Result not found')
}

export async function getDemoSamples(): Promise<DemoSample[]> {
  const response = await fetch(`${API_BASE}/demo-samples`)
  return readJson<DemoSample[]>(response, 'Demo sample list unavailable')
}

export async function startDemoDetection(sampleId: string): Promise<DetectionResponse> {
  const response = await fetch(`${API_BASE}/detect-demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sample_id: sampleId }),
  })

  return readJson<DetectionResponse>(response, 'Demo detection failed')
}

export async function getEdges(): Promise<EdgeRegistryItem[]> {
  const response = await fetch(`${API_BASE}/edges`)
  const payload = await readJson<EdgeRegistryResponse>(response, 'Edge list unavailable')
  return payload.edges ?? []
}

export async function getLatestEdgeReport(edgeId: string): Promise<EdgeIntelligenceReport> {
  const response = await fetch(`${API_BASE}/edges/${edgeId}/reports/latest`)
  return readJson<EdgeIntelligenceReport>(response, 'Edge report unavailable')
}

export async function getLatestEdgeAnalysis(edgeId: string): Promise<EdgeAnalysis> {
  const response = await fetch(`${API_BASE}/edges/${edgeId}/analysis`)
  return readJson<EdgeAnalysis>(response, 'Edge analysis unavailable')
}

export async function analyzeEdge(edgeId: string): Promise<EdgeAnalysis> {
  const response = await fetch(`${API_BASE}/edges/${edgeId}/analyze`, {
    method: 'POST',
  })

  return readJson<EdgeAnalysis>(response, 'Single-edge analysis failed')
}

export async function getLatestNetworkAnalysis(): Promise<NetworkAnalysis> {
  const response = await fetch(`${API_BASE}/network/analysis`)
  return readJson<NetworkAnalysis>(response, 'Network analysis unavailable')
}

export async function analyzeNetwork(): Promise<NetworkAnalysis> {
  const response = await fetch(`${API_BASE}/network/analyze`, {
    method: 'POST',
  })

  return readJson<NetworkAnalysis>(response, 'Network analysis failed')
}

// Backward-compatible aliases
export const getEdgeReport = getLatestEdgeReport
export const getEdgeAnalysis = getLatestEdgeAnalysis
export const getNetworkAnalysis = getLatestNetworkAnalysis
