import type { AnalysisResult, TimeWindow, AnomalyScore } from '../types'

/**
 * 异常分数面板与窗口日志量面板的共用口径。
 *
 * 两个面板以前各写一套：异常分数按 anomalies 的 windowIndex（数组下标）取轴，
 * 窗口日志量自己用数组位置推算窗口序号。这里统一成同一份配对后的窗口序列，
 * 分数只映射一次（按数组下标一一对应，不再做第二次推算）。
 */
export interface WindowSeriesPoint {
  index: number
  label: string
  count: number
  start: number
  end: number
  sigmaScore: number
  iqrScore: number
  isAnomaly: boolean
  timestamp: string
}

export function windowLabel(index: number): string {
  return 'W' + index
}

/**
 * 按数组下标把 windows 与 anomalies 配对成一份窗口序列。
 * 分数来自接口返回的 anomalies（后端只计算一次），这里不再重算，
 * 仅在缺少对应分数记录时回退到零值，保证面板取值口径一致。
 */
export function buildWindowSeries(result: AnalysisResult | null): WindowSeriesPoint[] {
  if (!result) return []
  return result.windows.map((w: TimeWindow, i: number) => {
    const a: AnomalyScore | undefined = result.anomalies[i]
    return {
      index: i,
      label: windowLabel(i),
      count: w.count,
      start: w.start,
      end: w.end,
      sigmaScore: a ? a.sigmaScore : 0,
      iqrScore: a ? a.iqrScore : 0,
      isAnomaly: a ? a.isAnomaly : false,
      timestamp: a ? a.timestamp : ''
    }
  })
}
