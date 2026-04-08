import styles from '../App.module.css'

export type AppSection = 'overview' | 'workspace' | 'archive'

type SidebarNavProps = {
  activeSection: AppSection
  onSelectSection: (section: AppSection) => void
  statusLabel: string
}

const ITEMS: Array<{ id: AppSection; label: string; note: string }> = [
  { id: 'overview', label: '系统总览', note: '查看三层架构、KPI 与运行边界。' },
  { id: 'workspace', label: '检测工作台', note: '上传 pcap、跟踪 edge-agent 检测任务。' },
  { id: 'archive', label: '威胁归档', note: '复盘异常标签、五元组记录与压降结果。' },
]

export function SidebarNav({ activeSection, onSelectSection, statusLabel }: SidebarNavProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brandBlock}>
        <span className={styles.brandEyebrow}>CONSOLE CONTROL PLANE</span>
        <h1 className={styles.brandTitle}>探微控制台</h1>
        <p className={styles.brandText}>
          统一管理 edge-agent 本地检测与 central-agent 中心研判，坚持只上传结构化 JSON 情报。
        </p>
      </div>

      <nav className={styles.nav} aria-label="主导航">
        {ITEMS.map((item) => {
          const active = item.id === activeSection

          return (
            <button
              key={item.id}
              type="button"
              className={`${styles.navItem} ${active ? styles.navItemActive : ''}`}
              aria-label={item.label}
              aria-current={active ? 'page' : undefined}
              onClick={() => onSelectSection(item.id)}
            >
              <span className={styles.navLabel}>{item.label}</span>
              <span className={styles.navNote}>{item.note}</span>
            </button>
          )
        })}
      </nav>

      <div className={styles.sidebarFooter}>
        <span className={styles.sidebarBadge}>ADMIN STATUS</span>
        <strong className={styles.sidebarValue}>{statusLabel}</strong>
      </div>
    </aside>
  )
}
