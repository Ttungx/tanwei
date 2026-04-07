import styles from '../App.module.css'
import type { AppSection } from './SidebarNav'

type TopbarProps = {
  activeSection: AppSection
  statusLabel: string
  detailLabel: string
  selectedEdgeId: string | null
  onShowEdge: () => void
  onShowCentral: () => void
  onReset: () => void
}

const SECTION_COPY: Record<AppSection, { title: string; detail: string }> = {
  overview: {
    title: 'Console Control Plane',
    detail: '统一查看边缘检测链路、结构化情报归档和中心侧分析结果。',
  },
  edge: {
    title: 'Edge-Agent Workspace',
    detail: '提交 pcap、跟踪流重组/SVM/LLM 阶段，并观察带宽压降结果。',
  },
  central: {
    title: 'Central-Agent Intelligence',
    detail: '按 edge1、edge2 等编号查看上报情报，并手动触发单 Edge 或全网综合研判。',
  },
}

export function Topbar({
  activeSection,
  statusLabel,
  detailLabel,
  selectedEdgeId,
  onShowEdge,
  onShowCentral,
  onReset,
}: TopbarProps) {
  const sectionCopy = SECTION_COPY[activeSection]

  return (
    <header className={styles.topbar}>
      <div className={styles.topbarCopy}>
        <span className={styles.topbarEyebrow}>Tanwei Console</span>
        <h2 className={styles.topbarTitle}>{sectionCopy.title}</h2>
        <p className={styles.topbarDetail}>{sectionCopy.detail}</p>
      </div>

      <div className={styles.topbarStatus}>
        <span className={styles.statusLabel}>运行状态</span>
        <strong>{statusLabel}</strong>
        <span>{detailLabel}</span>
        <span>{selectedEdgeId ? `当前边缘：${selectedEdgeId}` : '当前未选中 edge'}</span>
      </div>

      <div className={styles.topbarActions}>
        <button type="button" className={styles.secondaryAction} onClick={onShowEdge}>
          Edge 控制
        </button>
        <button type="button" className={styles.secondaryAction} onClick={onShowCentral}>
          Central 控制
        </button>
        <button type="button" className={styles.primaryAction} onClick={onReset}>
          刷新视图
        </button>
      </div>
    </header>
  )
}
