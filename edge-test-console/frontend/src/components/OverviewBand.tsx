import { buildOverviewViewModel } from '../lib/view-models'
import styles from '../App.module.css'

type OverviewBandProps = {
  viewModel: ReturnType<typeof buildOverviewViewModel>
}

export function OverviewBand({ viewModel }: OverviewBandProps) {
  return (
    <section className={styles.overviewBand} aria-labelledby="overview-band-title">
      <div className={styles.overviewHero}>
        <div className={styles.sectionIntro}>
          <span className={styles.sectionEyebrow}>Four-container Detection Flow</span>
          <h2 id="overview-band-title" className={styles.sectionTitle}>总览概况</h2>
          <p className={styles.sectionLead}>
            pcap 样本进入边缘侧后，先完成流重组和 SVM 预筛，再把异常候选交给 LLM 研判，并把压降收益写入威胁归档。
          </p>
        </div>

        <div className={styles.metricStrip}>
          {viewModel.evidenceCards.map((item) => (
            <article key={item.label} className={styles.metricTile}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </article>
          ))}
        </div>
      </div>

      <div className={styles.overviewGrid}>
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelEyebrow}>Four-container Flow</span>
            <h3>架构骨架</h3>
          </div>
          <div className={styles.stackList}>
            {viewModel.architectureCards.map((item) => (
              <article key={item.label} className={styles.stackCard}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <span className={styles.panelEyebrow}>Detection Roles</span>
            <h3>系统角色</h3>
          </div>
          <div className={styles.stackList}>
            {viewModel.systemCards.map((item) => (
              <article key={item.label} className={styles.stackCard}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  )
}
