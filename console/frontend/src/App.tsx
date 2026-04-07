import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react'
import {
  analyzeEdge,
  analyzeNetwork,
  getDemoSamples,
  getEdgeAnalysis,
  getEdgeReport,
  getEdges,
  getNetworkAnalysis,
  getTaskResult,
  getTaskStatus,
  startDemoDetection,
  uploadPcap,
} from './api/client'
import styles from './App.module.css'
import { SidebarNav, type AppSection } from './components/SidebarNav'
import { Topbar } from './components/Topbar'
import type {
  DemoSample,
  DetectionResult,
  EdgeAnalysis,
  EdgeIntelligenceReport,
  EdgeRegistryItem,
  NetworkAnalysis,
  PipelineStage,
  TaskStatus,
} from './types/api'

const STAGE_COPY: Record<PipelineStage, { label: string; detail: string }> = {
  pending: { label: '待命队列', detail: '等待新的流量样本进入 edge-agent。' },
  flow_reconstruction: { label: '流重组', detail: '基于五元组进行会话重建与截断。' },
  svm_filtering: { label: 'SVM 初筛', detail: '快速丢弃正常流量，降低后续推理成本。' },
  llm_inference: { label: 'LLM 推理', detail: '对异常候选完成边缘侧语义分类。' },
  completed: { label: '结果归档', detail: '边缘检测已完成，可查看归档结果。' },
  failed: { label: '流程失败', detail: '当前任务中断，需要重新提交样本。' },
}

