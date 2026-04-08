import styles from '../App.module.css'
import type { AppSection } from './SidebarNav'

type TopbarProps = {
  activeSection: AppSection
  statusLabel: string
  stageLabel: string
  taskId: string | null
  onArchive: () => void
  onReset: () => void
  onWorkspace: () => void
}

const SECTION_COPY: Record<AppSection, { title: string; detail: string }> = {
  overview: {
    title: '边缘检测总览',
    detail: '查看 pcap 检测链路、结构化情报归档和当前任务状态。',
  },
  workspace: {
    title: '检测工作台',
    detail: '提交 pcap、跟踪流重组/SVM/LLM 阶段，并观察带宽压降结果。',
  },
  archive: {
    title: '威胁归档',
    detail: '复盘异常标签、五元组记录与带宽压降结果。',
  },
}

export function Topbar({
  activeSection,
  statusLabel,
  stageLabel,
  taskId,
  onArchive,
  onReset,
  onWorkspace,
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
        <span>{stageLabel}</span>
        <span>{taskId ? `任务 ${taskId}` : '尚未创建任务'}</span>
      </div>

      <div className={styles.topbarActions}>
        <button type="button" className={styles.secondaryAction} onClick={onWorkspace}>
          前往检测工作台
        </button>
        <button type="button" className={styles.secondaryAction} onClick={onArchive}>
          查看威胁归档
        </button>
        <button type="button" className={styles.primaryAction} onClick={onReset}>
          重置工作台
        </button>
      </div>
    </header>
  )
}
