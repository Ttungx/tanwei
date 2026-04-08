import type { DemoSample, DetectionResult, PipelineStage } from '../types/api'

export type AppState = 'idle' | 'uploading' | 'processing' | 'completed' | 'failed'

interface MetricCard {
  label: string
  value: string
}

interface PipelineItem {
  label: string
  detail: string
}

interface OverviewCard {
  label: string
  value: string
}

interface DemoSampleCard {
  id: string
  title: string
  meta: string
  filename: string
  selected: boolean
}

interface ConsoleViewModel {
  stateLabel: string
  heroMetrics: MetricCard[]
}

interface OverviewViewModel {
  evidenceCards: OverviewCard[]
  pipeline: PipelineItem[]
  architectureCards: OverviewCard[]
  systemCards: OverviewCard[]
}

interface ConsoleViewModelInput {
  appState: AppState
  stage: PipelineStage
  message: string
  result: DetectionResult | null
  error: string | null
}

const APP_STATE_LABEL: Record<AppState, string> = {
  idle: '待命',
  uploading: '上传中',
  processing: '分析中',
  completed: '已完成',
  failed: '异常终止',
}

const PIPELINE: PipelineItem[] = [
  {
    label: '等待处理',
    detail: '任务进入队列，准备接管样本。',
  },
  {
    label: '流重组',
    detail: '对原始包进行会话重建，准备进入筛选链路。',
  },
  {
    label: 'SVM 初筛',
    detail: '快速过滤大部分正常流量，压低后续推理成本。',
  },
  {
    label: 'LLM 推理',
    detail: '对异常候选进行语义分析与标签判定。',
  },
  {
    label: '结果归档',
    detail: '输出威胁档案、五元组和压降摘要。',
  },
]

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export function buildConsoleViewModel(input: ConsoleViewModelInput): ConsoleViewModel {
  if (!input.result) {
    return {
      stateLabel: APP_STATE_LABEL[input.appState],
      heroMetrics: [
        { label: '处理模式', value: '边缘侧预检' },
        { label: '分析链路', value: 'SVM + LLM' },
        { label: '输出目标', value: '威胁档案' },
      ],
    }
  }

  return {
    stateLabel: APP_STATE_LABEL[input.appState],
    heroMetrics: [
      { label: '异常流量', value: String(input.result.statistics.anomaly_flows_detected) },
      { label: '压降节省', value: `${input.result.metrics.bandwidth_saved_percent.toFixed(1)}%` },
      { label: '推理耗时', value: `${(input.result.meta.processing_time_ms / 1000).toFixed(2)}s` },
    ],
  }
}

export function buildDemoSampleCards(
  samples: DemoSample[],
  selectedId: string | null,
): DemoSampleCard[] {
  return samples.map((sample) => ({
    id: sample.id,
    title: sample.display_name,
    meta: formatBytes(sample.size_bytes),
    filename: sample.filename,
    selected: sample.id === selectedId,
  }))
}

const ARCHITECTURE_CARDS: OverviewCard[] = [
  { label: '四容器闭环', value: 'Console -> Edge Agent -> SVM / LLM' },
  { label: '推理策略', value: 'SVM 初筛 + LLM 精判' },
  { label: '输出形式', value: '威胁档案与压降摘要' },
]

export function buildOverviewViewModel(result: DetectionResult | null): OverviewViewModel {
  if (!result) {
    return {
      evidenceCards: [
        { label: '带宽压降', value: '等待首个样本' },
        { label: '异常检出', value: '完成任务后生成' },
        { label: '处理耗时', value: '完成任务后生成' },
      ],
      pipeline: PIPELINE,
      architectureCards: ARCHITECTURE_CARDS,
      systemCards: [
        { label: '交互入口', value: '前端控制台' },
        { label: '推理链路', value: 'SVM + LLM' },
        { label: '运行形态', value: '边缘检测工作台' },
      ],
    }
  }

  return {
    evidenceCards: [
      { label: '带宽压降', value: `${result.metrics.bandwidth_saved_percent.toFixed(1)}%` },
      {
        label: '异常检出',
        value: `${result.statistics.anomaly_flows_detected} / ${result.statistics.total_flows}`,
      },
      { label: '处理耗时', value: `${(result.meta.processing_time_ms / 1000).toFixed(2)}s` },
    ],
    pipeline: PIPELINE,
    architectureCards: ARCHITECTURE_CARDS,
    systemCards: [
      { label: '交互入口', value: '前端控制台' },
      { label: '后端协调', value: '任务状态轮询' },
      { label: '结果归档', value: '威胁档案输出' },
    ],
  }
}
