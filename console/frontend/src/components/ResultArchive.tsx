import type { DetectionResult, EdgeReportHistoryItem } from '../types/api'
import { formatBytes } from '../lib/view-models'
import styles from './ResultArchive.module.css'

type ResultArchiveProps = {
  result: DetectionResult | null
  reportHistory?: EdgeReportHistoryItem[]
  selectedReportId?: string | null
  reportHistoryLoading?: boolean
  reportHistoryError?: string | null
  onSelectReport?: (reportId: string) => void
}

export function ResultArchive({
  result,
  reportHistory = [],
  selectedReportId = null,
  reportHistoryLoading = false,
  reportHistoryError = null,
  onSelectReport,
}: ResultArchiveProps) {
  if (!result) {
    return (
      <section className={styles.card}>
        <header className={styles.header}>
          <span className={styles.eyebrow}>RESULT ARCHIVE</span>
          <h2>结果归档</h2>
        </header>
        <div className={styles.emptyState}>
          <strong>等待首个完成任务</strong>
          <p>当前还没有可归档的检测结果。完成一次样本分析后，这里会显示压降摘要、威胁标签和五元组档案。</p>
        </div>
      </section>
    )
  }

  const completedAt = new Date(result.meta.timestamp).toLocaleString('zh-CN', {
    hour12: false,
  })
  const threatCount = result.statistics.anomaly_flows_detected
  const hasThreatDetails = result.threats.length > 0
  const archiveStatus = threatCount === 0 ? '已归档' : '待复核'
  const centralReporting = result.meta.central_reporting ?? null

  return (
    <section className={styles.card}>
      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>RESULT ARCHIVE</span>
          <h2>结果归档</h2>
        </div>
        <div className={styles.summaryPill}>
          <span>任务编号</span>
          <strong>{result.meta.task_id}</strong>
        </div>
      </header>

      <section className={styles.summarySection} aria-label="归档总览">
        <div className={styles.sectionHeading}>
          <span className={styles.sectionEyebrow}>ARCHIVE SUMMARY</span>
          <h3>归档总览</h3>
        </div>

        <div className={styles.metrics}>
          <div className={styles.metricCard}>
            <span>归档状态</span>
            <strong>{archiveStatus}</strong>
          </div>
          <div className={styles.metricCard}>
            <span>异常威胁</span>
            <strong>{threatCount}</strong>
          </div>
          <div className={styles.metricCard}>
            <span>完成时间</span>
            <strong>{completedAt}</strong>
          </div>
        </div>
      </section>

      <div className={styles.metrics}>
        <div className={styles.metricCard}>
          <span>带宽压降</span>
          <strong>{result.metrics.bandwidth_saved_percent.toFixed(1)}%</strong>
        </div>
        <div className={styles.metricCard}>
          <span>异常检出</span>
          <strong>{result.statistics.anomaly_flows_detected}</strong>
        </div>
        <div className={styles.metricCard}>
          <span>处理耗时</span>
          <strong>{(result.meta.processing_time_ms / 1000).toFixed(2)}s</strong>
        </div>
      </div>

      <section className={styles.summarySection} aria-label="中心上报">
        <div className={styles.sectionHeading}>
          <span className={styles.sectionEyebrow}>CENTRAL REPORTING</span>
          <h3>中心上报</h3>
        </div>

        <div className={styles.metrics}>
          <div className={styles.metricCard}>
            <span>状态</span>
            <strong>{centralReporting?.status ?? '未提供上送状态'}</strong>
          </div>
          <div className={styles.metricCard}>
            <span>中心报告 ID</span>
            <strong>{centralReporting?.central_report_id ?? '暂无'}</strong>
          </div>
          <div className={styles.metricCard}>
            <span>目标地址</span>
            <strong>{centralReporting?.central_url ?? '暂无'}</strong>
          </div>
        </div>

        {centralReporting?.error && (
          <div className={styles.emptyState}>
            <strong>上报异常</strong>
            <p>{centralReporting.error}</p>
          </div>
        )}
      </section>

      <section className={styles.summarySection} aria-label="历史报告">
        <div className={styles.sectionHeading}>
          <span className={styles.sectionEyebrow}>REPORT HISTORY</span>
          <h3>历史报告</h3>
        </div>

        {reportHistoryLoading && <div className={styles.emptyState}>历史报告加载中...</div>}
        {reportHistoryError && <div className={styles.emptyState}>{reportHistoryError}</div>}
        {!reportHistoryLoading && !reportHistoryError && reportHistory.length === 0 && (
          <div className={styles.emptyState}>
            <strong>暂无历史报告</strong>
            <p>当前 edge 还没有可切换的归档记录。</p>
          </div>
        )}
        {!reportHistoryLoading && !reportHistoryError && reportHistory.length > 0 && (
          <div className={styles.historyList}>
            {reportHistory.map((report) => {
              const active = report.report_id === selectedReportId
              return (
                <button
                  key={report.report_id}
                  type="button"
                  className={`${styles.historyCard} ${active ? styles.historyCardActive : ''}`}
                  onClick={() => onSelectReport?.(report.report_id)}
                >
                  <strong>{report.report_id}</strong>
                  <span>{report.summary.headline}</span>
                  <span>风险 {report.summary.risk_level}</span>
                  <span>威胁 {report.summary.threat_count}</span>
                </button>
              )
            })}
          </div>
        )}
      </section>

      <div className={styles.sizeGrid}>
        <div className={styles.sizeCard}>
          <span>原始 Pcap</span>
          <strong>{formatBytes(result.metrics.original_pcap_size_bytes)}</strong>
        </div>
        <div className={styles.sizeCard}>
          <span>JSON 输出</span>
          <strong>{formatBytes(result.metrics.json_output_size_bytes)}</strong>
        </div>
        <div className={styles.sizeCard}>
          <span>压降倍数</span>
          <strong>{result.statistics.bandwidth_reduction}</strong>
        </div>
      </div>

      <section className={styles.threatSection} aria-label="威胁证据">
        <div className={styles.sectionHeading}>
          <span className={styles.sectionEyebrow}>THREAT EVIDENCE</span>
          <h3>威胁证据</h3>
        </div>

        <div className={styles.threatList}>
        {threatCount === 0 ? (
          <div className={styles.emptyThreats}>
            <strong>零威胁归档</strong>
            <p>本次样本未检测到异常候选，结果已按正常档案归档。</p>
          </div>
        ) : !hasThreatDetails ? (
          <div className={styles.emptyThreats}>
            <strong>威胁明细待补充</strong>
            <p>已检出异常，但当前结果未返回详细威胁记录。</p>
          </div>
        ) : (
          result.threats.map((threat) => (
            <article key={threat.id} className={styles.threatCard}>
              <div className={styles.threatHeader}>
                <div>
                  <strong>{threat.classification.primary_label}</strong>
                  <span>{threat.classification.secondary_label}</span>
                </div>
                <span>{(threat.classification.confidence * 100).toFixed(0)}%</span>
              </div>

              <div className={styles.tupleGrid}>
                <div>
                  <span>源 IP</span>
                  <strong>{threat.five_tuple.src_ip}</strong>
                </div>
                <div>
                  <span>源端口</span>
                  <strong>{threat.five_tuple.src_port}</strong>
                </div>
                <div>
                  <span>目标 IP</span>
                  <strong>{threat.five_tuple.dst_ip}</strong>
                </div>
                <div>
                  <span>目标端口</span>
                  <strong>{threat.five_tuple.dst_port}</strong>
                </div>
                <div>
                  <span>协议</span>
                  <strong>{threat.five_tuple.protocol}</strong>
                </div>
                <div>
                  <span>Token</span>
                  <strong>{threat.token_info.token_count}</strong>
                </div>
                <div>
                  <span>包数量</span>
                  <strong>{threat.flow_metadata.packet_count}</strong>
                </div>
                <div>
                  <span>流量字节</span>
                  <strong>{formatBytes(threat.flow_metadata.byte_count)}</strong>
                </div>
              </div>
            </article>
          ))
        )}
        </div>
      </section>
    </section>
  )
}
