import { useState, useCallback, useEffect, useRef } from 'react'
import FileUpload from './components/FileUpload'
import PipelineStatus from './components/PipelineStatus'
import ResultDashboard from './components/ResultDashboard'
import { uploadPcap, getTaskStatus, getTaskResult } from './api/client'
import type { TaskStatus, DetectionResult, PipelineStage } from './types/api'
import styles from './App.module.css'

type AppState = 'idle' | 'uploading' | 'processing' | 'completed' | 'failed'

const STAGE_COPY: Record<PipelineStage, { label: string; detail: string }> = {
  pending: {
    label: '待命队列',
    detail: '等待接收新的流量样本与任务上下文。',
  },
  flow_reconstruction: {
    label: '流重组',
    detail: '对原始包进行会话重建，准备进入筛选链路。',
  },
  svm_filtering: {
    label: 'SVM 初筛',
    detail: '快速过滤大部分正常流量，压低后续推理成本。',
  },
  llm_inference: {
    label: 'LLM 推理',
    detail: '对异常候选进行语义分析与标签判定。',
  },
  completed: {
    label: '检测完成',
    detail: '结果已归档，可查看压降与威胁详情。',
  },
  failed: {
    label: '流程中断',
    detail: '当前任务未能完成，需要重新提交样本。',
  },
}

const APP_STATE_LABEL: Record<AppState, string> = {
  idle: '待命',
  uploading: '上传中',
  processing: '分析中',
  completed: '已完成',
  failed: '异常终止',
}

