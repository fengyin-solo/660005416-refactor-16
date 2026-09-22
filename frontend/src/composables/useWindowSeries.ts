import { computed, type ComputedRef } from 'vue'
import { useLogStore } from '../store/log'
import type { AnomalyScore, TimeWindow } from '../types'

/**
 * 两个面板共用的“按窗口”序列：
 *
 * 接口返回的 windows / anomalies 只在这里对齐、映射一遍，
 * 异常分数面板与窗口日志量面板都从同一份 WindowPoint[] 取值，
 * 窗口序号统一按数组下标对齐（anomalies 按 windowIndex 归位，
 * 而不是各自再按日志条数推算）。
 */
export interface WindowPoint {
  /** 窗口序号：窗口数组下标，两处面板共用同一口径 */
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

export interface WindowSeries {
  points: WindowPoint[]
  labels: string[]
  counts: number[]
  sigmaScores: number[]
  iqrScores: number[]
  anomalies: AnomalyScore[]
}

/** 模块级单例：同一份接口结果只做一次映射，两个面板共享同一计算缓存 */
let cachedSeries: ComputedRef<WindowSeries> | null = null

function buildSeries(windows: TimeWindow[], anomalies: AnomalyScore[]): WindowSeries {
  // 分数只从 anomalies 取一次，按 windowIndex 归到窗口数组下标
  const scoreByIndex = new Map<number, AnomalyScore>()
  for (const a of anomalies) scoreByIndex.set(a.windowIndex, a)

  const points: WindowPoint[] = windows.map((w, index) => {
    const score = scoreByIndex.get(index)
    return {
      index,
      label: 'W' + index,
      count: w.count,
      start: w.start,
      end: w.end,
      sigmaScore: score?.sigmaScore ?? 0,
      iqrScore: score?.iqrScore ?? 0,
      isAnomaly: score?.isAnomaly ?? false,
      timestamp: score?.timestamp ?? ''
    }
  })

  return {
    points,
    labels: points.map(p => p.label),
    counts: points.map(p => p.count),
    sigmaScores: points.map(p => p.sigmaScore),
    iqrScores: points.map(p => p.iqrScore),
    anomalies
  }
}

export function useWindowSeries(): ComputedRef<WindowSeries> {
  if (cachedSeries) return cachedSeries
  const store = useLogStore()
  const series = computed<WindowSeries>(() => {
    const result = store.result
    if (!result) {
      return { points: [], labels: [], counts: [], sigmaScores: [], iqrScores: [], anomalies: [] }
    }
    return buildSeries(result.windows, result.anomalies)
  })
  cachedSeries = series
  return series
}
