import type { DetectionResult } from '../types/api'
import styles from './ResultDashboard.module.css'

interface ResultDashboardProps {
  result: DetectionResult | null
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function ResultDashboard({ result }: ResultDashboardProps) {
  if (!result) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>
          <span className={styles.emptyEyebrow}>Result Archive</span>
          <h3 className={styles.emptyTitle}>结果面板正在等待第一份样本</h3>
          <p className={styles.emptyText}>
            上传后这里会生成四块信息: 统计摘要、压降结果、异常标签，以及可疑流的五元组档案。
          </p>
        </div>
      </div>
    )
  }

  const { statistics, threats, metrics } = result
  const threatLevel = threats.length > 0 ? '高风险样本' : '未见异常'
  const savedPercent = metrics.bandwidth_saved_percent.toFixed(1)

  return (
    <div className={styles.container}>
      <div className={styles.summaryHero}>
        <div>
          <span className={styles.eyebrow}>Result Archive</span>
          <h3 className={styles.title}>{threatLevel}</h3>
          <p className={styles.summaryText}>
            已完成 {statistics.total_flows} 条流的筛查，SVM 过滤率 {statistics.svm_filter_rate}，最终归档 {threats.length} 条异常候选。
          </p>
        </div>

        <div className={styles.summaryMeta}>
          <div>
            <span className={styles.metaLabel}>任务编号</span>
            <strong>{result.meta.task_id}</strong>
          </div>
          <div>
            <span className={styles.metaLabel}>处理耗时</span>
            <strong>{(result.meta.processing_time_ms / 1000).toFixed(2)}s</strong>
          </div>
        </div>
      </div>

      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{statistics.total_packets.toLocaleString()}</div>
          <div className={styles.statLabel}>总数据包</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{statistics.total_flows}</div>
          <div className={styles.statLabel}>总流数</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{statistics.normal_flows_dropped}</div>
          <div className={styles.statLabel}>已丢弃正常流</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{statistics.anomaly_flows_detected}</div>
          <div className={styles.statLabel}>检测到异常</div>
        </div>
      </div>

      <div className={styles.dualPanel}>
        <section className={styles.panelCard}>
          <div className={styles.sectionTitle}>带宽压降效果</div>
          <div className={styles.comparison}>
            <div className={styles.sizeBlock}>
              <div className={styles.sizeLabel}>原始 Pcap</div>
              <div className={`${styles.sizeBar} ${styles.originalBar}`}>
                {formatBytes(metrics.original_pcap_size_bytes)}
              </div>
            </div>
            <span className={styles.arrow}>→</span>
            <div className={styles.sizeBlock}>
              <div className={styles.sizeLabel}>JSON 输出</div>
              <div className={`${styles.sizeBar} ${styles.compressedBar}`}>
                {formatBytes(metrics.json_output_size_bytes)}
              </div>
            </div>
          </div>
        </section>

        <section className={styles.panelCard}>
          <div className={styles.sectionTitle}>归档摘要</div>
          <div className={styles.summaryList}>
            <div className={styles.summaryItem}>
              <span>节省带宽</span>
              <strong>{savedPercent}%</strong>
            </div>
            <div className={styles.summaryItem}>
              <span>带宽压降</span>
              <strong>{statistics.bandwidth_reduction}</strong>
            </div>
            <div className={styles.summaryItem}>
              <span>模型版本</span>
              <strong>{threats[0]?.classification.model ?? result.meta.agent_version}</strong>
            </div>
          </div>
        </section>
      </div>

      <div className={styles.threatsSection}>
        <div className={styles.sectionTitle}>威胁详情 ({threats.length})</div>

        {threats.length === 0 && (
          <div className={styles.cleanState}>
            当前样本未识别到异常流量，结果已按正常档案归档。
          </div>
        )}

        {threats.map((threat) => {
          const confidence = `${(threat.classification.confidence * 100).toFixed(0)}%`

          return (
            <div key={threat.id} className={styles.threatCard}>
              <div className={styles.threatHeader}>
                <div className={styles.threatLabel}>
                  <span className={styles.primaryLabel}>
                    {threat.classification.primary_label}
                  </span>
                  <span className={styles.secondaryLabel}>
                    {threat.classification.secondary_label}
                  </span>
                </div>
                <span className={styles.confidence}>{confidence} 置信度</span>
              </div>

              <div className={styles.confidenceTrack}>
                <div
                  className={styles.confidenceFill}
                  style={{ width: confidence }}
                />
              </div>

              <div className={styles.fiveTuple}>
                <div className={styles.tupleItem}>
                  <div>源 IP</div>
                  <div className={styles.tupleValue}>{threat.five_tuple.src_ip}</div>
                </div>
                <div className={styles.tupleItem}>
                  <div>源端口</div>
                  <div className={styles.tupleValue}>{threat.five_tuple.src_port}</div>
                </div>
                <div className={styles.tupleItem}>
                  <div>目标 IP</div>
                  <div className={styles.tupleValue}>{threat.five_tuple.dst_ip}</div>
                </div>
                <div className={styles.tupleItem}>
                  <div>目标端口</div>
                  <div className={styles.tupleValue}>{threat.five_tuple.dst_port}</div>
                </div>
                <div className={styles.tupleItem}>
                  <div>协议</div>
                  <div className={styles.tupleValue}>{threat.five_tuple.protocol}</div>
                </div>
              </div>

              <div className={styles.metaGrid}>
                <div>
                  <span>包数</span>
                  <strong>{threat.flow_metadata.packet_count}</strong>
                </div>
                <div>
                  <span>字节数</span>
                  <strong>{formatBytes(threat.flow_metadata.byte_count)}</strong>
                </div>
                <div>
                  <span>平均包长</span>
                  <strong>{Math.round(threat.flow_metadata.avg_packet_size)} B</strong>
                </div>
                <div>
                  <span>Token</span>
                  <strong>
                    {threat.token_info.token_count}
                    {threat.token_info.truncated ? ' / 截断' : ''}
                  </strong>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
