import type { DetectionResponse, TaskStatus, DetectionResult } from '../types/api'

const API_BASE = '/api'

export async function uploadPcap(file: File): Promise<DetectionResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/detect`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(error.detail || 'Upload failed')
  }

  return response.json()
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  const response = await fetch(`${API_BASE}/status/${taskId}`)

  if (!response.ok) {
    throw new Error('Task not found')
  }

  return response.json()
}

export async function getTaskResult(taskId: string): Promise<DetectionResult> {
  const response = await fetch(`${API_BASE}/result/${taskId}`)

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Result not found' }))
    throw new Error(error.detail || 'Result not found')
  }

  return response.json()
}
