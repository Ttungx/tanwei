import { useCallback, useEffect, useRef, useState } from 'react'
import { getTaskResult, getTaskStatus, uploadPcap } from './api/client'
import styles from './App.module.css'
import { PipelinePanel } from './components/PipelinePanel'
import { ResultArchive } from './components/ResultArchive'
import { SolutionOverview } from './components/SolutionOverview'
import { UploadWorkspace } from './components/UploadWorkspace'
import { buildConsoleViewModel, buildOverviewViewModel, type AppState } from './lib/view-models'
import type { DetectionResult, PipelineStage, TaskStatus } from './types/api'

type ViewMode = 'overview' | 'console'

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
    label: '结果归档',
    detail: '检测完成，异常档案和压降摘要已生成。',
  },
  failed: {
    label: '流程中断',
    detail: '本次任务未能完成，需要重新提交样本。',
  },
}

const NAV_ITEMS = [
  { id: 'overview', label: '方案概览' },
  { id: 'console', label: '控制台' },
  { id: 'archive', label: '结果归档' },
]

export default function App() {
  const [viewMode, setViewMode] = useState<ViewMode>('overview')
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

  const pollStatus = useCallback(async (taskId: string) => {
    activeTaskRef.current = taskId
    let consecutiveErrors = 0

    const poll = async (): Promise<boolean> => {
      if (activeTaskRef.current !== taskId) {
        return true
      }

      try {
        const status: TaskStatus = await getTaskStatus(taskId)
        consecutiveErrors = 0

        if (activeTaskRef.current !== taskId) {
          return true
        }

        setStage(status.stage)
        setProgress(status.progress)
        setMessage(status.message)

        if (status.stage === 'completed') {
          const resultData = await getTaskResult(taskId)
          setResult(resultData)
          setAppState('completed')
          clearPolling()
          return true
        }

        if (status.stage === 'failed') {
          setAppState('failed')
          setError(status.message)
          clearPolling()
          return true
        }

        return false
      } catch (pollError) {
        consecutiveErrors += 1

        if (consecutiveErrors >= 3) {
          setAppState('failed')
          setError(pollError instanceof Error ? pollError.message : '任务状态获取失败')
          clearPolling()
          return true
        }

        return false
      }
    }

    const loop = async () => {
      const done = await poll()

      if (!done && activeTaskRef.current === taskId) {
        pollTimeoutRef.current = window.setTimeout(loop, 1000)
      }
    }

    await loop()
  }, [clearPolling])

  const handleUpload = useCallback(async (file: File): Promise<boolean> => {
    clearPolling()
    setViewMode('console')
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
      await pollStatus(response.task_id)
      return true
    } catch (uploadError) {
      setAppState('failed')
      setError(uploadError instanceof Error ? uploadError.message : '样本上传失败')
      setMessage('样本上传未完成，请检查后端服务或重新尝试。')
      return false
    }
  }, [clearPolling, pollStatus])

  const handleReset = useCallback(() => {
    clearPolling()
    setTaskId(null)
    setAppState('idle')
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
  const consoleViewModel = buildConsoleViewModel({
    appState,
    stage,
    message,
    result,
    error,
  })
  const overviewViewModel = buildOverviewViewModel(result)

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brandBlock}>
          <span className={styles.brandEyebrow}>EDGE TEST CONSOLE</span>
          <h1 className={styles.brandTitle}>探微控制台</h1>
          <p className={styles.brandText}>边缘侧预筛、推理压降与威胁归档的一体化前端工作台。</p>
        </div>

        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => {
            const isActive =
              (item.id === 'overview' && viewMode === 'overview') ||
              (item.id === 'console' && viewMode === 'console') ||
              (item.id === 'archive' && viewMode === 'console')

            return (
              <button
                key={item.id}
                type="button"
                className={`${styles.navItem} ${isActive ? styles.navItemActive : ''}`}
                onClick={() => setViewMode(item.id === 'overview' ? 'overview' : 'console')}
              >
                <span className={styles.navIcon}>{item.label.slice(0, 1)}</span>
                <span>{item.label}</span>
              </button>
            )
          })}
        </nav>

        <div className={styles.sidebarFooter}>
          <span className={styles.footerBadge}>DESKTOP WORKSPACE</span>
          <span className={styles.footerMeta}>{consoleViewModel.stateLabel}</span>
        </div>
      </aside>

      <div className={styles.main}>
        <header className={styles.topbar}>
          <div>
            <span className={styles.topbarEyebrow}>Warm Console / Traffic Forensics</span>
            <p className={styles.topbarTitle}>{viewMode === 'overview' ? '方案概览' : '控制台'}</p>
          </div>

          <div className={styles.modeSwitch}>
            <button
              type="button"
              className={`${styles.modeButton} ${viewMode === 'overview' ? styles.modeButtonActive : ''}`}
              onClick={() => setViewMode('overview')}
            >
              方案概览
            </button>
            <button
              type="button"
              className={`${styles.modeButton} ${viewMode === 'console' ? styles.modeButtonActive : ''}`}
              onClick={() => setViewMode('console')}
            >
              控制台
            </button>
          </div>

          <div className={styles.statusCard}>
            <span>{consoleViewModel.stateLabel}</span>
            <strong>{message || currentStage.label}</strong>
          </div>
        </header>

        <main className={styles.content}>
          {viewMode === 'overview' ? (
            <SolutionOverview viewModel={overviewViewModel} />
          ) : (
            <>
              <section className={styles.heroCard}>
                <div className={styles.heroWatermark}>OVERVIEW</div>
                <div className={styles.heroCopy}>
                  <span className={styles.heroEyebrow}>TASK OVERVIEW</span>
                  <h2>围绕真实流量样本组织检测与归档</h2>
                  <p>
                    工作台保留现有上传、轮询和结果展示链路，同时把阶段进展、压降收益和威胁档案整合成控制台语义。
                  </p>
                </div>

                <div className={styles.heroStage}>
                  <span className={styles.heroStateBadge}>{consoleViewModel.stateLabel}</span>
                  <strong>{currentStage.label}</strong>
                  <p>{error || message || currentStage.detail}</p>
                </div>

                <div className={styles.heroMetrics}>
                  {consoleViewModel.heroMetrics.map((item) => (
                    <div key={item.label} className={styles.heroMetricCard}>
                      <span>{item.label}</span>
                      <strong>{item.value}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className={styles.workspace}>
                <div className={styles.workspaceColumn}>
                  <UploadWorkspace
                    disabled={appState === 'uploading' || appState === 'processing'}
                    isBusy={appState === 'uploading' || appState === 'processing'}
                    onUpload={handleUpload}
                  />

                  <div className={styles.noteCard}>
                    <span className={styles.noteLabel}>接口适配</span>
                    <p>当前页面继续使用现有 `uploadPcap`、`getTaskStatus`、`getTaskResult` 三个入口，不增加新的前后端契约。</p>
                  </div>
                </div>

                <div className={styles.workspaceColumn}>
                  <PipelinePanel
                    stage={stage}
                    progress={progress}
                    message={error || message}
                  />
                </div>
              </section>

              <section id="archive">
                <ResultArchive result={result} />
              </section>
            </>
          )}
        </main>

        {viewMode === 'console' && (
          <div className={styles.floatingBar}>
            <button type="button" className={styles.floatingGhost} onClick={() => setViewMode('overview')}>
              查看方案概览
            </button>
            <button type="button" className={styles.floatingGhost} onClick={handleReset}>
              重置工作台
            </button>
            <button
              type="button"
              className={styles.floatingPrimary}
              onClick={() => document.getElementById('archive')?.scrollIntoView({ behavior: 'smooth' })}
            >
              跳转结果归档
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