function formatTimestamp(value?: string | null): string {
  if (!value) {
    return '暂无'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatThreatLevel(value?: string | null): string {
  return value ? value.toUpperCase() : 'IDLE'
}

export default function App() {
  const [section, setSection] = useState<AppSection>('overview')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [stage, setStage] = useState<PipelineStage>('pending')
  const [message, setMessage] = useState('等待提交新的边缘检测任务。')
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [demoSamples, setDemoSamples] = useState<DemoSample[]>([])
  const [demoLoading, setDemoLoading] = useState(false)
  const [edgeList, setEdgeList] = useState<EdgeRegistryItem[]>([])
  const [edgeListLoading, setEdgeListLoading] = useState(false)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [selectedEdgeReport, setSelectedEdgeReport] = useState<EdgeIntelligenceReport | null>(null)
  const [selectedEdgeAnalysis, setSelectedEdgeAnalysis] = useState<EdgeAnalysis | null>(null)
  const [networkAnalysis, setNetworkAnalysis] = useState<NetworkAnalysis | null>(null)
  const [centralMessage, setCentralMessage] = useState('请选择一个 edge 查看归档情报。')
  const [centralError, setCentralError] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<'edge' | 'network' | null>(null)
  const pollTimeoutRef = useRef<number | null>(null)

  const clearPolling = useCallback(() => {
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current)
      pollTimeoutRef.current = null
    }
  }, [])

  const loadDemoSamples = useCallback(async () => {
    setDemoLoading(true)
    try {
      const samples = await getDemoSamples()
      setDemoSamples(samples)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '演示样本加载失败')
    } finally {
      setDemoLoading(false)
    }
  }, [])

  const loadEdgeRegistry = useCallback(async () => {
    setEdgeListLoading(true)
    try {
      const edges = await getEdges()
      setEdgeList(edges)

      setSelectedEdgeId((current) => {
        if (edges.length === 0) {
          return null
        }
        if (current && edges.some((item) => item.edge_id === current)) {
          return current
        }
        return edges[0].edge_id
      })
    } catch (loadError) {
      setCentralError(loadError instanceof Error ? loadError.message : 'Edge 列表加载失败')
    } finally {
      setEdgeListLoading(false)
    }
  }, [])

  const loadSelectedEdge = useCallback(async (edgeId: string) => {
    setCentralError(null)

    try {
      const report = await getEdgeReport(edgeId)
      setSelectedEdgeReport(report)
      setCentralMessage(`已载入 ${edgeId} 的最新结构化情报。`)
    } catch (loadError) {
      setSelectedEdgeReport(null)
      setSelectedEdgeAnalysis(null)
      setCentralError(loadError instanceof Error ? loadError.message : 'Edge 情报加载失败')
      return
    }

    try {
      const analysis = await getEdgeAnalysis(edgeId)
      setSelectedEdgeAnalysis(analysis)
    } catch {
      setSelectedEdgeAnalysis(null)
    }
  }, [])

  const loadNetworkAnalysisState = useCallback(async () => {
    try {
      const analysis = await getNetworkAnalysis()
      setNetworkAnalysis(analysis)
    } catch {
      setNetworkAnalysis(null)
    }
  }, [])

  const pollStatus = useCallback(async (nextTaskId: string) => {
    clearPolling()

    const runPoll = async (): Promise<void> => {
      try {
        const status: TaskStatus = await getTaskStatus(nextTaskId)
        setStage(status.stage)
        setMessage(status.message)

        if (status.stage === 'completed') {
          const resultPayload = await getTaskResult(nextTaskId)
          setResult(resultPayload)
          clearPolling()
          return
        }

        if (status.stage === 'failed') {
          setError(status.message)
          clearPolling()
          return
        }
      } catch (pollError) {
        setError(pollError instanceof Error ? pollError.message : '任务状态获取失败')
        clearPolling()
        return
      }

      pollTimeoutRef.current = window.setTimeout(runPoll, 1000)
    }

    await runPoll()
  }, [clearPolling])

  const startDetection = useCallback(async (runner: () => Promise<{ task_id: string; message: string }>) => {
    clearPolling()
    setSection('edge')
    setError(null)
    setResult(null)
    setStage('pending')
    setMessage('正在创建新的 edge-agent 检测任务。')

    try {
      const response = await runner()
      setTaskId(response.task_id)
      setMessage(response.message)
      await pollStatus(response.task_id)
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : '检测任务启动失败')
    }
  }, [clearPolling, pollStatus])

  const handleUpload = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    await startDetection(() => uploadPcap(file))
    event.target.value = ''
  }, [startDetection])

  const handleDemoStart = useCallback(async (sampleId: string) => {
    await startDetection(() => startDemoDetection(sampleId))
  }, [startDetection])

  const handleAnalyzeEdge = useCallback(async () => {
    if (!selectedEdgeId) {
      return
    }

    setBusyAction('edge')
    setCentralError(null)
    try {
      const analysis = await analyzeEdge(selectedEdgeId)
      setSelectedEdgeAnalysis(analysis)
      setCentralMessage(`${selectedEdgeId} 的中心分析已更新。`)
      await loadEdgeRegistry()
    } catch (analyzeError) {
      setCentralError(analyzeError instanceof Error ? analyzeError.message : '单 Edge 分析失败')
    } finally {
      setBusyAction(null)
    }
  }, [loadEdgeRegistry, selectedEdgeId])

  const handleAnalyzeNetwork = useCallback(async () => {
    setBusyAction('network')
    setCentralError(null)
    try {
      const analysis = await analyzeNetwork()
      setNetworkAnalysis(analysis)
      setCentralMessage('全网综合研判结果已更新。')
    } catch (analyzeError) {
      setCentralError(analyzeError instanceof Error ? analyzeError.message : '全网综合研判失败')
    } finally {
      setBusyAction(null)
    }
  }, [])

  const handleRefreshAll = useCallback(async () => {
    await Promise.all([loadDemoSamples(), loadEdgeRegistry(), loadNetworkAnalysisState()])
  }, [loadDemoSamples, loadEdgeRegistry, loadNetworkAnalysisState])

  useEffect(() => {
    void handleRefreshAll()

    return () => {
      clearPolling()
    }
  }, [clearPolling, handleRefreshAll])

  useEffect(() => {
    if (!selectedEdgeId) {
      setSelectedEdgeReport(null)
      setSelectedEdgeAnalysis(null)
      return
    }

    void loadSelectedEdge(selectedEdgeId)
  }, [loadSelectedEdge, selectedEdgeId])

  const stageCopy = STAGE_COPY[stage]
  const statusLabel = error ? 'Edge Failed' : result ? 'Edge Ready' : busyAction ? 'Central Busy' : 'Online'
  const detailLabel = section === 'central' ? centralMessage : stageCopy.label

  return (
    <div className={styles.shell}>
      <SidebarNav activeSection={section} onSelectSection={setSection} statusLabel={statusLabel} />

      <main className={styles.mainColumn}>
        <Topbar
          activeSection={section}
          statusLabel={statusLabel}
          detailLabel={detailLabel}
          selectedEdgeId={selectedEdgeId}
          onShowEdge={() => setSection('edge')}
          onShowCentral={() => setSection('central')}
          onReset={() => void handleRefreshAll()}
        />

        <div className={styles.content}>
          {section === 'overview' && (
            <section className={styles.overviewBand}>
              <div className={styles.overviewHero}>
                <div className={styles.sectionIntro}>
                  <span className={styles.sectionEyebrow}>Phase 1 Architecture</span>
                  <h3 className={styles.sectionTitle}>统一控制台 + 边缘检测 + 中心研判</h3>
                  <p className={styles.sectionLead}>
                    当前阶段只允许 edge-agent 向 central-agent 上传结构化 JSON 情报，禁止任何原始 pcap、
                    payload 或完整十六进制包上云，以确保核心网上行带宽压降目标继续成立。
                  </p>
                </div>

                <div className={styles.metricStrip}>
                  <div className={styles.metricTile}>
                    <span>Bandwidth KPI</span>
                    <strong>{result?.metrics.bandwidth_saved_percent ?? 70}%+</strong>
                  </div>
                  <div className={styles.metricTile}>
                    <span>Known Edges</span>
                    <strong>{edgeList.length}</strong>
                  </div>
                  <div className={styles.metricTile}>
                    <span>Selected Edge</span>
                    <strong>{selectedEdgeId ?? 'none'}</strong>
                  </div>
                </div>
              </div>

              <div className={styles.panelGrid}>
                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelEyebrow}>Control Plane</span>
                    <h3>调用边界</h3>
                  </div>
                  <div className={styles.stackList}>
                    <div className={styles.stackCard}>
                        <strong>console {'->'} edge-agent</strong>
                      <span>上传 pcap、查看检测状态与边缘结果。</span>
                    </div>
                    <div className={styles.stackCard}>
                        <strong>console {'->'} central-agent</strong>
                      <span>查看 edge 情报、单 Edge 分析、手动触发全网综合研判。</span>
                    </div>
                    <div className={styles.stackCard}>
                        <strong>edge-agent {'->'} central-agent</strong>
                      <span>仅允许上报 EdgeIntelligenceReport，不允许原始包上云。</span>
                    </div>
                  </div>
                </article>

                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelEyebrow}>Central Registry</span>
                    <h3>已注册边缘节点</h3>
                  </div>
                  <div className={styles.edgeRoster}>
                    {edgeListLoading && <p className={styles.mutedText}>正在载入 edge 列表...</p>}
                    {!edgeListLoading && edgeList.length === 0 && (
                      <p className={styles.mutedText}>尚无 edge 上报到 central-agent。</p>
                    )}
                    {edgeList.map((edge) => (
                      <button
                        key={edge.edge_id}
                        type="button"
                        className={`${styles.edgeRow} ${selectedEdgeId === edge.edge_id ? styles.edgeRowActive : ''}`}
                        onClick={() => {
                          setSelectedEdgeId(edge.edge_id)
                          setSection('central')
                        }}
                      >
                        <strong>{edge.edge_id}</strong>
                        <span>{edge.report_count} reports</span>
                        <span>{formatThreatLevel(edge.latest_threat_level)}</span>
                      </button>
                    ))}
                  </div>
                </article>
              </div>
            </section>
          )}

          {section === 'edge' && (
            <section className={styles.workspaceSection}>
              <div className={styles.workspaceGrid}>
                <div className={styles.workspaceColumn}>
                  <article className={styles.panel}>
                    <div className={styles.panelHeader}>
                      <span className={styles.panelEyebrow}>Edge-Agent Input</span>
                      <h3>上传样本</h3>
                    </div>
                    <label className={styles.fileDrop}>
                      <span>选择 `.pcap` 或 `.pcapng` 文件提交到 edge-agent</span>
                      <input type="file" accept=".pcap,.pcapng" onChange={handleUpload} />
                    </label>
                  </article>

                  <article className={styles.panel}>
                    <div className={styles.panelHeader}>
                      <span className={styles.panelEyebrow}>Demo Library</span>
                      <h3>演示样本</h3>
                    </div>
                    <div className={styles.demoList}>
                      {demoLoading && <p className={styles.mutedText}>正在载入演示样本...</p>}
                      {demoSamples.map((sample) => (
                        <button
                          key={sample.id}
                          type="button"
                          className={styles.demoItem}
                          onClick={() => void handleDemoStart(sample.id)}
                        >
                          <strong>{sample.display_name}</strong>
                          <span>{sample.filename}</span>
                        </button>
                      ))}
                    </div>
                  </article>
                </div>

                <div className={styles.workspaceColumn}>
                  <article className={styles.panel}>
                    <div className={styles.panelHeader}>
                      <span className={styles.panelEyebrow}>Pipeline State</span>
                      <h3>{stageCopy.label}</h3>
                    </div>
                    <p className={styles.sectionLead}>{stageCopy.detail}</p>
                    <p className={styles.mutedText}>{message}</p>
                    <p className={styles.mutedText}>{taskId ? `任务编号：${taskId}` : '尚未启动任务'}</p>
                  </article>

                  <article className={styles.panel}>
                    <div className={styles.panelHeader}>
                      <span className={styles.panelEyebrow}>Detection Output</span>
                      <h3>边缘检测结果</h3>
                    </div>
                    {result ? (
                      <div className={styles.resultGrid}>
                        <div className={styles.metricTile}>
                          <span>异常流数量</span>
                          <strong>{result.statistics.anomaly_flows_detected}</strong>
                        </div>
                        <div className={styles.metricTile}>
                          <span>SVM 过滤率</span>
                          <strong>{result.statistics.svm_filter_rate}</strong>
                        </div>
                        <div className={styles.metricTile}>
                          <span>带宽压降</span>
                          <strong>{result.statistics.bandwidth_reduction}</strong>
                        </div>
                        <div className={styles.resultList}>
                          {result.threats.map((threat) => (
                            <div key={threat.id} className={styles.resultItem}>
                              <strong>{threat.classification.primary_label}</strong>
                              <span>
                                {threat.five_tuple.src_ip}:{threat.five_tuple.src_port} {'->'} {threat.five_tuple.dst_ip}:
                                {threat.five_tuple.dst_port}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className={styles.mutedText}>边缘结果尚未生成。</p>
                    )}
                  </article>
                </div>
              </div>
            </section>
          )}

          {section === 'central' && (
            <section className={styles.archiveSection}>
              <div className={styles.panelGrid}>
                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelEyebrow}>Edge Selector</span>
                    <h3>选择边缘节点</h3>
                  </div>
                  <div className={styles.edgeRoster}>
                    {edgeList.map((edge) => (
                      <button
                        key={edge.edge_id}
                        type="button"
                        className={`${styles.edgeRow} ${selectedEdgeId === edge.edge_id ? styles.edgeRowActive : ''}`}
                        onClick={() => setSelectedEdgeId(edge.edge_id)}
                      >
                        <strong>{edge.edge_id}</strong>
                        <span>reports: {edge.report_count}</span>
                        <span>analysis: {edge.latest_analysis_status}</span>
                      </button>
                    ))}
                  </div>
                </article>

                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelEyebrow}>Manual Actions</span>
                    <h3>中心侧控制</h3>
                  </div>
                  <div className={styles.actionStack}>
                    <button
                      type="button"
                      className={styles.primaryAction}
                      disabled={!selectedEdgeId || busyAction !== null}
                      onClick={() => void handleAnalyzeEdge()}
                    >
                      {busyAction === 'edge' ? '正在分析单 Edge...' : `分析 ${selectedEdgeId ?? 'edge'}`}
                    </button>
                    <button
                      type="button"
                      className={styles.secondaryAction}
                      disabled={busyAction !== null}
                      onClick={() => void handleAnalyzeNetwork()}
                    >
                      {busyAction === 'network' ? '正在进行全网研判...' : '手动触发全网综合研判'}
                    </button>
                    <p className={styles.mutedText}>{centralMessage}</p>
                    {centralError && <p className={styles.errorText}>{centralError}</p>}
                  </div>
                </article>
              </div>

              <div className={styles.panelGrid}>
                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelEyebrow}>Latest Edge Report</span>
                    <h3>{selectedEdgeId ?? '未选中 edge'}</h3>
                  </div>
                  {selectedEdgeReport ? (
                    <div className={styles.resultGrid}>
                      <div className={styles.metricTile}>
                        <span>报告编号</span>
                        <strong>{selectedEdgeReport.report_id}</strong>
                      </div>
                      <div className={styles.metricTile}>
                        <span>上报时间</span>
                        <strong>{formatTimestamp(selectedEdgeReport.producer.reported_at)}</strong>
                      </div>
                      <div className={styles.metricTile}>
                        <span>威胁条目</span>
                        <strong>{selectedEdgeReport.threats.length}</strong>
                      </div>
                      <div className={styles.resultList}>
                        {selectedEdgeReport.threats.map((threat) => (
                          <div key={threat.threat_id} className={styles.resultItem}>
                            <strong>{threat.edge_classification?.primary_label ?? 'unknown'}</strong>
                            <span>
                                {threat.five_tuple.src_ip}:{threat.five_tuple.src_port} {'->'} {threat.five_tuple.dst_ip}:
                              {threat.five_tuple.dst_port}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className={styles.mutedText}>当前 edge 还没有可读取的结构化情报。</p>
                  )}
                </article>

                <article className={styles.panel}>
                  <div className={styles.panelHeader}>
                    <span className={styles.panelEyebrow}>Single-Edge Analysis</span>
                    <h3>中心侧单 Edge 研判</h3>
                  </div>
                  {selectedEdgeAnalysis ? (
                    <div className={styles.analysisCard}>
                      <div className={styles.analysisHeader}>
                        <strong>{formatThreatLevel(selectedEdgeAnalysis.threat_level)}</strong>
                        <span>{selectedEdgeAnalysis.analysis_state}</span>
                      </div>
                      <p>{selectedEdgeAnalysis.summary}</p>
                      <p className={styles.mutedText}>{selectedEdgeAnalysis.analysis}</p>
                      <ul className={styles.analysisList}>
                        {selectedEdgeAnalysis.recommendations.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <p className={styles.mutedText}>当前 edge 尚未执行中心侧分析。</p>
                  )}
                </article>
              </div>

              <article className={styles.panel}>
                <div className={styles.panelHeader}>
                  <span className={styles.panelEyebrow}>Network-Wide Analysis</span>
                  <h3>全网综合研判</h3>
                </div>
                {networkAnalysis ? (
                  <div className={styles.analysisCard}>
                    <div className={styles.analysisHeader}>
                      <strong>{formatThreatLevel(networkAnalysis.threat_level)}</strong>
                      <span>{networkAnalysis.edge_count} edges covered</span>
                    </div>
                    <p>{networkAnalysis.summary}</p>
                    <p className={styles.mutedText}>{networkAnalysis.analysis}</p>
                    <ul className={styles.analysisList}>
                      {networkAnalysis.recommendations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className={styles.mutedText}>尚未触发全网综合研判。</p>
                )}
              </article>
            </section>
          )}

          {error && (
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.panelEyebrow}>Runtime Notice</span>
                <h3>当前任务报错</h3>
              </div>
              <p className={styles.errorText}>{error}</p>
            </article>
          )}
        </div>
      </main>
    </div>
  )
}
