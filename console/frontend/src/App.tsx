import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getDemoSamples,
  getEdges,
  getEdgeReports,
  getLatestEdgeReport,
  getTaskResult,
  getTaskStatus,
  startDemoDetection,
  startEdgeAnalysis,
  startNetworkAnalysis,
  uploadPcap,
} from './api/client'
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
import type {
  DemoSample,
  DetectionResult,
  EdgeReportHistoryItem,
  EdgeLatestReport,
  EdgeSummary,
  NetworkAnalysisResult,
  PipelineStage,
  SampleSource,
  TaskStatus,
} from './types/api'

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

function formatTimestamp(value: string | null): string {
  if (!value) return '暂无'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function mergeReportHistory(
  latestReport: EdgeLatestReport | null,
  historyReports: EdgeReportHistoryItem[],
): EdgeReportHistoryItem[] {
  const reportMap = new Map<string, EdgeReportHistoryItem>()

  if (latestReport) {
    reportMap.set(latestReport.report_id, latestReport)
  }

  for (const report of historyReports) {
    reportMap.set(report.report_id, report)
  }

  return Array.from(reportMap.values()).sort(
    (left, right) => new Date(right.generated_at).getTime() - new Date(left.generated_at).getTime(),
  )
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
  const [edges, setEdges] = useState<EdgeSummary[]>([])
  const [edgesLoading, setEdgesLoading] = useState(true)
  const [edgesError, setEdgesError] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [selectedEdgeReport, setSelectedEdgeReport] = useState<EdgeLatestReport | null>(null)
  const [selectedEdgeReportId, setSelectedEdgeReportId] = useState<string | null>(null)
  const [edgeReports, setEdgeReports] = useState<EdgeReportHistoryItem[]>([])
  const [edgeReportLoading, setEdgeReportLoading] = useState(false)
  const [edgeReportError, setEdgeReportError] = useState<string | null>(null)
  const [edgeReportsLoading, setEdgeReportsLoading] = useState(false)
  const [edgeReportsError, setEdgeReportsError] = useState<string | null>(null)
  const [edgeAnalyzeBusy, setEdgeAnalyzeBusy] = useState(false)
  const [networkAnalysis, setNetworkAnalysis] = useState<NetworkAnalysisResult | null>(null)
  const [networkAnalyzeBusy, setNetworkAnalyzeBusy] = useState(false)
  const [networkAnalysisError, setNetworkAnalysisError] = useState<string | null>(null)
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

  const pollStatus = useCallback(
    async (nextTaskId: string, requestVersion: number) => {
      activeTaskRef.current = nextTaskId
      let consecutiveErrors = 0

      const poll = async (): Promise<boolean> => {
        if (activeTaskRef.current !== nextTaskId || requestVersionRef.current !== requestVersion) {
          return true
        }

        try {
          const status: TaskStatus = await getTaskStatus(nextTaskId)
          consecutiveErrors = 0

          if (activeTaskRef.current !== nextTaskId || requestVersionRef.current !== requestVersion) {
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
          if (activeTaskRef.current !== nextTaskId || requestVersionRef.current !== requestVersion) {
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
        if (!done && activeTaskRef.current === nextTaskId && requestVersionRef.current === requestVersion) {
          pollTimeoutRef.current = window.setTimeout(loop, 1000)
        }
      }

      await loop()
    },
    [clearPolling],
  )

  const handleUpload = useCallback(
    async (file: File): Promise<boolean> => {
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
        if (requestVersionRef.current !== requestVersion) return false

        setTaskId(response.task_id)
        setAppState('processing')
        setMessage(response.message || '任务已创建，等待进入流水线。')
        await pollStatus(response.task_id, requestVersion)
        return requestVersionRef.current === requestVersion
      } catch (uploadError) {
        if (requestVersionRef.current !== requestVersion) return false

        setAppState('failed')
        setError(uploadError instanceof Error ? uploadError.message : '样本上传失败')
        setMessage('样本上传未完成，请检查后端服务或重新尝试。')
        return false
      }
    },
    [invalidateRequests, pollStatus],
  )

  const handleDemoStart = useCallback(
    async (sampleId: string): Promise<boolean> => {
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
        if (requestVersionRef.current !== requestVersion) return false

        setTaskId(response.task_id)
        setMessage(response.message || '演示任务已创建，等待进入流水线。')
        await pollStatus(response.task_id, requestVersion)
        return requestVersionRef.current === requestVersion
      } catch (demoError) {
        if (requestVersionRef.current !== requestVersion) return false

        setAppState('failed')
        setError(demoError instanceof Error ? demoError.message : '演示样本检测失败')
        setMessage('演示任务未能启动，请检查后端服务或重新尝试。')
        return false
      }
    },
    [invalidateRequests, pollStatus],
  )

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
    void getEdges()
      .then((edgeItems) => {
        setEdges(edgeItems)
        setSelectedEdgeId((currentSelected) => currentSelected ?? edgeItems[0]?.edge_id ?? null)
        setEdgesError(null)
      })
      .catch((loadError) => {
        setEdges([])
        setSelectedEdgeId(null)
        setEdgesError(loadError instanceof Error ? loadError.message : 'Edge 列表加载失败')
      })
      .finally(() => {
        setEdgesLoading(false)
      })
  }, [])

  useEffect(() => {
    if (!selectedEdgeId) {
      setSelectedEdgeReport(null)
      setSelectedEdgeReportId(null)
      setEdgeReports([])
      return
    }

    let cancelled = false

    setEdgeReportLoading(true)
    setEdgeReportError(null)
    setEdgeReportsLoading(true)
    setEdgeReportsError(null)
    setSelectedEdgeReport(null)
    setSelectedEdgeReportId(null)
    setEdgeReports([])

    void Promise.allSettled([
      getLatestEdgeReport(selectedEdgeId),
      getEdgeReports(selectedEdgeId),
    ])
      .then(([latestResult, historyResult]) => {
        if (cancelled) return

        const latestReport =
          latestResult.status === 'fulfilled' ? latestResult.value : null
        const historyReports =
          historyResult.status === 'fulfilled' ? historyResult.value : []
        const mergedReports = mergeReportHistory(latestReport, historyReports)
        const displayedReport = latestReport ?? mergedReports[0] ?? null

        if (latestResult.status === 'rejected') {
          setEdgeReportError(
            latestResult.reason instanceof Error
              ? latestResult.reason.message
              : '最新情报加载失败',
          )
        } else {
          setEdgeReportError(null)
        }

        if (historyResult.status === 'rejected') {
          setEdgeReportsError(
            historyResult.reason instanceof Error
              ? historyResult.reason.message
              : '历史报告加载失败',
          )
        } else {
          setEdgeReportsError(null)
        }

        setEdgeReports(mergedReports)
        setSelectedEdgeReport(displayedReport)
        setSelectedEdgeReportId(displayedReport?.report_id ?? null)
      })
      .finally(() => {
        if (!cancelled) {
          setEdgeReportLoading(false)
          setEdgeReportsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selectedEdgeId])

  useEffect(() => {
    if (section !== 'workspace' || sampleSource !== 'demo' || demoSamplesRequestKey === 0) {
      return
    }

    const requestVersion = requestVersionRef.current
    setDemoSamplesLoading(true)
    setDemoSamplesError(null)

    void getDemoSamples()
      .then((samples) => {
        if (requestVersionRef.current !== requestVersion) return

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
        if (requestVersionRef.current !== requestVersion) return

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

  useEffect(() => {
    return () => {
      invalidateRequests()
    }
  }, [invalidateRequests])

  const handleEdgeAnalyze = useCallback(async () => {
    if (!selectedEdgeId) return

    setEdgeAnalyzeBusy(true)
    setEdgeReportError(null)

    try {
      const report = await startEdgeAnalysis(selectedEdgeId)
      let historyReports: EdgeReportHistoryItem[] = []

      try {
        historyReports = await getEdgeReports(selectedEdgeId)
        setEdgeReportsError(null)
      } catch (historyError) {
        setEdgeReportsError(
          historyError instanceof Error ? historyError.message : '历史报告加载失败',
        )
      }

      const mergedReports = mergeReportHistory(
        report,
        historyReports.length > 0 ? historyReports : edgeReports,
      )

      setSelectedEdgeReport(report)
      setSelectedEdgeReportId(report.report_id)
      setEdgeReports(mergedReports)
      setEdges((currentEdges) =>
        currentEdges.map((edge) =>
          edge.edge_id === selectedEdgeId
            ? {
                ...edge,
                threat_count: report.summary.threat_count,
                risk_level: report.summary.risk_level,
                last_reported_at: report.generated_at,
              }
            : edge,
        ),
      )
    } catch (analysisError) {
      setEdgeReportError(analysisError instanceof Error ? analysisError.message : '单 edge 分析失败')
    } finally {
      setEdgeAnalyzeBusy(false)
    }
  }, [edgeReports, selectedEdgeId])

  const handleNetworkAnalyze = useCallback(async () => {
    setNetworkAnalyzeBusy(true)
    setNetworkAnalysisError(null)

    try {
      const analysis = await startNetworkAnalysis()
      setNetworkAnalysis(analysis)
    } catch (analysisError) {
      setNetworkAnalysisError(
        analysisError instanceof Error ? analysisError.message : '全网综合研判失败',
      )
    } finally {
      setNetworkAnalyzeBusy(false)
    }
  }, [])

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
  const activeEdge = edges.find((edge) => edge.edge_id === selectedEdgeId) ?? null
  const controlPlaneStatus = edgesLoading
    ? '控制面加载中'
    : edgesError
      ? '控制面异常'
      : `${edges.length} 个 edge 在线视图`

  return (
    <div className={styles.shell}>
      <SidebarNav
        activeSection={section}
        onSelectSection={setSection}
        statusLabel={controlPlaneStatus}
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
          <section className={styles.controlPlaneSection} aria-labelledby="control-plane-title">
            <div className={styles.sectionIntro}>
              <span className={styles.sectionEyebrow}>Central Agent Control Plane</span>
              <h2 id="control-plane-title" className={styles.sectionTitle}>控制面</h2>
              <p className={styles.sectionLead}>
                统一查看 edge 清单、最新情报、单 edge 分析结果，以及全网综合研判摘要。
              </p>
            </div>

            <div className={styles.controlPlaneGrid}>
              <section className={styles.panel} aria-label="edge inventory">
                <div className={styles.panelHeader}>
                  <span className={styles.panelEyebrow}>Edge Inventory</span>
                  <h3>边缘节点列表</h3>
                </div>
                <div className={styles.edgeList}>
                  {edgesLoading && <div className={styles.emptyState}>正在加载 edge 列表...</div>}
                  {!edgesLoading && edgesError && <div className={styles.emptyState}>{edgesError}</div>}
                  {!edgesLoading &&
                    !edgesError &&
                    edges.map((edge) => {
                      const active = edge.edge_id === selectedEdgeId
                      return (
                        <button
                          key={edge.edge_id}
                          type="button"
                          className={`${styles.edgeCard} ${active ? styles.edgeCardActive : ''}`}
                          aria-label={`选择 ${edge.display_name}`}
                          onClick={() => setSelectedEdgeId(edge.edge_id)}
                        >
                          <div className={styles.edgeCardTop}>
                            <strong>{edge.display_name}</strong>
                            <span className={styles.edgeBadge}>{edge.status}</span>
                          </div>
                          <span>{edge.location}</span>
                          <span>
                            风险 {edge.risk_level} · 威胁 {edge.threat_count}
                          </span>
                          <span>最新上报 {formatTimestamp(edge.last_reported_at)}</span>
                        </button>
                      )
                    })}
                </div>
              </section>

              <section className={styles.panel} aria-label="edge intelligence">
                <div className={styles.panelHeader}>
                  <span className={styles.panelEyebrow}>Selected Edge</span>
                  <h3>最新情报</h3>
                </div>
                <div className={styles.summaryMetrics}>
                  <div className={styles.metricTile}>
                    <span>当前选择</span>
                    <strong>{activeEdge?.display_name ?? '未选择 edge'}</strong>
                  </div>
                  <div className={styles.metricTile}>
                    <span>风险等级</span>
                    <strong>{selectedEdgeReport?.summary.risk_level ?? activeEdge?.risk_level ?? '暂无'}</strong>
                  </div>
                  <div className={styles.metricTile}>
                    <span>威胁数量</span>
                    <strong>{selectedEdgeReport?.summary.threat_count ?? activeEdge?.threat_count ?? 0}</strong>
                  </div>
                </div>
                <div className={styles.controlActions}>
                  <button
                    type="button"
                    className={styles.primaryAction}
                    onClick={handleEdgeAnalyze}
                    disabled={!selectedEdgeId || edgeAnalyzeBusy}
                  >
                    {edgeAnalyzeBusy ? '单 edge 分析中...' : '触发单 edge 分析'}
                  </button>
                  <button
                    type="button"
                    className={styles.secondaryAction}
                    onClick={handleNetworkAnalyze}
                    disabled={networkAnalyzeBusy}
                  >
                    {networkAnalyzeBusy ? '全网研判中...' : '触发全网综合研判'}
                  </button>
                </div>
                {edgeReportLoading && <div className={styles.emptyState}>最新情报加载中...</div>}
                {edgeReportError && <div className={styles.emptyState}>{edgeReportError}</div>}
                {!edgeReportLoading && edgeReportsLoading && (
                  <div className={styles.emptyState}>历史报告加载中...</div>
                )}
                {edgeReportsError && <div className={styles.emptyState}>{edgeReportsError}</div>}
                {selectedEdgeReport && !edgeReportLoading && (
                  <div className={styles.reportSummary}>
                    <strong>{selectedEdgeReport.summary.headline}</strong>
                    <span>生成时间 {formatTimestamp(selectedEdgeReport.generated_at)}</span>
                    <span>历史归档 {edgeReports.length}</span>
                    <span>
                      带宽压降 {selectedEdgeReport.summary.bandwidth_saved_percent.toFixed(1)}%
                    </span>
                    <span>
                      处理耗时 {(selectedEdgeReport.report.meta.processing_time_ms / 1000).toFixed(2)}s
                    </span>
                  </div>
                )}
              </section>
            </div>

            <section className={styles.panel} aria-label="network analysis">
              <div className={styles.panelHeader}>
                <span className={styles.panelEyebrow}>Network Analysis</span>
                <h3>全网综合研判</h3>
              </div>
              {networkAnalysisError && <div className={styles.emptyState}>{networkAnalysisError}</div>}
              {!networkAnalysis && !networkAnalysisError && (
                <div className={styles.emptyState}>手动触发后将在这里显示综合研判结果。</div>
              )}
              {networkAnalysis && (
                <>
                  <div className={styles.summaryMetrics}>
                    <div className={styles.metricTile}>
                      <span>Edge 总数</span>
                      <strong>{networkAnalysis.summary.edge_count}</strong>
                    </div>
                    <div className={styles.metricTile}>
                      <span>告警节点</span>
                      <strong>{networkAnalysis.summary.edges_with_alerts}</strong>
                    </div>
                    <div className={styles.metricTile}>
                      <span>威胁总数</span>
                      <strong>{networkAnalysis.summary.total_threats}</strong>
                    </div>
                  </div>
                  <div className={styles.reportSummary}>
                    <strong>{networkAnalysis.summary.recommended_action}</strong>
                    <span>最高风险 edge: {networkAnalysis.summary.highest_risk_edge}</span>
                    <span>生成时间 {formatTimestamp(networkAnalysis.generated_at)}</span>
                  </div>
                  <div className={styles.networkEdgeGrid}>
                    {networkAnalysis.edges.map((edge) => (
                      <div key={edge.edge_id} className={styles.networkEdgeCard}>
                        <strong>{edge.display_name}</strong>
                        <span>风险 {edge.risk_level}</span>
                        <span>威胁 {edge.threat_count}</span>
                        <span>时间 {formatTimestamp(edge.generated_at)}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </section>
          </section>

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
                <span className={styles.sectionEyebrow}>Edge Agent Workspace</span>
                <h2 id="workspace-title" className={styles.sectionTitle}>检测工作台</h2>
                <p className={styles.sectionLead}>
                  保留上传与演示检测工作台，用于直接调用 edge-agent 检测入口并跟踪阶段回传。
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
                    <UploadWorkspace disabled={busy} isBusy={busy} onUpload={handleUpload} />
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
                  已完成任务会在这里汇总带宽压降、异常标签、五元组与处理耗时，便于复盘检测闭环。
                </p>
              </div>

              <ResultArchive
                result={result ?? selectedEdgeReport?.report ?? null}
                reportHistory={result ? [] : edgeReports}
                selectedReportId={result ? null : selectedEdgeReportId}
                reportHistoryLoading={!result && edgeReportsLoading}
                reportHistoryError={!result ? edgeReportsError : null}
                onSelectReport={(reportId) => {
                  const report = edgeReports.find((item) => item.report_id === reportId)
                  if (!report) return
                  setSelectedEdgeReport(report)
                  setSelectedEdgeReportId(reportId)
                }}
              />
            </section>
          )}
        </main>
      </div>
    </div>
  )
}
