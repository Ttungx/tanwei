import type { DetectionResult } from '../types/api'
import { formatBytes } from '../lib/view-models'
import styles from './ResultArchive.module.css'

type ResultArchiveProps = {
  result: DetectionResult | null
}

export function ResultArchive({ result }: ResultArchiveProps) {
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

      <div className={styles.threatList}>
        {result.threats.length === 0 ? (
          <div className={styles.emptyThreats}>
            <strong>未见异常流量</strong>
            <p>本次样本未检测到异常候选，结果已按正常档案归档。</p>
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
                  <span>目标 IP</span>
                  <strong>{threat.five_tuple.dst_ip}</strong>
                </div>
                <div>
                  <span>协议</span>
                  <strong>{threat.five_tuple.protocol}</strong>
                </div>
                <div>
                  <span>Token</span>
                  <strong>{threat.token_info.token_count}</strong>
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  )
}