export default function App() {
  const [appState, setAppState] = useState<AppState>('idle')
  const [_taskId, setTaskId] = useState<string | null>(null)
  const [stage, setStage] = useState<PipelineStage>('pending')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollTimeoutRef = useRef<number | null>(null)
  const activeTaskRef = useRef<string | null>(null)

  const clearPolling = useCallback(() => {
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current)
      pollTimeoutRef.current = null
    }
    activeTaskRef.current = null
  }, [])

  const pollStatus = useCallback(async (id: string) => {
    activeTaskRef.current = id
    let consecutiveErrors = 0

    const poll = async (): Promise<boolean> => {
      if (activeTaskRef.current !== id) {
        return true
      }

      try {
        const status: TaskStatus = await getTaskStatus(id)
        consecutiveErrors = 0

        if (activeTaskRef.current !== id) {
          return true
        }

        setStage(status.stage)
        setProgress(status.progress)
        setMessage(status.message)

        if (status.stage === 'completed') {
          try {
            const resultData = await getTaskResult(id)

            if (activeTaskRef.current !== id) {
              return true
            }

            setResult(resultData)
            setAppState('completed')
            clearPolling()
            return true
          } catch (err) {
            setError(err instanceof Error ? err.message : '结果获取失败')
            setAppState('failed')
            clearPolling()
            return true
          }
        }

        if (status.stage === 'failed') {
          setError(status.message)
          setAppState('failed')
          clearPolling()
          return true
        }

        return false
      } catch (err) {
        consecutiveErrors += 1

        if (consecutiveErrors >= 3) {
          setError(err instanceof Error ? err.message : '任务状态获取失败')
          setAppState('failed')
          clearPolling()
          return true
        }

        return false
      }
    }

    const pollLoop = async () => {
      const done = await poll()
      if (!done && activeTaskRef.current === id) {
        pollTimeoutRef.current = window.setTimeout(pollLoop, 1000)
      }
    }

    pollLoop()
  }, [clearPolling])

  const handleUpload = useCallback(async (file: File): Promise<boolean> => {
    clearPolling()
    setAppState('uploading')
    setError(null)
    setResult(null)
    setProgress(0)
    setStage('pending')
    setMessage('样本已接收，正在创建检测任务。')

    try {
      const response = await uploadPcap(file)
      setTaskId(response.task_id)
      setAppState('processing')
      setMessage(response.message || '任务已创建，等待进入流水线。')
      pollStatus(response.task_id)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setAppState('failed')
      setMessage('样本上传未完成，请检查后端服务或重新尝试。')
      return false
    }
  }, [clearPolling, pollStatus])

  const handleReset = useCallback(() => {
    clearPolling()
    setAppState('idle')
    setTaskId(null)
    setStage('pending')
    setProgress(0)
    setMessage('')
    setResult(null)
    setError(null)
  }, [clearPolling])

  useEffect(() => {
    return () => {
      clearPolling()
    }
  }, [clearPolling])

  const currentStage = STAGE_COPY[stage]
  const threatCount = result?.threats.length ?? 0
  const quickMetrics = result
    ? [
        { label: '异常流量', value: String(result.statistics.anomaly_flows_detected) },
        { label: '压降节省', value: `${result.metrics.bandwidth_saved_percent.toFixed(1)}%` },
        { label: '推理耗时', value: `${(result.meta.processing_time_ms / 1000).toFixed(2)}s` },
      ]
    : [
        { label: '处理模式', value: '边缘侧预检' },
        { label: '分析链路', value: 'SVM + LLM' },
        { label: '输出目标', value: '威胁档案' },
      ]

  return (
    <div className={styles.app}>
      <div className={styles.backdrop} />

      <header className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.eyebrow}>EDGE DOSSIER / TRAFFIC FORENSICS</span>
          <div className={styles.titleRow}>
            <h1 className={styles.logo}>探微控制台</h1>
            <span className={styles.stateBadge}>{APP_STATE_LABEL[appState]}</span>
          </div>
          <p className={styles.subtitle}>
            将 Pcap 样本转化为可读的异常档案，突出筛选压降、当前流水线状态与可疑五元组。
          </p>
        </div>

        <div className={styles.heroPanel}>
          <div className={styles.heroPanelLabel}>当前阶段</div>
          <div className={styles.heroPanelStage}>{currentStage.label}</div>
          <p className={styles.heroPanelText}>{message || currentStage.detail}</p>

          <div className={styles.metricRail}>
            {quickMetrics.map((item) => (
              <div key={item.label} className={styles.metricCard}>
                <span className={styles.metricLabel}>{item.label}</span>
                <strong className={styles.metricValue}>{item.value}</strong>
              </div>
            ))}
          </div>

          <div className={styles.heroFooter}>
            <span>阶段进度 {progress}%</span>
            <span>{threatCount > 0 ? `已标记 ${threatCount} 个威胁流` : '等待样本进入检测链路'}</span>
          </div>
        </div>
      </header>

      <main className={styles.workspace}>
        <section className={styles.controlColumn}>
          <div className={styles.sectionHeading}>
            <span className={styles.sectionIndex}>01</span>
            <div>
              <h2>样本入口</h2>
              <p>上传流量样本并触发一次新的边缘分析任务。</p>
            </div>
          </div>

          <FileUpload
            onUpload={handleUpload}
            disabled={appState === 'uploading' || appState === 'processing'}
          />

          {appState !== 'idle' && (
            <div className={styles.statusSection}>
              <div className={styles.sectionHeading}>
                <span className={styles.sectionIndex}>02</span>
                <div>
                  <h2>执行链路</h2>
                  <p>观察当前任务在重组、筛选与推理中的推进状态。</p>
                </div>
              </div>

              <PipelineStatus
                stage={stage}
                progress={progress}
                message={message}
              />

              {error && (
                <div className={styles.error}>
                  <strong>异常回执</strong>
                  <span>{error}</span>
                </div>
              )}

              {(appState === 'completed' || appState === 'failed') && (
                <button onClick={handleReset} className={styles.resetButton}>
                  重新检测
                </button>
              )}
            </div>
          )}

          <aside className={styles.sideNote}>
            <span className={styles.sideNoteTag}>运行提示</span>
            <p>如果后端不可用，控制台会回退到 mock 结果，方便你单独校验界面层级与交互。</p>
          </aside>
        </section>

        <section className={styles.resultColumn}>
          <div className={styles.sectionHeading}>
            <span className={styles.sectionIndex}>03</span>
            <div>
              <h2>结果档案</h2>
              <p>把统计摘要、压降效果与异常流详情整合进一张可扫描的战术面板。</p>
            </div>
          </div>

          <ResultDashboard result={result} />
        </section>
      </main>
    </div>
  )
}
