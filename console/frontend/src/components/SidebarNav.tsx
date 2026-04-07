import styles from '../App.module.css'

export type AppSection = 'overview' | 'workspace' | 'archive'

type SidebarNavProps = {
  activeSection: AppSection
  onSelectSection: (section: AppSection) => void
  statusLabel: string
}

const ITEMS: Array<{ id: AppSection; label: string; note: string }> = [
  { id: 'overview', label: '系统总览', note: '四容器流转与压降概览' },
  { id: 'workspace', label: '检测工作台', note: '样本接入与阶段过滤' },
  { id: 'archive', label: '威胁归档', note: '异常标签与五元组记录' },
]

export function SidebarNav({ activeSection, onSelectSection, statusLabel }: SidebarNavProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brandBlock}>
        <span className={styles.brandEyebrow}>EDGE TEST CONSOLE</span>
        <h1 className={styles.brandTitle}>探微控制台</h1>
        <p className={styles.brandText}>边缘侧接收 pcap 样本，经过分阶段过滤后输出带宽压降摘要与威胁档案。</p>
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
        <span className={styles.sidebarBadge}>DESKTOP SHELL</span>
        <strong className={styles.sidebarValue}>{statusLabel}</strong>
      </div>
    </aside>
  )
}
