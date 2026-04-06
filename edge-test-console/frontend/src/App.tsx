import { useCallback, useEffect, useRef, useState } from 'react'
import { getDemoSamples, getTaskResult, getTaskStatus, startDemoDetection, uploadPcap } from './api/client'
import styles from './App.module.css'
import { DemoSampleLibrary } from './components/DemoSampleLibrary'
import { OverviewBand } from './components/OverviewBand'
import { PipelinePanel } from './components/PipelinePanel'
import { ResultArchive } from './components/ResultArchive'
import { SidebarNav, type AppSection } from './components/SidebarNav'
import { TaskSummary } from './components/TaskSummary'
import { Topbar } from './components/Topbar'
import { UploadWorkspace } from './components/UploadWorkspace'
import { WorkflowChain } from './components/WorkflowChain'
import { buildConsoleViewModel, buildOverviewViewModel, type AppState } from './lib/view-models'
import type { DemoSample, DetectionResult, PipelineStage, SampleSource, TaskStatus } from './types/api'

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

export default function App() {
  const [section, setSection] = useState<AppSection>('overview')
  const [sampleSource, setSampleSource] = useState<SampleSource>('upload')
  const [appState, setAppState] = useState<AppState>('idle')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [stage, setStage] = useState<PipelineStage>('pending')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [demoSamples, setDemoSamples] = useState<DemoSample[]>([])
  const [demoSamplesLoaded, setDemoSamplesLoaded] = useState(false)
  const [demoSamplesLoading, setDemoSamplesLoading] = useState(false)
  const [demoSamplesError, setDemoSamplesError] = useState<string | null>(null)
  const [selectedDemoSampleId, setSelectedDemoSampleId] = useState<string | null>(null)
  const [demoSamplesRequestKey, setDemoSamplesRequestKey] = useState(0)
  const pollTimeoutRef = useRef<number | null>(null)
  const activeTaskRef = useRef<string | null>(null)
  const requestVersionRef = useRef(0)

  const clearPolling = useCallback(() => {
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current)
      pollTimeoutRef.current = null
    }
    activeTaskRef.current = null
  }, [])

  const invalidateRequests = useCallback(() => {
    requestVersionRef.current += 1
    clearPolling()
    setDemoSamplesLoading(false)
  }, [clearPolling])

  const pollStatus = useCallback(async (nextTaskId: string, requestVersion: number) => {
    activeTaskRef.current = nextTaskId
    let consecutiveErrors = 0

    const poll = async (): Promise<boolean> => {
      if (
        activeTaskRef.current !== nextTaskId ||
        requestVersionRef.current !== requestVersion
      ) {
        return true
      }

      try {
        const status: TaskStatus = await getTaskStatus(nextTaskId)
        consecutiveErrors = 0

        if (
          activeTaskRef.current !== nextTaskId ||
          requestVersionRef.current !== requestVersion
        ) {
          return true
        }

        setStage(status.stage)
        setProgress(status.progress)
        setMessage(status.message)

        if (status.stage === 'completed') {
          const resultData = await getTaskResult(nextTaskId)

          if (
            activeTaskRef.current !== nextTaskId ||
            requestVersionRef.current !== requestVersion
          ) {
            return true
          }

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
        if (
          activeTaskRef.current !== nextTaskId ||
          requestVersionRef.current !== requestVersion
        ) {
          return true
        }

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

      if (
        !done &&
        activeTaskRef.current === nextTaskId &&
        requestVersionRef.current === requestVersion
      ) {
        pollTimeoutRef.current = window.setTimeout(loop, 1000)
      }
    }

    await loop()
  }, [clearPolling])

  const handleUpload = useCallback(async (file: File): Promise<boolean> => {
    invalidateRequests()
    const requestVersion = requestVersionRef.current

    setSection('workspace')
    setAppState('uploading')
    setTaskId(null)
    setError(null)
    setResult(null)
    setProgress(0)
    setStage('pending')
    setMessage('样本已接收，正在创建检测任务。')

    try {
      const response = await uploadPcap(file)

      if (requestVersionRef.current !== requestVersion) {
        return false
      }

      setTaskId(response.task_id)
      setAppState('processing')
      setMessage(response.message || '任务已创建，等待进入流水线。')
      await pollStatus(response.task_id, requestVersion)
      return requestVersionRef.current === requestVersion
    } catch (uploadError) {
      if (requestVersionRef.current !== requestVersion) {
        return false
      }

      setAppState('failed')
      setError(uploadError instanceof Error ? uploadError.message : '样本上传失败')
      setMessage('样本上传未完成，请检查后端服务或重新尝试。')
      return false
    }
  }, [invalidateRequests, pollStatus])

  const handleDemoStart = useCallback(async (sampleId: string): Promise<boolean> => {
    invalidateRequests()
    const requestVersion = requestVersionRef.current

    setSection('workspace')
    setSampleSource('demo')
    setAppState('processing')
    setTaskId(null)
    setError(null)
    setResult(null)
    setProgress(0)
    setStage('pending')
    setMessage('演示样本已选择，正在创建检测任务。')

    try {
      const response = await startDemoDetection(sampleId)

      if (requestVersionRef.current !== requestVersion) {
        return false
      }

      setTaskId(response.task_id)
      setMessage(response.message || '演示任务已创建，等待进入流水线。')
      await pollStatus(response.task_id, requestVersion)
      return requestVersionRef.current === requestVersion
    } catch (demoError) {
      if (requestVersionRef.current !== requestVersion) {
        return false
      }

      setAppState('failed')
      setError(demoError instanceof Error ? demoError.message : '演示样本检测失败')
      setMessage('演示任务未能启动，请检查后端服务或重新尝试。')
      return false
    }
  }, [invalidateRequests, pollStatus])

  const handleReset = useCallback(() => {
    invalidateRequests()
    setTaskId(null)
    setSection('overview')
    setSampleSource('upload')
    setAppState('idle')
    setStage('pending')
    setProgress(0)
    setMessage('')
    setResult(null)
    setError(null)
    setDemoSamples([])
    setDemoSamplesLoaded(false)
    setDemoSamplesError(null)
    setSelectedDemoSampleId(null)
    setDemoSamplesRequestKey(0)
  }, [invalidateRequests])

  useEffect(() => {
    return () => {
      invalidateRequests()
    }
  }, [invalidateRequests])

  useEffect(() => {
    if (
      section !== 'workspace' ||
      sampleSource !== 'demo' ||
      demoSamplesRequestKey === 0
    ) {
      return
    }

    const requestVersion = requestVersionRef.current
    setDemoSamplesLoading(true)
    setDemoSamplesError(null)

    void getDemoSamples()
      .then((samples) => {
        if (requestVersionRef.current !== requestVersion) {
          return
        }

        setDemoSamples(samples)
        setSelectedDemoSampleId((currentSelected) => {
          if (currentSelected && samples.some((sample) => sample.id === currentSelected)) {
            return currentSelected
          }

          return samples[0]?.id ?? null
        })
        setDemoSamplesLoaded(true)
      })
      .catch((loadError) => {
        if (requestVersionRef.current !== requestVersion) {
          return
        }

        setDemoSamples([])
        setSelectedDemoSampleId(null)
        setDemoSamplesError(loadError instanceof Error ? loadError.message : '演示样本加载失败')
      })
      .finally(() => {
        if (requestVersionRef.current === requestVersion) {
          setDemoSamplesLoading(false)
        }
      })
  }, [demoSamplesRequestKey, sampleSource, section])

  const currentStage = STAGE_COPY[stage]
  const consoleViewModel = buildConsoleViewModel({
    appState,
    stage,
    message,
    result,
    error,
  })
  const overviewViewModel = buildOverviewViewModel(result)
  const busy = appState === 'uploading' || appState === 'processing'

  return (
    <div className={styles.shell}>
      <SidebarNav
        activeSection={section}
        onSelectSection={setSection}
        statusLabel={consoleViewModel.stateLabel}
      />

      <div className={styles.mainColumn}>
        <Topbar
          activeSection={section}
          statusLabel={consoleViewModel.stateLabel}
          stageLabel={message || currentStage.label}
          taskId={taskId}
          onArchive={() => setSection('archive')}
          onReset={handleReset}
          onWorkspace={() => setSection('workspace')}
        />

        <main className={styles.content}>
          {section === 'overview' && (
            <>
              <OverviewBand viewModel={overviewViewModel} />
              <div className={styles.panelGrid}>
                <WorkflowChain activeStage={stage} items={overviewViewModel.pipeline} />
                <TaskSummary
                  stateLabel={consoleViewModel.stateLabel}
                  stageLabel={currentStage.label}
                  stageDetail={error || message || currentStage.detail}
                  metrics={consoleViewModel.heroMetrics}
                />
              </div>
            </>
          )}

          {section === 'workspace' && (
            <section className={styles.workspaceSection} aria-labelledby="workspace-title">
              <div className={styles.sectionIntro}>
                <span className={styles.sectionEyebrow}>Edge Detection Workspace</span>
                <h2 id="workspace-title" className={styles.sectionTitle}>检测工作台</h2>
                <p className={styles.sectionLead}>
                  上传 pcap 样本后，任务会依次经过流重组、SVM 初筛和 LLM 研判，再把压降结果写入威胁归档。
                </p>
              </div>

              <div className={styles.workspaceGrid}>
                <div className={styles.workspaceColumn}>
                  <div className={styles.sourceSwitch}>
                    <div className={styles.sourceSwitchHeader}>
                      <span className={styles.panelEyebrow}>Sample Source</span>
                      <p>选择当前工作台的数据接入方式。</p>
                    </div>

                    <div className={styles.sourceRail} aria-label="工作台数据源">
                    <button
                      type="button"
                      className={`${styles.sourceTab} ${sampleSource === 'upload' ? styles.sourceTabActive : ''}`}
                      aria-label="本地上传"
                      aria-pressed={sampleSource === 'upload'}
                      onClick={() => setSampleSource('upload')}
                    >
                      <span className={styles.sourceTabLabel}>本地上传</span>
                      <span className={styles.sourceTabNote}>提交自有 pcap 样本，直接进入检测链路。</span>
                    </button>
                    <button
                      type="button"
                      className={`${styles.sourceTab} ${sampleSource === 'demo' ? styles.sourceTabActive : ''}`}
                      aria-label="演示样本"
                      aria-pressed={sampleSource === 'demo'}
                      onClick={() => {
                        setSampleSource('demo')
                        if (!demoSamplesLoaded || demoSamplesError) {
                          setDemoSamplesRequestKey((current) => current + 1)
                        }
                      }}
                    >
                      <span className={styles.sourceTabLabel}>演示样本</span>
                      <span className={styles.sourceTabNote}>调用内置流量包，快速展示完整状态回传。</span>
                    </button>
                  </div>
                  </div>

                  {sampleSource === 'upload' ? (
                    <UploadWorkspace
                      disabled={busy}
                      isBusy={busy}
                      onUpload={handleUpload}
                    />
                  ) : (
                    <DemoSampleLibrary
                      samples={demoSamples}
                      selectedSampleId={selectedDemoSampleId}
                      disabled={busy}
                      isBusy={busy}
                      isLoading={demoSamplesLoading}
                      error={demoSamplesError}
                      onSelect={setSelectedDemoSampleId}
                      onStart={handleDemoStart}
                    />
                  )}
                </div>

                <div className={styles.workspaceColumn}>
                  <TaskSummary
                    stateLabel={consoleViewModel.stateLabel}
                    stageLabel={currentStage.label}
                    stageDetail={error || message || currentStage.detail}
                    metrics={consoleViewModel.heroMetrics}
                  />
                  <PipelinePanel stage={stage} progress={progress} message={error || message} />
                </div>
              </div>
            </section>
          )}

          {section === 'archive' && (
            <section className={styles.archiveSection}>
              <div className={styles.sectionIntro}>
                <span className={styles.sectionEyebrow}>Threat Archive</span>
                <h2 className={styles.sectionTitle}>威胁归档</h2>
                <p className={styles.sectionLead}>
                  已完成任务会在这里汇总带宽压降、异常标签、五元组与处理耗时，便于复盘四容器检测闭环。
                </p>
              </div>

              <ResultArchive result={result} />
            </section>
          )}
        </main>
      </div>
    </div>
  )
}
